from odoo import models, fields

class BSReportWizard(models.TransientModel):
    _name = 'bs.report.wizard'
    _description = 'Balance Sheet Comparative Report Wizard'

    date = fields.Date(string="Date", required=True)
    company_ids = fields.Many2many('res.company', string="Companies")

    def action_print_report(self):
        data = {
            'date': str(self.date),
            'company_ids': self.company_ids.ids,
        }
        return self.env.ref('hr_payroll_report.bs_report_xlsx').report_action(self, data=data)
