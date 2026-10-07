# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AssetClassification(models.Model):
    _name = 'asset.classification'
    _description = "Asset Classification"

    name = fields.Char(string='Name', required="1")
