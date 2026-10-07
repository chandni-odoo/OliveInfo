from odoo import models, fields
from odoo.exceptions import ValidationError


class CostPlusReportWizard(models.TransientModel):
    _name = 'cost.plus.report.wizard'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    user_id = fields.Many2one('res.users',string="Created By")
    employee_id = fields.Many2one('hr.employee',string="Employee")

    def action_export_excel(self):
        return self.env.ref(
            'hr_payroll_report.action_cost_plus_report_xlsx'
        ).report_action(self)