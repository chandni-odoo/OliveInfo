# -*- coding: utf-8 -*-
from odoo import fields, models, api


class FleetLandfill(models.Model):
    _name = 'fleet.landfill'
    _description = 'Fleet Landfill'

    name = fields.Char(string='Name')
