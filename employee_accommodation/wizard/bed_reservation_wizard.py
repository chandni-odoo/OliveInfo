from odoo import models, fields, api

class BedReservationWizard(models.TransientModel):
    _name = 'bed.reservation.wizard'
    _description = 'Bed Reservation Wizard'

    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="To Date", required=True)
    reason = fields.Text(string="Reason", required=True)
    requested_by = fields.Many2one('res.users', string="Requested By", default=lambda self: self.env.user, required=True)

    def action_reserve_beds(self):
        active_ids = self.env.context.get('active_ids', [])
        beds = self.env['accommodation.bed'].browse(active_ids)
        beds.write({
            'status': 'reserved',
            'reserved_from': self.from_date,
            'reserved_to': self.to_date,
            'reservation_reason': self.reason,
            'requested_by': self.requested_by.id,
        })
        return {'type': 'ir.actions.act_window_close'}