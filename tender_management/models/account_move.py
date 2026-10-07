from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'


    def _get_month_matched_tender_lines(self, move, is_confirm):
        
        invoice_date = move.invoice_date or fields.Date.today()
        sale_lines = move.invoice_line_ids.mapped('sale_line_ids')
        result = self.env['tender.invoice.line']

        for sol in sale_lines:
            month_matched_invoices = sol.selected_invoice_ids.filtered(
                lambda t: (
                    t.invoice_date
                    and t.invoice_date.month == invoice_date.month
                    and t.invoice_date.year == invoice_date.year
                )
            )

            if not month_matched_invoices:
                continue

            tender_lines = self.env['tender.invoice.line'].search([
                ('invoice_id', 'in', month_matched_invoices.ids),
                ('is_confirm', '=', is_confirm)
            ])
            result |= tender_lines

        return result

    def action_post(self):
        res = super().action_post()

        for move in self:
            if (
                move.move_type == 'out_invoice'
                and move.branch_id.code == '2045'
                and move.state == 'posted'
            ):
                tender_lines = self._get_month_matched_tender_lines(
                    move, is_confirm=False
                )
                tender_lines.write({'is_confirm': True})

        return res

    def button_draft(self):
        """Reset is_confirm to False when invoice is reset to draft."""
        for move in self:
            if (
                move.move_type == 'out_invoice'
                and move.branch_id.code == '2045'
            ):
                tender_lines = self._get_month_matched_tender_lines(
                    move, is_confirm=True
                )
                tender_lines.write({'is_confirm': False})

        return super().button_draft()

    def unlink(self):
        """Reset is_confirm to False when invoice is deleted."""
        for move in self:
            if (
                move.move_type == 'out_invoice'
                and move.branch_id.code == '2045'
            ):
                tender_lines = self._get_month_matched_tender_lines(
                    move, is_confirm=True
                )
                tender_lines.write({'is_confirm': False})

        return super().unlink()

    # def action_post(self):
    #     res = super().action_post()

    #     for move in self:

    #         # Only branch 2045 customer invoices
    #         if (
    #             move.move_type == 'out_invoice'
    #             and move.branch_id.code == '2045'
    #             and move.state == 'posted'
    #         ):

    #             sale_lines = move.invoice_line_ids.mapped('sale_line_ids')

    #             for sol in sale_lines:

    #                 tender_lines = self.env['tender.invoice.line'].search([
    #                     ('invoice_id', 'in', sol.selected_invoice_ids.ids),
    #                     ('is_confirm', '=', False)
    #                 ])

    #                 tender_lines.write({
    #                     'is_confirm': True
    #                 })

    #     return res
    
    # def button_draft(self):
    #     """Reset is_confirm to False when invoice is reset to draft."""
    #     for move in self:
    #         if (
    #             move.move_type == 'out_invoice'
    #             and move.branch_id.code == '2045'
    #         ):
    #             sale_lines = move.invoice_line_ids.mapped('sale_line_ids')

    #             for sol in sale_lines:
    #                 tender_lines = self.env['tender.invoice.line'].search([
    #                     ('invoice_id', 'in', sol.selected_invoice_ids.ids),
    #                     ('is_confirm', '=', True)
    #                 ])
    #                 tender_lines.write({'is_confirm': False})

    #     return super().button_draft()

    # def unlink(self):
    #     """Reset is_confirm to False when invoice is deleted."""
    #     for move in self:
    #         if (
    #             move.move_type == 'out_invoice'
    #             and move.branch_id.code == '2045'
    #         ):
    #             sale_lines = move.invoice_line_ids.mapped('sale_line_ids')

    #             for sol in sale_lines:
    #                 tender_lines = self.env['tender.invoice.line'].search([
    #                     ('invoice_id', 'in', sol.selected_invoice_ids.ids),
    #                     ('is_confirm', '=', True)
    #                 ])
    #                 tender_lines.write({'is_confirm': False})

    #     return super().unlink()