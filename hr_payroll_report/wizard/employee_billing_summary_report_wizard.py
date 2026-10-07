from odoo import models, fields, api
from datetime import datetime

class EmployeeBillingSummaryReportWizard(models.TransientModel):
    _name = 'employee.billing.summary.report.wizard'
    _description = 'Employee Billing Summary Report Wizard'

    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)
    branch_ids = fields.Many2many('res.branch', string="Branches")

    def action_generate_report(self):
        data = {
            'date_from': self.date_from.strftime('%Y-%m-%d'),
            'date_to': self.date_to.strftime('%Y-%m-%d'),
            'branch_ids': self.branch_ids.ids,
        }
        return self.env.ref('hr_payroll_report.action_employee_billing_summary_report_xlsx').report_action(self, data=data)

