# -*- coding: utf-8 -*-
from odoo import models, fields


class DeliverySkip(models.Model):
    _name = 'delivery.skip'

    name = fields.Char(string='Name', required=True)
    file_content = fields.Binary(string='File Content')
    trip_id = fields.Many2one(
        comodel_name='custom.trip.sheet',
        string='Related Model',
        ondelete='cascade',
    )
