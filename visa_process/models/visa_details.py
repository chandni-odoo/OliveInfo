from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class VisaDetails(models.Model):
    _name = 'visa.details'
    _description = 'Visa Details'
    _rec_name = 'lot_no'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    lot_no = fields.Char(string='Lot No.')
    date_done = fields.Datetime(string="Date/Time")
    project = fields.Char(string='Project/Job')
    requested_id = fields.Many2one('res.partner',string="Requested By")
    attachment_id = fields.Binary(string='Attachment')
    visa_line_ids = fields.One2many('visa.details.line','visa_line_id',string="Lines")
    state = fields.Selection([('request','Request'),
                         ('receive','Received'),
                         ('update','Update'),
                         ('approve','Approvad'),
                         ('cancel','Cancelled')], default='request')
    visa_application_no = fields.Char(string="Visa Application No.")
    visa_app_id = fields.Char(string="Application ID")
    vp_no = fields.Char(string="VP No.")
    expiry_date = fields.Date(string="Expiry Date")
    status = fields.Selection([('approved','Approved'),('rejected','Rejected')], string="Status")
    applied_by = fields.Many2one('res.partner')




    def button_receive(self):
        self.state = 'receive'

    def button_update(self):
        self.state = 'update'

    def button_approve(self):
        self.state = 'approve'

    def button_cancel(self):
        self.state = 'cancel'






class VisaDetailsLine(models.Model):
    _name = 'visa.details.line'
    _description = 'Visa Details Lines'
    _rec_name = 'lot_line_no'
    
    requested_hr = fields.Integer(string="Lot/Quota -Requested(HR)")
    visa_line_id = fields.Many2one('visa.details','Visa')
    lot_quota  = fields.Integer(string="Lot/Quota")
    lot_line_no = fields.Char(string='Lot No. ')
    nationality = fields.Many2one('res.country',string="Nationality", required=True)
    type_of_visa = fields.Selection([('work_visa', 'Work Visa'),
                                    ('business_visa', 'Business Visa'),
                                    ], default='work_visa', string="Type Of Visa")
    type_of_visa_profession = fields.Selection([('labourer', 'LABOURER'),
                                    ('salesman', 'SALESMAN'),
                                    ('administrative', 'PUBLIC ADMINISTRATIVE'),
                                    ], string="Visa Profession")
    gender = fields.Selection([('male', 'Male'),
                             ('female', 'Female'),
                            ], string="Gender")

    requested_mol = fields.Integer(string="Requested In MOL")
    approval_count = fields.Integer(string="Approved")
    rejected_count = fields.Integer(string="Rejected")
    visa_sponsor = fields.Char(string="Sponsor")
    approval_date = fields.Datetime(string="Approval Date")
    reject_reason = fields.Char(string="Reject Reason")
    used_count = fields.Integer(string="Used Count")
    balance_count = fields.Integer(string="Balance Count")
    date_time = fields.Datetime('Applied on Date/Time')





