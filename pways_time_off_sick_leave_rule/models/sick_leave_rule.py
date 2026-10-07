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

    def _get_sick_leave_days(self):
        print('<<<<<<<<<<<<Sekfl>>>>>',self)
        # nvnmvm
        sick_leave_ids = self.env['hr.leave']
        total_leave_days = 0.0
        if self.employee_id:
            print('###########@@@@@@@@@@@@@@@@@@@2',self._get_date_list())
            for day in self._get_date_list():
                sick_leave_ids |= self.env['hr.leave'].search([
                    ('state', '=', 'validate'),
                    ('employee_id', '=', self.employee_id.id),
                    ('request_date_from', '<=', day),
                    ('request_date_to', '>=', day),
                    ('holiday_status_id.is_sick_leave', '=', True)])

            print('sick_leave_idssick_leave_ids----))))))))))))')
            rule_id = self.env['sick.leave.rule'].search([], limit=1)
            if self.employee_id.sick_leave_rule_id:
                rule_line_ids = self.employee_id.sick_leave_rule_id.rule_line_ids
            else:
                rule_line_ids = rule_id.rule_line_ids

            current_year = fields.Date.today().year
            service_year = self.employee_id.original_hire_date.year
            date_start, date_end = self._get_start_end_date()
            total_days = 0.0
            if current_year == service_year and rule_line_ids:
                non_service_year_rule_range = rule_line_ids.filtered(lambda x: x.is_service_year_only).sorted(key=lambda r: r.to_day, reverse=True)

                difference_service_days = (non_service_year_rule_range[0].to_day)
                print('non_service_year_rule_rangenon_service_year_rule_range=======',non_service_year_rule_range)
                from_day = self.employee_id.original_hire_date + timedelta(days=int(difference_service_days))

                if date_start <= from_day:
                    for sick_leave_id in sick_leave_ids:
                        days_from_joining = (sick_leave_id.request_date_from - self.employee_id.original_hire_date).days
                        for rule in rule_line_ids.filtered(lambda x: x.is_service_year_only):
                            if days_from_joining >= rule.from_day and days_from_joining <= rule.to_day and rule.is_service_year_only:
                                if rule.leave_type == 'paid':
                                    total_leave_days += sick_leave_id.number_of_days
                                elif rule.leave_type == 'half_pay':
                                    total_leave_days += sick_leave_id.number_of_days/2

                elif date_start >= from_day:
                    delta = date_start - from_day
                    days_range = [from_day + timedelta(days=i) for i in range(delta.days + 1)]
                    total_sick_leaves_days = self.env['hr.leave'].search([
                    ('state', '=', 'validate'),
                    ('holiday_status_id.is_sick_leave', '=', True),
                    ('employee_id', '=', self.employee_id.id),
                    ('request_date_from', 'in', days_range),
                    ('request_date_to', 'in', days_range)])
                    print('total_sick_leaves_daystotal_sick_leaves_daystotal_sick_leaves_days======',total_sick_leaves_days)
                    total_days += sum(total_sick_leaves_days.mapped('number_of_days'))
                    print('total_daystotal_daystotal_days====------------',total_days)
                    for sick_leave_id in sick_leave_ids:
                        for rule in rule_line_ids.filtered(lambda x: not x.is_service_year_only):
                            if (total_days >= rule.from_day or (rule.from_day - total_days) == 1) and (total_days + sick_leave_id.number_of_days) <= rule.to_day:
                                total_days += sick_leave_id.number_of_days
                                if rule.leave_type == 'paid':
                                    total_leave_days += sick_leave_id.number_of_days
                                elif rule.leave_type == 'half_pay':
                                    total_leave_days += sick_leave_id.number_of_days/2
                                break

                            elif (total_days >= rule.from_day or (rule.from_day - total_days) == 1) and (total_days + sick_leave_id.number_of_days) > rule.to_day:
                                remaining_days = abs(total_days + sick_leave_id.number_of_days - rule.to_day)
                                total_days += sick_leave_id.number_of_days - remaining_days
                                if rule.leave_type == 'paid':
                                    total_leave_days += (sick_leave_id.number_of_days - remaining_days)
                                elif rule.leave_type == 'half_pay':
                                    total_leave_days += (sick_leave_id.number_of_days - remaining_days)/2

                                for new_rule in rule_line_ids.filtered(lambda x: not x.is_service_year_only and x.id > rule.id):
                                    if (total_days >= new_rule.from_day or (new_rule.from_day - total_days) == 1) and (total_days + remaining_days) <= new_rule.to_day:
                                        total_days += remaining_days
                                        if new_rule.leave_type == 'paid':
                                            total_leave_days += remaining_days
                                        elif new_rule.leave_type == 'half_pay':
                                            total_leave_days += remaining_days/2
                                        break
                                    elif (total_days >= new_rule.from_day or (new_rule.from_day - total_days) == 1) and total_days > new_rule.to_day:
                                        remaining_days_2 = remaining_days - new_rule.to_day
                                        total_days += sick_leave_id.number_of_days - remaining_days_2
                                        if new_rule.leave_type == 'paid':
                                            total_leave_days += (sick_leave_id.number_of_days - remaining_days_2)
                                        elif new_rule.leave_type == 'half_pay':
                                            total_leave_days += (sick_leave_id.number_of_days - remaining_days_2)/2

                                            for line in rule_line_ids.filtered(lambda x: not x.is_service_year_only and x.id > new_rule.id):
                                                if (total_days >= line.from_day or (line.from_day - total_days) == 1) and (total_days + remaining_days_2) <= line.to_day:
                                                    total_days += remaining_days_2
                                                    if line.leave_type == 'paid':
                                                        total_leave_days += remaining_days_2
                                                    elif line.leave_type == 'half_pay':
                                                        total_leave_days += remaining_days_2/2
                                                    break
                                                elif (total_days >= line.from_day  or (line.from_day - total_days) == 1)  and not line.to_day:
                                                    total_days += remaining_days_2
                                                    if line.leave_type == 'paid':
                                                        total_leave_days += remaining_days_2
                                                    elif line.leave_type == 'half_pay':
                                                        total_leave_days += remaining_days_2/2
                                                    break
                                        break
                                    elif (total_days >= new_rule.from_day  or (new_rule.from_day - total_days) == 1) and not new_rule.to_day:
                                        total_days += remaining_days
                                        if new_rule.leave_type == 'paid':
                                            total_leave_days += remaining_days
                                        elif new_rule.leave_type == 'half_pay':
                                            total_leave_days += remaining_days/2
                                        break
                                break

                            elif (total_days >= rule.from_day or (rule.from_day - total_days) == 1) and not rule.to_day:
                                total_days += sick_leave_id.number_of_days
                                if rule.leave_type == 'paid':
                                    total_leave_days += sick_leave_id.number_of_days
                                elif rule.leave_type == 'half_pay':
                                    total_leave_days += sick_leave_id.number_of_days/2
                                break

            elif rule_line_ids :
                date = (str(current_year) + '-01-01')
                start_day = datetime.datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT).date()
                delta = date_start - start_day
                days_range = [start_day + timedelta(days=i) for i in range(delta.days + 1)]
                total_sick_leaves_days = self.env['hr.leave'].search([
                ('state', '=', 'validate'),
                ('holiday_status_id.is_sick_leave', '=', True),
                ('employee_id', '=', self.employee_id.id),
                ('request_date_from', 'in', days_range),
                ('request_date_to', 'in', days_range)])
                total_days += sum(total_sick_leaves_days.mapped('number_of_days'))
                for sick_leave_id in sick_leave_ids:
                    for rule in rule_line_ids.filtered(lambda x: not x.is_service_year_only):
                        if (total_days >= rule.from_day or (rule.from_day - total_days) == 1) and (total_days + sick_leave_id.number_of_days) <= rule.to_day:
                            total_days += sick_leave_id.number_of_days
                            if rule.leave_type == 'paid':
                                total_leave_days += sick_leave_id.number_of_days
                            elif rule.leave_type == 'half_pay':
                                total_leave_days += sick_leave_id.number_of_days/2
                            break

                        elif (total_days >= rule.from_day or (rule.from_day - total_days) == 1) and (total_days + sick_leave_id.number_of_days) > rule.to_day:
                            remaining_days = abs(total_days + sick_leave_id.number_of_days - rule.to_day)
                            total_days += sick_leave_id.number_of_days - remaining_days
                            if rule.leave_type == 'paid':
                                total_leave_days += (sick_leave_id.number_of_days - remaining_days)
                            elif rule.leave_type == 'half_pay':
                                total_leave_days += (sick_leave_id.number_of_days - remaining_days)/2

                            for new_rule in rule_line_ids.filtered(lambda x: not x.is_service_year_only and x.id > rule.id):
                                if (total_days >= new_rule.from_day or (new_rule.from_day - total_days) == 1) and (total_days + remaining_days) <= new_rule.to_day:
                                    total_days += remaining_days
                                    if new_rule.leave_type == 'paid':
                                        total_leave_days += remaining_days
                                    elif new_rule.leave_type == 'half_pay':
                                        total_leave_days += remaining_days/2
                                    break
                                elif (total_days >= new_rule.from_day or (new_rule.from_day - total_days) == 1) and total_days > new_rule.to_day:
                                    remaining_days_2 = remaining_days - new_rule.to_day
                                    total_days += sick_leave_id.number_of_days - remaining_days_2
                                    if new_rule.leave_type == 'paid':
                                        total_leave_days += (sick_leave_id.number_of_days - remaining_days_2)
                                    elif new_rule.leave_type == 'half_pay':
                                        total_leave_days += (sick_leave_id.number_of_days - remaining_days_2)/2

                                        for line in rule_line_ids.filtered(lambda x: not x.is_service_year_only and x.id > new_rule.id):
                                            if (total_days >= line.from_day or (line.from_day - total_days) == 1) and (total_days + remaining_days_2) <= line.to_day:
                                                total_days += remaining_days_2
                                                if line.leave_type == 'paid':
                                                    total_leave_days += remaining_days_2
                                                elif line.leave_type == 'half_pay':
                                                    total_leave_days += remaining_days_2/2
                                                break
                                            elif (total_days >= line.from_day  or (line.from_day - total_days) == 1)  and not line.to_day:
                                                total_days += remaining_days_2
                                                if line.leave_type == 'paid':
                                                    total_leave_days += remaining_days_2
                                                elif line.leave_type == 'half_pay':
                                                    total_leave_days += remaining_days_2/2
                                                break
                                    break
                                elif (total_days >= new_rule.from_day  or (new_rule.from_day - total_days) == 1) and not new_rule.to_day:
                                    total_days += remaining_days
                                    if new_rule.leave_type == 'paid':
                                        total_leave_days += remaining_days
                                    elif new_rule.leave_type == 'half_pay':
                                        total_leave_days += remaining_days/2
                                    break
                            break

                        elif (total_days >= rule.from_day or (rule.from_day - total_days) == 1) and not rule.to_day:
                            total_days += sick_leave_id.number_of_days
                            if rule.leave_type == 'paid':
                                total_leave_days += sick_leave_id.number_of_days
                            elif rule.leave_type == 'half_pay':
                                total_leave_days += sick_leave_id.number_of_days/2
                            break

        return total_leave_days

    # def _get_paid_leaves(self):
    #     print("<<<<<<<_get_paid_leaves_get_paid_leaves>>>>>",self)
    #     paid_leave = super(HrPaysleepInherit, self)._get_paid_leaves()
    #     print('ressdsdfdfdgfpaahdhhhf----========',paid_leave)
    #     sick_leave_days = self._get_sick_leave_days()
    #     print('sick_leave_dayssick_leave_days',sick_leave_days)
    #     if sick_leave_days:
    #         paid_leave += sick_leave_days
    #     return paid_leave

    def _get_unpaid_leaves(self):
        print('----------_get_unpaid_leaves------',self)
        unpaid_leave = super(HrPaysleepInherit, self)._get_unpaid_leaves()
        sick_leave_days = self._get_sick_leave_days()
        if sick_leave_days:
            unpaid_leave -= sick_leave_days
        return unpaid_leave

    # Globalteckz
    def _get_paid_unpaid_sick_leave_days(self):
        actual_paid_sick_leaves = 0.0
        actual_unpaid_sick_leaves = 0.0
        if self.employee_id:
            sick_leave_ids = self.env['hr.leave']
            cur_mon_paid_sick_leaves = 0.0
            paid_sick_leaves = 0.0
            unpaid_sick_leaves = 0.0
            total_service_days = 0
            unpaid_be_ninety = 0
            serv_date_list = []
            employee_hire_date = self.employee_id.original_hire_date
            current_date = fields.Date.today()
            # last_date = self.date_from - timedelta(days=1)
            delta_days = current_date - employee_hire_date  # as timedelta
            print('deltadeltadelta=======-----!!!!!delta_days!!!!!!!!!!!!!!!!-----', delta_days)
            total_service_days = delta_days.days + 1

            if total_service_days <= 90:
                for i in range(delta_days.days + 1):
                    serv_date_list.append(employee_hire_date + timedelta(days=i))
                print('days_listdays_listdays_list((((((((((((((', serv_date_list)

                for day in serv_date_list:
                    sick_leave_ids |= self.env['hr.leave'].search([
                        ('state', '=', 'validate'),
                        ('employee_id', '=', self.employee_id.id),
                        ('request_date_from', '<=', day),
                        ('request_date_to', '>=', day),
                        ('holiday_status_id.is_sick_leave', '=', True)])

                print('total_service_daystotal_service_days', total_service_days)
                print('total_service_daystotal_service_days', sick_leave_ids)
                rule_id = self.env['sick.leave.rule'].search([], limit=1)
                if self.employee_id.sick_leave_rule_id:
                    rule_line_ids = self.employee_id.sick_leave_rule_id.rule_line_ids
                else:
                    rule_line_ids = rule_id.rule_line_ids

                if rule_line_ids and sick_leave_ids:
                    for sick_leave in sick_leave_ids:
                        days_from_joining_start = (sick_leave.request_date_from - self.employee_id.original_hire_date).days
                        days_from_joining_end = (sick_leave.request_date_to - self.employee_id.original_hire_date).days
                        print('days_from_joining_start-----------000000000000',days_from_joining_start)
                        print('days_from_joining_end-----------000000000000',days_from_joining_end)
                        for rule in rule_line_ids.filtered(lambda x: x.is_service_year_only):
                            if days_from_joining_start >= rule.from_day and days_from_joining_start <= rule.to_day and days_from_joining_end >= rule.from_day and days_from_joining_end <= rule.to_day:
                                actual_unpaid_sick_leaves += sick_leave.number_of_days

                            elif days_from_joining_start >= rule.from_day and days_from_joining_start <= rule.to_day:
                                print('-------------------------',days_from_joining_end)
                                paid_leave = days_from_joining_end - rule.to_day
                                unpaid_leave = rule.to_day - days_from_joining_start
                                if paid_leave:
                                    paid_sick_leaves += paid_leave
                                if unpaid_leave:
                                    unpaid_sick_leaves += unpaid_leave

                        if days_from_joining_start > 90:
                            paid_sick_leaves += sick_leave.number_of_days

            # After 90 Days for first year
            elif total_service_days <= 365 and total_service_days > 90:

                current_serv_start = self.employee_id.original_hire_date
                last_date = self.employee_id.original_hire_date + timedelta(days=90)
                delta = last_date - current_serv_start

                days_first_list = []

                for i in range(delta.days + 1):
                    days_first_list.append(current_serv_start + timedelta(days=i))
                print('days_listdays_listdays_list((((((((((((((', days_first_list)

                for day in days_first_list:
                    sick_leave_ids = self.env['hr.leave'].search([
                        ('state', '=', 'validate'),
                        ('employee_id', '=', self.employee_id.id),
                        ('request_date_from', '<=', day),
                        ('request_date_to', '>=', day),
                        ('holiday_status_id.is_sick_leave', '=', True)])
                    print('sick_leave_timeoffssick_leave_timeoffs', sick_leave_ids)
                    print('sick_leave_timeoffssick_leave_timeoffs', day)
                    if sick_leave_ids:
                        unpaid_be_ninety  += 1
                    print('paid_sick_leaves3423453465656457', paid_sick_leaves)


                current_serv_start = self.employee_id.original_hire_date + timedelta(days=90)
                last_date = self.date_from - timedelta(days=1)
                delta = last_date - current_serv_start

                days_first_list = []

                for i in range(delta.days + 1):
                    days_first_list.append(current_serv_start + timedelta(days=i))
                print('days_listdays_listdays_list((((((((((((((', days_first_list)

                for day in days_first_list:
                    sick_leave_ids = self.env['hr.leave'].search([
                        ('state', '=', 'validate'),
                        ('employee_id', '=', self.employee_id.id),
                        ('request_date_from', '<=', day),
                        ('request_date_to', '>=', day),
                        ('holiday_status_id.is_sick_leave', '=', True)])
                    print('sick_leave_timeoffssick_leave_timeoffs', sick_leave_ids)
                    print('sick_leave_timeoffssick_leave_timeoffs', day)
                    if sick_leave_ids:
                        paid_sick_leaves += 1
                    print('paid_sick_leaves3423453465656457', paid_sick_leaves)

                current_date = fields.Date.today()
                last_date = self.date_to - timedelta(days=1)
                delta = self.date_to - self.date_from

                days_list_month = []

                for i in range(delta.days + 1):
                    days_list_month.append(self.date_from + timedelta(days=i))
                print('days_listdays_listdays_list((((((((((((((', days_list_month)

                for day in days_list_month:
                    sick_leave_ids = self.env['hr.leave'].search([
                        ('state', '=', 'validate'),
                        ('employee_id', '=', self.employee_id.id),
                        ('request_date_from', '<=', day),
                        ('request_date_to', '>=', day),
                        ('holiday_status_id.is_sick_leave', '=', True)])
                    print('sick_leave_timeoffssick_leave_timeoffs', sick_leave_ids)
                    if sick_leave_ids:
                        cur_mon_paid_sick_leaves += 1

            #  From second service year
            elif total_service_days > 365:

                service_year_frction = total_service_days / 365
                whole = math.floor(service_year_frction)
                print('wholewholewholewhole',whole)
                remain_frac = service_year_frction - whole
                print('self.employee_id.original_hire_date.year',self.employee_id.original_hire_date.year)
                print('self.employee_id.original_hire_date.year',type(self.employee_id.original_hire_date.year))
                current_serv_start = self.employee_id.original_hire_date + relativedelta(years=whole)
                print('current_serv_startcurrent_serv_start',current_serv_start)
                # current_serv_start = self.employee_id.original_hire_date + timedelta(days=whole * 365)
                current_date = fields.Date.today()
                last_date = self.date_from - timedelta(days=1)
                delta = last_date - current_serv_start

                days_list = []

                for i in range(delta.days + 1):
                    days_list.append(current_serv_start + timedelta(days=i))
                print('days_listdays_listdays_list((((((((((((((',days_list)

                for day in days_list:
                    sick_leave_ids = self.env['hr.leave'].search([
                        ('state', '=', 'validate'),
                        ('employee_id', '=', self.employee_id.id),
                        ('request_date_from', '<=', day),
                        ('request_date_to', '>=', day),
                        ('holiday_status_id.is_sick_leave', '=', True)])
                    print('sick_leave_timeoffssick_leave_timeoffs',sick_leave_ids)
                    print('sick_leave_timeoffssick_leave_timeoffs',day)
                    if sick_leave_ids:
                        paid_sick_leaves += 1
                    print('paid_sick_leaves3423453465656457',paid_sick_leaves)


                # for sick_leave in sick_leave_ids:
                #     paid_sick_leaves += sick_leave.number_of_days
                #
                # For current month sick leave

                service_year_frction = total_service_days / 365
                whole = math.floor(service_year_frction)
                print('wholewholewholewhole',whole)
                remain_frac = service_year_frction - whole
                print('self.employee_id.original_hire_date.year',self.employee_id.original_hire_date.year)
                print('self.employee_id.original_hire_date.year',type(self.employee_id.original_hire_date.year))
                current_serv_start = self.employee_id.original_hire_date + relativedelta(years=whole)
                print('current_serv_startcurrent_serv_start',current_serv_start)
                # current_serv_start = self.employee_id.original_hire_date + timedelta(days=whole * 365)
                current_date = fields.Date.today()
                last_date = self.date_to - timedelta(days=1)
                delta = self.date_to - self.date_from

                days_list = []

                for i in range(delta.days + 1):
                    days_list.append(self.date_from + timedelta(days=i))
                print('days_listdays_listdays_list((((((((((((((',days_list)

                for day in days_list:
                    sick_leave_ids = self.env['hr.leave'].search([
                        ('state', '=', 'validate'),
                        ('employee_id', '=', self.employee_id.id),
                        ('request_date_from', '<=', day),
                        ('request_date_to', '>=', day),
                        ('holiday_status_id.is_sick_leave', '=', True)])
                    print('sick_leave_timeoffssick_leave_timeoffs',sick_leave_ids)
                    if sick_leave_ids:
                        cur_mon_paid_sick_leaves += 1


                # for sick_leave in sick_leave_ids:
                #     cur_mon_paid_sick_leaves += sick_leave.number_of_days




            print('cur_mon_paid_sick_leavescur_mon_paid_sick_leaves-----',cur_mon_paid_sick_leaves)



            # Calculate paid and unpaid leaves
            if (paid_sick_leaves or cur_mon_paid_sick_leaves) and paid_sick_leaves <= 14:
                total_leave = paid_sick_leaves + cur_mon_paid_sick_leaves
                if total_leave <= 14:
                    actual_paid_sick_leaves = cur_mon_paid_sick_leaves
                elif total_leave > 14 and total_leave <= 42:
                    half_pay_sick = (total_leave - 14) / 2
                    full_paid = 14 - paid_sick_leaves
                    actual_paid_sick_leaves = full_paid + half_pay_sick
                elif total_leave and total_leave > 42:
                    actual_unpaid_sick_leaves = total_leave - 42
                    full_paid = 14 - paid_sick_leaves
                    half_pay_sick = (total_leave - 14 - actual_unpaid_sick_leaves) / 2
                    actual_paid_sick_leaves = full_paid + half_pay_sick
            elif paid_sick_leaves and paid_sick_leaves > 14 and paid_sick_leaves <= 42:
                total_leave = paid_sick_leaves + cur_mon_paid_sick_leaves
                if total_leave <= 42:
                    actual_paid_sick_leaves = (total_leave - paid_sick_leaves) / 2
                elif total_leave > 42:
                    actual_unpaid_sick_leaves = total_leave - 42
                    actual_paid_sick_leaves = (total_leave - paid_sick_leaves - actual_unpaid_sick_leaves) / 2
            elif paid_sick_leaves and paid_sick_leaves > 42:
                total_leave = paid_sick_leaves + cur_mon_paid_sick_leaves
                print('tot999999999992222222222222',total_leave)
                print('tot999999999992222222222222',paid_sick_leaves)
                print('tot999999999992222222222222',cur_mon_paid_sick_leaves)
                actual_unpaid_sick_leaves = cur_mon_paid_sick_leaves

            self.is_paid_sick = True if actual_paid_sick_leaves else False
            self.is_unpaid_sick = True if actual_unpaid_sick_leaves else False

        return actual_paid_sick_leaves , actual_unpaid_sick_leaves






    # def _get_start_emp_hire_date(self):
    #     """ This method will check start date and end date in payslip """
    #
    #     if self.employee_id:
    #         from datetime import datetime, timedelta
    #         employee_hire_date = self.employee_id.original_hire_date
    #         current_date = fields.Date.today()
    #         delta = current_date - employee_hire_date  # as timedelta
    #         print('deltadeltadelta=======-----!!!!!!!!!!!!!!!!!!!!!-----', delta)
    #         return [employee_hire_date + timedelta(days=i) for i in range(delta.days + 1)]

