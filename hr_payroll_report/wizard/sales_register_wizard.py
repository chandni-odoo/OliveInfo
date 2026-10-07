from odoo import models, fields, api
from datetime import datetime

class SalesRegisterReportWizard(models.TransientModel):
    _name = 'sales.register.report.wizard'
    _description = 'Sales Register Report Wizard'

    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)
    branch_ids = fields.Many2many('res.branch', string="Branches")

    def _get_months_list(self):
        """Return list of months (short names) between date_from and date_to"""
        months = []
        if self.date_from and self.date_to:
            current_date = self.date_from.replace(day=1)
            while current_date <= self.date_to:
                months.append(current_date.strftime('%b'))  # ['Jan', 'Feb', ...]
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
        return months

    def action_generate_report(self):
        """Trigger XLSX report"""
        data = {
            'date_from': self.date_from.strftime('%Y-%m-%d'),
            'date_to': self.date_to.strftime('%Y-%m-%d'),
            'branch_ids': self.branch_ids.ids,
            'months': self._get_months_list(),
        }
        return self.env.ref('hr_payroll_report.action_sales_register_report_xlsx').report_action(self, data=data)