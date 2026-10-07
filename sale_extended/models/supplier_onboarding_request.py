# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SupplierOnboardingRequest(models.Model):
    _name = 'supplier.onboarding.request'
    _description = "Supplier Onboarding Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Supplier Onboarding Request"

    name = fields.Char(string='Name', default="New", readonly=True)
    designation_id = fields.Many2one('hr.job',string="Designation")
    department_id = fields.Many2one('hr.department',string="Department")
    phone = fields.Char(string="Phone Work")
    mobile = fields.Char(string="Mobile")
    email = fields.Char(string="Email")
    support_level = fields.Selection([('low', 'Low'), ('high', 'High'), ('medium,','Medium')], default='low', string="Support Level")
    marital_status = fields.Selection([('unmarried', 'Unmarried'), ('married', 'Merried'), ('divorced,','Divorced')], default='unmarried', string="Marital Status")
    anniversary_date = fields.Date(string="Anniversary Date")
    hobbies = fields.Char(string="Hobbies")
    date_of_birth = fields.Date(string="Date Of Birth")
    religion_id = fields.Many2one('ethinic.code', string="Religion")
    location = fields.Char(string="Location")
    website = fields.Char(string='Website')
    bank_id = fields.Many2one('res.bank', string="Bank Name")
    iban = fields.Char(string="IBAN")
    bank_account_no = fields.Char(string='Bank Account Number')
    swift_code = fields.Char(string='Swift Code')
    bank_country_id = fields.Many2one('res.country', string='Bank Country Code')
    bank_address = fields.Char(string='Bank Address')
    acc_coordinator_id = fields.Many2one('hr.employee', string='Accounts Coordinator')
    sales_person_id= fields.Many2one('hr.employee', string='Sales Person')
    cs_coordinator_id = fields.Many2one('hr.employee' ,string="CS Coordinator")
    ope_coordinator_id = fields.Many2one('hr.employee', string="Operation Coordinator")
    initiated_id = fields.Many2one('hr.employee', string="Initiated By")
    lost_to = fields.Char(string='Lost To')
    comments = fields.Char(string='Comments')
    address_no = fields.Char(readonly="1", string="Address Number")
    currency_id = fields.Many2one('res.currency', string='Currency')
    spe_payee_id = fields.Many2one('res.partner', string='Special Payee')
    hold_payment = fields.Selection([('yes', 'Yes'), ('no', 'No')], default='no', string='Hold Payment')
    hold_reason_id = fields.Many2one('hold.reason', string="Reason Of Hold") 
    parent = fields.Selection([('parent_vendor', 'Parent Vendor'),('customer', 'Customer')], default='parent_vendor', string='Parent')
    child_ids = fields.One2many('res.partner', 'supplier_id')
    state = fields.Selection([('draft', 'Draft'), ('verification', 'Verification'), ('done', 'Done'), ('cancel','Cancel')], default='draft')
    credit_facility = fields.Selection([('agree', 'Agreed Credit Facilit'), ('limit', 'Limit Amount')], default='limit', string='Credit Facility')
    payment_instrument = fields.Selection([('cheque', 'Cheque'), ('cash', 'Cash'), ('wire_transfer', 'Wire Transfer'), ('cc', 'CC')], default='cash', string='Payment Instrument')
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
    document_line_ids = fields.One2many('hr.document.line', 'supplier_id')
    bank_ids = fields.One2many('res.partner.custom', 'supplier_id')
    state = fields.Selection([('draft', 'Draft'), ('verification', 'Verification'), ('done', 'Done'), ('cancel','Cancel')], default='draft')
    partner_id = fields.Many2one('res.partner', string="Supplier")
    customer_id  = fields.Char(string="Code", readonly=True)
    branch_id = fields.Many2one('res.branch', string="Branch")
    type_good_service = fields.Text(string="Type of Goods Service Availed")
    justification = fields.Text(string="Justification")
    parent_id = fields.Many2one('res.partner', string='Related Company', index=True)
    function = fields.Char(string='Job Position')
    title = fields.Many2one('res.partner.title')
    comment = fields.Html(string='Notes')
    city = fields.Char()
    zip = fields.Char(change_default=True)
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    email = fields.Char()
    phone = fields.Char()
    user_ids = fields.One2many('res.users', 'partner_id', string='Users', auto_join=True)
    company_id = fields.Many2one('res.company', 'Company', index=True)
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', domain="[('country_id', '=?', country_id)]")
    user_id = fields.Many2one('res.users', string='Salesperson',
      help='The internal user in charge of this contact.')
    color = fields.Integer(string='Color Index', default=0)
    # display_name = fields.Char(compute='_compute_display_name', recursive=True, store=True, index=True)
    display_name = fields.Char(string="Supplier Dispaly")
    is_company = fields.Boolean(string='Is a Company', default=False,
        help="Check if the contact is a company, otherwise it is a person")

    mobile = fields.Char()
    street = fields.Char()
    street2 = fields.Char()
    supplier_payment_term = fields.Many2one('account.payment.term', string="Payment Terms", related="partner_id.property_supplier_payment_term_id", readonly=False, store=True)
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice Address'),
         ('delivery', 'Delivery Address'),
         ('other', 'Other Address'),
         ("private", "Private Address"),
        ], string='Address Type',
        default='contact',
        help="Invoice & Delivery addresses are used in sales orders. Private addresses are only visible by authorized users.")
    company_type = fields.Selection(string='Company Type',
        selection=[('person', 'Individual'), ('company', 'Company')],
        default="company")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('supplier.onboarding.request') or _('New')
        return super(SupplierOnboardingRequest, self).create(vals)

    def button_approve(self):
        self.state = 'verification'
        return True

    def _prepare_order_line(self, line):
        return {
            'document_line_id' : line.document_line_id.id,
            'document_number' : line.document_number,
            'valid_from' : line.valid_from,
            'valid_to': line.valid_to,
            'status' : line.status,
            'receipt_no' : line.receipt_no,
            'receipt_date' : line.receipt_date,
            'remarks' : line.remarks,
            'attachment' : line.attachment,
        }
    def _prepare_bank_line(self, line):
        return {
            'bank_id' : line.bank_id.id,
            'branch_id' : line.branch_id.id,
            'acc_number' : line.account_no,
        }

    def _prepare_address_line(self, line):
        return {
            'name' : line.name,
            'type' : line.type,
            'title' : line.title.id,
            'street' : line.street,
            'comment' : line.comment,
            'email' : line.email,
            'phone' : line.phone,
            'mobile' : line.mobile,
            'parent_id' : line.parent_id.id,
            'function' : line.function,
            'street2' : line.street2,
            'city' : line.city,
            'state_id' : line.state_id.id,
            'zip' : line.zip,
            'country_id' : line.country_id.id,
            'user_id' : line.user_id.id,
            'company_id' : line.company_id.id,
        }

    def create_supplier(self):
        lines = [5,0,0]
        bank_lines = [5,0,0]
        type_id = self.env['contact.type'].search([('contact_name', '=', 'partner')], limit=1)
        lines = [(0,0, self._prepare_order_line(line)) for line in self.document_line_ids]
        bank_lines = [(0,0, self._prepare_bank_line(line)) for line in self.bank_ids]
        address_lines = [(0,0, self._prepare_address_line(line)) for line in self.child_ids]
        self.partner_id.write({
                'contract_type_id': type_id.id,
                'supplier_id': self.id,
                'is_supplier':True,
                'document_line_ids': lines,
                'bank_ids':bank_lines,
                'computer_card':self.computer_card,
                'trade_license':self.trade_license,
                'cc_validity':self.cc_validity,
                'tl_validity':self.tl_validity,
                'tax_card':self.tax_card,
                'tc_validity':self.tc_validity,
                'sponsor_id':self.sponsor_id,
                'sid_validity':self.sid_validity,
                'cr':self.cr,
                'cr_validity':self.cr_validity,
                'qid':self.qid,
                'qid_validity':self.qid_validity,
                'passport':self.passport,
                'passport_validity':self.passport_validity,
                'noc_sponsor':self.noc_sponsor,
                'designation_id':self.designation_id.id,
                'department_id':self.department_id.id,
                'marital_status':self.marital_status,
                'support_level':self.support_level,
                'hobbies':self.hobbies,
                'anniversary_date':self.anniversary_date,
                'religion_id':self.religion_id.id,
                'date_of_birth':self.date_of_birth,
                'location':self.location,
                'phone' :self.phone,
                'mobile' :self.mobile,
                'email' :self.email,
                'website' :self.website,
                'spe_payee_id' :self.spe_payee_id.id,
                'hold_payment' :self.hold_payment,
                'hold_reason_id' :self.hold_reason_id.id,
                'currency_id' :self.currency_id.id,
                'payment_instrument' :self.payment_instrument,
                'credit_facility' :self.credit_facility,
                'parent' :self.parent,
                'child_ids' :address_lines,
                'company_type' : self.company_type,



                })
        return {
            'name': ('Supplier'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'context': {
                'form_view_initial_mode': 'edit',
            },
        }

    def button_cancel(self):
        self.state = 'cancel'
        return True
