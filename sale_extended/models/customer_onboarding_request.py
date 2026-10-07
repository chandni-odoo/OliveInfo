# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class CustomerOnboardingRequest(models.Model):
    _name = 'customer.onboarding.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Customer Onboarding Request"

    name = fields.Char(readonly=True, default="New")
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    customer_id  = fields.Char(string="Code",readonly=True)
    designation_id = fields.Many2one('hr.job',string="Designation")
    department_id = fields.Many2one('hr.department',string="Department")
    phone = fields.Char(string="Phone")
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
    region_id = fields.Many2one('customer.region', string='Region')
    sector_id = fields.Many2one('customer.sector', string='Sector')
    industry_id = fields.Many2one('main.industry', string='Industry')
    location_id = fields.Many2one('hr.location', string='Location')
    grade_id = fields.Many2one('grade.type',string="Grade")
    segment_id = fields.Many2one('customer.segment',string="Segment")
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
    agreement_ref = fields.Char(string='Agreement')
    job_type_id = fields.Many2one('hr.job', string='Job Type')
    child_ids = fields.One2many('res.partner', 'onboarding_id')
    state = fields.Selection([('draft', 'Draft'), ('verification', 'Verification'), ('done', 'Done'), ('cancel','Cancel')], default='draft')
    sale_id = fields.Many2one('sale.order', 'Sale Order')
    document_line_ids = fields.One2many('hr.document.line', 'customer_id')
    branch_id = fields.Many2one('res.branch', string="Branch")
    bank_ids = fields.One2many('res.partner.custom', 'onboarding_id')
    payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms", related="partner_id.property_payment_term_id", readonly=False, store=True)
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
    display_name = fields.Char(string="customer Dispaly")
    is_company = fields.Boolean(string='Is a Company', default=False,
        help="Check if the contact is a company, otherwise it is a person")

    mobile = fields.Char()
    street = fields.Char()
    street2 = fields.Char()
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
        vals['name'] = self.env['ir.sequence'].next_by_code('customer.onboarding.request') or _('New')
        return super(CustomerOnboardingRequest, self).create(vals)

    def button_approve(self):
        self.state = 'verification'
        return True
        

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

    def create_customer(self):
        for rec in self:
            type_id = self.env['contact.type'].search([('contact_name', '=', 'partner')],limit=1)
            lines = [(0,0, self._prepare_order_line(line)) for line in rec.document_line_ids]
            address_lines = [(0,0, self._prepare_address_line(line)) for line in rec.child_ids]
            bank_lines = [(0,0, self._prepare_bank_line(line)) for line in rec.bank_ids]
            rec.partner_id.write({
                                    'onboarding_id': rec.id, 
                                    'is_customer':True,
                                    'phone' :rec.phone,
                                    'mobile' :rec.mobile,
                                    'document_line_ids': lines,
                                    'email' :rec.email,
                                    'branch_id' :rec.branch_id.id,
                                    'website' :rec.website,
                                    'child_ids' :address_lines,
                                    'bank_ids' : bank_lines,
                                    'branch_id' :rec.branch_id.id,
                                    'region_id' :rec.region_id.id,
                                    'industry_id' :rec.industry_id.id,
                                    'grade_id' :rec.grade_id.id,
                                    'sector_id' :rec.sector_id.id,
                                    'location_id' :rec.location_id.id,
                                    'segment_id' :rec.segment_id.id,
                                    'customer_profile' :rec.customer_profile,
                                    'license_no' :rec.license_no,
                                    'license_validity' :rec.license_validity,
                                    'annual_revenue' :rec.annual_revenue,
                                    'how_to_know' :rec.how_to_know,
                                    'issuing_authority' :rec.issuing_authority,
                                    'parent_company' :rec.parent_company,
                                    'total_employees' :rec.total_employees,
                                    'growth_rate' :rec.growth_rate,
                                    'advance_coll' :rec.advance_coll,
                                    'agreement_ref' :rec.agreement_ref,
                                    'contract_period' :rec.contract_period,
                                    'security_deposite' :rec.security_deposite,
                                    'job_type_id' :rec.job_type_id.id,
                                    'expected_sales' :rec.expected_sales,
                                    'designation_id' :rec.designation_id.id,
                                    'support_level' :rec.support_level,
                                    'anniversary_date' :rec.anniversary_date,
                                    'date_of_birth' :rec.date_of_birth,
                                    'location' :rec.location,
                                    'department_id' :rec.department_id.id,
                                    'marital_status' :rec.marital_status,
                                    'hobbies' :rec.hobbies,
                                    'religion_id' :rec.religion_id.id,
                                    'contract_type_id': type_id.id,
                                    'company_type' : rec.company_type,


                                })
        return {
            'name': ('Customer'),
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
