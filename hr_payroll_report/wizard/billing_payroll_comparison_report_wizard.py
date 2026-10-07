from odoo import models, fields, api
from datetime import datetime


class BillingPayrollComparisonWizard(models.TransientModel):
    _name = 'billing.payroll.comparison.wizard'
    _description = 'Billing Payroll Comparison Report Wizard'

    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)
    branch_ids = fields.Many2many('res.branch', string="Branch")

    def action_generate_report(self):
        return self.env.ref(
            'hr_payroll_report.action_billing_payroll_comparison_xlsx'
        ).report_action(self)