from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TenderInvoice(models.Model):
    _name = 'tender.invoice'
    _description = 'Tender Invoice'
    _rec_name = 'sale_line_id'

    sale_line_id = fields.Many2one(
        'sale.order.line',
        required=True,
        readonly=True
    )

    line_ids = fields.One2many(
        'tender.invoice.line',
        'tender_invoice_id'
    )

    valid_invoice_ids = fields.Many2many(
        'account.move',
        compute='_compute_valid_invoice_ids',
        string='Valid Invoices'
    )

    # @api.depends('sale_line_id')
    # def _compute_valid_invoice_ids(self):
    #     for rec in self:
    #         if not rec.sale_line_id:
    #             rec.valid_invoice_ids = False
    #             continue

    #         tender = rec.sale_line_id.order_id.opportunity_id.tender_id
    #         if not tender:
    #             rec.valid_invoice_ids = False
    #             continue

    #         invoices = self.env['account.move'].search([
    #             ('move_type', '=', 'out_invoice'),
    #             ('state', '=', 'posted'),
    #             ('branch_id.code', '!=', '2045'),
    #             (
    #                 'invoice_line_ids.sale_line_ids.order_id.opportunity_id.tender_id',
    #                 '=',
    #                 tender.id
    #             ),
    #         ])
    #         rec.valid_invoice_ids = invoices

    @api.depends('sale_line_id')
    def _compute_valid_invoice_ids(self):
        for rec in self:
            if not rec.sale_line_id:
                rec.valid_invoice_ids = False
                continue

            tender = rec.sale_line_id.order_id.opportunity_id.tender_id
            if not tender:
                rec.valid_invoice_ids = False
                continue

            # Get invoices already billed: those whose name appears in posted
            # branch 2045 invoice line descriptions (since you embed tender_inv.name
            # in the invoice line 'name' field inside _create_tender_invoices)
            posted_2045_invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('branch_id.code', '=', '2045'),
                ('invoice_line_ids.sale_line_ids.order_id.opportunity_id.tender_id', '=', tender.id),
            ])

            # Extract already billed tender invoice IDs from the posted 2045 invoice lines
            # In _create_tender_invoices you link: 'sale_line_ids': [(4, sol.id)]
            # So we can get the selected_invoice_ids from those sale lines
            already_billed_ids = posted_2045_invoices.mapped(
                'invoice_line_ids.sale_line_ids.selected_invoice_ids'
            ).ids

            invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('branch_id.code', '!=', '2045'),
                (
                    'invoice_line_ids.sale_line_ids.order_id.opportunity_id.tender_id',
                    '=',
                    tender.id
                ),
                ('id', 'not in', already_billed_ids),  # exclude already billed
            ])
            rec.valid_invoice_ids = invoices

    # @api.model
    # def default_get(self, fields_list):
    #     res = super().default_get(fields_list)

    #     sale_line_id = self.env.context.get('default_sale_line_id')
    #     if not sale_line_id:
    #         return res

    #     sale_line = self.env['sale.order.line'].browse(sale_line_id)
    #     if not sale_line.exists():
    #         return res

    #     res['sale_line_id'] = sale_line.id

    #     selected_invoices = sale_line.selected_invoice_ids
    #     if selected_invoices:
    #         res['line_ids'] = [
    #             (0, 0, {
    #                 'invoice_id': inv.id,
    #                 'customer_id': inv.partner_id.id,
    #                 'branch_id': inv.branch_id.id if inv.branch_id else False,
    #                 'invoice_date': inv.invoice_date,
    #                 'invoice_amount': inv.amount_total,
    #             }) for inv in selected_invoices
    #         ]

    #     return res

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        sale_line_id = self.env.context.get('default_sale_line_id')
        if not sale_line_id:
            return res

        sale_line = self.env['sale.order.line'].browse(sale_line_id)
        if not sale_line.exists():
            return res

        res['sale_line_id'] = sale_line.id

        selected_invoices = sale_line.selected_invoice_ids

        if selected_invoices:
            line_vals = []

            for inv in selected_invoices:

                # check already confirmed or not
                existing_line = self.env['tender.invoice.line'].search([
                    ('invoice_id', '=', inv.id),
                    ('is_confirm', '=', True)
                ], limit=1)

                line_vals.append((0, 0, {
                    'invoice_id': inv.id,
                    'customer_id': inv.partner_id.id,
                    'branch_id': inv.branch_id.id if inv.branch_id else False,
                    'invoice_date': inv.invoice_date,
                    'invoice_amount': inv.amount_total,
                    'is_confirm': existing_line.is_confirm if existing_line else False,
                }))

            res['line_ids'] = line_vals

        return res

    def action_apply(self):
        self.ensure_one()

        invoice_ids = self.line_ids.mapped('invoice_id')

        if not invoice_ids:
            raise UserError(_("Please select at least one invoice before applying."))

        self.sale_line_id.sudo().write({
            'selected_invoice_ids': [(6, 0, invoice_ids.ids)]
        })

        return {'type': 'ir.actions.act_window_close'}
    

class TenderInvoiceLine(models.Model):
    _name = 'tender.invoice.line'
    _description = 'Tender Invoice Line'

    tender_invoice_id = fields.Many2one(
        'tender.invoice',
        ondelete='cascade'
    )

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice Number',
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        readonly=True
    )
    branch_id = fields.Many2one(
        'res.branch',
        string='branch',
        readonly=True
    )

    invoice_date = fields.Date(
        string='Invoice Date',
        readonly=True
    )

    invoice_amount = fields.Float(
        string='Invoice Amount',
        readonly=True
    )

    is_confirm = fields.Boolean(
        string='Billed',
        readonly=True,
        default=False
    )
    

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        """Auto-fill all details when an invoice is selected."""
        if self.invoice_id:
            self.customer_id = self.invoice_id.partner_id.id
            self.branch_id = self.invoice_id.branch_id.id if self.invoice_id.branch_id else False
            self.invoice_date = self.invoice_id.invoice_date
            self.invoice_amount = self.invoice_id.amount_total
        else:
            self.customer_id = False
            self.branch_id = False
            self.invoice_date = False
            self.invoice_amount = 0.0
    