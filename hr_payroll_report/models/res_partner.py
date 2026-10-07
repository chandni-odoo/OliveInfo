from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    legal_case = fields.Boolean(string="Under Legal Case", tracking=True)
