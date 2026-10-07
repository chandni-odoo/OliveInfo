from odoo import models, fields, api


class CustomerOnboardingWizard(models.TransientModel):
    _name = 'customer.onboarding.wizard'
    _description = 'Customer Onboarding Wizard'

    client_accommodation_id = fields.Many2one(
        'client.accommodation', 
        string="Accommodation Contract", 
        required=True
    )

    customer_name = fields.Char(
        string="Customer Name", 
        related='client_accommodation_id.customer_id.name', 
        readonly=True
    )

    def action_occupied_beds(self):
        active_ids = self.env.context.get('active_ids', [])
        beds = self.env['accommodation.bed'].browse(active_ids)
        beds.write({
            'status': 'occupied',
            'occupied_customer': self.client_accommodation_id.customer_id.name,
            'check_in_time': fields.Datetime.now()
        })
        
        return {'type': 'ir.actions.act_window_close'}