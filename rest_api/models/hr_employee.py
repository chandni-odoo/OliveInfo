from odoo import models, fields, api
from datetime import timedelta


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'HR Employee'

    imei_number = fields.Char(string='IMEI', copy=False, tracking=True)