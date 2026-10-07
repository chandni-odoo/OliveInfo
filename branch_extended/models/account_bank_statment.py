# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.model
    def _prepare_liquidity_move_line_vals(self):
        res = super(AccountBankStatementLine, self)._prepare_liquidity_move_line_vals()
        res.update({'branch_id': self.branch_id.id})
        return res

    @api.model
    def _prepare_counterpart_move_line_vals(self, counterpart_vals, move_line=None):
        res = super(AccountBankStatementLine, self)._prepare_counterpart_move_line_vals(counterpart_vals, move_line=None)
        res.update({'branch_id': self.branch_id.id})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        res = super(AccountBankStatementLine, self).create(vals_list)
        for line in res.line_ids:
            for move in line.move_id:
                move.branch_id = line.branch_id.id
        return res
