# -*- coding: utf-8 -*-
from odoo import fields, models
import logging
_logger = logging.getLogger(__name__)


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    permit_ids = fields.Many2many(
        'vehicle.permit',
        'vehicle_permit_rel'
        'permit_id',
        'vehicle_id',
        string='Permits',
    )
    warranty_details = fields.Text(string="Warranty Details")
    warranty_date = fields.Date(string="Warranty Date")
    vehicle_insurance_ids = fields.One2many('fleet.vehicle.insurance', 'vehicle_id', string="Insurance")
    shift_ids = fields.One2many('fleet.vehicle.shift', 'vehicle_id', string="Shift Details")

    def action_mark_repair(self):
        active_state = self.env.ref('fleet.fleet_vehicle_state_new_request')
        for record in self:
            record.state_id = active_state

    def action_active(self):
        repair_state = self.env.ref('mtech_vehicle_extended.fleet_vehicle_state_repair')
        for record in self:
            record.state_id = repair_state


class FleetVehicleInsurance(models.Model):
    _name = 'fleet.vehicle.insurance'

    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    insurance_company = fields.Many2one('res.partner', string="Insurance Company")
    policy_number = fields.Char(string="Policy Number")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    insurance_amount = fields.Float(string="Insurance Amount")
    premium_amount = fields.Float(string="Premium Amount")
    insurance_type = fields.Selection(
        [('comprehensive', 'Comprehensive'),
         ('third_party', 'Third Party')],
        string="Insurance Type"
    )
    attachment = fields.Binary(string="Attachment")
    attachment_filename = fields.Char(string="Attachment Filename")


class FleetVehicleShift(models.Model):
    _name = 'fleet.vehicle.shift'
    _description = 'Fleet Vehicle Shift'

    scheduled_date = fields.Date(string="Scheduled Date", required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", required=True)
    shift_type = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('night', 'Night')
    ], string="Shift Type", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    employee_type = fields.Selection([
        ('driver', 'Driver'),
        ('helper', 'Helper')
    ], string="Employee Type", required=True)
    active_shift = fields.Boolean(string="Active Shift", default=True)
    assign_shift_id = fields.Many2one('assign.shift', "Assigned Shift")
