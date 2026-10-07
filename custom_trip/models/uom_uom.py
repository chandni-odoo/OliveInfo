# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError


class UnitsOfMeasure(models.Model):
    _inherit = "uom.uom"

    lumpsum_check = fields.Boolean(string='Lumpsum Check')


class UOM(models.Model):
    _inherit = "uom.category"

    lumpsum_check = fields.Boolean(string='Lumpsum Check')
    