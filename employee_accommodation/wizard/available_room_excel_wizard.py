from odoo import models, fields

class AvailableRoomExcelWizard(models.TransientModel):
    _name = "available.room.excel.wizard"
    _description = "Room Availability Excel Report Wizard"
    
    camp_ids = fields.Many2many(
        'accommodation.camp',
        string="Camps", 
        domain=[('status', '=', 'active')]
    )
    
    def generate_excel_report(self):
        return {
            'type': 'ir.actions.report',
            'report_name': 'employee_accommodation.available_room_excel_report',
            'report_type': 'xlsx',
            'data': {'camp_ids': self.camp_ids.ids},
        }