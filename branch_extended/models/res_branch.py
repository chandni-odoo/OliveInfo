# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.osv import expression


class ResBranch(models.Model):
    _inherit = 'res.branch'

    code = fields.Char(string="Branch Code")
    branch_group_id = fields.Many2one('res.branch.group', string="Branch Group")
    branch_for = fields.Selection([('hro', 'HRO'), ('mro', 'MRO'), ('es', 'ES')], string='Branch For')
    sale_sequence_id = fields.Many2one('ir.sequence', string="Sale Sequence")

class BranchGroup(models.Model):
    _name = 'res.branch.group'
    _description = "Branch Group"

    name = fields.Char("Group Name", required=True)

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
        res = super(AccountBankStatementLine, self).create(vals_list)
        for line in res.line_ids.filtered(lambda x: x.move_id):
            line.move_id.branch_id = line.branch_id and line.branch_id.id
        return res

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        if self.branch_id:
            line_id = self.browse(self._origin.id)
            if line_id and line_id.move_id:
                line_id.move_id.write({'branch_id': self.branch_id.id})
                line_id.move_id.line_ids.write({'branch_id': self.branch_id.id})
