# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AssetLocation(models.Model):
    _name = 'asset.location'
    _description = "Asset Location"

    name = fields.Char(string='Name', required="1")
