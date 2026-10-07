from odoo import models, fields

class AccountAccount(models.Model):
    _inherit = 'account.account'

    pl_group_id = fields.Many2one(
        'pl.group',
        string="P&L Group"
    )

    bs_group_id = fields.Many2one(
        'bs.group',
        string="BS Group"
    )