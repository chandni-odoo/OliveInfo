# -*- coding: utf-8 -*-

from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = "stock.move"

    indent_line_id = fields.Many2one('indent.request.line', string='Indent Line')
