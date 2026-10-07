# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    permit_ids = fields.Many2many(
        'vehicle.permit',
        'vehicle_permit_relation'
        'permit_id',
        'vehicle_id',
        string='Permits',
    )
    job_order = fields.Many2one('sale.order', string="Job Order")
    customer_id = fields.Many2one('res.partner', string="Customer")
    aging = fields.Integer(string="Aging (Days)")
    latitude = fields.Float(string="Latitude", digits='Lat-Long')
    longitude = fields.Float(string="Longitude", digits='Lat-Long')
    color = fields.Selection(
        selection=[
            ('red', 'Red'),
            ('blue', 'Blue'),
            ('yellow', 'Yellow'),
            ('black', 'Black'),
            ('white', 'White'),
            ('orange', 'Orange'),
        ], string='Color')

    status = fields.Selection(
        selection=[
            ('available', 'Available'),
            ('deployed', 'Deployed'),
            ('repair', 'Repair'),
            ('damage', 'Damage'),
            ('lost', 'Lost'),
            ('scraped', 'Scraped'),
        ],
        string='Status',
        default='available',
        required=True,
        help='Status of the item'
    )

    @api.onchange('task_id')
    def _onchange_task_id(self):
        for record in self:
            if record.task_id:
                record.customer_id = record.task_id.partner_id
                record.job_order = record.task_id.sale_order_id

    @api.onchange('skip_load_ids')
    def onchange_trip_sheet_ids(self):
        for rec in self:
            if rec.skip_load_ids:
                last_record = rec.skip_load_ids[-1]

                rec.location = last_record.partner_location_id.name if last_record.partner_location_id else False

                if last_record.date_from:
                    date_from = last_record.date_from.date()
                    today = date.today()
                    rec.aging = (today - date_from).days + 1
                else:
                    rec.aging = 0
