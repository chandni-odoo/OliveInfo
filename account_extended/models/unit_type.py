# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnitType(models.Model):
    _name = 'unit.type'
    _description = "Unit Type"

    name = fields.Char(string='Name', required="1")
    is_invoice = fields.Boolean(string="Is Invoice")

class ResCompany(models.Model):
    _inherit = 'res.company'

    bank_id = fields.Many2one('res.bank', string="Bank")

class Product(models.Model):
    _inherit = 'product.product'

    unit_type_id = fields.Many2one('unit.type', string="Unit")

