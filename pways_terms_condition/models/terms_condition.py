from odoo import api, models, fields, _

class TermsCondition(models.Model):
    _name = "terms.condition"
    _description = "Terms Condition"

    name = fields.Char(string="Name")
    condition_type = fields.Selection([('invoice', 'Invoice'), ('picking', 'Picking'), ('sale', 'Sales Order'), ('purchase', 'Purchase Order'), ('bill', 'Bills')], required=True)
    description = fields.Html(string="Description", translate=True)
