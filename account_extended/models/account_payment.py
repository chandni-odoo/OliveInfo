from odoo import api, fields, models, _
from datetime import date


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    receipt_date = fields.Date(string="Receipt date", default=fields.Date.today())
    residual_amount = fields.Float("Residual Amount", compute="_compute_resdual_amount")

    @api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency', 'move_id.line_ids.account_id')
    def _compute_resdual_amount(self):
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
            reconcile_lines = (counterpart_lines + writeoff_lines).filtered(lambda line: line.account_id.reconcile)
            pay.residual_amount = sum(reconcile_lines.mapped('amount_residual'))
