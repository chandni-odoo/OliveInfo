from odoo import api, fields, models, _

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    branch_id = fields.Many2one('res.branch', string="Branch")
