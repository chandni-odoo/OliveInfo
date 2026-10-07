# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    onboarding_id = fields.Many2one('customer.onboarding.request')
    supplier_id = fields.Many2one('supplier.onboarding.request')
    address_no = fields.Char(string="Customer", readonly="1")
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    region_id = fields.Many2one('customer.region', string='Region')
    sector_id = fields.Many2one('customer.sector', string='Sector')
    location_id = fields.Many2one('hr.location', string='Location')
    grade_id = fields.Many2one('grade.type',string="Grade")
    segment_id = fields.Many2one('customer.segment',string="Segment")
    hold_option = fields.Selection([('all', 'All'), ('quote', 'Quote'), ('hold','Hold'), ('bill', 'Bill'), ('receipts', 'Receipts')], default='quote', string="Hold")
    hold_reason = fields.Char(string="Hold Reason")
    credit_block = fields.Selection([('yes', 'Yes'), ('no', 'No')], default='no', string='Credit Block')
    credit_facility = fields.Selection([('agree', 'Agreed Credit Facilit'), ('limit', 'Limit Amount')], default='limit', string='Credit Facility')
    credit_limit = fields.Float(string="Credit Limit") 
    ava_credit_bal = fields.Float(string='Available Credit Balance')

    ava_unbilled_bal = fields.Float(string='Total Unbilled Balance')

    credit_days = fields.Integer(default="30",string="Credit Days")
    credit_message = fields.Char(string="Credit Message")
    credit_manager = fields.Many2one('hr.employee', string="Credit Manager")
    collection_manager = fields.Many2one('hr.employee', string="Collection Manager")
    delivery_address = fields.Char(string='Bill Delivery Address')
    payment_instrument = fields.Selection([('cheque', 'Cheque'), ('cash', 'Cash'), ('wire_transfer', 'Wire Transfer'), ('cc', 'CC')], default='cash', string='Payment Instrument')
    billing_method = fields.Selection([('invoice', 'E-Invoice'), ('courier', 'Courier'), ('delivery', 'Delivery'), ('self service portal', 'Self Service Portal')], default='delivery', string='Billing Method')
    customer_profile = fields.Char(string="Customer Profile")
    parent_company = fields.Char(string="Parent Company")
    license_no = fields.Char(string="License No")
    issuing_authority = fields.Char(string="Issuing Authority")
    license_validity = fields.Date(string="License Validity")
    growth_rate = fields.Float(string="Growth Rate")
    annual_revenue = fields.Float(string="Annual Revenue")
    total_employees = fields.Integer(string="Total Employees")
    how_to_know = fields.Char(string="How to Know")
    acc_coordinator_id = fields.Many2one('hr.employee', string='Accounts Coordinator')
    sales_person_id= fields.Many2one('hr.employee', string='Sales Person')
    cs_coordinator_id = fields.Many2one('hr.employee' ,string="CS Coordinator")
    ope_coordinator_id = fields.Many2one('hr.employee', string="Operation Coordinator")
    initiated_id = fields.Many2one('hr.employee', string="Initiated By")
    lost_to = fields.Char(string='Lost To')
    comments = fields.Char(string='Comments')
    advance_coll = fields.Char(string='Advance Collected')
    security_deposite = fields.Char(string='Security Deposit Collected')
    contract_period = fields.Char(string='Contract Period')
    expected_sales  = fields.Integer(string='Expected Sales')
    agreement_ref = fields.Char(string='Agreement Reference')
    job_type_id = fields.Char(string='Job Type')
    add_no = fields.Char(readonly="1", string="Address Number")
    currency_id = fields.Many2one('res.currency', string='Currency')
    spe_payee_id = fields.Many2one('res.partner', string='Special Payee')
    hold_payment = fields.Selection([('yes', 'Yes'), ('no', 'No')], default='no', string='Hold Payment')
    hold_reason_id = fields.Many2one('hold.reason', string="Reason Of Hold") 
    parent = fields.Selection([('parent_vendor', 'Parent Vendor'),('customer', 'Customer')], default='parent_vendor', string='Parent')
    is_customer = fields.Boolean("Is Customer")
    is_supplier = fields.Boolean("Is Vendor")
    document_line_ids = fields.One2many('hr.document.line', 'partner_id')
    site_count = fields.Integer(compute='_site_count',)
    site_visit_count = fields.Integer(compute='_compute_site_visit_count', string='Site Visit')
    contact_type = fields.Selection(related="contract_type_id.contact_name")
    designation_id = fields.Many2one('hr.job',string="Designation")
    department_id = fields.Many2one('hr.department',string="Department")
    support_level = fields.Selection([('low', 'Low'), ('high', 'High'), ('medium,','Medium')], default='low', string="Support Level")
    marital_status = fields.Selection([('unmarried', 'Unmarried'), ('married', 'Merried'), ('divorced,','Divorced')], default='unmarried', string="Marital Status")
    anniversary_date = fields.Date(string="Anniversary Date")
    hobbies = fields.Char(string="Hobbies")
    date_of_birth = fields.Date(string="Date Of Birth")
    religion_id = fields.Many2one('ethinic.code', string="Religion")
    location = fields.Char(string="Location")
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice Address'),
         ('delivery', 'Delivery Address'),
         ('other', 'Location'),
         ("private", "Private Address"),
        ], string='Address Type',
        default='contact',
        help="Invoice & Delivery addresses are used in sales orders. Private addresses are only visible by authorized users.")
    computer_card = fields.Char(string="Computer Card")
    cc_validity = fields.Date(string='CC Validity')
    trade_license = fields.Char(string="Trade License")
    tl_validity = fields.Date(string='TL Validity')
    tax_card = fields.Char(string="Tax Card")
    tc_validity = fields.Date(string='TC Validity')
    sponsor_id = fields.Char(string="Sponsor ID")
    sid_validity = fields.Date(string='SID Validity')
    cr = fields.Char(string="CR")
    cr_validity = fields.Date(string='CR Validity')
    qid = fields.Char(string="QID")
    qid_validity= fields.Date(string='QID Validity')
    passport = fields.Char(string="Passport")
    passport_validity= fields.Date(string='Passport Validity')
    noc_sponsor = fields.Selection([('no','No'),('yes','Yes')],default="no",string="NOC from Sponsor")

    @api.onchange('contract_type_id')
    def _onchange_contract_type_id(self):
        if self.contract_type_id:
            if self.contract_type_id.contact_name == 'employee':
                self.is_customer = True

    def _site_count(self):
        for rec in self:
            rec.site_count = self.env['sale.site.inspection'].search_count([('company_id', '=', rec.id)])

    def site_inspection(self):
        sites = self.env['sale.site.inspection'].search([('company_id', '=', self.id)])
        return {
            'name': _('Site Inspection'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.site.inspection',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', sites.ids)],
        }
    def _compute_site_visit_count(self):
        for rec in self:
            rec.site_visit_count = self.env['site.visit'].search_count([('partner_id', '=', rec.id)])

    def open_site_visit(self):
        site_visit = self.env['site.visit'].search([('partner_id', '=', self.id)])
        return {
            'name': _('Site Visit'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'site.visit',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', site_visit.ids)],
        }
    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        if vals.get('is_company')==False and vals.get('company_id')!=False:
            if res.parent_id.is_customer == True:
                res.write({'customer_rank':1, 'is_customer':True})
            else:
                res.write({'customer_rank':0, 'is_customer':False})

            if res.parent_id.is_supplier == True:
                res.write({'supplier_rank':1, 'is_supplier':True})
            else:
                res.write({'supplier_rank':0, 'is_supplier':False})
        else:
            if vals.get('is_customer') == True:
                res.write({'customer_rank':1})
            elif vals.get('is_customer') == False:
                res.write({'customer_rank':0})

            if vals.get('is_supplier') == True:
                res.write({'supplier_rank':1})
            elif vals.get('is_supplier') == False:
                res.write({'supplier_rank':0})
        if vals.get('is_customer') or vals.get('is_supplier'):
            res['address_no'] = self.env['ir.sequence'].next_by_code('res.partner') or _('New')
        return res

    def write(self, vals):
        res = None
        for record in self:
            if vals.get('is_customer') and not record.address_no:
                vals['address_no'] = self.env['ir.sequence'].next_by_code('res.partner') or _('New')
                onboarding_id = self.env['customer.onboarding.request'].browse(vals.get('onboarding_id'))
                if onboarding_id:
                    onboarding_id.state = 'done'
                    onboarding_id.customer_id = vals['address_no']
            if vals.get('is_supplier') and not record.address_no:
                vals['address_no'] = self.env['ir.sequence'].next_by_code('res.partner') or _('New')
                supplier_id = self.env['supplier.onboarding.request'].browse(vals.get('supplier_id'))
                if supplier_id:
                    supplier_id.state = 'done'
                    supplier_id.customer_id = vals['address_no']
            if vals.get('is_customer') == True:
                vals.update({'customer_rank': 1})
                res = super(ResPartner,self).write(vals)
                if record.child_ids:
                    record.child_ids.write({'customer_rank': 1, 'is_customer': True})
            elif vals.get('is_customer') == False:
                vals.update({'customer_rank':0})
                res = super(ResPartner,self).write(vals)
                if record.child_ids:
                    record.child_ids.write({'customer_rank': 0, 'is_customer': False})
                
            if vals.get('is_supplier')==True:
                vals.update({'supplier_rank':1})
                res = super(ResPartner,self).write(vals)
                if record.child_ids:
                    record.child_ids.write({'supplier_rank':1,'is_supplier':True})
            elif vals.get('is_supplier')==False:
                vals.update({'supplier_rank':0})
                res = super(ResPartner,self).write(vals)
                if record.child_ids:
                    record.child_ids.write({'supplier_rank':0,'is_supplier':False})
        if res==None:
            res = super(ResPartner,self).write(vals)
        return res

    def name_get(self):
        res_list = []
        for rec in self:
            if rec.name and rec.address_no:
                res_list.append((rec.id,rec.name +' - ' + rec.address_no))
            else:
                res_list.append((rec.id, rec.name))
        return res_list

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = []
        if name:
            args = args + ['|', ('name', operator, name), ('address_no', operator, name)]
        res = super(ResPartner, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        partners = self.search(args)
        if name:
            res = list(set(res + partners.ids))

        return res


class ResPartnerCustom(models.Model):
    _name = 'res.partner.custom'
    _description = "Res Parent Custom"

    onboarding_id = fields.Many2one('customer.onboarding.request')
    supplier_id = fields.Many2one('supplier.onboarding.request')
    bank_id = fields.Many2one('res.bank', string="Bank")
    branch_id = fields.Many2one('res.bank.branch', string="Branch")
    account_no = fields.Char(string="Account Number")
