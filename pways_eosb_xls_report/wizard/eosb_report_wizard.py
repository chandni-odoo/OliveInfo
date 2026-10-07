from odoo import models, fields, api, _
import datetime
from datetime import timedelta, date


class EmployeeEosbWizard(models.TransientModel):
    _name = 'employee.eosb.wizard'
    _description = "Employee End Of service Benefit Wizard"

    as_on_date = fields.Date(string="Date", default=date.today(), required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, required=True)
    branch_ids = fields.Many2many('res.branch', string="Branch")
    emp_status_active = fields.Boolean(string="Active")
    emp_status_leave = fields.Boolean(string="Leave")
    emp_status_resigned = fields.Boolean(string="Resigned")
    emp_status_terminated = fields.Boolean(string="Terminated")
    employer_change = fields.Boolean(string="Employer Change")

    def print_eosb_report_xls(self):            
        data = {
            'as_on_date': self.as_on_date,
            'company_id':self.company_id.id,
            'branch_ids': self.branch_ids.ids,
            'emp_status_active': self.emp_status_active,
            'emp_status_leave': self.emp_status_leave,
            'emp_status_resigned': self.emp_status_resigned,
            'emp_status_terminated': self.emp_status_terminated,
            'employer_change': self.employer_change,
            }
        return self.env.ref('pways_eosb_xls_report.eosb_xlsx').report_action(self, data=data)

    def print_eosb_branch_report_xls(self):
        data = {
            'as_on_date': self.as_on_date,
            'company_id':self.company_id.id,
            'branch_ids': self.branch_ids.ids,
            }
        return self.env.ref('pways_eosb_xls_report.eosb_xlsx_branch').report_action(self, data=data)
