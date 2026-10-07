# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    custom_invoice_date = fields.Date(string="Received Date")

    # Delete invoice using update biiling status for cost plus
    def unlink(self):
        # self.line_ids.unlink()
        for move_line in self.invoice_line_ids:
            if move_line.cost_plus_line_id:
                move_line.cost_plus_line_id.sudo().write({'billing_status': False})
        return super(AccountMove, self).unlink()







