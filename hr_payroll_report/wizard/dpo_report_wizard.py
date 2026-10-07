from odoo import models, fields, api, _
from odoo.exceptions import UserError
 
 
class DpoReportWizard(models.TransientModel):
    _name = 'dpo.report.wizard'
    _description = 'DPO Report Wizard'
 
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
 
    branch_ids = fields.Many2many('res.branch', string="Branches")
    supplier_ids = fields.Many2many(
        'res.partner',
        string="Suppliers",
        domain=[('supplier_rank', '>', 0)]
    )
 
    def action_print_report(self):
        if self.date_from > self.date_to:
            raise UserError(_("Invalid Date Range"))
 
        return self.env.ref('hr_payroll_report.dpo_report_xlsx').report_action(self)
 