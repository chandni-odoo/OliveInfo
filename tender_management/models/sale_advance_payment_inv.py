from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoice(self, order, so_line, amount):
        invoice = super()._create_invoice(order, so_line, amount)
        return invoice

    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(
            self.env.context.get('active_ids', [])
        )

        # Check if any order is branch 2045 with billing_percent lines
        branch_2045_orders = sale_orders.filtered(
            lambda o: o.branch_id.code == '2045'
        )

        if branch_2045_orders:
            return self._create_tender_invoices(branch_2045_orders)

        return super().create_invoices()
    
    def _create_tender_invoices(self, orders):
        invoice_ids = []

        # Determine the reference date from wizard (inv_date) or today
        reference_date = self.inv_date or fields.Date.today()

        for order in orders:
            billing_lines = order.order_line.filtered(
                lambda l: l.billing_percent > 0 and l.selected_invoice_ids
            )

            normal_lines = order.order_line.filtered(
                lambda l: l.billing_percent <= 0
            )

            if not billing_lines:
                res = super().create_invoices()
                continue

            invoice_line_vals = []

            for sol in billing_lines:
                billing_percent = sol.billing_percent / 100.0

                # ── NEW: filter by same month/year as reference_date ──────────────
                month_filtered_invoices = sol.selected_invoice_ids.filtered(
                    lambda t: (
                        t.invoice_date
                        and t.invoice_date.month == reference_date.month
                        and t.invoice_date.year == reference_date.year
                    )
                )
                # ──────────────────────────────────────────────────────────────────

                # Then exclude already confirmed tender invoice lines
                eligible_invoices = month_filtered_invoices.filtered(
                    lambda t: not self.env['tender.invoice.line'].search([
                        ('invoice_id', '=', t.id),
                        ('is_confirm', '=', True)
                    ], limit=1)
                )

                if not eligible_invoices:
                    continue

                for tender_inv in eligible_invoices:
                    billed_amount = tender_inv.amount_total * billing_percent

                    invoice_line_vals.append((0, 0, {
                        'product_id': sol.product_id.id,
                        'name': (
                            f"{sol.name} @ {sol.billing_percent}% "
                            f"{tender_inv.partner_id.name} "
                            f"BILLS "
                            f"{tender_inv.invoice_date.strftime('%B %Y') if tender_inv.invoice_date else ''} "
                            f"({tender_inv.name})"
                        ).upper(),
                        'quantity': 1,
                        'price_unit': billed_amount,
                        'tax_ids': [(6, 0, sol.tax_id.ids)],
                        'sale_line_ids': [(4, sol.id)],
                        'account_id': self._get_invoice_account(sol),
                    }))

            # Add normal sale order lines with billing_percent = 0
            for sol in normal_lines:
                invoice_line_vals.append((0, 0, {
                    'product_id': sol.product_id.id,
                    'name': sol.name,
                    'quantity': sol.product_uom_qty,
                    'product_uom_id': sol.product_uom.id,
                    'price_unit': sol.price_unit,
                    'discount': sol.discount,
                    'tax_ids': [(6, 0, sol.tax_id.ids)],
                    'sale_line_ids': [(4, sol.id)],
                    'account_id': self._get_invoice_account(sol),
                }))

            if not invoice_line_vals:
                continue

            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': order.partner_id.id,
                'partner_shipping_id': order.partner_shipping_id.id,
                'currency_id': order.currency_id.id,
                'invoice_origin': order.name,
                'invoice_date': reference_date,
                'branch_id': order.branch_id.id,
                'invoice_line_ids': invoice_line_vals,
                'fiscal_position_id': order.fiscal_position_id.id,
                'invoice_payment_term_id': order.payment_term_id.id,
                'narration': order.note,
            }

            invoice = self.env['account.move'].sudo().create(invoice_vals)
            invoice_ids.append(invoice.id)

        if not invoice_ids:
            return super().create_invoices()

        if self.env.context.get('open_invoices'):
            return {
                'type': 'ir.actions.act_window',
                'name': _('Invoices'),
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', invoice_ids)],
                'target': 'current',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': invoice_ids[0],
            'view_mode': 'form',
            'target': 'current',
        }
    

    # def _create_tender_invoices(self, orders):
    #     """
    #     Create invoices for branch 2045 orders.
    #     For each sale order line with billing_percent > 0 and selected_invoice_ids,
    #     create invoice lines referencing those tender invoices.
    #     """
    #     invoice_ids = []

    #     for order in orders:
    #         billing_lines = order.order_line.filtered(
    #             lambda l: l.billing_percent > 0 and l.selected_invoice_ids
    #         )

    #         normal_lines = order.order_line.filtered(
    #             lambda l: l.billing_percent <= 0
    #         )

    #         if not billing_lines:
    #             # Fall back to normal invoice creation for this order
    #             res = super().create_invoices()
    #             continue

    #         # Group: one invoice per order
    #         invoice_line_vals = []

    #         for sol in billing_lines:
    #             billing_percent = sol.billing_percent / 100.0

    #             # for tender_inv in sol.selected_invoice_ids:
    #             for tender_inv in sol.selected_invoice_ids.filtered(lambda t: not self.env['tender.invoice.line'].search([
    #                 ('invoice_id', '=', t.id),
    #                 ('is_confirm', '=', True)
    #             ], limit=1)):
    #                 # Calculate amount based on billing percent of tender invoice
    #                 billed_amount = tender_inv.amount_total * billing_percent

    #                 invoice_line_vals.append((0, 0, {
    #                     'product_id': sol.product_id.id,
    #                     'name': (
    #                         f"{sol.name} @ {sol.billing_percent}% "
    #                         f"{tender_inv.partner_id.name} "
    #                         f"BILLS "
    #                         f"{tender_inv.invoice_date.strftime('%B %Y') if tender_inv.invoice_date else ''} "
    #                         f"({tender_inv.name})"
    #                     ).upper(),
    #                     'quantity': 1,
    #                     'price_unit': billed_amount,
    #                     'tax_ids': [(6, 0, sol.tax_id.ids)],
    #                     'sale_line_ids': [(4, sol.id)],
    #                     'account_id': self._get_invoice_account(sol),
    #                 }))

    #             # Add normal sale order lines with billing_percent = 0
    #             for sol in normal_lines:
    #                 invoice_line_vals.append((0, 0, {
    #                     'product_id': sol.product_id.id,
    #                     'name': sol.name,
    #                     'quantity': sol.product_uom_qty,
    #                     'product_uom_id': sol.product_uom.id,
    #                     'price_unit': sol.price_unit,
    #                     'discount': sol.discount,
    #                     'tax_ids': [(6, 0, sol.tax_id.ids)],
    #                     'sale_line_ids': [(4, sol.id)],
    #                     'account_id': self._get_invoice_account(sol),
    #                 }))

    #         if not invoice_line_vals:
    #             continue

    #         invoice_vals = {
    #             'move_type': 'out_invoice',
    #             'partner_id': order.partner_id.id,
    #             'partner_shipping_id': order.partner_shipping_id.id,
    #             'currency_id': order.currency_id.id,
    #             'invoice_origin': order.name,
    #             'invoice_date': self.inv_date or fields.Date.today(),
    #             'branch_id': order.branch_id.id,
    #             'invoice_line_ids': invoice_line_vals,
    #             'fiscal_position_id': order.fiscal_position_id.id,
    #             'invoice_payment_term_id': order.payment_term_id.id,
    #             'narration': order.note,
    #         }

    #         invoice = self.env['account.move'].sudo().create(invoice_vals)
    #         invoice_ids.append(invoice.id)

    #     if not invoice_ids:
    #         return super().create_invoices()

    #     # Return action based on button clicked
    #     if self.env.context.get('open_invoices'):
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'name': _('Invoices'),
    #             'res_model': 'account.move',
    #             'view_mode': 'tree,form',
    #             'domain': [('id', 'in', invoice_ids)],
    #             'target': 'current',
    #         }

    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': _('Invoice'),
    #         'res_model': 'account.move',
    #         'res_id': invoice_ids[0],
    #         'view_mode': 'form',
    #         'target': 'current',
    #     }

    def _get_invoice_account(self, sale_line):
        """Get the income account for the product on the sale line."""
        product = sale_line.product_id
        account = (
            product.property_account_income_id
            or product.categ_id.property_account_income_categ_id
        )
        if not account:
            raise UserError(
                _(
                    "No income account defined for product '%s'.\n"
                    "Please configure it on the product or its category."
                ) % product.name
            )
        return account.id