# -*- coding: utf-8 -*-
from odoo import fields, models


class JobOrderStage(models.Model):
    _name = 'job.order.stage'
    _description = 'Job Order Stage'

    name = fields.Char(string='Name')
