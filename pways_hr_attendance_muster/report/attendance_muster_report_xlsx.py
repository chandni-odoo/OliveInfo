# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from pytz import timezone, UTC
from datetime import timedelta
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import pytz
import datetime


class EmployeeAttandaneXlsx(models.AbstractModel):
    _name = 'report.pways_hr_attendance_muster.attendance_muster_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_holiday_leave_data(self, employee_id, from_date, to_date, un_present_days):
        public_holiday_dates = []
        for date in un_present_days:
            date_start = date.strftime(DEFAULT_SERVER_DATE_FORMAT)
            fil_date = date_start + ' 00:00:00'
            holiday_ids = self.env['resource.calendar.leaves'].search(
                [('date_from', '<=', fil_date), ('date_to', '>=', fil_date), ('resource_id', '=', False)])
            # leave_ids = self.env['hr.leave'].search([('employee_id', '=', employee_id.id), ('request_date_from', '<=', date), ('request_date_to', '>=', date)],limit=1)
            if holiday_ids:
                public_holiday_dates.append(date_start)
        return public_holiday_dates

    def _get_weekoff_leave_data(self, from_date, to_date, employee_id):
        weekoff_dates = []
        day_of_week_ids = employee_id.dayofweek_ids.filtered(
            lambda x: x.date and x.date >= from_date and x.date <= to_date)
        day_of_week_days = day_of_week_ids.mapped('date')
        for dates in day_of_week_days:
            # leave_ids = self.env['hr.leave'].search([('employee_id', '=', employee_id.id), ('request_date_from', '<=', dates), ('request_date_to', '>=', dates)], limit=1)
            # if not leave_ids:
            weekoff_dates.append(dates.strftime(DEFAULT_SERVER_DATE_FORMAT))
        return weekoff_dates

    def _get_paid_leave_data(self, employee_id, un_present_days):
        leave_ids = self.env['hr.leave']
        paid_leave_days = 0
        paid_dates = []
        for date in un_present_days:
            leave_domain = [
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id.id),
                ('request_date_from', '<=', date),
                ('request_date_to', '>=', date),
                ('holiday_status_id.is_sick_leave', '=', False),
                ('holiday_status_id.work_entry_type_id.is_paid', '=', True)]
            paid_leave_ids = self.env['hr.leave'].search(leave_domain)
            leave_ids |= paid_leave_ids
        if leave_ids:
            for paid in un_present_days:
                if paid >= min(leave_ids.mapped('request_date_from')) and paid <= max(
                        leave_ids.mapped('request_date_to')):
                    paid_dates.append(paid.strftime(DEFAULT_SERVER_DATE_FORMAT))

            # delta = min(leave_ids.mapped('request_date_from')) - max(leave_ids.mapped('request_date_to'))
            # for paid in leave_ids:
            #     paid_days = min(leave_ids.mapped('request_date_from'))
            #     for i in range(delta.days + 1):
            #         days = paid_days + timedelta(days=i)
            #         paid_dates.append(days.strftime(DEFAULT_SERVER_DATE_FORMAT))

        paid_leave_days = len(paid_dates)
        return paid_dates, paid_leave_days

    def _get_sick_leave_data(self, employee_id, un_present_days):
        sick_leave_ids = self.env['hr.leave']
        sick_leave_days = 0
        sick_dates = []
        for date in un_present_days:
            leave_domain = [
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id.id),
                ('request_date_from', '<=', date),
                ('request_date_to', '>=', date),
                ('holiday_status_id.is_sick_leave', '=', True)]
            # ('holiday_status_id.work_entry_type_id.is_paid', '=', False)]

            sick_leave_ids |= self.env['hr.leave'].search(leave_domain)

        if sick_leave_ids:
            for sick in un_present_days:
                if sick >= min(sick_leave_ids.mapped('request_date_from')) and sick <= max(
                        sick_leave_ids.mapped('request_date_to')):
                    sick_dates.append(sick.strftime(DEFAULT_SERVER_DATE_FORMAT))

        sick_leave_days = len(sick_dates)
        return sick_dates, sick_leave_days

    def _get_unpaid_leave_data(self, employee_id, un_present_days):
        unpaid_leave_ids = self.env['hr.leave']
        unpaid_leave_days = 0
        unpaid_dates = []
        for date in un_present_days:
            leave_domain = [
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id.id),
                ('request_date_from', '<=', date),
                ('request_date_to', '>=', date),
                ('holiday_status_id.work_entry_type_id.is_paid', '=', False)]

            unpaid_leave_ids |= self.env['hr.leave'].search(leave_domain)
        if unpaid_leave_ids:
            for unpaid in un_present_days:
                if unpaid >= min(unpaid_leave_ids.mapped('request_date_from')) and unpaid <= max(
                        unpaid_leave_ids.mapped('request_date_to')):
                    unpaid_dates.append(unpaid.strftime(DEFAULT_SERVER_DATE_FORMAT))

        unpaid_leave_days = len(unpaid_dates)
        return unpaid_dates, unpaid_leave_days

    def _get_overtime_data(self, employee_id, from_date, to_date):
        overtime_hours = 0.0
        overtime_ids = self.env['bt.hr.overtime'].search([
            ('start_date', '>=', from_date),
            ('start_date', '<=', to_date),
            ('employee_id', '=', employee_id.id),
        ])
        if overtime_ids:
            overtime_hours = round(sum(overtime_ids.mapped('overtime_hours')), 2)
        return overtime_hours

    # point no 13
    def generate_xlsx_report(self, workbook, data, products=None):
        from_date = datetime.datetime.strptime(data.get('date_from'), '%Y-%m-%d').date()
        to_date = datetime.datetime.strptime(data.get('date_to'), '%Y-%m-%d').date()
        branch_ids = data.get('branch_ids')
        batch_ids = data.get('batch_ids')
        employee_data = {}
        header = []
        emp_list = []
        total_list = []
        colmun_list = []
        if from_date and to_date:
            delta_date = to_date - from_date
            all_days = [from_date + timedelta(days=i) for i in range(delta_date.days + 1)]
            print('\nall_days++++++++++++++++', all_days)

            format1 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
            format2 = workbook.add_format({'font_size': 10, 'bold': True})
            format3 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': True})
            format4 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
            format5 = workbook.add_format({'font_size': 10, 'align': 'left'})

            sheet = workbook.add_worksheet("Attendance Muster Report")
            sheet.merge_range('A1:N1', 'Attendance Muster Report', format1)

            sheet.write('A8', "Employer Number", format2)
            sheet.write('B8', "Employer Name", format2)
            sheet.write('C8', "Original Hire Date", format2)
            sheet.write('D8', "OT Eligibility", format2)
            sheet.write('E8', "Std Working Hours", format2)
            sheet.write('F8', "Contract Status", format2)
            sheet.write('G8', "Employee Status", format2)
            sheet.write('H8', "Branch Code", format2)
            sheet.write('I8', "Payroll Batch", format2)
            sheet.write('I3', "P = Present", format2)
            sheet.write('I4', "A = Absent", format2)
            sheet.write('I5', "H = Holiday", format2)
            sheet.write('I6', "OT/H = Overtime", format2)
            sheet.write('K3', "WO = Week Off", format2)
            sheet.write('K4', "UL = Unpaid leave", format2)
            sheet.write('K5', "PL = Paid Leave", format2)
            sheet.write('K6', "Att/H = Attendance Hours", format2)
            sheet.write('K7', "Sick Leave", format2)
            sheet.merge_range('AM7:AS7', "Total", format1)

            header.append({'start_date': from_date.strftime("%d-%m-%Y"), 'end_date': to_date.strftime("%d-%m-%Y")})
            for date in header:
                sheet.merge_range('B3:D3', "Date From : " + date['start_date'], format2)
                sheet.merge_range('E3:G3', "Date To : " + date['end_date'], format2)

            att_emp_list = []
            e_emp_list = []

            # For Attendance
            domain = [('check_in', '>=', from_date), ('check_out', '<=', to_date)]
            if branch_ids:
                domain.append(('employee_id.branch_id', 'in', branch_ids))
            if batch_ids:
                domain.append(('employee_id.payroll_batch_id', 'in', batch_ids))
            attendance_ids = self.env['hr.attendance'].search(domain)
            for att in attendance_ids:
                att_emp_list.append(att.employee_id.id)

            # print('attendance_ids++++++++++++++++++', attendance_ids)
            # for rec in attendance_ids:
            #     if rec.employee_id.id not in employee_data:
            #         employee_data[rec.employee_id.id] = rec
            #     else:
            #         employee_data[rec.employee_id.id] |= rec

            # For Employee
            emp_domain = []
            if branch_ids:
                emp_domain.append(('branch_id', 'in', branch_ids))
            if batch_ids:
                emp_domain.append(('payroll_batch_id', 'in', batch_ids))
            if len(emp_domain) >= 1:
                employee_ids = self.env['hr.employee'].search(emp_domain)
            else:
                employee_ids = self.env['hr.employee'].search([])
            for emp in employee_ids:
                e_emp_list.append(emp.id)

            # Both Union in list
            emp_l = att_emp_list + e_emp_list
            final_employees = list(set(emp_l))

            total_emp = self.env['hr.employee'].browse(final_employees)
            for rec in total_emp:
                if rec.id not in employee_data:
                    employee_data[rec.id] = rec
                else:
                    employee_data[rec.id] |= rec

            print('\n\nemployee_data++++++++++++++++', employee_data)

            # emp vise data
            for key, values in employee_data.items():
                emp_values = values
                new_domain = [('employee_id', '=', values.id), ('check_in', '>=', from_date), ('check_out', '<=', to_date)]
                if branch_ids:
                    new_domain.append(('employee_id.branch_id', 'in', branch_ids))
                if batch_ids:
                    new_domain.append(('employee_id.payroll_batch_id', 'in', batch_ids))
                att_values = self.env['hr.attendance'].search(new_domain)
                print('att_values++++++++++++newatt++++++', att_values)

                if att_values:
                    values = att_values
                else:
                    values = emp_values

                # if not key == 1824:
                #     continue
                employee_id = self.env['hr.employee'].browse(key)

                # needtoremove
                # if employee_id.id == 1547:
                # if employee_id.id == 1888:

                fil_date = []
                worked_hours_list = []
                holiday_dates = []
                att_hours = 0.0
                overtime_hours = 0.0
                total_records = 0.0
                day_list = []

                # get all dates
                try:
                    for date in values.mapped('check_in'):
                        fil_date.append(date.date())
                except Exception as e:
                    pass

                for f_date in fil_date:
                    day_list.append(fields.Date.to_string(f_date))

                # add calculative methods
                if employee_id.overtime_eligibility == 'yes':
                    overtime_hours = self._get_overtime_data(employee_id, from_date, to_date)

                un_present_days = set(all_days) - set(day_list)
                unpaid_dates, unpaid_leave_days = self._get_unpaid_leave_data(employee_id, un_present_days)
                paid_dates, paid_leave_days = self._get_paid_leave_data(employee_id, un_present_days)

                sick_dates, sick_leave_days = self._get_sick_leave_data(employee_id, un_present_days)

                weekoff_dates = self._get_weekoff_leave_data(from_date, to_date, employee_id)
                public_holiday_dates = self._get_holiday_leave_data(employee_id, from_date, to_date,
                                                                    un_present_days)

                # if key == 1824:
                #     print("<<<<<\n\n<<<<<<un_present_days>>>>>>>>>", len(un_present_days))
                #     print("<<<<<<<\n\n<<<<Public_holiday_dates>>>>>>>>", public_holiday_dates)
                #     print("<<<<<\n\n<<<<<<Weekoff_dates>>>>>>>>>", weekoff_dates)
                #     print("<<<<<<\n\n<<<<<Unpaid_dates>>>>>>>>>", unpaid_dates)
                #     print("<<<<<\n\n<<<<<<Paid_dates>>>>>>>>>", paid_dates)

                to_filter_week_off = list(set(public_holiday_dates + paid_dates + unpaid_dates))
                to_filter_holidays = list(set(paid_dates + unpaid_dates))

                # if key == 1824:
                #     print("<<<<<<\n\n<<<<<to_filter_week_off>>>>>>>>>", to_filter_week_off)
                #     print("<<<<<<\n\n<<<<<to_filter_holidays>>>>>>>>>", to_filter_holidays)

                fil_weekoff_dates = list(set(weekoff_dates) - set(to_filter_week_off))
                fil_holidays = list(set(public_holiday_dates) - set(to_filter_holidays))

                holiday_dates = fil_weekoff_dates + paid_dates + unpaid_dates + fil_holidays

                # if key == 1824:
                #     print("<<<<<\n\n<<<<<<fil_weekoff_dates>>>>>>>>>", fil_weekoff_dates)
                #     print("<<<<<\n\n<<<<<<fil_holidays>>>>>>>>>", fil_holidays)
                #     print("<<<<<\n \n \n \n<<<<<<holiday_dates>>>>>>>>>", holiday_dates)

                print('day_list+++++++++++++', day_list, '\n+++++', set(day_list))
                print('holiday_dates+++++++++++++', holiday_dates, '\n+++++', set(holiday_dates))

                total_p_days = set(day_list) - set(holiday_dates)
                print('total_p_days++++++++++++++', total_p_days, len(total_p_days))

                present_day = len(total_p_days)
                # re-calculate
                public_holidays_days = len(fil_holidays)
                week_off_days = len(fil_weekoff_dates)
                unpaid_leave_days = len(unpaid_dates)
                paid_leave_days = len(paid_dates)
                sick_leave_days = len(sick_dates)
                total_days = week_off_days + unpaid_leave_days + paid_leave_days + sick_leave_days + public_holidays_days + present_day

                # if key == 1824:
                #     print("<<<<<\n\n<<<<<<public_holidays_days>>>>>>>>>", public_holidays_days)
                #     print("<<<<<\n\n<<<<<<week_off_days>>>>>>>>>", week_off_days)
                #     print("<<<<<\n\n<<<<<<paid_leave_days>>>>>>>>>", paid_leave_days)
                #     print("<<<<<\n\n<<<<<<unpaid_leave_days>>>>>>>>>", unpaid_leave_days)
                #     print("<<<<<\n\n<<<<<<total_days>>>>>>>>>", total_days)

                # absent days
                total_absent_days = 0
                absent_days = len(all_days) - total_days
                if absent_days >= 0:
                    total_absent_days = absent_days

                try:
                    att_hours = round(sum(values.mapped('worked_hours')), 2)
                except Exception as e:
                    att_hours = None

                total_records = paid_leave_days + sick_leave_days + present_day + week_off_days + public_holidays_days
                total_list.append({
                    'present': present_day if present_day else 0,
                    'absent': total_absent_days if total_absent_days else 0,
                    'week_off_records': week_off_days if week_off_days else 0,
                    'unpaid_leave_records': unpaid_leave_days if unpaid_leave_days else 0,
                    'paid_leave_records': paid_leave_days if paid_leave_days else 0,
                    'sick_leave_records': sick_leave_days if sick_leave_days else 0,
                    'holidays_records': public_holidays_days if public_holidays_days else 0,
                    'ot_hours_records': overtime_hours,
                    'attendance_hours_records': att_hours if att_hours else None,
                    'total_records': total_records,
                })

                # other data
                if employee_id:
                    ot_eligibility = dict(employee_id._fields['overtime_eligibility'].selection).get(
                        employee_id.overtime_eligibility)
                    emp_status = dict(employee_id._fields['emp_status'].selection).get(employee_id.emp_status)
                    emp_code = employee_id.emp_no
                    branch_code = employee_id.branch_id.code
                    payroll_batch = employee_id.payroll_batch_id.payroll_batch
                    original_hire_date = str(employee_id.original_hire_date)
                    contract_id = employee_id.contract_ids.filtered(lambda x: x.state == 'open')
                    working_hours, state = None, None
                    if contract_id:
                        # state = dict(contract_id._fields['state'].selection).get(contract_id.state)
                        state = dict(contract_id[0]._fields['state'].selection).get(contract_id[0].state)
                        working_hours = contract_id[0].work_hours
                    emp_list.append({
                        'employer_id': employee_id.name,
                        'emp_code': emp_code if emp_code else False,
                        'hire_date': original_hire_date if original_hire_date else False,
                        'ot_eligibility': ot_eligibility if ot_eligibility else False,
                        'std_work_hrs': working_hours if working_hours else 0,
                        'contract_status': state if state else False,
                        'employer_status': emp_status if emp_status else False,
                        'branch_code': branch_code if branch_code else False,
                        'payroll_batch': payroll_batch if payroll_batch else False,
                    })

                # dynamic days column and data
                row_number = 7
                column_number = 9
                for spec_date in all_days:
                    sheet.write(row_number, column_number, spec_date.strftime("%d"), format2)
                    column_number += 1
                    worked_hours = ''

                    if spec_date in fil_date:
                        att_rec = values.filtered(lambda x: x.check_in.date() == spec_date)
                        worked_hours = round(sum(att_rec.mapped('worked_hours')), 2)

                    else:
                        if str(spec_date) in fil_holidays:
                            worked_hours += "H"

                        elif str(spec_date) in fil_weekoff_dates:
                            worked_hours += "WO"

                        elif str(spec_date) in unpaid_dates:
                            worked_hours = "UL"

                        elif str(spec_date) in paid_dates:
                            worked_hours = "PL"

                        elif str(spec_date) in sick_dates:
                            worked_hours = "SL"

                        else:
                            worked_hours = "A"

                    worked_hours_list.append(worked_hours)
                colmun_list.append(worked_hours_list)

            if not employee_data.keys():
                row_number = 7
                column_number = 9
                for spec_date in all_days:
                    sheet.write(row_number, column_number, spec_date.strftime("%d"), format2)
                    column_number += 1

            # calculative column
            row_number = 7
            column_number = 8 + len(all_days)
            sheet.write(row_number, column_number + 1, "P", format2)
            sheet.write(row_number, column_number + 2, "A", format2)
            sheet.write(row_number, column_number + 3, "UL", format2)
            sheet.write(row_number, column_number + 4, "PL", format2)
            sheet.write(row_number, column_number + 5, "SL", format2)
            sheet.write(row_number, column_number + 6, "WO", format2)
            sheet.write(row_number, column_number + 7, "H", format2)
            sheet.write(row_number, column_number + 8, "OT/H", format2)
            sheet.write(row_number, column_number + 9, "Att/H", format2)
            sheet.write(row_number, column_number + 10, "Paid Days", format2)

            # employee data
            row_number = 8
            column_number = 0
            for val in emp_list:
                try:
                    sheet.write(row_number, column_number, val['emp_code'], format5)
                    sheet.write(row_number, column_number + 1, val['employer_id'], format5)
                    sheet.write(row_number, column_number + 2, val['hire_date'], format5)
                    sheet.write(row_number, column_number + 3, val['ot_eligibility'], format5)
                    sheet.write(row_number, column_number + 4, val['std_work_hrs'], format5)
                    sheet.write(row_number, column_number + 5, val['contract_status'], format5)
                    sheet.write(row_number, column_number + 6, val['employer_status'], format5)
                    sheet.write(row_number, column_number + 7, val['branch_code'], format5)
                    sheet.write(row_number, column_number + 8, val['payroll_batch'], format5)
                    row_number += 1
                except Exception as e:
                    sheet.write(row_number, column_number, val, format5)
                    sheet.write(row_number, column_number + 1, val, format5)
                    sheet.write(row_number, column_number + 2, val, format5)
                    sheet.write(row_number, column_number + 3, val, format5)
                    sheet.write(row_number, column_number + 4, val, format5)
                    sheet.write(row_number, column_number + 5, val, format5)
                    sheet.write(row_number, column_number + 6, val, format5)
                    sheet.write(row_number, column_number + 7, val, format5)
                    sheet.write(row_number, column_number + 8, val, format5)
                    row_number += 1

            # column data
            row_number = 8

            for val_list in colmun_list:
                column_number = 9
                for val in val_list:
                    sheet.write(row_number, column_number, str(val), format5)
                    column_number += 1
                row_number += 1

            column_number -= 1
            row_number = 8
            for total_leave in total_list:
                try:
                    sheet.write(row_number, column_number + 1, total_leave['present'], format5)
                    sheet.write(row_number, column_number + 2, total_leave['absent'], format5)
                    sheet.write(row_number, column_number + 3, total_leave['unpaid_leave_records'], format5)
                    sheet.write(row_number, column_number + 4, total_leave['paid_leave_records'], format5)
                    sheet.write(row_number, column_number + 5, total_leave['sick_leave_records'], format5)
                    sheet.write(row_number, column_number + 6, total_leave['week_off_records'], format5)
                    sheet.write(row_number, column_number + 7, total_leave['holidays_records'], format5)
                    sheet.write(row_number, column_number + 8, total_leave['ot_hours_records'], format5)
                    sheet.write(row_number, column_number + 9, total_leave['attendance_hours_records'], format5)
                    sheet.write(row_number, column_number + 10, total_leave['total_records'], format5)
                    row_number += 1
                except Exception as e:
                    sheet.write(row_number, column_number + 1, total_leave, format5)
                    sheet.write(row_number, column_number + 2, total_leave, format5)
                    sheet.write(row_number, column_number + 3, total_leave, format5)
                    sheet.write(row_number, column_number + 4, total_leave, format5)
                    sheet.write(row_number, column_number + 5, total_leave, format5)
                    sheet.write(row_number, column_number + 6, total_leave, format5)
                    sheet.write(row_number, column_number + 7, total_leave, format5)
                    sheet.write(row_number, column_number + 8, total_leave, format5)
                    sheet.write(row_number, column_number + 9, total_leave, format5)
                    sheet.write(row_number, column_number + 10, total_leave, format5)
                    row_number += 1
