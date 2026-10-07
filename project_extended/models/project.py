# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, timedelta

from datetime import datetime, date
from dateutil import parser
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

import logging
import re
from io import BytesIO



_logger = logging.getLogger(__name__)


class TimeoffRamadan(models.Model):
    _name = 'timeoff.ramadan'
    _description = "Ramadan"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    hours = fields.Float(string="Hours")


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    task_id = fields.Many2one('project.task')
    holiday_task = fields.Boolean('Holiday For task')
    date_difference = fields.Integer(
        string='Days', compute='_compute_date_difference', store=True
    )

    @api.depends('date_from', 'date_to')
    def _compute_date_difference(self):
        for holiday in self:
            if holiday.date_from and holiday.date_to:
                holiday.date_difference = (holiday.date_to - holiday.date_from).days
            else:
                holiday.date_difference = 0


class TaskCalendarLeaves(models.Model):
    _name = 'task.calendar.leaves'
    _description = 'Task Calendar Leaves'

    name = fields.Char(string="Holiday name")
    task_id = fields.Many2one('project.task')
    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")
    remarks = fields.Text(string="Remarks")
    days = fields.Integer(
        string='Days', compute='_compute_date_difference', store=True
    )

    @api.depends('date_from', 'date_to')
    def _compute_date_difference(self):
        for holiday in self:

            if holiday.date_from and holiday.date_to:
                holiday.days = (holiday.date_to - holiday.date_from).days +1
            else:
                holiday.days = 0


class ProjectTask(models.Model):
    _inherit = "project.task"

    seq_code = fields.Char(default='New', readonly=True, copy=False)
    contact_person_id = fields.Many2one('res.partner', string="Contact Person")
    contact_name = fields.Char(string='Contact Name')
    contact_no = fields.Char(string='Contact Number')
    user_id = fields.Many2one('res.users', string="Supervisor")
    emp_id = fields.Many2one('hr.employee', string="Supervisor")
    deployment_date = fields.Date(string='Deployment Date')
    duration = fields.Selection([('unlimited', 'Unlimited'), ('limited', 'Limited')], string='Duration of Contract')
    no_of_prof = fields.Integer(string='No. of Resources')
    trade_test = fields.Boolean(string="Trade Test")
    project_end_date = fields.Date(string="End Date")
    skill_ids = fields.Many2many('hr.skill', string="Skills")
    employee_ids = fields.Many2many('hr.employee', compute="_compute_employee_ids")
    resource_ids = fields.Many2many('hr.employee', string='Resource')
    total_qty = fields.Float(string="Total Quantity", compute='_compute_task_total')
    total_amount = fields.Float(string="Total Amount", compute='_compute_task_total')
    total_hours = fields.Float(string="Total Hours", compute='_compute_task_total')
    # ADD Field
    # customer_location_id = fields.Many2one('res.partner')
    partner_location_id = fields.Many2one('contact.location')
    waste_type_id = fields.Many2one('waste.type')
    equipment_type_id = fields.Many2one('equipment.type')
    own_bin = fields.Char('Own Bin')
    customer_bin = fields.Char('Customer Bin')
    vehicle_type_id = fields.Many2one('vehicle.type')
    hazardous = fields.Boolean(string="Hazardous", related="waste_type_id.hazardous")
    no_of_trip = fields.Float(string="No of Trip")
    quantity = fields.Float(string="Quantity", readonly=True, related="sale_line_id.product_uom_qty")
    unit_id = fields.Many2one('uom.uom', string='UOM', readonly=True, related="sale_line_id.product_uom")
    frequency = fields.Selection(
        [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('on_call', 'On Call')], default='daily',
        string="Freq")
    # frequency_id = fields.Many2one('so.frequency', string="Frequency")
    weekday = fields.Selection(
        [('1', 'Monday'), ('2', 'Tuesday'), ('3', 'Wednesday'), ('4', 'Thursday'), ('5', 'Friday'), ('6', 'Saturday'),
         ('7', 'Sunday'), ], string='Day Name', default='1')
    time = fields.Char()
    vehicle_id = fields.Many2one('fleet.vehicle')
    driver = fields.Many2one('hr.employee')
    helper = fields.Many2one("hr.employee")
    branch_for = fields.Selection(related="branch_id.branch_for")
    branch_id = fields.Many2one('res.branch', string='Branch')
    start_date = fields.Date('Start Date', compute="_compute_date")
    end_date = fields.Date('End Date', compute="_compute_date")
    std_hrs = fields.Float(string="Standerd Hours", related='sale_line_id.std_hrs')
    overtime_lines_ids = fields.One2many('overtime.lines', 'overtime_id')
    attendance_ids = fields.One2many('hr.attendance', 'task_id')
    normal_overtime = fields.Float(string='Normal OverTime', compute='_compute_overtime')
    special_overtime = fields.Float(string='Special OverTime', compute='_compute_overtime')
    shift_allocation_ids = fields.One2many('shift.allocation', 'task_id')

    public_holidays_ids = fields.Many2many('resource.calendar.leaves', compute='_compute_public_holidays',
                                           readonly=False)
    # public_holidays_ids = fields.One2many('resource.calendar.leaves', 'task_id', readonly=False) # comment by shon
    resource_history_ids = fields.One2many('task.resource.history', 'task_id')
    special_sale_line_id = fields.Many2one('sale.order.line', string="Special Overtime")
    normal_sale_line_id = fields.Many2one('sale.order.line', string="Normal OverTime")
    t_hours_spent = fields.Float(string="Total Hours Spent")
    units_amounts = fields.Float(string="Total Hours Spent")

    # override planned_hours
    planned_hours = fields.Float("Initially Planned Hours", related='total_hours', store=True,
                                 help='Time planned to achieve this task (including its sub-tasks).', tracking=True)

    # Point no 8 PS2
    remaining_amount = fields.Float("Remaining Amount", compute='_compute_remaining_amount', store=False, readonly=True,
                                    help="Total remaining amount, can be re-estimated periodically by the assignee of the task.")

    # def _compute_hazardous(self):
    #     self.hazardous = self.waste_type_id.hazardous

    public_holidays_count = fields.Integer(
        string='Public Holidays Count', compute='_compute_public_holidays_count')
    # public_holidays_task = fields.Many2many('task.calendar.leaves', 'task_id')

    public_holidays_task = fields.One2many(
        'task.calendar.leaves', 'task_id', string="Task Holidays"
    )

    task_holidays_count = fields.Integer(
        string='Task Holidays Count', compute='_compute_task_public_holidays_count')

    def _compute_public_holidays_count(self):
        for task in (self):
            task.public_holidays_count = sum(self.public_holidays_ids.mapped('date_difference'))

    @api.depends('public_holidays_task.days')
    def _compute_task_public_holidays_count(self):
        for task in (self):
            task.task_holidays_count = sum(self.public_holidays_task.mapped('days'))

    # @api.model # will remove this block
    # def fetch_public_holidays(self):
    #     for task in self:
    #         if task.start_date and task.end_date:
    #             task_start_date = task.start_date
    #             task_end_date = task.end_date
    #             # Search for public holidays within the task's date range
    #             public_holidays = self.env['resource.calendar.leaves'].search([
    #                 ('date_from', '>=', task.start_date), ('resource_id', '=', False)
    #             ])
    #             holidays = self.env['resource.calendar.leaves'].search(
    #                 [('date_from', '>=', task_start_date), ('resource_id', '=', False)]).ids
    #             # Convert found holidays into task.calendar.leaves records
    #             holiday_lines = []
    #             for holiday in public_holidays:
    #                 existing_holiday = self.env['task.calendar.leaves'].search([
    #                     ('name', '=', holiday.name),
    #                     ('task_id', '=', task.id)
    #                 ], limit=1)
    #                 # Create the holiday record if not already associated with the task
    #                 if not existing_holiday:
    #                     new_holiday = self.env['task.calendar.leaves'].create({
    #                         'name': holiday.name,
    #                         'task_id': task.id,
    #                         'date_from': holiday.date_from.date(), # extract only date
    #                         'date_to': holiday.date_to.date(),
    #                     })
    #                     holiday_lines.append(new_holiday.id)
    #                 else:
    #                     holiday_lines.append(existing_holiday.id)
    #             # Update public_holidays_ids with existing and newly created holidays
    #             task.public_holidays_task = [(4, holiday_id) for holiday_id in holiday_lines]

    def _compute_date(self):
        for record in self:
            if record.sale_order_id.branch_id.branch_for == 'es':
                record.start_date = record.sale_order_id.start_date
                record.end_date = record.sale_order_id.end_date
            else:
                record.start_date = record.sale_line_id.start_date
                record.end_date = record.sale_line_id.end_date

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for vals in lines:
            seq_code = self.env['ir.sequence'].next_by_code('project.task') or ('New')
            if vals.sale_order_id:
                vals.seq_code = (_("%(sale_order_id)s / %(seq_code)s") % {
                    'sale_order_id': vals.sale_order_id.name if vals.sale_order_id else '',
                    'seq_code': seq_code
                })
            else:
                vals.seq_code = seq_code
            if vals.sale_line_id.trade_test:
                lines.write({'trade_test': True})
            # if vals.sale_order_id.location:
            # lines.write({'location_id': vals.sale_order_id.location.id})
        return lines

    @api.onchange('total_hours')
    def _onchange_planned_hours(self):
        self.planned_hours = self.total_hours

    @api.onchange('resource_ids')
    def _onchange_resource_ids(self):
        res_ref = self.env['task.resource.history']
        for resource_id in self.resource_ids:
            if len(self.resource_history_ids.filtered(lambda x: x.employee_id.id == resource_id._origin.id).ids) == 0:
                val = {
                    'employee_id': resource_id._origin.id,
                    'task_id': self.id,
                    'date_start': self.start_date,
                    'date_end': self.end_date,
                }
                res_ref.create(val)

    @api.model
    def _compute_public_holidays(self):
        for task in self:
            # get holiday from 'resource.calendar.leaves and insert in 'task.calendar.leaves
            task_start_date = task.start_date
            task_end_date = task.end_date
            # holidays = self.env['resource.calendar.leaves'].search([('date_from', '>=', task_start_date),('resource_id', '=', False)]).ids
            holidays = self.env['resource.calendar.leaves'].search([
                ('date_from', '>=', task_start_date),
                ('date_to', '<=', task_end_date),
                ('resource_id', '=', False)
            ]).ids
            task.public_holidays_ids = [(6, 0, holidays)]

    def _compute_overtime(self):
        for task in self:
            task.normal_overtime = sum(
                task.overtime_lines_ids.filtered(lambda x: x.ot_type.code == 'NOD' or x.ot_type.code == 'RAMD').mapped(
                    'ot_hour'))
            task.special_overtime = sum(
                task.overtime_lines_ids.filtered(lambda x: x.ot_type.code != 'NOD' and x.ot_type.code != 'RAMD').mapped(
                    'ot_hour'))
            task.normal_sale_line_id.qty_delivered = task.normal_overtime
            task.special_sale_line_id.qty_delivered = task.special_overtime

    def action_open_attendance(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attendance',
            'view_type': 'form',
            'res_model': 'hr.attendance',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': "{'create': False}",
            'domain': [('task_id', '=', self.id)],
        }

    def _find_universal(self, check_in):
        # convert Date to string
        universal_holidays_ids = self.public_holidays_ids.filtered(
            lambda x: x.date_from.date() <= check_in and x.date_to.date() >= check_in)
        if len(universal_holidays_ids.ids) > 0:
            return 'SPHD' if len(universal_holidays_ids.mapped('special_holidays')) > 0 else 'HDS'
        ramadan_leave = self.env['timeoff.ramadan'].search([('date_from', '<=', check_in), ('date_to', '>=', check_in)])
        if ramadan_leave:
            return 'RAMD'
        return False

    def _get_overtime_type(self, check_in, day_of_week_ids=False):
        if day_of_week_ids:
            return 'WDS'
        universal_days = self._find_universal(check_in)
        if universal_days:
            return universal_days
        ramadan_days = self._find_universal(check_in)
        if ramadan_days:
            return ramadan_days
        return 'NOD'

    @api.depends('timesheet_ids.units_amounts')
    def _update_task_timesheet(self, employee, attendance):
        _logger.info("\n<<_update_task_timesheet FUNCTION>>-----------%s", self.filtered(lambda x: x.start_date))

        timesheet = self.env['account.analytic.line'].search(
            [('employee_id', '=', employee.id), ('attendance_id', '=', attendance.id),
             ('date', '=', attendance.check_in.date())], limit=1)

        total_sub_time = round(attendance.worked_hours, 2)
        only_hr = str(total_sub_time).split('.')[0]
        only_min = str(total_sub_time).split('.')[1]
        if int(only_min) == 5:
            only_min = str(only_min) + '0'
        minutes = (int(only_min) * 60 / 100)
        custom_worked = float(only_hr) + float((int(minutes) / 100))

        try:
            if timesheet:
                _logger.info("Updating existing timesheet: %s", timesheet.id)
                timesheet.write({
                    'units_amounts': float(custom_worked),
                })
            else:
                _logger.info("Creating new timesheet for employee: %s", employee.name)

                attendance_date = attendance.check_in.date()

                # Search for public holidays related to the task
                public_holidays = self.env['resource.calendar.leaves'].search([
                    ('date_from', '>=', attendance.task_id.start_date),
                    ('date_to', '<=', attendance.task_id.end_date),
                    ('resource_id', '=', False)
                ])
                task_holidays = self.env['task.calendar.leaves'].search([
                    ('task_id', '=', attendance.task_id.id),
                    ('date_from', '>=', attendance.task_id.start_date),
                    ('date_to', '<=', attendance.task_id.end_date)
                ])

                # public_holidays = self.env['resource.calendar.leaves'].search([
                #     ('holiday_task', '=', attendance.task_id.id)  # Use the correct field
                # ])
                weekend = self.env['hr.day.of.week'].search([
                    ('employee_id', '=', employee.id),
                    ('date', '=', attendance_date)
                ])  # 773589,773591,773593,773595

                std_hours = attendance.task_id.std_hrs  # Default to standard hours

                # Loop through the public holidays to check if attendance falls on any holiday
                for holiday in public_holidays:
                    if holiday.date_from <= attendance.check_in <= holiday.date_to:  # Check if attendance falls within holiday
                        std_hours = 0.0  # Set worked hours to 0 if attendance falls on a holiday
                        _logger.info("Attendance falls on public holiday: %s", holiday.name)
                        break  # Exit the loop since we found a matching holiday
                    elif task_holidays:
                        std_hours = 0.0  # Set worked hours to 0 if attendance falls on a task holiday
                        _logger.info("Attendance falls on public holiday: %s", task_holidays.name)
                    elif weekend:
                        std_hours = 0.0  # Set worked hours to 0 if attendance falls on a weekday

                # Create the analytic line with the proper worked hours
                aal = self.env['account.analytic.line'].create({
                    'account_id': attendance.partner_id.contract_ids[0].id if attendance.partner_id else False,
                    'task_id': attendance.task_id.id if attendance.task_id else False,
                    'date': attendance.check_in.date(),
                    'employee_id': employee.id,
                    'unit_amount': std_hours,  # Set worked hours or 0 if it's a holiday
                    'units_amounts': float(attendance.worked_hours),  # Attendance working hours
                    'name': '/',
                    'attendance_id': attendance.id
                })

                _logger.info("Created new timesheet: %s", aal.id)  # Log the newly created timesheet

                # Update the attendance record with the created analytic line
                attendance.write({
                    'analytic_id': aal.id
                })
        except Exception as e:

            _logger.error("Error while updating/creating timesheet for employee %s: %s", employee.name, str(e))

    # def _update_task_timesheet(self, employee, attendance):
    #     _logger.info("\n<<_update_task_timesheet FUNCTION>>-----------%s", self.filtered(lambda x: x.start_date))
    #
    #     timesheet = self.env['account.analytic.line'].search(
    #         [('employee_id', '=', employee.id), ('attendance_id', '=', attendance.id),
    #          ('date', '=', attendance.check_in.date())], limit=1)
    #
    #     total_sub_time = round(attendance.worked_hours, 2)
    #     only_hr = str(total_sub_time).split('.')[0]
    #     only_min = str(total_sub_time).split('.')[1]
    #     if int(only_min) == 5:
    #         only_min = str(only_min) + '0'
    #     minutes = (int(only_min) * 60 / 100)
    #     custom_worked = float(only_hr) + float((int(minutes) / 100))
    #
    #     if timesheet:
    #         timesheet.write({
    #             # 'unit_amount': attendance.task_id.std_hrs,
    #             'units_amounts': float(custom_worked),
    #         })
    #     else:
    #         # New method to attendance  is on PH checking
    #         attendance_date = attendance.check_in.date()
    #
    #         # Search for public holidays related to the task or general public holidays
    #         public_holidays = self.env['resource.calendar.leaves'].search([
    #             ('task_id', '=', attendance.task_id.id),  # Task-specific holiday
    #         ])
    #         # Initialize worked_hours to the actual worked hours
    #         std_hours = attendance.task_id.std_hrs
    #
    #         # Loop through the public holidays and check if attendance falls within any holiday range
    #         for holiday in public_holidays:
    #             if holiday.date_from <= attendance.check_in <= holiday.date_to:  # Check if attendance falls within holiday
    #                 std_hours = 0.0  # Set worked hours to 0 if attendance falls on a holiday
    #                 break  # Exit the loop since we found a matching holiday
    #         # # Check if attendance date is a public holiday
    #         # if public_holidays:
    #         #     std_hours = 0.0
    #         # else:
    #         #     std_hours = attendance.task_id.std_hrs
    #
    #         aal = self.env['account.analytic.line'].create({
    #             'account_id': attendance.partner_id.contract_ids[0].id if attendance.partner_id else False,
    #             'task_id': attendance.task_id.id if attendance.task_id else False,
    #             'date': attendance.check_in.date(),
    #             'employee_id': employee.id,
    #             # comment by shon on 21 oct 2024 to get zero if public holiday
    #             #'unit_amount': attendance.task_id.std_hrs,  # standard hrs'
    #             'units_amount': std_hours,  # attendance working hrs 0 id PH
    #             'units_amounts': float(attendance.worked_hours),  # attendance working hrs
    #             'name': '/',
    #             'attendance_id': attendance.id
    #         })
    #         attendance.write({
    #             'analytic_id': aal.id
    #         })
    #
    #     # existing_line = self.env['account.analytic.line'].search([('date', '=', parser.parse(record_line['check_in:day']).date()), ('employee_id', '=', employee_id.id), ('task_id', '=', task.id)])
    #     # if existing_line and existing_line.unit_amount != record_line['worked_hours']:
    #     #     existing_line.write({'unit_amount': task.std_hrs})

    @api.onchange('vehicle_id')
    def _onchange_date_to(self):
        if self.vehicle_id:
            self.driver = self.vehicle_id.driver and self.vehicle_id.driver.id
            self.helper = self.vehicle_id.helper and self.vehicle_id.helper.id

    def _compute_task_total(self):
        for task in self:
            lpo_line_ids = self.env['lpo.control.line'].search([('sale_order_line_id', '=', task.sale_line_id.id)])
            task.total_qty = sum(lpo_line_ids.mapped('quantity'))
            task.total_amount = sum(lpo_line_ids.mapped('amount'))
            task.total_hours = sum(lpo_line_ids.mapped('no_of_hour'))
            task.t_hours_spent = sum(task.timesheet_ids.mapped('units_amounts'))

    # @api.depends('effective_hours', 'subtask_effective_hours', 'planned_hours')
    def _compute_remaining_hours(self):
        for task in self:
            task.remaining_hours = task.planned_hours - task.t_hours_spent

    # @api.depends('effective_hours', 'subtask_effective_hours', 'planned_hours')
    def _compute_remaining_amount(self):
        for rec in self:
            sale_line = None
            hours_spent_total = 0
            for timesheet in rec.timesheet_ids:
                hours_spent_total = hours_spent_total + (timesheet.so_line.price_unit * timesheet.unit_amount)
                sale_line = timesheet.so_line

            if sale_line:
                normal_hours_spent_total = sale_line.overtime * rec.normal_overtime if sale_line.overtime else 0
                special_hours_spent_total = sale_line.sp_overtime * rec.special_overtime if sale_line.sp_overtime else 0
            else:
                normal_hours_spent_total = 0
                special_hours_spent_total = 0

            rec.remaining_amount = rec.total_amount - (
                    hours_spent_total + normal_hours_spent_total + special_hours_spent_total)

    # @api.depends('skill_ids', 'resource_ids', 'timesheet_ids','timesheet_ids')
    def _compute_employee_ids(self):
        employee_ids = self.env['hr.employee']
        for record in self:
            assigned_emp_ids = self.env['project.task'].search([('resource_ids', '!=', False)]).mapped('resource_ids')
            emp_ids = self.env['hr.employee'].search(
                [('id', 'not in', assigned_emp_ids.ids), ('product_ids', '!=', False)])
            record.employee_ids = emp_ids.filtered(lambda x: record.sale_line_id.product_id in x.product_ids)
            timesheet_ids = record.timesheet_ids
            # overtime_timesheet_ids = record.overtime_lines_ids.mapped('timesheet_id')
            # append_timesheet_ids = timesheet_ids - overtime_timesheet_ids
            overtime_lines = []
            record.remaining_hours = record.planned_hours - record.t_hours_spent
            for timesheet in timesheet_ids:
                ramadan_leave = self.env['timeoff.ramadan']
                day_of_week_ids = timesheet.employee_id.dayofweek_ids.filtered(
                    lambda x: x.date and x.date == timesheet.date)
                universal_holidays_id = self.public_holidays_ids.filtered(
                    lambda x: x.date_from.date() <= timesheet.date and x.date_to.date() >= timesheet.date)
                if not universal_holidays_id or not day_of_week_ids:
                    ramadan_leave = self.env['timeoff.ramadan'].search(
                        [('date_from', '<=', timesheet.date), ('date_to', '>=', timesheet.date)], limit=1)
                    contract_work_hour = ramadan_leave and ramadan_leave.hours or record.std_hrs
                if universal_holidays_id or day_of_week_ids:
                    overtime = timesheet.units_amounts
                else:
                    overtime = timesheet.units_amounts - contract_work_hour
                if overtime > 0:
                    # universal_holidays_id = self.env['resource.calendar.leaves'].search([('date_from', '<=', timesheet.date), ('date_to', '>=', timesheet.date), ('resource_id', '=', False)], limit=1)
                    ot_code = self._get_overtime_type(timesheet.date, day_of_week_ids)
                    ot_type = self.env['hr.ot.type'].search([('code', '=', ot_code)], limit=1)

                    vals = {
                        'employee_id': timesheet.employee_id.id,
                        'timesheet_id': timesheet.id,
                        'ot_date': timesheet.date,
                        'ot_hour': overtime,
                        'overtime_id': record.id,
                        'ot_type': ot_type and ot_type.id,
                    }
                    overtime_id = record.overtime_lines_ids.filtered(
                        lambda x: x.ot_date == timesheet.date and x.employee_id.id == timesheet.employee_id.id)
                    if overtime_id:
                        overtime_id.write({'ot_hour': overtime, 'ot_type': ot_type and ot_type.id})
                    else:
                        self.env['overtime.lines'].create(vals)
                    # overtime_lines.append([0, 0,])
            # record.overtime_lines_ids = overtime_lines

    def action_shift_allocation(self):
        view_id = self.env.ref('pways_hr_shift_allocation.hr_shift_allocation_wizard').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Bulk Allocation'),
            'view_mode': 'form',
            'res_model': 'allocation.wizard',
            'target': 'new',
            'context': {'default_employee_ids': self.resource_ids.ids},
            'views': [[view_id, 'form']],
        }


class OvertimeLines(models.Model):
    _name = "overtime.lines"
    _description = "OverTime Line"

    overtime_id = fields.Many2one('project.task')
    employee_id = fields.Many2one('hr.employee', string="Resource")
    timesheet_id = fields.Many2one('account.analytic.line', string='Analytic Line', ondelete='cascade')
    ot_date = fields.Date(string="OverTime Date")
    ot_hour = fields.Float(string="OverTime Hour")
    ot_type = fields.Many2one('hr.ot.type', string="OT Types")
    invoiced = fields.Boolean(string="Is Invoice")


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    skill_ids = fields.Many2many('hr.skill', string="skills", related='product_id.skill_ids')
    skill_product_ids = fields.Many2many('hr.skill')

    def _timesheet_create_task(self, project):
        task = super(SaleOrderLine, self)._timesheet_create_task(project)
        start_date = task.sale_line_id.start_date
        end_date = task.sale_line_id.end_date
        total_days = end_date - start_date
        # frequency_day = task.sale_line_id.frequency_id.days
        # trip_days = total_days.days
        # total_trip = int(trip_days/frequency_day)
        # for trip in range(total_trip):
        #     trip_id = self.env['trip.sheet'].create({
        #                 'project_task': task.id or False,
        #                 'order_id': self.order_id.id or False,
        #                 'project': task.project_id.id or False,
        #                 'client_id': task.sale_line_id.order_id.partner_id.id or False,
        #             })
        instruction = ''
        if type(self.order_id.instruction) != type(True):
            instruction = self.order_id.instruction
        task.write({
            'skill_ids': self.skill_ids.ids,
            'no_of_prof': self.product_uom_qty,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'duration': self.contract_type,
            'std_hrs': self.std_hrs,
            'branch_id': self.order_id.branch_id.id,
            'contact_name': self.order_id.contact_name,
            'contact_no': self.order_id.mobile,
            'description': instruction,

        })
        if task.sale_line_id.order_id.branch_for == 'hro':
            if self.env.ref('project_extended.product_soc_product_template').id and self.env.ref(
                    'project_extended.product_noc_product_template').id:
                special_sale_line_id = self.env['sale.order.line'].create({
                    'product_id': self.env.ref('project_extended.product_soc_product_template').id or False,
                    # 'employee_id': task.sale_line_id.employee_id.id,
                    'name': "%(line_product_name)s - %(display_name)s - %(task_name)s" % {
                        'line_product_name': task.sale_line_id.product_id.name,
                        'display_name': 'SOC',
                        'task_name': task.seq_code,
                    },
                    # - %(employee_name)s |  'employee_name': task.sale_line_id.employee_id.name,
                    'order_id': self.order_id.id or False,
                    'project_id': task.project_id.id or False,
                    'task_id': task.id,
                    'price_unit': task.sale_line_id.sp_overtime,
                })
                normal_sale_line_id = self.env['sale.order.line'].create({
                    'product_id': self.env.ref('project_extended.product_noc_product_template').id or False,
                    # 'employee_id': task.sale_line_id.employee_id.id,
                    'name': "%(line_product_name)s - %(display_name)s - %(task_name)s" % {
                        'line_product_name': task.sale_line_id.product_id.name,
                        'display_name': 'NOC',
                        'task_name': task.seq_code,
                    },
                    # - %(employee_name)s | 'employee_name': task.sale_line_id.employee_id.name,
                    'order_id': self.order_id.id or False,
                    'project_id': task.project_id.id or False,
                    'task_id': task.id,
                    'price_unit': task.sale_line_id.overtime,
                })
            else:
                raise UserError('Please define Inter reference Code or Product not found for Special OT Product ')
            task.write({'special_sale_line_id': special_sale_line_id.id, 'normal_sale_line_id': normal_sale_line_id.id})
            # if product_special_ot and product_normal_ot:
        # product_special_ot = self.env['product.product'].search([('default_code', '=', 'SOC')], limit=1)
        # product_normal_ot = self.env['product.product'].search([('default_code', '=', 'NOC')], limit=1)
        return task


class ProductTemplate(models.Model):
    _inherit = "product.template"

    skill_ids = fields.Many2many('hr.skill', string="Skills")
    waste_type_id = fields.Many2one('waste.type')
    hazardous = fields.Boolean()
    branch_for = fields.Selection(related='branch_id.branch_for')


class ProductProduct(models.Model):
    _inherit = "product.product"

    skill_ids = fields.Many2many('hr.skill', string="Skills")
    waste_type_id = fields.Many2one('waste.type')
    hazardous = fields.Boolean()
    branch_for = fields.Selection(related='branch_id.branch_for')


class ProjectProject(models.Model):
    _inherit = "project.project"

    total_qty = fields.Float(string="Total Quantity", compute='_compute_project_total')
    total_amount = fields.Float(string="Total Amount", compute='_compute_project_total')
    total_no_of_hour = fields.Float(string="Total Hours", compute='_compute_project_total')
    contact_name = fields.Char(string='Contact Name')
    mobile = fields.Char('Mobile', readonly=False, store=True)

    def _compute_project_total(self):
        for project in self:
            lpo_ids = self.env['lpo.control'].search([('sale_id', '=', project.sale_order_id.id)])
            project.total_qty = sum(lpo_ids.mapped('total_qty'))
            project.total_amount = sum(lpo_ids.mapped('total_amount'))
            project.total_no_of_hour = sum(lpo_ids.mapped('total_no_of_hour'))


class ProjectProject(models.Model):
    _name = "waste.type"
    _description = "waste Types"

    name = fields.Char()
    hazardous = fields.Boolean()


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    equipment_type_id = fields.Many2one('equipment.type')
    hazardous = fields.Boolean()


class EquipmentType(models.Model):
    _name = "equipment.type"
    _description = "Equipment Type"

    name = fields.Char()


class Vehicle(models.Model):
    _inherit = 'fleet.vehicle'

    vehicle_type_id = fields.Many2one('vehicle.type')
    driver = fields.Many2one('hr.employee')
    helper = fields.Many2one('hr.employee')
    product_ids = fields.Many2many('product.product', string="Service Category")
    equipment_type_ids = fields.Many2many('equipment.type')
    hazardous = fields.Boolean()


class VehicleType(models.Model):
    _name = "vehicle.type"
    _description = "Vehicle Type"

    name = fields.Char(string="Name")
    compactor = fields.Boolean()


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    units_amounts = fields.Float(string="Total Hours Spent")
    is_trip_type_visit = fields.Boolean(string="Trip / Visit", help="if field value TRUE means Trip")

    attendance_id = fields.Many2one('hr.attendance', string='Attendance id', ondelete='cascade')
    timesheet_ids = fields.One2many('overtime.lines', 'timesheet_id', string='Timesheets')

    @api.onchange('units_amounts')
    def _onchange_units_amounts(self):
        for rec in self:
            universal_holidays_id = rec.task_id.public_holidays_ids.filtered(
                lambda x: x.date_from.date() <= rec.date and x.date_to.date() >= rec.date)

            task_holidays = self.env['task.calendar.leaves'].search([
                # ('task_id', '=', rec.task_id.id.origin),
                ('task_id', '=', rec.task_id.id),
                ('date_from', '<=', rec.date),
                ('date_to', '>=', rec.date)
            ])

            task_holidays_id = rec.task_id.public_holidays_task.filtered(
                lambda x: x.date_from >= rec.date and x.date_to <= rec.date)

            day_of_week_ids = rec.employee_id.dayofweek_ids.filtered(lambda x: x.date and x.date == rec.date)

            if universal_holidays_id or day_of_week_ids or task_holidays:
                rec.unit_amount = 0.0
            elif rec.units_amounts >= rec.task_id.std_hrs:
                rec.unit_amount = rec.task_id.std_hrs
            else:
                rec.unit_amount = rec.units_amounts

    def unlink(self):
        overtime_lines = self.mapped('timesheet_ids')
        for overtime_line in overtime_lines:
            overtime_line.unlink()
        return super(AccountAnalyticLine, self).unlink()
