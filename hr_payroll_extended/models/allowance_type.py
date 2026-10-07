from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrAllowType(models.Model):
	_name = "hr.allow.type"
	_inherit = ['mail.thread', 'mail.activity.mixin']


	seq = fields.Char()
	name = fields.Char()
	code = fields.Char()
	amount = fields.Float()
	type = fields.Selection([('deduction', 'Deduction'), ('allowance', 'Allowance')]) 
