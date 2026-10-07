# -*- coding: utf-8 -*-
from odoo import fields, models


class Permit(models.Model):
    _name = 'vehicle.permit'
    _description = 'Permits'

    name = fields.Char(string='Name')
