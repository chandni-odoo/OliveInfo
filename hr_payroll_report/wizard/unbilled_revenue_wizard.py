from odoo import models, fields, api

class UnbilledRevenueReportWizard(models.TransientModel):
    _name = 'unbilled.revenue.report.wizard'
    _description = 'Unbilled Revenue Report Wizard'

    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    branch_ids = fields.Many2many('res.branch', string="Branches")

    def action_generate_report(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'branch_ids': self.branch_ids.ids,
        }
        return self.env.ref('hr_payroll_report.action_unbilled_revenue_report_xlsx').report_action(self, data=data)