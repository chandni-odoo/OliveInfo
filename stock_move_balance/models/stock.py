# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class StockMove(models.Model):
    _inherit = 'stock.move'
    
    def get_opening_balance(self):
        self.opening_balance = 0
        if self.date and self.product_id:
            product_ids = self.env['product.product'].with_context(to_date=self.date).search([
            ('type', '=', 'product'),('id', '=', self.product_id.id)])
            if len(product_ids.ids) > 0:
                self.opening_balance = product_ids.mapped('qty_available')[0]

    def get_closing_balance(self):
        self.closing_balance = 0
        if self.opening_balance or self.product_uom_qty:
            self.closing_balance = self.opening_balance + self.product_uom_qty 


    opening_balance = fields.Integer(string='Opening Balance', compute='get_opening_balance')
    closing_balance = fields.Integer(string='Closing Balance', compute='get_closing_balance')

