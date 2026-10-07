from odoo import models, fields, api

class AvailableBedsWizard(models.TransientModel):
    _name = "available.beds.wizard"
    _description = "Available Beds Report Wizard"

    camp_ids = fields.Many2many('accommodation.camp', string="Camps", domain=[('status', '=', 'active')])

    def action_print_report(self):
        return self.env.ref('employee_accommodation.available_beds_report_action').report_action(self, data={
            'camp_ids': self.camp_ids.ids,  
        })