# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta, datetime, time, date
from odoo.tools.float_utils import float_round

import math
import calendar
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

class HolidaysLeave(models.Model):
    _inherit = "hr.leave"

    emergency_contact_number = fields.Char('Emergency Contact Number')
    air_ticket = fields.Selection([('company', 'Company'), ('self', 'Self')], string="Air Ticket")
    address = fields.Text('Address')
    duty_resumption_leave = fields.Boolean("Duty Resumption Done")
    is_calender_day = fields.Boolean("Calender Day")

    check_leave_view = fields.Boolean("Leave Done on Duty Resumption", default=False)
    cal_custom_duration = fields.Float('Planned Duration', readonly=True, copy=False)

    recycle_planning = fields.Selection([('no', 'No'),
        ('from_date', 'From Date')], string="Recycle Planning",
        default='no')
    # custom_duration_hide = fields.Boolean('Hide Duration', default=False, readonly=True, copy=False)

    def count_weekdays(self):
        start_date = self.date_from
        end_date = self.date_to
        day_count = 0
        current_date = start_date
        while current_date <= end_date:
            # if current_date.weekday() < 5:  # 0-4 are weekdays (Monday to Friday)
            day_count += 1
            current_date += timedelta(days=1)
        return day_count

    @api.depends('holiday_status_id', 'date_from', 'date_to', 'employee_id')
    def _compute_number_of_days(self):
        for holiday in self:
            if holiday.holiday_status_id.is_calender_day:
                if holiday.date_from and holiday.date_to:
                    days_count = self.count_weekdays()
                    holiday.number_of_days = days_count
                else:
                    holiday.number_of_days = 0
            else:
                if holiday.date_from and holiday.date_to and holiday.employee_id.id:
                    holiday.number_of_days = \
                        holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)['days']

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date_state(self):
        if self.env.context.get('leave_skip_state_check'):
            return
        for holiday in self:
            if holiday.duty_resumption_leave == False and holiday.state in ['cancel', 'refuse', 'validate1',
                                                                            'validate']:
                raise ValidationError(_("This modification is not allowed in the current state."))

    # @api.constrains('date_from', 'date_to', 'employee_id')
    # def _check_date_state(self):
    #     if self.env.context.get('leave_skip_state_check'):
    #         return
    #     for holiday in self:
    #         print('holiday++++++++++++++++++', holiday)
    #         if holiday.cal_custom_duration > 0:
    #             if holiday.state in ['cancel', 'refuse', 'validate1', 'validate']:
    #                 raise ValidationError(_("This modification is not allowed in the current state."))

    # COMMENT BY SHON ON 21 OCT 2024
    # def action_approve(self):
    #     if not self.env.user.has_group('leave_extended.leave_approval_group'):
    #         raise UserError("You Dont have Access Rights in leave approval group!!!")
    #     return super(HolidaysLeave, self).action_approve()

    def action_validate(self):
        # COMMENT BY SHON ON 21 OCT 2024
        # if not self.env.user.has_group('leave_extended.validate_leave_approved_group'):
        #     raise UserError("You Dont have Access Rights validate leave approved group!!!")

        """ From Date using Recycle Planing Remove Record for Planning Slot """
        if self.recycle_planning == 'from_date':
            if self.request_date_from and self.request_date_to:
                from_date = self.request_date_from.strftime("%Y-%m-%d %H:%M:%S")
                to_date = self.request_date_to.strftime("%Y-%m-%d %H:%M:%S")
                planning = self.env['planning.slot'].search([('employee_id', '=', self.employee_ids.id)])

                """ Planning for Created Time Off """
                for p in planning:
                    date_from = p.start_datetime.date()
                    date_end = p.end_datetime.date()
                    """ Same Date Planning For Selelcted Leave Dates """
                    self.env['planning.slot'].search(
                        [('start_datetime', '=', from_date), ('end_datetime', '=', to_date),
                         ('resource_ids', 'in', self.employee_ids.ids)])

                    # Add Demobilize
                    for demobilize in p.employee_id.task_ids:
                        if demobilize.planning_id == p:
                            demobilize.write({'demobilize_date': from_date,
                                              'remarks': 'Leave Approved ' + from_date + '-' + to_date,
                                              'is_demobilize': True})
                            p.write({'end_datetime': from_date})

                    """ Find Planning for Between Dates """
                    if str(date_from) <= str(self.request_date_from) <= str(date_end):
                        plannnings = self.env['planning.slot'].search(
                            [('start_datetime', '<=', from_date), ('end_datetime', '>=', to_date),
                             ('employee_id', '=', self.employee_ids.id)])

                        for plans in plannnings:
                            for demobilize in plans.employee_id.task_ids:
                                if demobilize.planning_id == plans:
                                    demobilize.write({'demobilize_date': from_date, 'remarks': 'Leave Approved ' + from_date + '-' + to_date, 'is_demobilize': True})
                                    plans.write({'end_datetime': from_date})

        # if not self.env.user.has_group('leave_extended.leave_approval_group'):
        #     raise UserError("You Dont have Access Rights!!!")

        return super(HolidaysLeave, self).action_validate()

    def action_refuse(self):
        print('refuse')
        if not self.env.user.has_group('leave_extended.leave_approval_group'):
            raise UserError("You Dont have Access Rights!!!")
        return super(HolidaysLeave, self).action_refuse()


class HolidaysLeaveType(models.Model):
    _inherit = "hr.leave.type"

    is_calender_day = fields.Boolean("Calender Day")

    allow_duty_resumption = fields.Boolean('Allow Duty Resumption')
    adjust_leave_bal = fields.Boolean('Adjust Leave Balance on Duty Resumption')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    no_of_week_off = fields.Char(string="No Of Week Off's")
    emp_seq = fields.Char()
    passport_id = fields.Char('Passport No', groups="hr.group_hr_user", tracking=True, required=False, default="NA")
    week_off_id = fields.Many2one('no.week.selection', string="No. Of Week Off's")

    @api.model
    def create(self, vals):
        # point no 6
        print('\n\nright', self.env.user.has_group('leave_extended.create_employee_group'))
        if self.env.user.has_group('leave_extended.create_employee_group'):
            if 'hr_employee_type' in vals:
                if vals.get('hr_employee_type') == 'own':
                    vals['emp_seq'] = self.env['ir.sequence'].next_by_code('hr.employee.own') or 'New'
                    vals['emp_no'] = vals['emp_seq']
                else:
                    vals['emp_seq'] = self.env['ir.sequence'].next_by_code('hr.employee.subcontractor') or 'New'
                    vals['emp_no'] = vals['emp_seq']
        else:
            raise UserError('You dont have Rights...')
        return super(HrEmployee, self).create(vals)

    def update_employee_leave_status(self):
        employees = self.env['hr.employee'].search([])
        for emp in employees:
            if emp.emp_status != 'leave':
                leaves = self.env['hr.leave'].search(
                    [('holiday_status_id.is_sick_leave', '=', False), ('employee_id', '=', emp.id),
                     ('request_date_from', '<=', date.today()),
                     ('state', '=', 'validate'),
                     ('request_date_to', '>=', date.today())])
                if leaves:
                    emp.update({
                        'emp_status': 'leave',
                    })


class DutyResumption(models.Model):
    _name = 'duty.resumption'
    _description = 'Duty Resumption'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name")
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    reporting_date = fields.Date(string="Reporting Date", tracking=True, readonly=False, default=date.today())
    duty_resumption_date = fields.Date(string="Duty Resumption Date", tracking=True, readonly=False,
                                       default=date.today())
    reason = fields.Text('Early / Late Reason', tracking=True)
    state = fields.Selection([('new', 'New'), ('approved', 'Approved'), ('cancel', 'Cancel')], default='new',
                             tracking=True)
    leave_id = fields.Many2one('hr.leave', string="Leave", domain=[('duty_resumption_leave', '=', False)])
    leave_type_id = fields.Many2one('hr.leave.type', string="Leave Type", tracking=True,
                                    related="leave_id.holiday_status_id")
    date_from = fields.Date('Start Date', related="leave_id.request_date_from")
    date_to = fields.Date('End Date', related="leave_id.request_date_to")
    early_late_text = fields.Char('Early/Late', compute="_compute_early_late_text", store=True)
    remaining_leaves = fields.Float('Available Leaves', related="leave_type_id.leaves_taken")

    activity_id = fields.Char('Activity')

    @api.depends('reporting_date')
    def _compute_early_late_text(self):
        for rec in self:
            if rec.reporting_date and rec.date_to:
                early_late = (rec.reporting_date - rec.date_to).days
                print('early_late+++++++++++++++++++', early_late)
                if early_late > 1:
                    rec.early_late_text = str(early_late - 1) + ' Days Late'
                elif early_late <= 0:
                    rec.early_late_text = str((-1 * early_late) + 1) + ' Days Early'
                else:
                    rec.early_late_text = 'On Time'
            else:
                rec.early_late_text = ''

    def get_future_leave(self, rec):
        print('get_future_leave+++++++++++++', rec)

        self.ensure_one()
        exist_allowing_leave = 0
        pre_total_allowed_staff_leave = 0

        allocation_with_accural = self.env['hr.leave.allocation'].search(
            [('holiday_status_id', '=', rec.leave_id.holiday_status_id.id),
             ('employee_id', '=', rec.employee_id.id), ('allocation_type', '=', 'accrual')])

        if allocation_with_accural:

            start_date = allocation_with_accural.date_from
            today_date = date.today()
            timedelta = today_date - start_date
            completed_days = timedelta.days
            fraction_year = completed_days / 365
            whole = math.floor(fraction_year)
            curent_service_year = fraction_year - whole
            year_whole = math.ceil(fraction_year)

            accrual_line = []
            for accrual_ratio in allocation_with_accural.accrual_plan_id.level_ids:
                if accrual_ratio.start_count <= completed_days:
                    accrual_line.append(accrual_ratio)
            print('complteeddd ratio+_+_+__+++__+_+_', accrual_line)

            if accrual_line and len(accrual_line) == 1:
                exist_allowing_leave = (1 - curent_service_year) * 365 * accrual_line[0].added_value

            elif accrual_line and len(accrual_line) != 1:
                length = len(accrual_line)
                exist_allowing_leave = (1 - curent_service_year) * 365 * accrual_line[length - 1].added_value

            total_allowed_staff_leave = exist_allowing_leave + rec.leave_id.holiday_status_id.virtual_remaining_leaves
            pre_total_allowed_staff_leave = format(total_allowed_staff_leave, '.2f')

        print('pre_total_allowed_staff_leave+++++++++++++++', pre_total_allowed_staff_leave)
        return pre_total_allowed_staff_leave

    # point no 1
    @api.depends('duty_resumption_date', 'reporting_date', 'date_to')
    def action_create_leave(self):
        for rec in self:
            early_late = (rec.reporting_date - rec.date_to).days
            print('\n\n\nearly_late++++++++++++++++', early_late, )
            print('+duty_resumption_leave++++++++++++', rec.leave_id.duty_resumption_leave)
            print('staff or non stafff++++++++++', rec.leave_type_id.adjust_leave_bal)
            if rec.leave_type_id.adjust_leave_bal:
                # FOR STAFF (NON WORKER)
                if early_late > 1 and rec.leave_id.duty_resumption_leave == False:
                    # LATE
                    early_late = early_late - 1
                    employee = self.env['hr.employee'].browse(rec.employee_id.id)

                    total_leaves = float(employee.allocation_count)
                    remaining_leaves = float(employee.remaining_leaves)
                    print('remaining_leaves+++++++++++++', remaining_leaves)

                    aa = self.get_future_leave(rec)
                    print('+++++++++++++++++++++', aa)

                    r_f = remaining_leaves + float(aa)
                    print('rfrfrfrfrfrfrfrrffrfrf+++++++++', r_f)

                    # left_leaves = float(employee.allocation_count) - float(employee.allocation_used_count)
                    # left_leaves = remaining_leaves
                    left_leaves = remaining_leaves + float(aa)

                    if early_late > left_leaves:
                        # IF LEAVE IS NOT THERE TO ADJUST CREATE UNPAID LEAVE
                        unpaid_leaves = early_late - left_leaves
                        if unpaid_leaves >= 1:
                            unpaid_leaves = unpaid_leaves
                        else:
                            unpaid_leaves = 1

                        actual_selected_leave_days = rec.leave_id.number_of_days
                        leave = self.env['hr.leave'].browse(rec.leave_id.id)
                        new_date_to = leave.request_date_to + timedelta(days=early_late)

                        # if left_leaves > 0:
                        if left_leaves >= 1:
                            existing_leave_end = left_leaves
                            # leave_end_date = rec.leave_id.request_date_to + timedelta(days=int(abs(existing_leave_end)))
                            leave_end_date = rec.reporting_date
                        else:
                            existing_leave_end = 0
                            leave_end_date = rec.leave_id.request_date_to

                        # days = (rec.leave_id.request_date_to - leave_end_date).days
                        # num_sun = days // 7
                        # if (days % 7 + rec.leave_id.request_date_to.isoweekday()) >= 7:
                        #     num_sun += 1
                        # num_sun = abs(num_sun) + 1

                        new_duration = int(rec.leave_id.number_of_days + abs(existing_leave_end))
                        # leave_end_date = leave_end_date + timedelta(days=int(num_sun))
                        leave_end_date = leave_end_date

                        leave.update({
                            'cal_custom_duration': actual_selected_leave_days,
                            'number_of_days': new_duration,
                        })
                        query = "UPDATE hr_leave set request_date_to='%s' where id='%s'" % (leave_end_date, leave.id)
                        self.env.cr.execute(query)

                        # unpaid_duration = early_late - new_duration - 1
                        unpaid_duration = early_late - existing_leave_end

                        ref_leave = self.env['hr.leave']
                        leave_type_id = self.env['hr.leave.type'].search(
                            [('name', 'in', ['Unpaid (Late) - DQ', 'Unpaid (Late) - DS']),
                             ('company_id', '=', rec.employee_id.company_id.id)], limit=1)

                        start_unpaid_date = leave_end_date + timedelta(days=1)
                        end_unpaid_date = start_unpaid_date + timedelta(days=int(abs(unpaid_duration)))

                        leave_vals = {
                            'holiday_status_id': leave_type_id.id,
                            'employee_id': rec.employee_id.id,
                            'number_of_days': math.ceil(unpaid_duration),
                            'request_date_from': start_unpaid_date,
                            'date_from': start_unpaid_date,
                            'request_date_to': end_unpaid_date,
                            'date_to': end_unpaid_date,
                            'duty_resumption_leave': True,
                            'check_leave_view': True,
                        }
                        new_unpaid_leaves = ref_leave.create(leave_vals)
                    else:
                        # IF LEAVE IS THERE TO ADJUST SUBTRACT FROM LEAVE
                        if rec.leave_id:
                            actual_selected_leave_days = rec.leave_id.number_of_days
                            sub_leave = actual_selected_leave_days + early_late
                            leave = self.env['hr.leave'].browse(rec.leave_id.id)
                            new_date_to = leave.request_date_to + timedelta(days=early_late)
                            leave.update({
                                'cal_custom_duration': actual_selected_leave_days,
                                'number_of_days': sub_leave,
                            })
                            query = "UPDATE hr_leave set request_date_to='%s' where id='%s'" % (new_date_to, leave.id)
                            self.env.cr.execute(query)
                if early_late <= 0:
                    # EARLY
                    if early_late == 0:
                        original_early_late = -1
                    else:
                        original_early_late = early_late - 1
                    early_late = early_late - 1
                    if rec.leave_id:
                        actual_selected_leave_days = rec.leave_id.number_of_days
                        # Addition because early date is negative
                        sub_leave = actual_selected_leave_days + early_late
                        leave = self.env['hr.leave'].browse(rec.leave_id.id)
                        new_date_to = leave.request_date_to - timedelta(days=(-1 * original_early_late))
                        leave.update({
                            'cal_custom_duration': actual_selected_leave_days,
                            'number_of_days': sub_leave,
                        })
                        query = "UPDATE hr_leave set request_date_to='%s' where id='%s'" % (new_date_to, leave.id)
                        self.env.cr.execute(query)
            else:
                # FOR NON STAFF (WORKER)
                if early_late > 1 and rec.leave_id.duty_resumption_leave == False:
                    # LATE
                    early_late = early_late - 1

                    unpaid_duration = early_late - rec.leave_id.number_of_days
                    start_unpaid_date = rec.leave_id.request_date_to + timedelta(days=int(1))
                    end_unpaid_date = start_unpaid_date + timedelta(days=int(early_late - 1))

                    ref_leave = self.env['hr.leave']
                    # leave_type_id = self.env['hr.leave.type'].search(
                    #     [('work_entry_type_id.is_paid', '=', False), ('requires_allocation', '=', 'no'),
                    #      ('company_id', '=', rec.employee_id.company_id.id)], limit=1)
                    leave_type_id = self.env['hr.leave.type'].search(
                        [('name', 'in', ['Unpaid (Late) - DQ', 'Unpaid (Late) - DS']),
                         ('company_id', '=', rec.employee_id.company_id.id)], limit=1)

                    # start_unpaid_date = rec.date_to + timedelta(days=1)
                    employee = self.env['hr.employee'].browse(rec.employee_id.id)
                    left_leaves = float(employee.allocation_count) - float(employee.allocation_used_count)
                    unpaid_leaves = early_late - left_leaves
                    if unpaid_leaves >= 1:
                        unpaid_leaves = unpaid_leaves
                    else:
                        unpaid_leaves = 1
                    # if early_late < 1:
                    #     early_late = 1
                    leave_vals = {
                        'holiday_status_id': leave_type_id.id,
                        'employee_id': rec.employee_id.id,
                        'number_of_days': math.ceil(early_late),
                        'request_date_from': start_unpaid_date,
                        'date_from': start_unpaid_date,
                        'request_date_to': end_unpaid_date,
                        'date_to': end_unpaid_date,
                        'duty_resumption_leave': True,
                        'check_leave_view': True,
                    }
                    new_unpaid_leaves = ref_leave.create(leave_vals)
                if early_late <= 0:
                    # EARLY
                    if early_late == 0:
                        original_early_late = -1
                    else:
                        original_early_late = early_late - 1
                    early_late = early_late - 1
                    if rec.leave_id:
                        actual_selected_leave_days = rec.leave_id.number_of_days
                        # Addition because early date is negative
                        sub_leave = actual_selected_leave_days + early_late
                        leave = self.env['hr.leave'].browse(rec.leave_id.id)
                        new_date_to = leave.request_date_to - timedelta(days=(-1 * original_early_late))
                        leave.update({
                            'cal_custom_duration': actual_selected_leave_days,
                            'number_of_days': sub_leave,
                        })
                        query = "UPDATE hr_leave set request_date_to='%s' where id='%s'" % (new_date_to, leave.id)
                        self.env.cr.execute(query)

    def action_approve(self):
        self.action_create_leave()
        self.leave_id.update({
            'duty_resumption_leave': True
        })
        self.employee_id.update({
            'emp_status': 'active',
        })

        if self.activity_id:
            total_activity = self.activity_id.split(', ')
            total_activity = [int(x) for x in total_activity]
            activity_id = self.env['mail.activity'].browse(total_activity)
            for activity in activity_id:
                activity.action_done()

        return self.write({'state': 'approved'})

    @api.onchange('employee_id')
    def _on_change_employee_id(self):
        if self.employee_id:
            self.date_from = False
            self.date_to = False
            self.leave_id = False

    def action_cancel(self):
        leave = self.leave_id
        if leave:
            leave.update({
                'duty_resumption_leave': False
            })

        return self.write({'state': 'cancel'})

    def unlink(self):
        for res in self:
            if res.state == 'approved':
                raise UserError('You cannot Delete the Approved Duty Resumption')
        return super(DutyResumption, self).unlink()

    @api.model
    def create(self, vals):
        res = super(DutyResumption, self).create(vals)

        time_off = res.leave_id
        time_off.write({
            'check_leave_view': True,
            # 'duty_resumption_leave': True,
        })

        users_obj = self.env['res.users']
        users = []
        for user in users_obj.search([]):
            if user.has_group("leave_extended.duty_approval_group"):
                users.append(user.id)

        activity_type = self.env['mail.activity.type'].search(
            [('name', 'like', 'Request Approval for Duty Resumption')], limit=1)

        activity_list = []
        for user in users:
            model_id = self.env['ir.model'].sudo().search([('model', '=', 'duty.resumption')], limit=1)
            activity_vals = {'res_model_id': model_id.id,
                             'res_model': 'duty.resumption',
                             'res_id': res.id,
                             'res_name': 'New Duty Resumption Created!!!',
                             'user_id': user,
                             'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')}
            if activity_type:
                activity_vals.update({
                    'activity_type_id': activity_type.id,
                })
            activity_id = self.env['mail.activity'].create(activity_vals)
            activity_list.append(activity_id.id)

        print('activity_list++++++++++++++++++', activity_list)
        res.update({
            'activity_id': str(', '.join(str(x) for x in activity_list)),
        })

        return res


class NoWeekSelection(models.Model):
    _name = 'no.week.selection'
    _description = 'Week Selection'

    name = fields.Char(string="Name")
