from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class VisaApplicant(models.Model):
	_name = 'visa.applicant'
	_description = 'Visa Application'
	_rec_name = 'requested_id'
	_inherit = ['mail.thread', 'mail.activity.mixin']



	requested_id = fields.Many2one('res.partner',string="Requested By")
	date_done = fields.Datetime(string="Date And Time")
	applicant_no = fields.Char(string='Applicant No.')
	state = fields.Selection([('step1','step1'),
	                         ('step2','step2'),
	                         ('step3','step3'),
	                         ('step4','step4'),
	                         ('step5','step5'),
	                         ('step6','step6'),
	                         ('step7','step7'),
	                         ('cancel','Cancelled')], default='step1')
	applicant_line_ids = fields.One2many('visa.applicant.line','applicant_id',string="Application Line")






	def button_step1(self):
	    self.state = 'step2'

	def button_step2(self):
	    self.state = 'step3'

	def button_step3(self):
	    self.state = 'step4'

	def button_step4(self):
	    self.state = 'step5'

	def button_step5(self):
	    self.state = 'step6'

	def button_step6(self):
	    self.state = 'step7'


	def button_cancel(self):
	    self.state = 'cancel'



class VisaApplicantLine(models.Model):
	_name = 'visa.applicant.line'


	candidate_id = fields.Many2one('visa.details',string="Candidate ID")
	branch_id = fields.Many2one('res.branch')
	partner_name = fields.Char("Applicant's Name")
	visa_profession_id = fields.Many2one('visa.profession', string="Visa Profession")
	gender = fields.Selection([('male', 'Male'),('female', 'Female'),('other', 'Other')])
	job_id = fields.Many2one('hr.job', "Job")
	nationality = fields.Many2one('res.country', "Nationality")
	attachment = fields.Binary(string='Attachment')
	visa_status = fields.Selection([('request','Requested'),
	                         		('approve','Approvad'),
	                         		('cancel','Cancelled')], default='request',string="Visa Status")
	passport = fields.Char(string="Passport")
	applicant_id = fields.Many2one('visa.applicant')



	quota_no = fields.Char(string="Lot/Quota No.")
	vp_no = fields.Char(string="VP No.")
	reason_moi = fields.Text(string="Reason")

	visa_status = fields.Selection([('applied','Applied'),
	                         ('under_process','Under Process'),
	                         ('received','Received'),
	                         ('done','Done'),
	                         ('rejected','Rejected'),
	                         ('re_apply','Re-Apply')],
	                         string="Visa Status")
	type_of_visa = fields.Selection([('work_visa', 'Work Visa'),
	                                ('business_visa', 'Business Visa'),
	                                ], default='work_visa', string="Type Of Visa")
	date_applied = fields.Datetime(string="Date/Time Applied")
	applied_by = fields.Many2one('res.partner',string="Applied By")
	qvc = fields.Selection([('no','No'),
	                         ('yes','Yes')],string="QVC")
	qvc_status = fields.Selection([('na','N/A'),
	                         ('applied','Applied/Sent')])
	# qvc_notification
	# qvc_passed = fields.
	medical_status = fields.Selection([('on_arrival','On Arrival'),('done','Done/Attach Any Docs')],string='Medical Status')
	finger_print = fields.Selection([('on_arrival','On Arrival'),('done','Done/Attach Any Docs')],string='Finger Print')
	contract = fields.Selection([('on_arrival','On Arrival'),('done','Done/Attach Any Docs')],string='Contract')
	qvc_cost = fields.Integer(string="QVC Cost(QAR)")
	ticket_status = fields.Selection([('applied','Applied'),
										('received','Received'),
										('sent','Sent')],string="Ticket Status")
	update_ticket_status = fields.Selection([('applied','Applied'),
										('received','Received'),
										('sent','Sent')],string="Updated Ticket Status")
	ticket_cost = fields.Integer(string="Ticket Cost")
	entry_date = fields.Date(string="Entry Date")
	visa_expiry_date = fields.Date(string="Visa Expiry Date")



	approved_date = fields.Datetime(string="Approved Date")
	visa_no = fields.Integer(string="Visa No.")
	validity = fields.Date(string="Validity")

	medical_status2 = fields.Selection([('applied','Applied'),
	                         ('under_process','Under Process'),
	                         ('received','Received'),
	                         ('done','Done'),
	                         ('rejected','Rejected'),
	                         ('re_apply','Re-Apply')],string="Medical Status")
	finger_print_status = fields.Selection([('applied','Applied'),
	                         ('under_process','Under Process'),
	                         ('received','Received'),
	                         ('done','Done'),
	                         ('rejected','Rejected'),
	                         ('re_apply','Re-Apply')],string="Finger Print Status")

	contract_status = fields.Selection([('prepared','Prepared'),
										('signed','Signed'),
										('done','Done')],
										string='Medical Status')

	qid_status = fields.Selection([('applied','Applied'),
										('received','Received'),
										('done','Done')],
										string='QID Status')

	medical_cost = fields.Integer(string="Medical Cost")
	finger_print_cost = fields.Integer(string="Finger Print Cost")
	contract_cost = fields.Integer(string="Contract Cost")
	qid_cost = fields.Integer(string="QID Cost")
	total_cost = fields.Integer(string="Total Cost")












