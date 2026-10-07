# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from pytz import timezone
from datetime import datetime
import pytz
import datetime as dt
import datetime

from odoo.exceptions import UserError, ValidationError

class ActualAttendance(models.Model):
    _name = 'actual.attendance'
    _description = 'Actual Attendance'

    date = fields.Date(string='Date', required=True)
    emp_no = fields.Char(string='Employee Number')
    employee_name = fields.Char(string='Employee Name')
    task = fields.Char(string='Task Code')
    actual_type = fields.Char(string='Type')

    employee_id = fields.Many2one('hr.employee', string="Employee Name")
    task_id = fields.Many2one('project.task', string="Task")

    status = fields.Selection(
        [('general', 'General'), ('idle', 'Idle'), ('stand_by', 'Stand By'), ('on_duty', 'On Duty'),
         ('training', 'Training')], default='on_duty', tracking=True, string='Status')
    day1 = fields.Char(string='D1')
    day2 = fields.Char(string='D2')
    day3 = fields.Char(string='D3')
    day4 = fields.Char(string='D4')
    day5 = fields.Char(string='D5')
    day6 = fields.Char(string='D6')
    day7 = fields.Char(string='D7')
    day8 = fields.Char(string='D8')
    day9 = fields.Char(string='D9')
    day10 = fields.Char(string='D10')
    # up to Day 20
    day11 = fields.Char(string='D11')
    day12 = fields.Char(string='D12')
    day13 = fields.Char(string='D13')
    day14 = fields.Char(string='D14')
    day15 = fields.Char(string='D15')
    day16 = fields.Char(string='D16')
    day17 = fields.Char(string='D17')
    day18 = fields.Char(string='D18')
    day19 = fields.Char(string='D19')
    day20 = fields.Char(string='D20')
    # up to Day 31
    day21 = fields.Char(string='D21')
    day22 = fields.Char(string='D22')
    day23 = fields.Char(string='D23')
    day24 = fields.Char(string='D24')
    day25 = fields.Char(string='D25')
    day26 = fields.Char(string='D26')
    day27 = fields.Char(string='D27')
    day28 = fields.Char(string='D28')
    day29 = fields.Char(string='D29')
    day30 = fields.Char(string='D30')
    day31 = fields.Char(string='D31')
    time = fields.Char(string="Time")
    active = fields.Boolean(string="Active", default=True)

    @api.model
    def create(self, vals):
        if vals.get('emp_no') and not vals.get('employee_id'):
            hr_employee = self.env['hr.employee'].search([('emp_no', 'ilike', vals['emp_no'])], limit=1)
            if hr_employee:
                vals['employee_id'] = hr_employee.id
        if 'task' in vals and not vals.get('task_id'):
            task = self.env['project.task'].search([('seq_code', 'ilike', vals['task'])], limit=1)
            if task:
                vals['task_id'] = task.id
        record = super(ActualAttendance, self).create(vals)
        return record

    @api.onchange('emp_no')
    def onchange_emp_no(self):
        for record in self:
            if record.emp_no:
                hr_id = self.env['hr.employee'].search([('emp_no', 'ilike', record.emp_no)])
                self.write({'employee_id': hr_id.id})

    @api.onchange('task')
    def onchange_task(self):
        for record in self:
            if record.task:
                task_id = self.env['project.task'].search([('seq_code', 'ilike', record.task)])
                self.write({'task_id': task_id.id})

    def convert_to_qatar_timezone(self, datetime_str):
        datetime_obj = fields.Datetime.from_string(datetime_str)
        qatar_timezone = pytz.timezone('Asia/Qatar')
        converted_time = datetime_obj.astimezone(qatar_timezone)
        converted_time -= dt.timedelta(hours=6)
        return converted_time.strftime('%Y-%m-%d %H:%M:%S')

    """ Import Actual Attendnance """
    def post_action(self):
        for record in self:
            if record.active:
                date = record.date
                time_str = record.time
                if not record.time:
                    raise UserError("Please Enter Check In Time!")
                for i in range(1, 32):
                    day_field_name = 'day{}'.format(i)
                    day_value = getattr(record, day_field_name)

                    hr_ids = self.env['hr.employee'].search([('emp_no', '=', record.emp_no)])
                    task_id = self.env['project.task'].search([('seq_code', '=', record.task)])

                    if day_value != False and day_value != 'ABS' and day_value != 'SICK' and day_value != 'W/O':
                        day = date.replace(day=i)
                        date_object = dt.datetime.strptime(str(day), '%Y-%m-%d').date()
                        formats = ['%H:%M', '%H:%M:%S']
                        for fmt in formats:
                            try:
                                parsed_time = dt.datetime.strptime(str(time_str),fmt).time()
                                mytime = parsed_time
                                check_in = dt.datetime.combine(date_object, mytime)

                                # endday_value = dt.datetime.strptime(str(day_value),'%H:%M:%S').time()
                                endday_value = dt.datetime.strptime(str(day_value),fmt).time()

                                hours = endday_value.hour
                                minutes = endday_value.minute
                                seconds = endday_value.second

                                check_out = check_in + dt.timedelta(hours=hours, minutes=minutes, seconds=seconds)

                                checkin_time = self.convert_to_qatar_timezone(check_in)
                                checkout_time = self.convert_to_qatar_timezone(check_out)
                                for hr_id in hr_ids:
                                    if record.employee_id or hr_id:
                                        attendance_vals = {
                                            'employee_id': record.employee_id.id or hr_id.id,
                                            'check_in': checkin_time,
                                            'check_out': checkout_time,
                                            'status': record.status,
                                            'task_id': record.task_id.id,
                                            'emp_id': record.task_id.emp_id.id,
                                            'partner_id': record.task_id.partner_id.id,
                                            'sale_order_id': record.task_id.sale_order_id.id,
                                        }
                                        attendance_id = self.env['hr.attendance'].create(attendance_vals)
                                        record.write({'active': False})
                                        attendance_id.task_id._update_task_timesheet(record.employee_id or hr_id,attendance_id)
                                    else:
                                        raise ValidationError(_("Employee Number '%s' does not exists!" % (record.emp_no)))

                            except ValueError:
                                pass
            else:
                raise UserError("This Attendance is one time Posted")