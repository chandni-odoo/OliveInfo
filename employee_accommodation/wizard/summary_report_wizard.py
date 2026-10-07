from odoo import models, fields

class RoomSummaryWizard(models.TransientModel):
    _name = "room.summary.wizard"
    _description = "Room Summary Wizard"

    camp_ids = fields.Many2many("accommodation.camp", string="Camps", domain=[('status', '=', 'active')])

    def action_generate_report(self):
        data = {
            'camp_ids': self.camp_ids.ids if self.camp_ids else [],
        }
        return self.env.ref('employee_accommodation.report_room_summary_pdf').report_action(None, data=data)