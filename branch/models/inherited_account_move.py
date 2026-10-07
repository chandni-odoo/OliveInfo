# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'

    branch_id = fields.Many2one('res.branch', string="Branch")

    # @api.model
    # def default_get(self, default_fields):
    #     branch_id = False
    #     res = super(AccountMove, self).default_get(default_fields)
    #     if self._context.get('branch_id'):
    #         branch_id = self._context.get('branch_id')
    #     elif self.env.user.branch_id:
    #         branch_id = self.env.user.branch_id.id
    #     res.update({'branch_id' : branch_id})
    #     return res

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_branch = self.branch_id
        if selected_branch and self.invoice_line_ids and self.line_ids:
            if self.move_type in ['out_invoice', 'out_refund', 'out_receipt']:
                line_ids = self.line_ids.filtered(lambda x: x.account_id.user_type_id.type == 'receivable')
                line_ids.write({'branch_id': selected_branch.id})

            if self.move_type in ['in_invoice', 'in_refund', 'in_receipt']:
                line_ids = self.line_ids.filtered(lambda x: x.account_id.user_type_id.type == 'payable')
                line_ids.write({'branch_id': selected_branch.id})


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    branch_id = fields.Many2one('res.branch', string="Branch")

    # @api.model
    # def default_get(self, default_fields):
    #     res = super(AccountMoveLine, self).default_get(default_fields)
    #     if self._context.get('branch_id'):
    #         branch_id = self._context.get('branch_id')
    #     elif self.env.user.branch_id:
    #         branch_id = self.env.user.branch_id.id
    #     if self.move_id.branch_id:
    #         branch_id = self.move_id.branch_id.id
    #     res.update({'branch_id' : branch_id})
    #     return res

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        for vals in vals_list:
            move = self.env['account.move'].browse(vals['move_id'])
            if 'branch_id' not in vals or not vals.get('branch_id'):
                vals['branch_id'] = move.branch_id.id
        return super(AccountMoveLine, self).create(vals_list)
