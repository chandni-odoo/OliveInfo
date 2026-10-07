# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AssetSubLocation(models.Model):
    _name = 'asset.sub.location'
    _description = "Asset Sub Location"

    name = fields.Char(string='Name', required="1")
    location_id = fields.Many2one('asset.location', string="Location", required="1")
