from odoo import models, fields, api

class AvailableBedsExcelWizard(models.TransientModel):
    _name = "available.beds.excel.wizard"
    _description = "Available Beds Excel Report Wizard"

    camp_ids = fields.Many2many('accommodation.camp', string="Camps", domain=[('status', '=', 'active')])

    def action_generate_excel(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.report',
            'report_name': 'employee_accommodation.available_beds_excel_report',
            'report_type': 'xlsx',
            'model': 'available.beds.excel.wizard',
            'docids': self.ids,
            'data': {
                'camp_ids': self.camp_ids.ids
            },
            'config': {
                'report_name': 'Available Beds Report'
            }
        }