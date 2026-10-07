# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ShiftAllocation(models.Model):
    _inherit = "shift.allocation"

    task_id = fields.Many2one('project.task', string='Task', copy=False)
    planning_id = fields.Many2one('planning.slot', string='Planning')
