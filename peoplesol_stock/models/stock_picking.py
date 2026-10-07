# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class StockPickingo(models.Model):
    _inherit = 'stock.picking'

    terms_id = fields.Many2one('terms.condition', string="Terms and Conditions", default=lambda self: self.env['terms.condition'].search([('condition_type', '=', 'picking')], limit=1))

    @api.onchange('terms_id')
    def onchange_terms_id(self):
        self.note = self.terms_id.description
