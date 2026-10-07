# -*- coding: utf-8 -*-
from odoo import fields, api, models, _
from datetime import date, datetime, timedelta
from ast import literal_eval
import datetime
import time
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import logging
import datetime
import traceback

from collections import Counter
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = "res.company"

    min_overtime = fields.Float(string="Min Overtime")
    max_overtime = fields.Float(string="Max Overtime")
    types = fields.Selection([('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')])


class BtHrOvertimeWizard(models.TransientModel):
    _name = "run.overtime.wizard"
    _description = "Run Overtime wizard"

    def run_overtime_scheduler(self):
        cron = self.env['ir.cron'].sudo().search([('name', '=', 'Run Overtime Scheduler')], limit=1)
        print('cron+++++++++++++++++++', cron)
        cron.sudo().method_direct_trigger()


class BtHrOvertime(models.Model):
    _name = "bt.hr.overtime"
    _description = "Bt Hr Overtime"
    _rec_name = 'employee_id'
    _order = 'id desc'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    manager_id = fields.Many2one('hr.employee', string='Manager')
    start_date = fields.Datetime('Date')
    date = fields.Date(string="Date Overtime")
    overtime_hours = fields.Float('Overtime Hours')
    notes = fields.Text(string='Notes')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'), ('validate', 'Approved'),
         ('cancel', 'Cancelled')], default='draft', copy=False)
    attendance_id = fields.Many2one('hr.attendance', string='Attendance')
    attendance_ids = fields.Many2many('hr.attendance', string='Attendance')
    rate = fields.Float(string="Rate")
    ot_type_id = fields.Many2one('hr.ot.type', string="OT Types")
    is_payslip_create = fields.Boolean(string="Payslip Created")
    payslip_input_id = fields.Many2one('hr.payslip.input', 'Input ID')
    work_hours = fields.Float(string='Working Hours')
    is_ramadan = fields.Boolean(string="Ramadan")

    # def write(self, values):
    #     overtime_id = super(BtHrOvertime, self).write(values)
    #     ramadan_id = self.env['hr.ot.type'].search([('code', '=', 'RAMD')])
    #     for rec in self:
    #         if rec.is_ramadan and rec.ot_type_id.id != ramadan_id.id :
    #             rec.ot_type_id = ramadan_id.id
    #     return overtime_id

    def _find_universal(self, check_in):
        # convert Date to string
        flag = False
        universal_holidays_id = self.env['resource.calendar.leaves'].search(
            [('date_from', '<', check_in), ('date_to', '>', check_in), ('resource_id', '=', False),
             ('holiday_task', '=', False)], limit=1)
        if universal_holidays_id:
            return 'SPHD' if universal_holidays_id.special_holidays else 'HDS'
        return False

    def _find_ramadan(self, check_in):
        # convert Date to string
        flag = False
        ramadan_leave = self.env['timeoff.ramadan'].search([('date_from', '<=', check_in), ('date_to', '>=', check_in)])
        if ramadan_leave:
            return 'RAMD'
        return False

    def _get_overtime_type(self, check_in, day_of_week_ids=False):
        universal_days = self._find_universal(check_in)
        if universal_days:
            return universal_days
        if day_of_week_ids:
            return 'WDS'
        else:
            ramadan_days = self._find_ramadan(check_in)
            if ramadan_days:
                return ramadan_days
            else:
                return 'NOD'

    # def _get_start_end_date(self):
    #     """ This method will check start date and end date in payslip """
    #     date_start = self.date_from
    #     date_end = self.date_to
    #     if self.contract_id and self.date_from < self.contract_id.date_start:
    #         date_start = self.contract_id.date_start
    #     if self.contract_id and self.contract_id.date_end and self.contract_id.date_end < self.date_to:
    #         date_end = self.contract_id.date_end
    #     return date_start, date_end

    def _get_date_list(self):
        from datetime import datetime, timedelta
        date_start, date_end = self._get_start_end_date()
        delta = date_end - date_start  # as timedelta
        return [date_start + timedelta(days=i) for i in range(delta.days + 1)]

    def get_start_stop_datetime(self, day):
        date_start = day.strftime(DEFAULT_SERVER_DATE_FORMAT) + " 00:00:00"
        date_stop = day.strftime(DEFAULT_SERVER_DATE_FORMAT) + " 23:59:59"
        date_utc_start = self._get_utc_time(date_start)
        date_utc_stop = self._get_utc_time(date_stop)
        return date_utc_start, date_utc_stop

    def _get_utc_time(self, date):
        """ Need to configure a time (local to server) in proper manners"""
        user_tz = self.env.user.tz or self.env.context.get('tz') or 'UTC'
        local = pytz.timezone(user_tz)
        date = datetime.datetime.strptime(datetime.datetime.strftime(
            local.localize(datetime.datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(pytz.utc),
            "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
        return date

    # point no 3
    @api.model
    def run_overtime_scheduler(self):
        """ This Function is called by scheduler. """
        attend_signin_ids = self.env['hr.attendance'].sudo().search([('overtime_created', '=', False)], limit=8000)

        for attendance in attend_signin_ids.filtered(
                lambda x: x.check_in and x.check_out and x.employee_id.overtime_eligibility == 'yes'):

            _logger.info("Processing attendance for employee: %s (ID: %s)", attendance.employee_id.name, attendance.employee_id.id)

            start_date, end_date = self.get_start_stop_datetime(attendance.check_in)
            attendance_ids = self.env['hr.attendance'].sudo().search(
                [('employee_id', '=', attendance.employee_id.id), ('check_in', '<', end_date), ('check_in', '>', start_date)])
            work_hours = sum(attendance_ids.mapped('worked_hours'))

            date_check_in = attendance.check_in
            date_check_out = attendance.check_out
            day_of_week_ids = attendance.employee_id.dayofweek_ids.filtered(lambda x: x.date and x.date == date_check_in.date())

            public_leave = self.env['resource.calendar.leaves'].sudo().search(
                [('date_from', '<=', date_check_in), ('date_to', '>=', date_check_out), ('resource_id', '=', False),
                 ('holiday_task', '=', False)], limit=1)

            ramadan_leave = self.env['timeoff.ramadan'].sudo().search(
                [('date_from', '<=', date_check_in.date()), ('date_to', '>=', date_check_in.date())], limit=1)

            full_calculation = public_leave or day_of_week_ids

            contract = self.env['hr.contract'].sudo().search(
                [('employee_id', '=', attendance.employee_id.id), ('state', '=', 'open')], limit=1)

            if contract:
                contract_work_hour = ramadan_leave.hours if ramadan_leave else contract.work_hours
                overtime_hours = work_hours if full_calculation else work_hours - contract_work_hour

                if overtime_hours > 0:
                    overtime_type = self._get_overtime_type(attendance.check_in, day_of_week_ids)
                    ot_type_id = self.env['hr.ot.type'].sudo().search([('code', '=', overtime_type)], limit=1)

                    existing_overtime = self.env['bt.hr.overtime'].sudo().search(
                        [('ot_type_id', '=', ot_type_id.id), ('employee_id', '=', attendance.employee_id.id),
                         ('date', '=', date_check_in.date())], limit=1)

                    if existing_overtime:
                        existing_overtime.write({
                            'overtime_hours': round(overtime_hours, 2),
                            'attendance_ids': [(6, 0, attendance_ids.ids)]
                        })
                    else:
                        vals = {
                            'employee_id': attendance.employee_id.id,
                            'manager_id': attendance.employee_id.parent_id.id if attendance.employee_id.parent_id else False,
                            'start_date': attendance.check_in,
                            'date': date_check_in.date(),
                            'overtime_hours': round(overtime_hours, 2),
                            'work_hours': round(contract_work_hour, 2),
                            'attendance_id': attendance.id,
                            'attendance_ids': [(6, 0, attendance_ids.ids)],
                            'ot_type_id': ot_type_id.id if ot_type_id else False,
                            'is_ramadan': bool(ramadan_leave)
                        }
                        self.env['bt.hr.overtime'].sudo().create(vals)

                    attendance_ids.write({'overtime_created': True})
                    self._cr.commit()

    @api.model
    def run_overtime_scheduler_manually(self):
        """ This Function is called by scheduler. """
        attend_signin_ids = self.env['hr.attendance'].sudo().search([('overtime_created', '=', False)])

        for attendance in attend_signin_ids.filtered(
                lambda x: x.check_in and x.check_out and x.employee_id.overtime_eligibility == 'yes'):

            _logger.info("Processing attendance for employee: %s (ID: %s)", attendance.employee_id.name, attendance.employee_id.id)

            start_date, end_date = self.get_start_stop_datetime(attendance.check_in)
            attendance_ids = self.env['hr.attendance'].sudo().search(
                [('employee_id', '=', attendance.employee_id.id), ('check_in', '<', end_date), ('check_in', '>', start_date)])
            work_hours = sum(attendance_ids.mapped('worked_hours'))

            date_check_in = attendance.check_in
            date_check_out = attendance.check_out
            day_of_week_ids = attendance.employee_id.dayofweek_ids.filtered(lambda x: x.date and x.date == date_check_in.date())

            public_leave = self.env['resource.calendar.leaves'].sudo().search(
                [('date_from', '<=', date_check_in), ('date_to', '>=', date_check_out), ('resource_id', '=', False),
                 ('holiday_task', '=', False)], limit=1)

            ramadan_leave = self.env['timeoff.ramadan'].sudo().search(
                [('date_from', '<=', date_check_in.date()), ('date_to', '>=', date_check_in.date())], limit=1)

            full_calculation = public_leave or day_of_week_ids

            contract = self.env['hr.contract'].sudo().search(
                [('employee_id', '=', attendance.employee_id.id), ('state', '=', 'open')], limit=1)

            if contract:
                contract_work_hour = ramadan_leave.hours if ramadan_leave else contract.work_hours
                overtime_hours = work_hours if full_calculation else work_hours - contract_work_hour

                if overtime_hours > 0:
                    overtime_type = self._get_overtime_type(attendance.check_in, day_of_week_ids)
                    ot_type_id = self.env['hr.ot.type'].sudo().search([('code', '=', overtime_type)], limit=1)

                    existing_overtime = self.env['bt.hr.overtime'].sudo().search(
                        [('ot_type_id', '=', ot_type_id.id), ('employee_id', '=', attendance.employee_id.id),
                         ('date', '=', date_check_in.date())], limit=1)

                    if existing_overtime:
                        existing_overtime.write({
                            'overtime_hours': round(overtime_hours, 2),
                            'attendance_ids': [(6, 0, attendance_ids.ids)]
                        })
                    else:
                        vals = {
                            'employee_id': attendance.employee_id.id,
                            'manager_id': attendance.employee_id.parent_id.id if attendance.employee_id.parent_id else False,
                            'start_date': attendance.check_in,
                            'date': date_check_in.date(),
                            'overtime_hours': round(overtime_hours, 2),
                            'work_hours': round(contract_work_hour, 2),
                            'attendance_id': attendance.id,
                            'attendance_ids': [(6, 0, attendance_ids.ids)],
                            'ot_type_id': ot_type_id.id if ot_type_id else False,
                            'is_ramadan': bool(ramadan_leave)
                        }
                        self.env['bt.hr.overtime'].sudo().create(vals)

                    attendance_ids.write({'overtime_created': True})
                    self._cr.commit()

    def action_submit(self):
        return self.write({'state': 'confirm'})

    def action_cancel(self):
        return self.write({'state': 'cancel'})

    def action_approve(self):
        return self.write({'state': 'validate'})

    def action_refuse(self):
        return self.write({'state': 'refuse'})

    def action_view_attendance(self):
        attendances = self.mapped('attendance_ids')
        action = self.env.ref('hr_attendance.hr_attendance_action').read()[0]
        if len(attendances) > 1:
            action['domain'] = [('id', 'in', attendances.ids)]
        elif len(attendances) == 1:
            action['views'] = [(self.env.ref('hr_attendance.hr_attendance_view_form').id, 'form')]
            action['res_id'] = attendances.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


class Contract(models.Model):
    _inherit = 'hr.contract'

    work_hours = fields.Float(string='Working Hours', default=8)
    type_of_contract = fields.Selection(
        [('normal_days', 'Normal Days'), ('weekday_days', 'Week Days'), ('holidays', 'Holidays'),
         ('special_holidays', 'Special Holidays')], string="Typs of Contract")
    normal_days_rate = fields.Float(string="Normal Days")
    weekday_days_rate = fields.Float(string="Weekday Days")
    holidays_rate = fields.Float(string="Holidays Rate")
    special_holidays = fields.Float(string="Special Holidays")


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    overtime_created = fields.Boolean(string='Overtime Created', default=False, copy=False)


class PayslipOverTime(models.Model):
    _inherit = 'hr.payslip'

    overtime_ids = fields.Many2many('bt.hr.overtime')

    def action_payslip_done(self):
        overtime_ids = self.env['bt.hr.overtime']
        for rec in self:
            bt_overtime_ids = self.env['bt.hr.overtime'].search(
                [('employee_id', '=', rec.employee_id.id), ('start_date', '>=', rec.date_from),
                 ('start_date', '<=', rec.date_to), ('state', '=', 'validate'), ('is_payslip_create', '=', False)])
            overtime_ids |= bt_overtime_ids
            before_bt_overtime_ids = self.env['bt.hr.overtime'].search(
                [('employee_id', '=', rec.employee_id.id), ('start_date', '<=', rec.date_from),
                 ('start_date', '<=', rec.date_to), ('state', '=', 'validate'), ('is_payslip_create', '=', False)])
            overtime_ids |= before_bt_overtime_ids

            if overtime_ids:
                overtime_ids.write({'is_payslip_create': True})
        return super(PayslipOverTime, self).action_payslip_done()

    def action_payslip_cancel(self):
        overtime_ids = self.env['bt.hr.overtime']
        for rec in self:
            bt_overtime_ids = self.env['bt.hr.overtime'].search(
                [('employee_id', '=', rec.employee_id.id), ('start_date', '>=', rec.date_from),
                 ('start_date', '<=', rec.date_to), ('state', '=', 'validate'), ('is_payslip_create', '=', True)])
            overtime_ids |= bt_overtime_ids
            before_bt_overtime_ids = self.env['bt.hr.overtime'].search(
                [('employee_id', '=', rec.employee_id.id), ('start_date', '<=', rec.date_from),
                 ('start_date', '<=', rec.date_to), ('state', '=', 'validate'), ('is_payslip_create', '=', True)])
            overtime_ids |= before_bt_overtime_ids

            if overtime_ids:
                overtime_ids.write({'is_payslip_create': False})
        return super(PayslipOverTime, self).action_payslip_cancel()
