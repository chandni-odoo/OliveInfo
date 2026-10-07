from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime

class LeaveAccrualReportWizard(models.TransientModel):
    _name = 'leave.accrual.report.wizard'
    _description = 'Leave Accrual Report Wizard'
    
    as_on_date = fields.Date(string='As On Date', required=True, default=fields.Date.context_today)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    
    def action_generate_excel_report(self):
        data = {
            'as_on_date': self.as_on_date,
            'employee_id': self.employee_id.id if self.employee_id else False,
            'employee_name': self.employee_id.name if self.employee_id else 'All Employees',
        }
        return self.env.ref('hr_menu_extended.action_leave_accrual_xlsx_report').report_action(self, data=data)
