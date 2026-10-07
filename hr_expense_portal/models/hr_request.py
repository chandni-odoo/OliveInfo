from odoo import models, fields, api, _

class HrRequest(models.Model):
	_name = "request.request"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Hr Accident"

	name = fields.Char(default='New', readonly=True,copy=False)
	state = fields.Selection([('draft','Draft'),('confirm','Confirm'), ('approve','Approve'), ('submit','Submit')], default='draft')
	employee_id = fields.Many2one('hr.employee')
	department_id = fields.Many2one('hr.department')
	job_id = fields.Many2one('hr.job')
	reqest_date = fields.Date(string="Request Date")
	description = fields.Text(string="Description")
	type_id = fields.Many2one('hr.request.type', string="Request Type")

	def button_confirm(self):
		self.state = 'confirm'

	def button_approve(self):
		self.state = 'approve'

	def button_submit(self):
		self.state = 'submit'

	@api.onchange('employee_id')
	def _onChangeEmployee(self):
		if self.employee_id:
			self.department_id = self.employee_id.department_id and self.employee_id.department_id.id	
			self.job_id = self.employee_id.job_id and self.employee_id.job_id.id		

	@api.model
	def create(self, vals):
		if vals.get('name', 'New') == 'New':
			vals['name'] = self.env['ir.sequence'].next_by_code('request.request') or ('New')
		return super(HrRequest, self).create(vals)

class RequestType(models.Model):
	_name = "hr.request.type"

	name = fields.Char()
	code = fields.Char()







	


