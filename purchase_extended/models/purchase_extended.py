# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from num2words import num2words


class Purchase(models.Model):
    _name = 'purchase.type'

    name = fields.Char(string='Purchase Name', required="1")
    purchase_type = fields.Selection([('capex', 'Capex'), ('opex', 'Opex'), ('small','Small'), ('other','Other')], default='other', string="Purchase Type")
    code = fields.Char(string="Code")

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_type = fields.Many2one('purchase.type',string="Purchase Type")
    order_by = fields.Char(string="Order Taken By")
    code = fields.Char(string="Code", related="partner_id.address_no")
    terms_id = fields.Many2one('terms.condition', string="Terms and Conditions", default=lambda self: self.env['terms.condition'].search([('condition_type', '=', 'purchase')], limit=1))

    @api.onchange('terms_id')
    def onchange_terms_id(self):
        self.notes = self.terms_id.description

    def convert_num_to_word(self):
        amount = sum(self.order_line.mapped('price_subtotal'))
        amount_in_words = self.currency_id.with_context(lang=self.partner_id.lang or 'es_ES').amount_to_text(
            amount).title()
        return amount_in_words

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    account_expense_id = fields.Many2one('account.account', string="Expense Account")

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        self.account_expense_id = self.product_id.categ_id.property_account_expense_categ_id or self.product_id.property_account_expense_id or False
        return res

class ResCompany(models.Model):
    _inherit = 'res.company'

    top_right = fields.Binary()
    bottom_left = fields.Binary()
    bottom_right = fields.Binary()
