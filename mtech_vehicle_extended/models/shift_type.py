# -*- coding: utf-8 -*-
from odoo import fields, models


class ShiftType(models.Model):
    _name = 'fleet.shift.type'
    _description = 'Shift Type'

    name = fields.Char(string='Name')
