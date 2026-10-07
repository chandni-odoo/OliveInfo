from odoo import models, fields, api

class AvailableroomWizard(models.TransientModel):
    _name = "available.room.wizard"
    _description = "Room Availability Report Wizard"
    
    camp_ids = fields.Many2many(
        'accommodation.camp',
        string="Camps", domain=[('status', '=', 'active')])
    
    def generate_report(self):
        return self.env.ref('employee_accommodation.available_room_report_action').report_action(self, data={
            'camp_ids': self.camp_ids.ids,  
        })
    

    

    