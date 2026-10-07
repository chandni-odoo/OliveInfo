# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import timedelta, datetime, time

class SaleAgreement(models.Model):
    _name = 'sale.agreement'
    _description = "Sale Agreement"

    name = fields.Char(default="New", readonly=True, copy=False)
    date_of_agreement = fields.Date(string="Agreement Date")
    sale_id = fields.Many2one('sale.order', string='Quotation Ref')
    attachment_id  = fields.Binary(string='Attachment')
    branch_id = fields.Many2one('res.branch', string="Branch")
    partner_id = fields.Many2one('res.partner', string="Customer")
    customer_id  = fields.Char(related="partner_id.address_no", string="Code")
    representative  = fields.Char(string="Representative")
    company_id = fields.Many2one('res.company', string="Company", readonly=True)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", required=True, readonly=False,
        string='Currency', help="Main currency of the company.")
    street = fields.Char('Street', readonly=True, store=True)
    street2 = fields.Char('Street2', readonly=True, store=True)
    zip = fields.Char('Zip', readonly=True, store=True)
    city = fields.Char('City', readonly=True, store=True)
    state_id = fields.Many2one(
        "res.country.state", string='State', readonly=True, store=True)
    country_id = fields.Many2one(
        'res.country', string='Country', readonly=True, store=True)
    # representative  = fields.Char(string="Representative")
    company_representative  = fields.Char(string="Representative")

    valid_from = fields.Many2one('agreement.validity',string="Agreement Validity",)
    valid_to = fields.Date(string="Agreement End Date")
    payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms")
    agreement_line_ids = fields.One2many('sale.agreement.line', 'agreement_id')
    tax_totals_json = fields.Char()
    food = fields.Boolean('Food')
    accommodation = fields.Boolean('Accommodation')
    transport = fields.Boolean('Transport')
    fat = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='FAT', readonly=True, default=True, compute="_compute_fat")
    sale_type = fields.Selection([('standard', 'Standard'), ('bundle', 'Bundle'), ('cost_plus', 'Cost Plus')], default='standard', string="Type")
    
    @api.depends('food', 'accommodation', 'transport')
    def _compute_fat(self):
        for rec in self:
            if rec.food or rec.accommodation or rec.transport:
                rec.fat = 'yes'
            else:
                rec.fat='no'

    @api.onchange('valid_from', 'date_of_agreement')
    def _onchange_date_to(self):
        if self.date_of_agreement:
            if self.valid_from.agreement_year == '1':
                self.valid_to = self.date_of_agreement + timedelta(days=365)
            if self.valid_from.agreement_year == '2':
                self.valid_to = self.date_of_agreement + timedelta(days=730)
        else:
            self.valid_to = False

    @api.model
    def create(self, vals):
        if vals.get('name', 'New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.agreement') or ('New')
        sale_id = self.env['sale.order'].browse(vals.get('sale_id'))
        if sale_id:
            sale_id.state = 'agreement'
        return super(SaleAgreement, self).create(vals)

class SaleAgreementLine(models.Model):
    _name = "sale.agreement.line"
    _description = "Sale Agreement Line"

    agreement_id  = fields.Many2one("sale.agreement")
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Text(string='Description', required=True)
    product_uom_qty = fields.Float(string='Quantity', required=True, default=1.0)
    period = fields.Integer(string="Period")
    duration = fields.Selection([('hour', 'Hour'), ('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year')], default='hour', string="Duration")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    contract_type= fields.Selection([('limited', 'Limited'), ('unlimited', 'Unlimited')], default='limited', string="Contract")
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
    agency_fee = fields.Selection([('fix', 'Fix'), ('percentage', 'Percentage')], default='fix', string="Agency Fee")
    sale_amount = fields.Float(string='Amount')
    overtime = fields.Float(string="Overtime")
    sp_overtime = fields.Float(string="Special Overtime")
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    price_subtotal = fields.Monetary(string='Subtotal')
    currency_id = fields.Many2one(related='agreement_id.currency_id', depends=['agreement_id.currency_id'], store=True, string='Currency')
    std_hrs = fields.Float(string="Std hrs")
    ot_hrs = fields.Float(string="OT hrs")


class CustomerRegion(models.Model):
    _name = 'agreement.validity'
    _description = "Agreement Validity"

    name = fields.Char(string="Agreement Valid", required=True)
    agreement_year = fields.Selection([('1', '1 Year'), ('2', '2 Year'), ('3,','3 Year'), ('4,','4 Year'), ('5,','5 Year')], default='1', string="Agreement Year")
