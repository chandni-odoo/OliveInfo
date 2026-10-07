from odoo import models, fields, api
from odoo.exceptions import UserError

class ManpowerReportWizard(models.TransientModel):
    _name = 'manpower.report.wizard'
    _description = 'Manpower Requisition Report Wizard'
    
    branch_ids = fields.Many2many(
        'res.branch',
        string='Departments/Business Units'
    )
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise UserError("From Date cannot be greater than To Date")
    
    def action_generate_report(self):
        self.ensure_one()
        return self.env.ref('visa_processing.action_manpower_requisition_xlsx_report').report_action(self)