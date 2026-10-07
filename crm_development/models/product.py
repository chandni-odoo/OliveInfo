from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one(
        'product.brand',
        string='Brand',
        help='Select the product brand'
    )
    specification_attachment = fields.Many2many(
        'ir.attachment',
        string='Specification Documents',
        help='Attach specification documents here'
    )
    incoterm_ids = fields.Many2many(
        'account.incoterms',
        string='Incoterms'
    )

class ProductTemplate(models.Model):
    _inherit = 'product.product'

    brand_id = fields.Many2one(
        'product.brand',
        string='Brand',
        help='Select the product brand'
    )
    specification_attachment = fields.Many2many(
        'ir.attachment',
        string='Specification Documents',
        help='Attach specification documents here'
    )
    incoterm_ids = fields.Many2many(
        'account.incoterms',
        'product_incoterm_rel',
        'product_id',
        'incoterm_id',
        string='Incoterms'
    )

class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'

    name = fields.Char(string='Brand Name')
    code = fields.Char(string='Brand Code')
    description = fields.Text(string='Description')