from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class AcpReportWizard(models.TransientModel):
    _name = 'acp.report.wizard'
    _description = 'ACP Report Wizard'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    branch_ids = fields.Many2many('res.branch', string="Branches")
    customer_ids = fields.Many2many('res.partner', string="Customers")

    def action_print_report(self):
        if self.date_from > self.date_to:
            raise UserError(_("Invalid Date Range"))

        return self.env.ref('hr_payroll_report.acp_report_xlsx').report_action(self)