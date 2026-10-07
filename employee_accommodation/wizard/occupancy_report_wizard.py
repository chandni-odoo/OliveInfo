from odoo import models, fields, api

class OccupancyReportWizard(models.TransientModel):
    _name = 'occupancy.report.wizard'
    _description = 'Occupancy Report Wizard'
    

    to_date = fields.Date(string="As On Date", required=True)
    camp_ids = fields.Many2many('accommodation.camp', string="Camps", domain=[('status', '=', 'active')])
    floor_ids = fields.Many2many('accommodation.floor', string="Floors", domain="[('camp_id', 'in', camp_ids)]")
    room_ids = fields.Many2many('accommodation.room', string="Rooms", domain="[('floor_id', 'in', floor_ids)]")
    
    def action_print_report(self):
        data = {
            'to_date': self.to_date,
            'camp_ids': self.camp_ids.ids,
            'floor_ids': self.floor_ids.ids,
            'room_ids': self.room_ids.ids, 
        }
        return self.env.ref('employee_accommodation.occupancy_report_action').report_action(self, data=data)



