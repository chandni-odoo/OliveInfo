from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class TransferModel(models.Model):
    _inherit = "account.transfer.model"

    branch_id = fields.Many2one('res.branch', string="Branch")
    transfer_template_id = fields.Many2one('transfer.template', string="Transfer Template")

    @api.onchange('transfer_template_id')
    def onchange_transfer_template_id(self):
        destination_data = [(5,0,0)]
        if self.transfer_template_id:
            for destination in self.transfer_template_id.destination_account_ids:
                d_vals = {
                    'branch_id' : destination.branch_id.id,
                    'account_id' : destination.account_id.id,
                    'percent': destination.percent if destination.percent > 0 else 100,
                }
                destination_data.append((0, 0, d_vals))
            self.line_ids = destination_data
            self.account_ids = [(4, x) for x in self.transfer_template_id.origin_account_ids.mapped('account_id').ids]
            self.write({'branch_id': self.transfer_template_id.branch_id.id})
            self.account_ids.write({'branch_id': self.branch_id.id})

    @api.constrains('line_ids')
    def _check_line_ids_percent(self):
        for record in self.line_ids:
            if not (record.percent <= 100.0):
                raise ValidationError(_('The account (%s) percentage (%s) should be less or equal to 100 !', record.account_id.name, record.percent))


class TransferModelLine(models.Model):
    _inherit = "account.transfer.model.line"

    branch_id = fields.Many2one('res.branch', string="Branch")

    def _get_origin_account_transfer_move_line_values(self, origin_account, amount, is_debit, write_date):
        result = super(TransferModelLine, self)._get_origin_account_transfer_move_line_values(origin_account, amount, is_debit, write_date)
        result.update({
            'branch_id' : origin_account.branch_id.id,
        })
        return result

    def _get_destination_account_transfer_move_line_values(self, origin_account, amount, is_debit, write_date):
        result = super(TransferModelLine, self)._get_destination_account_transfer_move_line_values(origin_account, amount, is_debit, write_date)
        result.update({
            'branch_id': self.branch_id.id,
        })
        return result

class AccountAccount(models.Model):
    _inherit = "account.account"

    branch_id = fields.Many2one('res.branch', string="Branch")
