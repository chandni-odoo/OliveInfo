from odoo import models, fields


class Recyclables(models.Model):
    _name = 'waste.recyclables'
    _description = 'Recyclables'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True
    )

    description = fields.Text(
        string='Description'
    )


class SkipLoader(models.Model):
    _inherit = 'skip.loader'

    recyclables_id = fields.Many2one(
        'waste.recyclables',
        string='Recyclables'
    )