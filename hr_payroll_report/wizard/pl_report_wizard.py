from odoo import models, fields
from datetime import date, datetime


class PLReportWizard(models.TransientModel):
    _name = 'pl.report.wizard'
    _description = 'P&L Comparative Report Wizard'

    date = fields.Date(string="Date", required=True)
    company_ids = fields.Many2many('res.company', string="Companies")

    def action_print_report(self):
        data = {
            'date': self.date,
            'company_ids': self.company_ids.ids,
        }
        return self.env.ref('hr_payroll_report.pl_report_xlsx').report_action(self, data=data)