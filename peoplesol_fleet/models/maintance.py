# -*- coding: utf-8 -*-
from odoo import api, fields, models,_

class Maintance(models.Model):
    _inherit = 'repair.order'

    job_no = fields.Char('Job No.')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Fleet No.')
    license_plate = fields.Char(related="vehicle_id.license_plate")
    make  = fields.Char('Make')
    model = fields.Char('Model')
    km_in = fields.Float('Km In')
    km_out = fields.Float('Km Out')
    date_in  = fields.Datetime('Date In')
    date_out  = fields.Datetime('Date Out')
    checked_id  = fields.Many2one('hr.employee', 'Checked By')
