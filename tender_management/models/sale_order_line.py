from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    branch_code = fields.Char(
        related='branch_id.code',
        string='Branch Code',
        store=False
    )

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    billing_percent = fields.Float(string='Billing %')
    selected_invoice_ids = fields.Many2many(
        'account.move',
        string="Selected Invoices"
    )

    def action_open_tender_invoice(self):
        self.ensure_one()

        if self.order_id.branch_id.code != '2045':
            raise UserError(_("Invoice view allowed only for Branch 2045."))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Tender Invoices',
            'res_model': 'tender.invoice',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_line_id': self.id,
            }
        }
