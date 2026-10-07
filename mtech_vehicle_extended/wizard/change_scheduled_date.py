# -*- coding: utf-8 -*-
from odoo import models, fields


class ChangeScheduledDate(models.Model):
    _name = 'change.scheduled.date.wizard'
    _description = 'Change Scheduled Date Wizard'

    old_scheduled_date = fields.Datetime(string="Old Scheduled Date", required=True, default=fields.Datetime.now)
    new_scheduled_date = fields.Datetime(string="New Scheduled Date", required=True)

    def action_confirm(self):
        """Update the schedule_date field of all selected custom.trip.sheet records."""
        trip_sheet_ids = self.env.context.get('active_ids', [])
        if trip_sheet_ids:
            self.env['custom.trip.sheet'].browse(trip_sheet_ids).write({
                'schedule_date': self.new_scheduled_date,
            })
        return {'type': 'ir.actions.act_window_close'}
