# -*- coding: utf-8 -*-
import logging
from odoo import api, models, fields

_logger = logging.getLogger(__name__)


class ChangeScheduledDateOrder(models.Model):
    _name = 'change.scheduled.date.order.wizard'
    _description = 'Change Vehicles On Delivery Orders'

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    shift_type_id = fields.Many2one('fleet.shift.type', "Shift")
    new_vehicle_id = fields.Many2one('fleet.vehicle', string="New Vehicle")
    delivery_orders_ids = fields.Many2many('custom.trip.sheet', 'sequence', string="Tripsheets")
    note = fields.Text(string="Add a note")

    @api.model
    def default_get(self, fields_list):
        """ Ensures that pre-selected records from list view appear in wizard """
        res = super(ChangeScheduledDateOrder, self).default_get(fields_list)
        active_ids = self._context.get('active_ids', [])
        if active_ids:
            res['delivery_orders_ids'] = [(6, 0, active_ids)]
        return res

    @api.onchange('start_date', 'end_date', 'vehicle_id', 'shift_type_id')
    def _onchange_fetch_trip_sheets(self):
        if self.start_date and self.end_date and self.vehicle_id and self.shift_type_id:
            trip_sheets = self.env['custom.trip.sheet'].search([
                ('schedule_date', '>=', self.start_date),
                ('schedule_date', '<=', self.end_date),
                ('vehicle_no_id', '=', self.vehicle_id.id),
                ('shift_id', '=', self.shift_type_id.id)
            ])

            # 🚀 **Merge already selected records + newly fetched records**
            existing_records = self.delivery_orders_ids.ids  # Already selected from list view
            new_records = trip_sheets.ids  # Newly fetched based on filters
            combined_records = list(set(existing_records + new_records))  # Merge & remove duplicates

            self.delivery_orders_ids = [(6, 0, combined_records)]

    def action_transfer(self):
        """Updates date_from, date_to, and vehicle_no_id in selected or all delivery orders."""
        trips_to_update = self.delivery_orders_ids or self.env['custom.trip.sheet'].browse([])

        for trip in trips_to_update:
            _logger.info(f"Updating Trip {trip.id}: Vehicle {self.new_vehicle_id.name}, Dates {self.start_date} to {self.end_date}")
            trip.write({
                'date_from': self.start_date,
                'date_to': self.end_date,
                'vehicle_no_id': self.new_vehicle_id.id,
            })

        # if self.vehicle_id:
        #     # _logger.info(f"Updating Vehicle Shift {self.vehicle_id.id}: Setting Vehicle to {self.new_vehicle_id.name}")
        #     self.delivery_orders_ids.write({'vehicle_id': self.new_vehicle_id.id})
