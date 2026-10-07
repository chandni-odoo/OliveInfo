from odoo import models, fields, api
from datetime import datetime

class NewCustomerRevenueWizard(models.TransientModel):
    _name = 'new.customer.revenue.wizard'
    _description = 'New Customer Revenue Report Wizard'

    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True,
        default=lambda self: datetime.now().year
    )
    branch_ids = fields.Many2many('res.branch', string="Branches")

    @api.model
    def _get_year_selection(self):
        """Return list of years from 2020 to current year + 1"""
        current_year = datetime.now().year
        return [(str(year), str(year)) for year in range(2020, current_year + 2)]

    def _get_months_list(self):
        """Return list of all months for the selected year"""
        months = []
        if self.year:
            for month in range(1, 13):
                date_obj = datetime(int(self.year), month, 1)
                months.append(date_obj.strftime('%b'))  # ['Jan', 'Feb', ..., 'Dec']
        return months

    def action_generate_report(self):
        """Trigger XLSX report"""
        data = {
            'year': self.year,
            'branch_ids': self.branch_ids.ids,
            'months': self._get_months_list(),
        }
        return self.env.ref('hr_payroll_report.action_new_customer_revenue_report_xlsx').report_action(self, data=data)