# -*- coding: utf-8 -*-
from odoo import fields, models, api


class OperationSchedule(models.Model):
    _name = 'operation.schedule'
    _description = 'Operation Schedule'
    _rec_name = 'scheduled_date'

    assign_shift_id = fields.Many2one('assign.shift', "Assign Shift")
    active_shift = fields.Boolean("Active Shift")
    scheduled_date = fields.Date("Scheduled Date")
    day_name = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string="Day Name", default='monday')
    employee_id = fields.Many2one('hr.employee', "Employee")
    vehicle_id = fields.Many2one('fleet.vehicle', "Vehicle")
    shift_type = fields.Many2one('fleet.shift.type', "Shift Type")
    week_off = fields.Boolean("Week Off")
    employee_type = fields.Selection([
        ('driver', 'Driver'),
        ('helper', 'Helper')
    ], string="Employee Type", required=True)
    company_id = fields.Many2one('res.company', "Company")


    @api.model
    def create(self, vals):
        record = super(OperationSchedule, self).create(vals)
        if vals.get('week_off', False):
            record._create_week_off_record()
        else:
            record._remove_week_off_record()
        return record

    def write(self, vals):
        res = super(OperationSchedule, self).write(vals)
        if 'week_off' in vals:
            for record in self:
                if vals['week_off']:
                    record._create_week_off_record()
                else:
                    record._remove_week_off_record()
        return res

    def _create_week_off_record(self):
        self.ensure_one()
        if not self.week_off or not self.employee_id or not self.scheduled_date:
            return
            
        # Check if record already exists to avoid duplicates
        existing_record = self.env['hr.day.of.week'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '=', self.scheduled_date),
        ], limit=1)
        
        if not existing_record:
            self.env['hr.day.of.week'].create({
                'employee_id': self.employee_id.id,
                'date': self.scheduled_date,
                'week_id': self._get_week_id_for_day(self.day_name),
            })

    def _remove_week_off_record(self):
        self.ensure_one()
        if not self.employee_id or not self.scheduled_date:
            return
            
        # Find and delete any existing week off record for this employee and date
        existing_records = self.env['hr.day.of.week'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '=', self.scheduled_date),
        ])
        
        if existing_records:
            existing_records.unlink()

    def _get_week_id_for_day(self, day_name):
        """Helper method to get the week.week record for the given day name"""
        week_model = self.env['week.week']
        day_mapping = {
            'monday': week_model.search([('name', 'ilike', 'Monday')], limit=1),
            'tuesday': week_model.search([('name', 'ilike', 'Tuesday')], limit=1),
            'wednesday': week_model.search([('name', 'ilike', 'Wednesday')], limit=1),
            'thursday': week_model.search([('name', 'ilike', 'Thursday')], limit=1),
            'friday': week_model.search([('name', 'ilike', 'Friday')], limit=1),
            'saturday': week_model.search([('name', 'ilike', 'Saturday')], limit=1),
            'sunday': week_model.search([('name', 'ilike', 'Sunday')], limit=1),
        }
        return day_mapping.get(day_name, week_model).id

