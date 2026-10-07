# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime, timedelta


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    task_id = fields.Many2one('project.task', string='Task')
    user_id = fields.Many2one('res.users', string="Supervisor", store=True)
    emp_id = fields.Many2one('hr.employee', string="Supervisor", store=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', store=True)
    partner_id = fields.Many2one('res.partner', string='Customer', store=True)
    status = fields.Selection(
        [('general', 'General'), ('idle', 'Idle'), ('stand_by', 'Stand By'), ('on_duty', 'On Duty'),
         ('training', 'Training')], default='on_duty', string='Status')
    analytic_id = fields.Many2one('account.analytic.line', string='Timesheet id', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)

        for vals in vals_list:
            status = vals.get('status', 'general')
            if 'deduct_3' in self._context:
                res.check_in -= timedelta(hours=3)

            check_in_with_offset = res.check_in + timedelta(hours=3)
            check_in_str = datetime.strftime(check_in_with_offset, '%Y-%m-%d %H:%M:%S')

            shift_domain = [
                ('employee_id', '=', res.employee_id.id),
                ('date_from', '<=', check_in_str),
                ('date_to', '>=', check_in_str)
            ]
            if 'deduct_3' not in self._context:
                shift_domain.append(('task_id', '=', res.task_id.id))

            shifts = self.env['shift.allocation'].search(shift_domain)

            if not shifts:
                res.status = status
                continue

            for shift in shifts:
                if not self._is_shift_valid(shift, res, check_in_with_offset):
                    res.status = status
                    continue

                if not self._assign_task_to_attendance(shift, res, check_in_with_offset):
                    res.status = status

        return res

    def _is_shift_valid(self, shift, attendance, check_in_with_offset):
        """Helper method to validate the shift."""
        if 'deduct_3' in self._context:
            check_in_hrs = float(attendance.check_in.strftime('%H-%M').replace("-", "."))
        else:
            check_in_hrs = float((attendance.check_in + timedelta(hours=3)).strftime('%H-%M').replace("-", "."))

        shift_start_time = self._get_shift_start_time(shift)
        return float(shift_start_time) == check_in_hrs

    def _get_shift_start_time(self, shift):
        """Helper method to get the start time of the shift in float format."""
        hours_from_hr = str(shift.shift_id.hours_from).split('.')
        value_to_check = int(hours_from_hr[0])
        value_to_check_min = hours_from_hr[1][:2]
        if int(value_to_check_min) == 5:
            value_to_check_min = str(value_to_check_min) + '0'
        minutes = (int(value_to_check_min) / 100) * 60 / 100
        round_minutes = round(minutes, 2)
        return int(value_to_check) + round_minutes

    def _assign_task_to_attendance(self, shift, attendance, check_in_with_offset):
        """Helper method to assign the task to the attendance."""
        resource_domain = [
            ('task_id', '=', shift.task_id.id),
            ('employee_id', '=', attendance.employee_id.id),
            ('date_start', '<=', check_in_with_offset),
            ('date_end', '>=', check_in_with_offset)
        ]
        resources = self.env['task.resource.history'].search(resource_domain)

        for resource in resources:
            if not resource:
                continue
            if resource.demobilize_date and check_in_with_offset.strftime('%Y-%m-%d') >= resource.demobilize_date.strftime('%Y-%m-%d'):
                continue
            self._update_attendance_from_shift(attendance, shift)
            return True

        return False

    def _update_attendance_from_shift(self, attendance, shift):
        """Helper method to update attendance record with shift information."""
        attendance.task_id = shift.task_id
        attendance.emp_id = shift.task_id.emp_id.id if shift.task_id.emp_id else False
        attendance.sale_order_id = shift.task_id.sale_order_id.id if shift.task_id.sale_order_id else False
        attendance.partner_id = shift.task_id.sale_order_id.partner_id.id if shift.task_id.sale_order_id.partner_id else False
        attendance.status = 'general'
        shift.task_id._update_task_timesheet(attendance.employee_id, attendance)

    def write(self, vals):
        if not self._context.get('from_create', False):
            resource_obj = self.env['task.resource.history']
            if 'check_in' in vals:
                if vals.get('check_in'):
                    check_date = vals.get('check_in')
                    if isinstance(check_date, str):
                        check_date = datetime.strptime(check_date, '%Y-%m-%d %H:%M:%S')
                else:
                    check_date = self.check_in
                    if isinstance(check_date, str):
                        check_date = datetime.strptime(check_date, '%Y-%m-%d %H:%M:%S')
                check_in = datetime.strftime(check_date + timedelta(hours=3), ('%Y-%m-%d'))
                employee_id = vals.get('employee_id') if vals.get('employee_id') else self.employee_id
                shift_obj = self.env['shift.allocation']
                shift_ids = shift_obj.search(
                    [('employee_id', '=', employee_id.id), ('date_from', '<=', check_in), ('date_to', '>=', check_in)])
                if not shift_ids:
                    vals.update({'status': 'stand_by'})
                for shift_id in shift_ids:
                    if shift_id:
                        check_in_hrs = float(
                            datetime.strftime(check_date + timedelta(hours=3), ('%H-%M')).replace("-", "."))
                        hours_from_hr = str(shift_id.shift_id.hours_from).split('.')
                        value_to_check = int(hours_from_hr[0])
                        value_to_check_min = hours_from_hr[1][:2]
                        if int(value_to_check_min) == 5:
                            value_to_check_min = str(value_to_check_min) + '0'
                        minutes = (int(value_to_check_min) / 100) * 60 / 100
                        round_minutes = round(minutes, 2)
                        final_value = int(value_to_check) + round_minutes
                        if float(final_value) == check_in_hrs:
                            if shift_id.task_id:
                                resource_ids = resource_obj.search(
                                    [('task_id', '=', shift_id.task_id.id), ('employee_id', '=', employee_id.id),
                                     ('date_start', '<=', check_in), ('date_end', '>=', check_in)])
                                for resource_id in resource_ids:
                                    if resource_id:
                                        if resource_id.demobilize_date:
                                            resource_date = datetime.strftime(resource_id.demobilize_date, ('%Y-%m-%d'))
                                            check_in_res = datetime.strftime(check_date + timedelta(hours=3), ('%Y-%m-%d'))
                                            if check_in_res < resource_date:
                                                vals.update({'task_id': shift_id.task_id.id, 'status': 'on_duty'})
                                                if shift_id.task_id.emp_id:
                                                    vals.update({'emp_id': shift_id.task_id.emp_id.id})
                                                if shift_id.task_id.sale_order_id:
                                                    vals.update({'sale_order_id': shift_id.task_id.sale_order_id.id})
                                                if shift_id.task_id.sale_order_id.partner_id:
                                                    vals.update(
                                                        {'partner_id': shift_id.task_id.sale_order_id.partner_id.id})
                                        else:
                                            print("IN CONDITION HURRR")
                                            vals.update({'task_id': shift_id.task_id.id, 'status': 'on_duty'})
                                            if shift_id.task_id.emp_id:
                                                vals.update({'emp_id': shift_id.task_id.emp_id.id})
                                            if shift_id.task_id.sale_order_id:
                                                vals.update({'sale_order_id': shift_id.task_id.sale_order_id.id})
                                            if shift_id.task_id.sale_order_id.partner_id:
                                                vals.update({'partner_id': shift_id.task_id.sale_order_id.partner_id.id})

                            else:
                                vals.update({'status': 'stand_by'})
                        else:
                            vals.update(
                                {'status': 'idle', 'emp_id': False, 'task_id': False, 'sale_order_id': False,
                                 'partner_id': False})
                    else:
                        vals.update({'status': 'stand_by'})

        res = super(HrAttendance, self).write(vals)
        if not self._context.get('from_create', False):
            if 'check_in' in vals or 'check_out' in vals:
                if self.employee_id.task_shift_ids or self.employee_id.tasks_shift_allocation_ids:
                    self.mapped('task_id')._update_task_timesheet(self.employee_id, self)
        return res
    
    
