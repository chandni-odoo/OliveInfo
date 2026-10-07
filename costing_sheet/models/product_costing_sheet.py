from  datetime import date
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    costing_line_ids = fields.One2many('costing.sheet','costing_product_id')


class CostingSheet(models.Model):
    _name = "costing.sheet" 
    _description = "Costing Sheet"


    qty_price = fields.Integer(string="Price")
    costing_product_id = fields.Many2one('product.template','Costing')
    sequence = fields.Integer(default=10)
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")
    name = fields.Char(string="Sheet",required=True)