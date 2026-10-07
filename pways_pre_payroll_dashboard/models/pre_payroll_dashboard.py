from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import datetime
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta

class PrePayrollDashboard(models.Model):
    _name = 'pre.payroll.dashboard'
    _description = "Pre Payroll Dashboard"

    date_from = fields.Date('Start Date')
    date_end = fields.Date('End Date')
    batch_id = fields.Many2one('payroll.batch', string="Batch")

    def action_open_dashboard(self):
        active_id = self.env.context.get('active_id')
        return {
            'name': 'Dashboard',
            'type': 'ir.actions.client',
            'tag': 'payslip_dashboard',
            'context': "{'reqisition_id': active_id}",
        }

    def _get_date_list(self):
        if self.date_from and self.date_end:
            delta_date = self.date_end - self.date_from
            all_days = [self.date_from + timedelta(days=i) for i in range(delta_date.days + 1)]
            return all_days

    def _get_utc_time(self, date):
        """ Need to configure a time (local to server) in proper manners"""
        user_tz = self.env.user.tz or self.env.context.get('tz') or 'UTC'
        local = pytz.timezone(user_tz)
        date = datetime.datetime.strptime(datetime.datetime.strftime(local.localize(datetime.datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(pytz.utc),"%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
        return date

    def get_start_stop_datetime(self, day):
        date_start = day.strftime(DEFAULT_SERVER_DATE_FORMAT) + " 00:00:00"
        date_stop = day.strftime(DEFAULT_SERVER_DATE_FORMAT) +" 23:59:59"
        date_utc_start = self._get_utc_time(date_start)
        date_utc_stop = self._get_utc_time(date_stop)
        return date_start, date_stop

    def _get_total_days(self):
        total_days = 0
        start_date = datetime.datetime.strptime(self.date_from.strftime('%Y-%m-%d %H:%M:%S'), DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.datetime.strptime(self.date_end.strftime('%Y-%m-%d %H:%M:%S'), DEFAULT_SERVER_DATETIME_FORMAT)
        difference = end_date - start_date
        if difference:
            number_of_days = abs(difference.days + 1)
            total_days = number_of_days
        return total_days

    # Public Holiday return total days and days list 
    def get_public_holidays_dates(self):
        public_holidays = []
        start_date = self.date_from
        end_date = self.date_end
        public_holidays_ids = self.env['resource.calendar.leaves'].search([('date_from', '>=', start_date), ('date_to', '<=', end_date), ('resource_id', '=',False),('holiday_task', '=', False)])
        for holiday in public_holidays_ids:
            curr_date = holiday.date_from.date()
            while curr_date <= holiday.date_to.date():
                public_holidays.append(curr_date.strftime("%d/%m/%Y"))
                curr_date += timedelta(days=1)
        public_holidays_days = len(public_holidays)
        return public_holidays, public_holidays_days

    def get_present_days(self, employee):
        date_from = self.date_from
        date_to = self.date_end
        domain = [('employee_id', '=', employee.id), ('check_in', '>=', date_from), ('check_in', '<=', date_to)]
        ignore_ids = []
        for obj in self.env['hr.attendance'].search(domain):
            start_date = datetime.datetime.strptime(obj.check_in.strftime('%Y-%m-%d %H:%M:%S'), DEFAULT_SERVER_DATETIME_FORMAT)
            record_check_in = fields.Date.from_string(start_date)
            day_of_week_ids = obj.employee_id.dayofweek_ids.filtered(lambda x: x.date == record_check_in)
            public_leaves = self.env['resource.calendar.leaves'].search([('date_from', '<', obj.check_in), ('date_to', '>', obj.check_in)])
            public_holidays = public_leaves.filtered(lambda x: not x.resource_id)
            if public_holidays or day_of_week_ids:
                ignore_ids.append(obj.id)
        domain = domain + [('id', 'not in', ignore_ids)]
        day_attandance_lines = self.env['hr.attendance'].read_group(domain, ['employee_id', 'worked_hours'], ['check_in:day'])
        return float(len(day_attandance_lines))

    def get_week_off_dates(self, employee):
        total_leaves = []
        week_off_days = 0
        date_start = self.date_from
        date_end = self.date_end
        day_of_week_ids = employee.dayofweek_ids.filtered(lambda x: x.date and x.date >= date_start and x.date <= date_end)
        day_of_week_days = day_of_week_ids.mapped('date')
        paid_leave, un_paid_leave, sick_leave = self._total_leaves(employee)
        total_leaves = paid_leave + un_paid_leave + sick_leave
        weekoff_dates= []
        for dates in day_of_week_days:
            if dates not in total_leaves:
                weekoff_dates.append(dates.strftime(DEFAULT_SERVER_DATE_FORMAT))
        week_off_days = len(weekoff_dates)
        return weekoff_dates , week_off_days

    def total_overtime(self, employee):
        overtime_hours = 0.0
        date_from = self.date_from
        date_to = self.date_end
        overtime_ids = self.env['bt.hr.overtime'].search([
            ('state', '=', 'validate'),('start_date', '>=', date_from),
            ('start_date', '<=', date_to),('employee_id', '=', employee.id)])
        normal_overtime = round(sum(overtime_ids.filtered(lambda x: x.ot_type_id.code in ['NOD', 'RAMD']).mapped('overtime_hours')), 2)
        special_overtime = round(sum(overtime_ids.filtered(lambda x: x.ot_type_id.code not in ['NOD', 'RAMD']).mapped('overtime_hours')), 2)
        return normal_overtime, special_overtime

    #Total unpaid sick and paid leave emoloyee
    def _total_leaves(self, employee):
        list_paid =[]
        list_unpaid =[]
        list_sick =[]
        leave_ids = self.env['hr.leave'].search([
            ('state', '=', 'validate'),('employee_id', '=', employee.id),
            ('request_date_from', '>=', self.date_from),('request_date_to', '<=', self.date_end)])
        unpaid_leave_ids = leave_ids.filtered(lambda x: not x.holiday_status_id.work_entry_type_id.is_paid and not x.holiday_status_id.is_paid)
        paid_leave_ids = leave_ids.filtered(lambda x: x.holiday_status_id.work_entry_type_id.is_paid)
        sick_leave_ids = leave_ids.filtered(lambda x: x.holiday_status_id.is_sick_leave)
        for paid in paid_leave_ids:
            curr_date = paid.date_from
            while curr_date <= paid.date_to:
                list_paid.append(curr_date.strftime("%d/%m/%Y"))
                curr_date += timedelta(days=1)
        for unpaid in unpaid_leave_ids:
            curr_date = unpaid.date_from
            while curr_date <= unpaid.date_to:
                list_unpaid.append(curr_date.strftime("%d/%m/%Y"))
                curr_date += timedelta(days=1)
        for sick in sick_leave_ids:
            curr_date = sick.date_from
            while curr_date <= sick.date_to:
                list_sick.append(curr_date.strftime("%d/%m/%Y"))
                curr_date += timedelta(days=1)
        return list_paid, list_unpaid, list_sick

    def get_attendance_days_time(self, employee):
        employee = employee
        worked_hours = 0.0
        number_of_days = 0.0

        holidays_uni_days = []
        # Public holidays
        uni_holidays_dates , public_holidays = self.get_public_holidays_dates()
        for uni_days in uni_holidays_dates:
            number_of_days +=1
            holidays_uni_days.append(uni_days)

        # Week off days
        weekoff_dates, week_of_days = self.get_week_off_dates(employee)
        # Overlapping dates
        holidays_week_off_days = []
        for weekoff_date in weekoff_dates:
            if weekoff_date not in uni_holidays_dates:
                number_of_days += 1
                holidays_week_off_days.append(weekoff_date) 
        return number_of_days

    def get_payslip_line_data(self, requsition_id=None):
        data = []
        header = []
        header.append({
                'start_date' : self.date_from.strftime("%d-%m-%Y"),
                'end_date': self.date_end.strftime("%d-%m-%Y"),
                'pay_batch_id': self.batch_id.payroll_batch,
                })
        # domain = [('check_in', '>=', date_from), ('check_in', '<=', date_to)]
        contract_ids = self.env['hr.contract'].search([('date_start', '<=', self.date_from), ('date_start', '<=', self.date_end) , ('state', '=', 'open')])
        employee_ids = contract_ids.mapped('employee_id')
        if self.batch_id:
            employee_ids = employee_ids.filtered(lambda x: x.payroll_batch_id == self.batch_id)
        public_holidays , public_holidays_days = self.get_public_holidays_dates()
        total_days = self._get_total_days()
        for employee in employee_ids:
            contract_start = "NA"
            contract_end = "NA"
            working_hours = 0
            state = "Not Running"
            emp_status = dict(employee._fields['emp_status'].selection).get(employee.emp_status)
            contract_id = self.env['hr.contract'].search([('employee_id', '=', employee.id),('state', '=', 'open')], limit=1)
            ot_eligibility = dict(employee._fields['overtime_eligibility'].selection).get(employee.overtime_eligibility)
            if contract_id:
                state = dict(contract_id._fields['state'].selection).get(contract_id.state)
                working_hours = contract_id.work_hours
                contract_start = contract_id.date_start
                if contract_start:
                    contract_start = contract_id.date_start.strftime("%d-%m-%Y")
                else:
                    contract_start = "NA"
                contract_end = contract_id.date_end
                if contract_end:
                    contract_end = contract_id.date_end.strftime("%d-%m-%Y")
                else:
                    contract_end = "NA"
            week_off_dates_list, week_off_days = self.get_week_off_dates(employee)
            attendence_day = self.get_present_days(employee)
            normal_ot, special_ot = self.total_overtime(employee)
            paid_leave, un_paid_leave, sick_leave = self._total_leaves(employee)
            public_holidays = public_holidays_days
            total_week_holiday = self.get_attendance_days_time(employee)
            total_absent_days = 0
            absent_days = total_days - (total_week_holiday + attendence_day + len(paid_leave) + len(un_paid_leave) + len(sick_leave))
            if absent_days >= 0:
                total_absent_days = absent_days
            data.append({
                    'id': 5,
                    'emp_code': employee.emp_no,
                    'employee': employee.name,
                    'emp_status': emp_status,
                    'contract_status': state,
                    'working_hours': working_hours,
                    'ot_eligibility': ot_eligibility,
                    'contract_start': contract_start,
                    'contract_end': contract_end,
                    'attendence_day': attendence_day,
                    'weekoff_days': week_off_days,
                    'public_holiday': public_holidays,
                    'paid_leave': len(paid_leave),
                    'un_paid_leave': len(un_paid_leave),
                    'sick_leave': len(sick_leave),
                    'absent_days':  total_absent_days,
                    'total_days': total_days,
                    'normal_ot': normal_ot,
                    'special_ot': special_ot,
                    'branch': employee.branch_id.name,
                })
        return {'employee_ids': data, 'header': header}
