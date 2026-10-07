from odoo import api, models, fields, _
from datetime import date
import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import timedelta, date
from datetime import datetime, timedelta
import math


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sick_leave_rule_id = fields.Many2one('sick.leave.rule', 'Sick Leave Rule')

class SickLeaveRule(models.Model):
    _name = "sick.leave.rule"
    _description = "Sick Leave Rule"

    name = fields.Char(string="Name")
    date = fields.Date('Date', default=fields.Date.today())
    rule_line_ids = fields.One2many('sick.leave.rule.lines', 'rule_line_id', string='Leave Rule Lines')

    @api.model
    def default_get(self, fields):
        vals = super(SickLeaveRule, self).default_get(fields)
        line = [(0, 0, {'from_day': 0, 'to_day': 90, 'is_service_year_only': True, 'leave_type': 'unpaid'}),
        (0, 0, {'from_day': 0, 'to_day': 14, 'is_service_year_only': False, 'leave_type': 'paid'}),
        (0, 0, {'from_day': 15, 'to_day': 42, 'is_service_year_only': False, 'leave_type': 'half_pay'}),
        (0, 0, {'from_day': 43, 'to_day': 0, 'is_service_year_only': False, 'leave_type': 'unpaid'})]
        vals['rule_line_ids'] = line
        return vals

class SickLeaveRuleLines(models.Model):
    _name = "sick.leave.rule.lines"
    _description = "Sick Leave Rule Lines"

    rule_line_id = fields.Many2one('sick.leave.rule')
    from_day = fields.Integer('From')
    to_day = fields.Integer('To')
    is_service_year_only = fields.Boolean('Applied on Service Year')
    leave_type = fields.Selection([('paid', 'Paid Leave'), ('half_pay', 'Half Paid Leave'), ('unpaid', 'Unpaid Leave')], string='Leave Type')


class HrPaysleepInherit(models.Model):
    _inherit = 'hr.payslip'

    paid_sick_leave = fields.Float('Paid Sick Leave', readonly=1)
    unpaid_sick_leave = fields.Float('Unpaid Sick Leave', compute="_compute_unpaid_sick_leave")
    is_paid_sick = fields.Boolean('Is Paid Sick', readonly=1)
    is_unpaid_sick = fields.Boolean('Is Unpaid Sick', readonly=1)
    
    @api.depends('date_from','date_to','contract_id')
    def _compute_unpaid_sick_leave(self):
        for rec in self:
            total_days = 0
            for day in rec._get_date_list():
                total_sick_leaves_days = self.env['hr.leave'].search([
                    ('state', '=', 'validate'),
                    ('holiday_status_id.is_sick_leave', '=', True),
                    ('employee_id', '=', rec.employee_id.id),
                    ('request_date_from', '<=', day),
                    ('request_date_to', '>=', day)])
                if total_sick_leaves_days:
                    total_days += 1
                rec.unpaid_sick_leave = total_days - rec.paid_sick_leave

    @api.depends('worked_days_line_ids')
    def _compute_attendance_total_days(self):
        print('4444433111111',self)
        for rec in self:
            attendance_days = 0
            total_att_days = 0
            # leave_days = rec._get_paid_leaves()
            # for work in rec.worked_days_line_ids.filtered(lambda x: x.work_entry_type_id and x.work_entry_type_id.code in ('WORK100', 'LEAVE120')):
            #     attendance_days += work.number_of_days
            #     total_att_days = attendance_days + leave_days
            #     if total_att_days > rec.salary_days:
            total_att_days = rec.public_holidays + rec.present_day + rec.leave_day + rec.shift_days + rec.paid_sick_leave
            rec.attendance_days = rec.salary_days if total_att_days > rec.salary_days else total_att_days

    @api.depends('worked_days_line_ids')
    def _compute_leave_day(self):
        for rec in self:
            leave_days = rec._get_paid_leaves()
            paid_sick_leaves, unpaid_sick_leaves = rec._get_paid_unpaid_sick_leave_days()
            rec.leave_day = leave_days
            rec.paid_sick_leave = paid_sick_leaves
            # rec.unpaid_sick_leave = unpaid_sick_leaves

# <<<<<<< HEAD
#     @api.depends('worked_days_line_ids')
#     def _compute_leave_day(self):
#         for rec in self:
#             leave_days = rec._get_paid_leaves()
#             paid_sick_leaves , unpaid_sick_leaves = self._get_paid_unpaid_sick_leave_days()
#             print('leave_daysleave_daysleave_daysleave_days=============',leave_days)
#             print('paid_sick_leaves=============',paid_sick_leaves)
#             print('unpaid_sick_leaves=============',unpaid_sick_leaves)
#             rec.leave_day = leave_days
#             rec.paid_sick_leave = paid_sick_leaves
#             rec.unpaid_sick_leave = unpaid_sick_leaves


# =======
# >>>>>>> 0d2a1c6847c60b66b19f13a6f35e21573196038f

    # Globalteckz
    def _get_paid_unpaid_sick_leave_days(self):
        sick_leave_ids = self.env['hr.leave']
        total_leave_days = 0.0
        total_service_days = 0.0
        actual_paid_leaves = 0.0
        actual_unpaid_leaves = 0.0
        if self.employee_id:
            emp_hire_date = self.employee_id.original_hire_date
            delta = self.date_to - emp_hire_date
            total_service_days = delta.days + 1
            days_range_set = [self.employee_id.original_hire_date + timedelta(days=i) for i in range(total_service_days)]


            rule_id = self.env['sick.leave.rule'].search([], limit=1)
            if self.employee_id.sick_leave_rule_id:
                rule_line_ids = self.employee_id.sick_leave_rule_id.rule_line_ids
            else:
                rule_line_ids = rule_id.rule_line_ids

            date_start = self.date_from
            date_end = self.date_to
            total_days = 0.0
            total_days_unpaid = 0.0
            total_days_paid = 0.0
            if total_service_days <= 365 and rule_line_ids:
                non_service_year_rule_range = rule_line_ids.filtered(lambda x: x.is_service_year_only).sorted(
                    key=lambda r: r.to_day, reverse=True)

                difference_service_days = (non_service_year_rule_range[0].to_day)
                from_day = self.employee_id.original_hire_date + timedelta(days=int(difference_service_days) - 1)
                days_range_set = [self.employee_id.original_hire_date + timedelta(days=i) for i in
                                  range(difference_service_days)]

    # Before 90 Days
    #             sick off before 90 days
                if date_start <= from_day and date_end <= from_day:

                    delta_set = date_end - date_start
                    days_range_set = [date_start + timedelta(days=i) for i in range(delta_set.days + 1)]
                    for day in days_range_set:
                        total_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if total_sick_leaves_days:
                            total_days += 1

                    actual_unpaid_leaves = actual_unpaid_leaves + total_days

                elif date_start <= from_day and date_end > from_day:

                    delta_bef = from_day - date_start
                    days_range_bef = [date_start + timedelta(days=i) for i in range(delta_bef.days + 1)]
                    for day in days_range_bef:
                        total_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if total_sick_leaves_days:
                            total_days_unpaid += 1

                    actual_unpaid_leaves = actual_unpaid_leaves + total_days_unpaid


                    delta_aft = date_end - from_day
                    start_date_aft = from_day + relativedelta(days=1)
                    days_range_aft = [start_date_aft + timedelta(days=i) for i in range(delta_aft.days)]
                    for day in days_range_aft:
                        total_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if total_sick_leaves_days:
                            total_days_paid += 1

                    actual_paid_leaves = actual_paid_leaves + total_days_paid



                    full_paid_rule =  rule_line_ids.filtered(lambda x: x.leave_type == 'paid')
                    half_paid_rule =  rule_line_ids.filtered(lambda x: x.leave_type == 'half_pay')
                    un_paid_rule =  rule_line_ids.filtered(lambda x: x.leave_type == 'unpaid' and not x.is_service_year_only)

                    if actual_paid_leaves and actual_paid_leaves <= full_paid_rule.to_day:
                        actual_paid_leaves = actual_paid_leaves
                    elif actual_paid_leaves >= half_paid_rule.from_day and actual_paid_leaves <= half_paid_rule.to_day:
                        actual_paid_leaves = full_paid_rule.to_day + (actual_paid_leaves - full_paid_rule.to_day) / 2
                    elif actual_paid_leaves > un_paid_rule.from_day:
                        full_paid = full_paid_rule.to_day
                        unpaid = actual_paid_leaves - half_paid_rule.to_day
                        half_paid = actual_paid_leaves - unpaid - full_paid
                        actual_paid_leaves = full_paid + half_paid / 2
                        actual_unpaid_leaves = actual_unpaid_leaves + unpaid


    # After 90 days

                elif date_start > from_day:
                    paid_days = 0.0
                    delta = date_start - from_day
                    days_range = [(from_day + timedelta(days=1)) + timedelta(days=i) for i in range(delta.days - 1)]
                    for day in days_range:
                        total_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if total_sick_leaves_days:
                            total_days += 1


                    full_paid_rule = rule_line_ids.filtered(lambda x: x.leave_type == 'paid')
                    half_paid_rule = rule_line_ids.filtered(lambda x: x.leave_type == 'half_pay')
                    un_paid_rule = rule_line_ids.filtered(lambda x: x.leave_type == 'unpaid' and not x.is_service_year_only)

                    if total_days <= half_paid_rule.to_day:
                        paid_days = total_days
                    elif total_days >= un_paid_rule.from_day:
                        paid_days = half_paid_rule.to_day
                        actual_unpaid_leaves = total_days - paid_days


                    delta_month = date_end - date_start
                    days_range = [date_start + timedelta(days=i) for i in range(delta_month.days + 1)]
                    total_days_month = 0.0
                    for day in days_range:
                        month_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if month_sick_leaves_days:
                            total_days_month += 1

                    if total_days_month and actual_unpaid_leaves:
                       actual_unpaid_leaves = total_days_month
                    elif not actual_unpaid_leaves and paid_days <= half_paid_rule.to_day:
                        total_sum = total_days_month + paid_days
                        if total_sum <= full_paid_rule.to_day:
                            actual_paid_leaves = total_sum - paid_days
                        elif total_sum >= half_paid_rule.from_day and total_sum <= half_paid_rule.to_day and paid_days <= full_paid_rule.to_day:
                            full_pay = full_paid_rule.to_day - paid_days
                            half_pay = total_days_month - full_pay
                            actual_paid_leaves = full_pay + half_pay / 2
                        elif total_sum >= half_paid_rule.from_day and total_sum <= half_paid_rule.to_day and paid_days > full_paid_rule.to_day:
                            half_paying = total_sum - paid_days
                            actual_paid_leaves = half_paying / 2
                        elif total_sum >= un_paid_rule.from_day and paid_days <= full_paid_rule.to_day:
                            remain_full_pay = full_paid_rule.to_day - paid_days
                            remain_half_pay = half_paid_rule.to_day / 2
                            actual_paid_leaves = remain_full_pay + remain_half_pay
                            actual_unpaid_leaves = total_sum - half_paid_rule.to_day
                        elif total_sum >= un_paid_rule.from_day and paid_days > full_paid_rule.to_day:
                            remain_hal_pay = half_paid_rule.to_day - paid_days
                            actual_paid_leaves = remain_hal_pay / 2
                            actual_unpaid_leaves = total_sum - half_paid_rule.to_day

    #  After 365 days
            elif total_service_days > 365:
                service_year_frction = total_service_days / 365
                whole = math.floor(service_year_frction)
                current_serv_start = self.employee_id.original_hire_date + relativedelta(years=whole)
                last_date = self.date_from - timedelta(days=1)
                delta = last_date - current_serv_start

    #  Overlap with First service
                if self.date_from < current_serv_start and whole == 1:
                    non_service_year_rule_range = rule_line_ids.filtered(lambda x: x.is_service_year_only).sorted(
                        key=lambda r: r.to_day, reverse=True)

                    difference_service_days = (non_service_year_rule_range[0].to_day)
                    from_day = self.employee_id.original_hire_date + timedelta(days=int(difference_service_days - 1))

                    paid_days = 0.0
                    delta = date_start - from_day
                    days_range = [(from_day + timedelta(days=1)) + timedelta(days=i) for i in range(delta.days - 1)]
                    for day in days_range:
                        total_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if total_sick_leaves_days:
                            total_days += 1

                    full_paid_rule = rule_line_ids.filtered(lambda x: x.leave_type == 'paid')
                    half_paid_rule = rule_line_ids.filtered(lambda x: x.leave_type == 'half_pay')
                    un_paid_rule = rule_line_ids.filtered(
                        lambda x: x.leave_type == 'unpaid' and not x.is_service_year_only)

                    if total_days <= half_paid_rule.to_day:
                        paid_days = total_days
                    elif total_days >= un_paid_rule.from_day:
                        paid_days = half_paid_rule.to_day
                        actual_unpaid_leaves = total_days - paid_days


                    sec_serv_start = self.employee_id.original_hire_date + relativedelta(years=1)
                    first_service_end = sec_serv_start
                    delta_month = first_service_end - date_start

                    days_range = [date_start + timedelta(days=i) for i in range(delta_month.days)]
                    total_days_month = 0.0
                    for day in days_range:
                        month_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if month_sick_leaves_days:
                            total_days_month += 1

                    if total_days_month and actual_unpaid_leaves:
                        actual_unpaid_leaves = total_days_month
                    elif not actual_unpaid_leaves and paid_days <= half_paid_rule.to_day:
                        total_sum = total_days_month + paid_days
                        if total_sum <= full_paid_rule.to_day:
                            actual_paid_leaves = total_sum - paid_days
                        elif total_sum >= half_paid_rule.from_day and total_sum <= half_paid_rule.to_day and paid_days <= full_paid_rule.to_day:
                            full_pay = full_paid_rule.to_day - paid_days
                            half_pay = total_days_month - full_pay
                            actual_paid_leaves = full_pay + half_pay / 2
                        elif total_sum >= half_paid_rule.from_day and total_sum <= half_paid_rule.to_day and paid_days > full_paid_rule.to_day:
                            half_paying = total_sum - paid_days
                            actual_paid_leaves = half_paying / 2
                        elif total_sum >= un_paid_rule.from_day and paid_days <= full_paid_rule.to_day:
                            remain_full_pay = full_paid_rule.to_day - paid_days
                            remain_half_pay = half_paid_rule.to_day / 2
                            actual_paid_leaves = remain_full_pay + remain_half_pay
                            actual_unpaid_leaves = total_sum - half_paid_rule.to_day
                        elif total_sum >= un_paid_rule.from_day and paid_days > full_paid_rule.to_day:
                            remain_hal_pay = half_paid_rule.to_day - paid_days
                            actual_paid_leaves = remain_hal_pay / 2
                            actual_unpaid_leaves = total_sum - half_paid_rule.to_day

        # calculate second year sickoff
                    sec_serv_start = self.employee_id.original_hire_date + relativedelta(years=1)
                    first_service_end = sec_serv_start - relativedelta(days=1)
                    delta_month = self.date_to - sec_serv_start

                    days_range = [sec_serv_start + timedelta(days=i) for i in range(delta_month.days + 1)]
                    total_days_month = 0.0
                    for day in days_range:
                        month_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if month_sick_leaves_days:
                            total_days_month += 1


                    next_actual_paid_leaves = 0.0
                    next_actual_unpaid_leaves = 0.0
                    if total_days_month:
                        if total_days_month <= full_paid_rule.to_day:
                            next_actual_paid_leaves = total_days_month
                        elif total_days_month > full_paid_rule.to_day and half_paid_rule.to_day >= total_days_month:
                            next_actual_paid_leaves = full_paid_rule.to_day + (total_days_month - full_paid_rule.to_day) / 2
                        elif total_days_month > half_paid_rule.to_day:
                            next_actual_paid_leaves = full_paid_rule.to_day + ( half_paid_rule.to_day - full_paid_rule.to_day) / 2
                            next_actual_unpaid_leaves = total_days_month - half_paid_rule.to_day

                    actual_paid_leaves = actual_paid_leaves + next_actual_paid_leaves
                    actual_unpaid_leaves = actual_unpaid_leaves + next_actual_unpaid_leaves

    # Overlap from second year sickoff
                elif self.date_from < current_serv_start and whole != 1:
                    before_serv_start = current_serv_start - relativedelta(years=1)

                    paid_days = 0.0
                    delta = date_start - before_serv_start
                    days_range = [before_serv_start + timedelta(days=i) for i in range(delta.days)]
                    for day in days_range:
                        total_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if total_sick_leaves_days:
                            total_days += 1


                    full_paid_rule = rule_line_ids.filtered(lambda x: x.leave_type == 'paid')
                    half_paid_rule = rule_line_ids.filtered(lambda x: x.leave_type == 'half_pay')
                    un_paid_rule = rule_line_ids.filtered(
                        lambda x: x.leave_type == 'unpaid' and not x.is_service_year_only)

                    if total_days <= half_paid_rule.to_day:
                        paid_days = total_days
                    elif total_days >= un_paid_rule.from_day:
                        paid_days = half_paid_rule.to_day
                        actual_unpaid_leaves = total_days - paid_days


        # Calculate second start sickoff
                    before_service_end = current_serv_start - relativedelta(days=1)
                    delta_month = before_service_end - date_start

                    days_range = [date_start + timedelta(days=i) for i in range(delta_month.days + 1)]
                    total_days_month = 0.0
                    for day in days_range:
                        month_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if month_sick_leaves_days:
                            total_days_month += 1


                    if total_days_month and actual_unpaid_leaves:
                        actual_unpaid_leaves = total_days_month
                    elif not actual_unpaid_leaves and paid_days <= half_paid_rule.to_day:
                        total_sum = total_days_month + paid_days
                        if total_sum <= full_paid_rule.to_day:
                            actual_paid_leaves = total_sum - paid_days
                        elif total_sum >= half_paid_rule.from_day and total_sum <= half_paid_rule.to_day and paid_days <= full_paid_rule.to_day:
                            full_pay = full_paid_rule.to_day - paid_days
                            half_pay = total_days_month - full_pay
                            actual_paid_leaves = full_pay + half_pay / 2
                        elif total_sum >= half_paid_rule.from_day and total_sum <= half_paid_rule.to_day and paid_days > full_paid_rule.to_day:
                            half_paying = total_sum - paid_days
                            actual_paid_leaves = half_paying / 2
                        elif total_sum >= un_paid_rule.from_day and paid_days <= full_paid_rule.to_day:
                            remain_full_pay = full_paid_rule.to_day - paid_days
                            remain_half_pay = half_paid_rule.to_day / 2
                            actual_paid_leaves = remain_full_pay + remain_half_pay
                            actual_unpaid_leaves = total_sum - half_paid_rule.to_day
                        elif total_sum >= un_paid_rule.from_day and paid_days > full_paid_rule.to_day:
                            remain_hal_pay = half_paid_rule.to_day - paid_days
                            actual_paid_leaves = remain_hal_pay / 2
                            actual_unpaid_leaves = total_sum - half_paid_rule.to_day

        # calculate second year sickoff
                    delta_month = self.date_to - current_serv_start

                    days_range = [current_serv_start + timedelta(days=i) for i in range(delta_month.days + 1)]
                    total_days_month = 0.0
                    for day in days_range:
                        month_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if month_sick_leaves_days:
                            total_days_month += 1


                    next_actual_paid_leaves = 0.0
                    next_actual_unpaid_leaves = 0.0
                    if total_days_month:
                        if total_days_month <= full_paid_rule.to_day:
                            next_actual_paid_leaves = total_days_month
                        elif total_days_month > full_paid_rule.to_day and half_paid_rule.to_day >= total_days_month:
                            next_actual_paid_leaves = full_paid_rule.to_day + (
                                        total_days_month - full_paid_rule.to_day) / 2
                        elif total_days_month > half_paid_rule.to_day:
                            next_actual_paid_leaves = full_paid_rule.to_day + (
                                        half_paid_rule.to_day - full_paid_rule.to_day) / 2
                            next_actual_unpaid_leaves = total_days_month - half_paid_rule.to_day

                    actual_paid_leaves = actual_paid_leaves + next_actual_paid_leaves
                    actual_unpaid_leaves = actual_unpaid_leaves + next_actual_unpaid_leaves

    # calculate sickoff from second service year
                elif self.date_from >= current_serv_start:

                    paid_days = 0.0
                    delta = date_start - current_serv_start
                    days_range = [current_serv_start + timedelta(days=i) for i in range(delta.days)]

                    for day in days_range:
                        year_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if year_sick_leaves_days:
                            total_days += 1


                    full_paid_rule = rule_line_ids.filtered(lambda x: x.leave_type == 'paid')
                    half_paid_rule = rule_line_ids.filtered(lambda x: x.leave_type == 'half_pay')
                    un_paid_rule = rule_line_ids.filtered(
                        lambda x: x.leave_type == 'unpaid' and not x.is_service_year_only)

                    if total_days <= half_paid_rule.to_day:
                        paid_days = total_days
                    elif total_days >= un_paid_rule.from_day:
                        paid_days = half_paid_rule.to_day
                        actual_unpaid_leaves = total_days - paid_days


                    before_service_end = current_serv_start - relativedelta(days=1)
                    delta_month = date_end - date_start

                    days_range = [date_start + timedelta(days=i) for i in range(delta_month.days + 1)]
                    total_days_month = 0.0
                    for day in days_range:
                        month_sick_leaves_days = self.env['hr.leave'].search([
                            ('state', '=', 'validate'),
                            ('holiday_status_id.is_sick_leave', '=', True),
                            ('employee_id', '=', self.employee_id.id),
                            ('request_date_from', '<=', day),
                            ('request_date_to', '>=', day)])
                        if month_sick_leaves_days:
                            total_days_month += 1


                    if total_days_month and actual_unpaid_leaves:
                        actual_unpaid_leaves = total_days_month
                    elif not actual_unpaid_leaves and paid_days <= half_paid_rule.to_day:
                        total_sum = total_days_month + paid_days
                        if total_sum <= full_paid_rule.to_day:
                            actual_paid_leaves = total_sum - paid_days
                        elif total_sum >= half_paid_rule.from_day and total_sum <= half_paid_rule.to_day and paid_days <= full_paid_rule.to_day:
                            full_pay = full_paid_rule.to_day - paid_days
                            half_pay = total_days_month - full_pay
                            actual_paid_leaves = full_pay + half_pay / 2
                        elif total_sum >= half_paid_rule.from_day and total_sum <= half_paid_rule.to_day and paid_days > full_paid_rule.to_day:
                            half_paying = total_sum - paid_days
                            actual_paid_leaves = half_paying / 2
                        elif total_sum >= un_paid_rule.from_day and paid_days <= full_paid_rule.to_day:
                            remain_full_pay = full_paid_rule.to_day - paid_days
                            remain_half_pay = half_paid_rule.to_day / 2
                            actual_paid_leaves = remain_full_pay + remain_half_pay
                            actual_unpaid_leaves = total_sum - half_paid_rule.to_day
                        elif total_sum >= un_paid_rule.from_day and paid_days > full_paid_rule.to_day:
                            remain_hal_pay = half_paid_rule.to_day - paid_days
                            actual_paid_leaves = remain_hal_pay / 2
                            actual_unpaid_leaves = total_sum - half_paid_rule.to_day


            self.is_paid_sick = True if actual_paid_leaves else False
            self.is_unpaid_sick = True if actual_unpaid_leaves else False
        return actual_paid_leaves , actual_unpaid_leaves

#     def _get_unpaid_leaves(self):
#         unpaid_leave = super(HrPaysleepInherit, self)._get_unpaid_leaves()
#         unpaid_sick_leave = self.unpaid_sick_leave
#         if unpaid_sick_leave:
#             unpaid_leave += unpaid_sick_leave
#         return unpaid_leave

    @api.depends('salary_days','attendance_days','unpaid_day','unpaid_sick_leave')
    def _get_absent_leaves_days(self):
        absent_leave = super(HrPaysleepInherit, self)._get_absent_leaves_days()
        for rec in self:
            if rec.unpaid_sick_leave:
                rec.absent_day = float(rec.salary_days) - float(rec.attendance_days) - float(rec.unpaid_day) - float(rec.unpaid_sick_leave)
                return rec.absent_day
            else:
                rec.absent_day = 0.0
                return rec.absent_day
