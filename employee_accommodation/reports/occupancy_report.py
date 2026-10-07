from odoo import models, api

class OccupancyListReport(models.AbstractModel):
    _name = 'report.employee_accommodation.occupancy_list_report_template'
    _description = 'Occupancy List Report'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['accommodation.check.in'].search([('status', '=', 'checked_in')])
        return {
            'doc_ids': self.env['accommodation.check.in'].browse(docids),
            'doc_model': 'accommodation.check.in',
            'docs': docs,
        }
        