from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AcpWorkingWizard(models.TransientModel):
    _name = 'acp.working.wizard'
    _description = 'ACP Working Report Wizard'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    branch_ids = fields.Many2many('res.branch', string="Branches")
    customer_ids = fields.Many2many('res.partner', string="Customers")

    exclude_legal_case = fields.Boolean(string="Exclude Legal Case Customers")

    def action_print_report(self):
        if self.date_from > self.date_to:
            raise UserError(_("Invalid Date Range"))

        return self.env.ref('hr_payroll_report.acp_working_report_xlsx').report_action(self)