# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date


class CustomTripSheet(models.Model):
    _inherit = 'custom.trip.sheet'
    _description = 'Custom Trip Sheet'

    schedule_id = fields.Many2one('shift.schedule', string="Shift Schedule")
    schedule_date = fields.Datetime(string="Schedule Date", required=True)
    shift_id = fields.Many2one('fleet.shift.type', string="Shift", required=True)
    final_collection = fields.Boolean(string="Final Collection")
    latitude = fields.Float(string="Latitude", digits='Lat-Long')
    longitude = fields.Float(string="Longitude", digits='Lat-Long')
    invoice_no = fields.Char(string="Invoice No")
    delivery_skip_ids = fields.One2many(
        comodel_name='delivery.skip',
        inverse_name='trip_id',
        string='Delivery Skip',
    )
    landfill_id = fields.Many2one('fleet.landfill', string="Landfill")

    coll_del_status = fields.Char(
        string="Collection/Delivery Status",
        compute="_compute_coll_del_status",
        store=True
    )
    frequency_value = fields.Selection(related="task_id.frequency_value", string="Frequency")

    @api.depends("skip_load_ids.coll_del")
    def _compute_coll_del_status(self):
        for order in self:
            coll_del_values = set(order.skip_load_ids.mapped("coll_del"))  # Get unique coll_del values

            if coll_del_values == {"collection"}:
                order.coll_del_status = "Collection"
            elif coll_del_values == {"delivery"}:
                order.coll_del_status = "Delivery"
            elif {"collection", "delivery"}.issubset(coll_del_values):
                order.coll_del_status = "Collection, Delivery"
            else:
                order.coll_del_status = ", ".join(coll_del_values) if coll_del_values else "Unknown"

    def button_approve(self):
        super(CustomTripSheet, self).button_approve()
        for record in self:
            for line in record.skip_load_ids:
                if line.maintenance_equ_id:
                    if line.trip_id.final_collection and line.trip_id.coll_del_status == "Collection":
                        if line.trip_id.date_from:
                            date_from = line.trip_id.date_from.date()
                            today = date.today()
                            line.maintenance_equ_id.sudo().write({
                                'aging': (today - date_from).days + 1,
                                'location': line.trip_id.site.name if line.trip_id.site else False,
                                'customer_id': line.trip_id.customer_id.id if line.trip_id.customer_id else False,
                                'latitude': line.trip_id.latitude if line.trip_id.latitude else False,
                                'longitude': line.trip_id.longitude if line.trip_id.longitude else False,
                                'task_id': line.trip_id.task_id.id if line.trip_id.task_id else False,
                                'job_order': line.trip_id.task_id.sale_order_id.id if line.trip_id.task_id.sale_order_id else False,
                                'coll_del_status': 'collection',
                                'status': 'available'
                            })
                    elif line.trip_id.coll_del_status == "Collection":
                        print('222222222222\n')
                        if line.trip_id.date_from:
                            date_from = line.trip_id.date_from.date()
                            today = date.today()
                            line.maintenance_equ_id.sudo().write({
                                'aging': (today - date_from).days + 1,
                                'location': line.trip_id.site.name if line.trip_id.site else False,
                                'customer_id': line.trip_id.customer_id.id if line.trip_id.customer_id else False,
                                'latitude': line.trip_id.latitude if line.trip_id.latitude else False,
                                'longitude': line.trip_id.longitude if line.trip_id.longitude else False,
                                'task_id': line.trip_id.task_id.id if line.trip_id.task_id else False,
                                'job_order': line.trip_id.task_id.sale_order_id.id if line.trip_id.task_id.sale_order_id else False,
                                'coll_del_status': 'delivery',
                                'status': 'deployed'
                            })
                    elif line.trip_id.coll_del_status == "Delivery":
                        print('>>>>>>>>>>>>>>>>\n')
                        if line.trip_id.date_from:
                            date_from = line.trip_id.date_from.date()
                            today = date.today()
                            line.maintenance_equ_id.sudo().write({
                                'aging': (today - date_from).days + 1,
                                'location': line.trip_id.site.name if line.trip_id.site else False,
                                'customer_id': line.trip_id.customer_id.id if line.trip_id.customer_id else False,
                                'latitude': line.trip_id.latitude if line.trip_id.latitude else False,
                                'longitude': line.trip_id.longitude if line.trip_id.longitude else False,
                                'task_id': line.trip_id.task_id.id if line.trip_id.task_id else False,
                                'job_order': line.trip_id.task_id.sale_order_id.id if line.trip_id.task_id.sale_order_id else False,
                                'coll_del_status': 'delivery',
                                'status': 'deployed'
                            })

                    elif line.trip_id.coll_del_status == "Collection, Delivery":
                        print('!!!!!!!!!!!!!!!! Collection & Delivery Both Found\n\n')
                        coll_del = line.coll_del.strip().lower()

                        if coll_del == "collection":
                            print('Collection Line Found')
                            date_from = line.trip_id.date_from.date()
                            today = date.today()
                            line.maintenance_equ_id.sudo().write({
                                'aging': (today - date_from).days + 1,
                                'location': line.trip_id.site.name if line.trip_id.site else False,
                                'customer_id': line.trip_id.customer_id.id if line.trip_id.customer_id else False,
                                'latitude': line.trip_id.latitude if line.trip_id.latitude else False,
                                'longitude': line.trip_id.longitude if line.trip_id.longitude else False,
                                'task_id': line.trip_id.task_id.id if line.trip_id.task_id else False,
                                'job_order': line.trip_id.task_id.sale_order_id.id if line.trip_id.task_id.sale_order_id else False,
                                'coll_del_status': 'collection',
                                'status': 'available'
                            })

                        elif coll_del == "delivery":
                            print('Delivery Line Found')
                            date_from = line.trip_id.date_from.date()
                            today = date.today()
                            line.maintenance_equ_id.sudo().write({
                                'aging': (today - date_from).days + 1,
                                'location': line.trip_id.site.name if line.trip_id.site else False,
                                'customer_id': line.trip_id.customer_id.id if line.trip_id.customer_id else False,
                                'latitude': line.trip_id.latitude if line.trip_id.latitude else False,
                                'longitude': line.trip_id.longitude if line.trip_id.longitude else False,
                                'task_id': line.trip_id.task_id.id if line.trip_id.task_id else False,
                                'job_order': line.trip_id.task_id.sale_order_id.id if line.trip_id.task_id.sale_order_id else False,
                                'coll_del_status': 'delivery',
                                'status': 'deployed'
                            })

        return True
