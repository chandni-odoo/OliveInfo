# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class Product(models.Model):
    _inherit = "product.template"

    is_fuel_product = fields.Boolean(
        string="Is Fuel Product",
        help="Allow Crate Fuel Product")

class Move(models.Model):
    _inherit = "account.move"

    trip_id = fields.Many2one('trip.trip', string="Trip")
    log_fuel_id = fields.Many2one('fleet.vehicle.log.fuel', string="Fleet Vehicle Log Fuel")
