from odoo import models, fields, api

class ContractReportWizard(models.TransientModel):
    _name = 'contract.report.wizard'
    _description = 'HR Contract Salary Report Wizard'

    branch_ids = fields.Many2many('res.branch', string="Branch")
    billable = fields.Boolean("Billable Only", default=True)
    active_status = fields.Boolean("Active")
    leave_status = fields.Boolean("Leave")
    hide_zero_records = fields.Boolean("Hide Zero Records", default=True)

    def action_generate_report(self):
        return self.env.ref('hr_payroll_report.action_contract_salary_report').report_action(self)