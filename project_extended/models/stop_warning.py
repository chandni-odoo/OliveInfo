# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class LpoControlLine(models.Model):
    _name = 'stop.warning'
    _description = "Stop Warning Control"

    stop_check = fields.Boolean('Stop')
    warning_check = fields.Boolean('Warning')

    @api.onchange('stop_check')
    def _onchange_stop_check(self):
        if self.stop_check:
            self.warning_check = False

    @api.onchange('warning_check')
    def _onchange_warning_check(self):
        if self.warning_check:
            self.stop_check = False
