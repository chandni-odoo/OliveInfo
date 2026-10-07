from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class LeaveSettlementWizard(models.Model):
	_name = "leave.settlement.wizard"

	journal_id = fields.Many2one('account.journal')
	credit_account_id = fields.Many2one('account.account')
	debit_account_id = fields.Many2one('account.account')
	employee_id = fields.Many2one('hr.employee')

	@api.model
	def default_get(self,fields):
		res = super(LeaveSettlementWizard, self).default_get(fields)
		active_id = self.env.context.get('active_id')
		if active_id:
			settlement_id = self.env['leave.settlement'].browse(active_id)
			if settlement_id:
				res.update({'employee_id': settlement_id.employee_id.id})
		return res

	
