from odoo import models, fields, api, _


class OtherEarnings(models.Model):
    _inherit = 'other.earnings'
    
    cost_reference = fields.Char(string="Cost Plus Reference", readonly=True)
