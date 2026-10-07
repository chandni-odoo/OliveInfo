# -- coding: utf-8 --

from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class AssignShift(models.Model):
    _name = 'assign.shift'
    _description = 'Assign Shift'
    _rec_name = "vehicle_id"

    vehicle_id = fields.Many2one('fleet.vehicle', "Vehicle")
    shift_type_id = fields.Many2one('fleet.shift.type', "Shift")
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
    emp_week_off = fields.One2many('employee.week.offs', 'assign_shift_id', string="Emp Week Offs")
    schedule_generated = fields.Boolean("Schedule Generated", default=False)

    def unlink(self):
        for record in self:
            self.env['operation.schedule'].search([('assign_shift_id', '=', record.id)]).unlink()
            self.env['fleet.vehicle.shift'].search([('assign_shift_id', '=', record.id)]).unlink()
        return super(AssignShift, self).unlink()

    def get_date_weekday_mapping(self, start_date, end_date):
        """
        Creates a calendar mapping dates to their respective weekdays within the range.
        """
        calendar_dates = {}
        current_date = start_date
        week_counter = {}

        while current_date <= end_date:
            day_name = current_date.strftime('%A').lower()

            if day_name not in calendar_dates:
                calendar_dates[day_name] = []

            calendar_dates[day_name].append(current_date)

            week_number = len(calendar_dates[day_name])
            if day_name not in week_counter:
                week_counter[day_name] = {}
            week_counter[day_name][week_number] = current_date

            current_date += timedelta(days=1)

        return week_counter

    def get_correct_date_from_calendar(self, calendar_dates, week_day, week_number):
        """
        Retrieves the exact date from the pre-generated calendar.
        """
        week_day = week_day.lower()
        if week_day in calendar_dates and week_number in calendar_dates[week_day]:
            return calendar_dates[week_day][week_number]
        return None

    def generate_operation_schedule(self):
        for record in self:
            if record.schedule_generated:
                continue

            if not record.date_from or not record.date_to:
                raise UserError(_("Please set both Date From and Date To."))

            start_date = fields.Date.from_string(record.date_from)
            end_date = fields.Date.from_string(record.date_to)

            scheduled_employees = {}

            current_date = start_date
            while current_date <= end_date:
                current_day = current_date.strftime('%A').lower()

                for emp_week_off in record.emp_week_off:
                    week_off_days = []
                    if emp_week_off.week1:
                        week_off_days.append(emp_week_off.week1.lower())
                    if emp_week_off.week2:
                        week_off_days.append(emp_week_off.week2.lower())
                    if emp_week_off.week3:
                        week_off_days.append(emp_week_off.week3.lower())
                    if emp_week_off.week4:
                        week_off_days.append(emp_week_off.week4.lower())
                    if emp_week_off.week5:
                        week_off_days.append(emp_week_off.week5.lower())

                    if current_day in week_off_days:
                        week_off_val = True
                        active_shift_val = False
                    else:
                        week_off_val = False
                        active_shift_val = True

                    scheduled_employees.setdefault(current_date, set())
                    if emp_week_off.employee_id.id in scheduled_employees[current_date]:
                        raise ValidationError(
                            _("Error: Employee %s is already assigned for date %s!")
                            % (emp_week_off.employee_id.name, current_date.strftime('%d-%b-%Y'))
                        )
                    scheduled_employees[current_date].add(emp_week_off.employee_id.id)

                    schedule_vals = {
                        'assign_shift_id': record.id,
                        'scheduled_date': current_date,
                        'vehicle_id': record.vehicle_id.id,
                        'shift_type': record.shift_type_id.id,
                        'day_name': current_day,
                        'week_off': week_off_val,
                        'active_shift': active_shift_val,
                        'employee_id': emp_week_off.employee_id.id,
                        'employee_type': emp_week_off.week_off_type,
                        'company_id': self.env.company.id,
                    }
                    self.env['operation.schedule'].create(schedule_vals)

                    if record.vehicle_id:
                        record.vehicle_id.write({
                            'shift_ids': [(0, 0, {
                                'scheduled_date': current_date,
                                'shift_type': record.shift_type_id.name.lower(),
                                'employee_id': emp_week_off.employee_id.id,
                                'employee_type': emp_week_off.week_off_type,
                                'active_shift': False,
                            })]
                        })

                current_date += timedelta(days=1)

            record.schedule_generated = True


class EmployeeWeekOffs(models.Model):
    _name = 'employee.week.offs'
    _description = 'Employee Week Offs'

    assign_shift_id = fields.Many2one('assign.shift', "Assigned Shift")
    week_off_type = fields.Selection([
        ('driver', 'Driver'),
        ('helper', 'Helper')
    ], string="Type", default='driver')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    week1 = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string="Week 1", default='monday')
    week2 = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string="Week 2", default='monday')
    week3 = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string="Week 3", default='monday')
    week4 = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string="Week 4", default='monday')
    week5 = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string="Week 5", default='monday')

    # @api.onchange('week_off_type', 'employee_id')
    # def _onchange_week_off_type(self):
    #     if self.week_off_type == 'driver':
    #         return {'domain': {'employee_id': [('is_driver', '=', True)]}}
    #     elif self.week_off_type == 'helper':
    #         return {'domain': {'employee_id': [('is_helper', '=', True)]}}
    #     else:
    #         return {'domain': {'employee_id': []}}

    @api.onchange('week_off_type', 'assign_shift_id')
    def _onchange_week_off_type(self):
        self.employee_id = False
        return self._get_employee_domain()

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        return self._get_employee_domain()

    def _get_employee_domain(self):
        domain = []
        if self.week_off_type == 'driver':
            domain.append(('is_driver', '=', True))
        elif self.week_off_type == 'helper':
            domain.append(('is_helper', '=', True))
        
        # Only filter if we have a valid shift assignment with dates
        if self.assign_shift_id and self.assign_shift_id.date_from and self.assign_shift_id.date_to:
            # Find employees who are already assigned during this period
            overlapping_employees = self.env['employee.week.offs'].search([
                ('employee_id', '!=', False),
                ('week_off_type', '=', self.week_off_type),
                ('assign_shift_id.date_to', '>=', self.assign_shift_id.date_from),
                ('assign_shift_id.date_from', '<=', self.assign_shift_id.date_to),
            ]).mapped('employee_id.id')
            
            # Exclude these employees from the domain
            if overlapping_employees:
                domain.append(('id', 'not in', overlapping_employees))
        
        return {'domain': {'employee_id': domain}}

    @api.constrains('employee_id', 'assign_shift_id')
    def _check_employee_assignments(self):
        for record in self:
            if record.assign_shift_id and record.employee_id:
                overlapping = self.env['employee.week.offs'].search([
                    ('id', '!=', record.id),
                    ('employee_id', '=', record.employee_id.id),
                    ('week_off_type', '=', record.week_off_type),
                    ('assign_shift_id.date_to', '>=', record.assign_shift_id.date_from),
                    ('assign_shift_id.date_from', '<=', record.assign_shift_id.date_to),
                ], limit=1)
                if overlapping:
                    raise ValidationError(_(
                        "Employee %s is already assigned to another shift from %s to %s"
                    ) % (
                        record.employee_id.name,
                        overlapping.assign_shift_id.date_from,
                        overlapping.assign_shift_id.date_to
                    ))
                

    