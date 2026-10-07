# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
import pytz
import datetime
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    leave_ids = fields.One2many('hr.leave', 'employee_id')


class ProductXlsx(models.AbstractModel):
    _name = 'report.pways_eosb_xls_report.eosb_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def get_unproductive_days(self, gratuity_date, employee_id):
        unpaid_leave_days = 0.0
        for date in gratuity_date:
            # print("\n\n DATEEEEEEEEEE", date)
            unpaid_leave_ids = employee_id.leave_ids.filtered(lambda
                                                                  x: x.state == 'validate' and x.request_date_from >= date and x.request_date_to <= date and not x.holiday_status_id.is_paid and not x.holiday_status_id.work_entry_type_id.is_paid)
            # print("\n\n unpaid_leave_ids",unpaid_leave_ids)
            for rec in unpaid_leave_ids:
                unpaid_leave_days += 1

            attendance_ids = employee_id.attendance_ids.filtered(lambda
                                                                     x: x.check_in.date() >= date if x.check_in else None and x.check_out.date() <= date if x.check_out else None)
            # print("\n\n attendance_ids",attendance_ids)
            week_off_ids = employee_id.dayofweek_ids.filtered(lambda x: x.date == date)
            # print("\n\n week_off_ids",week_off_ids)
            public_holiday_ids = self.env['resource.calendar.leaves'].search(
                [('date_from', '<=', date), ('date_to', '>=', date), ('resource_id', '=', False)])
            # print("\n\n public_holiday_ids",public_holiday_ids)
            if not attendance_ids and not week_off_ids and not public_holiday_ids and not unpaid_leave_ids:
                unpaid_leave_days += 1
        return unpaid_leave_days
    
    def generate_xlsx_report(self, workbook, data, products=None):
        employee_details = []
        date = datetime.datetime.strptime(data.get('as_on_date'), '%Y-%m-%d').date()
        company_id = data.get('company_id')
        branch_ids = data.get('branch_ids')

        emp_status_active = data.get('emp_status_active')
        emp_status_leave = data.get('emp_status_leave')
        emp_status_resigned = data.get('emp_status_resigned')
        emp_status_terminated = data.get('emp_status_terminated')
        emp_status_employer_change = data.get('employer_change')

        # Build status list
        status_list = []
        if emp_status_active:
            status_list.append('active')
        if emp_status_leave:
            status_list.append('leave')
        if emp_status_resigned:
            status_list.append('resigned')
        if emp_status_terminated:
            status_list.append('terminated')
        if emp_status_employer_change:
            status_list.append('employer_change')

        company_name = self.env['res.company'].browse(company_id)
        company_gratuity_date = company_name.gratuity_date
        if not company_gratuity_date:
            raise ValidationError(_("Please set gratuity date in employee setting."))

        if date:
            domain = [('date_start', '<=', date), ('state', '=', 'open'), ('company_id', '=', int(company_id))]
            if branch_ids:
                domain.append(('branch_id', 'in', branch_ids))
            contract_ids = self.env['hr.contract'].search(domain)
            employees = contract_ids.mapped('employee_id')

            if status_list:
                employees = employees.filtered(lambda emp: emp.emp_status in status_list)

            for employee in employees:
                original_hire_date = str(employee.original_hire_date)
                branch_code = employee.branch_id.code
                emp_code = employee.emp_no

                passage_allowance = 0.0
                travel_benefit = employee.travel_benefit
                travel_benefit_ticket = travel_benefit.tickets
                travel_benefit_month = travel_benefit.month

                travel_sector_id = employee.travel_sector_id
                travel_sector_amount = travel_sector_id.amount
                if travel_benefit_month > 0:
                    passage_allowance = travel_sector_amount * travel_benefit_ticket

                contract_id = contract_ids.filtered(lambda x: x.employee_id == employee and x.state == 'open')
                allowance = 0.0
                if travel_benefit and travel_benefit.name == 'Passage Allowance':
                    allowance = sum(
                        contract_id.allowance_ids.filtered(
                            lambda x: x.category_id.code == 'ALW' and x.code != 'AIRTKTMNTL'
                        ).mapped('amount')
                    )
                else:
                    allowance = sum(
                        contract_id.allowance_ids.filtered(lambda x: x.category_id.code == 'ALW').mapped('amount')
                    )

                basic_salary = contract_id[-1].wage
                gross_amount = contract_id[-1].gross_amount
                net_amount = contract_id[-1].net_amount
                total_pay = basic_salary + allowance

                # ✅ Accrued Leave Balance Calculation (using remaining_leaves)
                accrued_leave_days = 0.0
                accrued_leave_amount = 0.0
                last_leave_date = False
                allocation_ids = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'validate')
                ])
                accrued_leave_days = sum(allocation_ids.mapped('remaining_leaves'))

                daily_rate = (gross_amount / 30) if gross_amount > 0 else 0
                accrued_leave_amount = accrued_leave_days * daily_rate

                # 3. ✅ Get last leave date from hr.leave model
                last_leave = self.env['hr.leave'].search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'validate')
                ], order='request_date_to desc', limit=1)

                if last_leave:
                    last_leave_date = last_leave.request_date_to
                else:
                    last_leave_date = False

                # passage accrued calculation
                leave_ids = self.env['hr.leave']
                leave_ids_noairticket = self.env['hr.leave']
                last_date_new = False

                accural_ids = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', employee.id),
                    ('allocation_type', '=', 'accrual'),
                    ('state', '=', 'validate')
                ])

                holiday_status_ids = accural_ids.mapped('holiday_status_id')
                for holiday_status_id in holiday_status_ids:
                    take_leave_ids = self.env['hr.leave'].search([
                        ('employee_id', '=', employee.id),
                        ('holiday_status_id', '=', holiday_status_id.id),
                        ('air_ticket', '=', 'company'),
                        ('request_date_from', '<', datetime.datetime.now().strftime('%Y-%m-%d'))
                    ])
                    leave_ids |= take_leave_ids

                if leave_ids_noairticket:
                    last_date_new = str(max(leave_ids_noairticket.mapped('request_date_from')))
                if leave_ids:
                    last_date = str(max(leave_ids.mapped('request_date_from')))
                    passage_last_date = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()
                else:
                    last_date = str(employee.original_hire_date)
                    passage_last_date = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()

                passage_days = (date - passage_last_date).days
                passage_daily_rate = 0.0
                if travel_benefit_month == 12:
                    passage_daily_rate = (travel_sector_amount / 365)
                if travel_benefit_month == 24:
                    passage_daily_rate = (travel_sector_amount / 730)
                # passage_accrued = (passage_days * passage_daily_rate * travel_benefit_ticket)

                # travel_ticket = travel_sector_amount * travel_benefit_ticket
                # if passage_accrued > travel_ticket:
                #     new_passage_accrued = travel_sector_amount
                # else:
                #     new_passage_accrued = passage_accrued

                passage_accrued = (passage_days * passage_daily_rate * travel_benefit_ticket)
                if passage_accrued < 0:
                    passage_accrued = 0.0

                travel_ticket = travel_sector_amount * travel_benefit_ticket
                if passage_accrued > travel_ticket:
                    new_passage_accrued = travel_sector_amount
                else:
                    new_passage_accrued = passage_accrued

                amount = (gross_amount / 30) if gross_amount > 0 else 0
                accrued_leave_amount = (accrued_leave_days * amount)

                # Gratuity calculation
                gratuity_amount = 0.0
                delta_date = date - company_gratuity_date
                gratuity_date = [company_gratuity_date + timedelta(days=i) for i in range(delta_date.days + 1)]
                joined_date = employee.original_hire_date
                gratuity_days = ((date - joined_date + timedelta(days=1)).days) if date and joined_date else 0.0

                gratuity_unproductive_days = employee.gratuity_unproductive_days
                unproductive_days = self.get_unproductive_days(gratuity_date, employee)
                total_unproductive_days = unproductive_days + gratuity_unproductive_days
                eligible_days = gratuity_days - total_unproductive_days

                if eligible_days < 365:
                    gratuity_amount = 0
                if eligible_days >= 0 and eligible_days <= 1825:
                    gratuity_amount = (basic_salary * (12 / 365)) * ((21 / 365) * eligible_days)
                if eligible_days > 1825:
                    more_then_five = int(date.year) - int(joined_date.year) - 5
                    up_five_year_eligible_days = eligible_days - 1825
                    less_five_amount = ((basic_salary * (12 / 365)) * ((21 / 365 * 1825)))
                    more_five_amount = ((basic_salary * (12 / 365)) * (30 / 365 * up_five_year_eligible_days))
                    gratuity_amount = less_five_amount + more_five_amount

                employee_details.append({
                    'employee_name': employee.name,
                    'original_hire_date': original_hire_date if original_hire_date else False,
                    'branch_code': branch_code if branch_code else False,
                    'emp_code': emp_code if emp_code else False,
                    'gratuity_days': gratuity_days if gratuity_days else 0.0,
                    'basic_salary': basic_salary if basic_salary else 0.0,
                    'allowance': allowance if allowance else 0.0,
                    'total_pay': total_pay if total_pay else 0.0,
                    'travel_benefit': travel_benefit.name if travel_benefit else False,
                    'tickets': travel_benefit_ticket if travel_benefit_ticket else 0.0,
                    'travel_sector': travel_sector_id.name if travel_sector_id else False,
                    'passage_accrued': round(new_passage_accrued, 2),
                    'passage_allowance': round(passage_allowance, 2),
                    'last_leave_date': last_leave_date.strftime('%d-%m-%Y') if last_leave_date else '',
                    'leave_days': round(accrued_leave_days, 2),   # ✅ Now showing Accrued Balance
                    'leave_pay_accrued': 0 if accrued_leave_amount < 0 else round(accrued_leave_amount, 2),
                    'total_gratuity_accrued': round(gratuity_amount),
                    'emp_status': employee.emp_status,
                })

            sheet = workbook.add_worksheet('End Of service Benefit')
            format1 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
            format2 = workbook.add_format({'font_size': 10, 'bold': True})
            format3 = workbook.add_format({'font_size': 10, 'align': 'left'})

            sheet.merge_range('A2:E2', 'Employees - Benefit Accrued As On : ' + date.strftime("%d-%m-%Y"), format1)
            sheet.merge_range('F2:I2', 'Company: ' + company_name.name, format1)
            sheet.write('A5', "Branch Code", format2)
            sheet.write('B5', "Employee Number", format2)
            sheet.write('C5', "Employee Name", format2)
            sheet.write('D5', "Originial Hire Date", format2)
            sheet.write('E5', "Gratuity Days", format2)
            sheet.write('F5', "Basic Salary", format2)
            sheet.write('G5', "Allowance", format2)
            sheet.write('H5', "Total Pay", format2)
            sheet.write('I5', "Travel Benefit", format2)
            sheet.write('J5', "Tickets", format2)
            sheet.write('K5', "Travel Sector", format2)
            sheet.write('L5', "Passage Accrued", format2)
            sheet.write('M5', "Passage Allowance", format2)
            sheet.write('N5', "Last Leave Date", format2)
            sheet.write('O5', "Leave Days", format2)
            sheet.write('P5', "Leave Pay Accrued", format2)
            sheet.write('Q5', "Total Gratuity Accrued", format2)
            sheet.write('R5', "Status", format2)

            row_number = 5
            column_number = 0
            for emp in employee_details:
                sheet.write(row_number, column_number, emp['branch_code'], format3)
                sheet.write(row_number, column_number + 1, emp['emp_code'], format3)
                sheet.write(row_number, column_number + 2, emp['employee_name'], format3)
                sheet.write(row_number, column_number + 3, emp['original_hire_date'], format3)
                sheet.write(row_number, column_number + 4, emp['gratuity_days'], format3)
                sheet.write(row_number, column_number + 5, emp['basic_salary'], format3)
                sheet.write(row_number, column_number + 6, emp['allowance'], format3)
                sheet.write(row_number, column_number + 7, emp['total_pay'], format3)
                sheet.write(row_number, column_number + 8, str(emp['travel_benefit']), format3)
                sheet.write(row_number, column_number + 9, int(emp['tickets']), format3)
                sheet.write(row_number, column_number + 10, emp['travel_sector'], format3)
                sheet.write(row_number, column_number + 11, emp['passage_accrued'], format3)
                sheet.write(row_number, column_number + 12, emp['passage_allowance'], format3)
                sheet.write(row_number, column_number + 13, emp['last_leave_date'], format3)
                sheet.write(row_number, column_number + 14, emp['leave_days'], format3)
                sheet.write(row_number, column_number + 15, emp['leave_pay_accrued'], format3)
                sheet.write(row_number, column_number + 16, emp['total_gratuity_accrued'], format3)
                sheet.write(row_number, column_number + 17, emp['emp_status'], format3)
                row_number += 1

    # point no 16
    # def generate_xlsx_report(self, workbook, data, products=None):
    #     employee_details = []
    #     date = datetime.datetime.strptime(data.get('as_on_date'), '%Y-%m-%d').date()
    #     company_id = data.get('company_id')
    #     branch_ids = data.get('branch_ids')

    #     emp_status_active = data.get('emp_status_active')
    #     emp_status_leave = data.get('emp_status_leave')
    #     emp_status_resigned = data.get('emp_status_resigned')
    #     emp_status_terminated = data.get('emp_status_terminated')
    #     emp_status_employer_change = data.get('employer_change')

    #     # build status list
    #     status_list = []
    #     if emp_status_active:
    #         status_list.append('active')
    #     if emp_status_leave:
    #         status_list.append('leave')
    #     if emp_status_resigned:
    #         status_list.append('resigned')
    #     if emp_status_terminated:
    #         status_list.append('terminated')
    #     if emp_status_employer_change:
    #         status_list.append('employer_change')

    #     company_name = self.env['res.company'].browse(company_id)
    #     company_gratuity_date = company_name.gratuity_date
    #     if not company_gratuity_date:
    #         raise ValidationError(_("Please set gratuity date in employee setting."))
    #     if date:
    #         domain = [('date_start', '<=', date), ('state', '=', 'open'), ('company_id', '=', int(company_id))]
    #         if branch_ids:
    #             domain.append(('branch_id', 'in', branch_ids))
    #         contract_ids = self.env['hr.contract'].search(domain)

    #         employees = contract_ids.mapped('employee_id')

    #         # 🧭 Filter employees by selected emp_status if any selected
    #         if status_list:
    #             employees = employees.filtered(lambda emp: emp.emp_status in status_list)

    #         # for employee in contract_ids.mapped('employee_id'):
    #         for employee in employees:
    #             # if employee.id == 1793:
    #             # print('\nemployee++++++++++++++++', employee.id, employee.name, employee.branch_id.code)
    #             #     continue
    #             original_hire_date = str(employee.original_hire_date)
    #             branch_code = employee.branch_id.code
    #             emp_code = employee.emp_no

    #             passage_allowance = 0.0
    #             travel_benefit = employee.travel_benefit
    #             travel_benefit_ticket = travel_benefit.tickets
    #             travel_benefit_month = travel_benefit.month

    #             travel_sector_id = employee.travel_sector_id
    #             travel_sector_amount = travel_sector_id.amount
    #             if travel_benefit_month > 0:
    #                 # passage_allowance = ((travel_benefit_ticket * (travel_sector_amount / travel_benefit_month)))
    #                 # passage_allowance = (((travel_sector_amount * travel_benefit_ticket) / travel_benefit_month))
    #                 passage_allowance = travel_sector_amount * travel_benefit_ticket

    #             contract_id = contract_ids.filtered(lambda x: x.employee_id == employee and x.state == 'open')
    #             # allowance = sum(
    #             #     contract_id.allowance_ids.filtered(lambda x: x.category_id.code == 'ALW').mapped('amount'))
    #             allowance = 0.0
    #             if travel_benefit and travel_benefit.name == 'Passage Allowance':
    #                 allowance = sum(
    #                     contract_id.allowance_ids.filtered(
    #                         lambda x: x.category_id.code == 'ALW' and x.code != 'AIRTKTMNTL'
    #                     ).mapped('amount')
    #                 )
    #             else:
    #                 # Include all allowances with code 'ALW'
    #                 allowance = sum(
    #                     contract_id.allowance_ids.filtered(lambda x: x.category_id.code == 'ALW').mapped('amount')
    #                 )

    #             basic_salary = contract_id[-1].wage
    #             gross_amount = contract_id[-1].gross_amount
    #             net_amount = contract_id[-1].net_amount
    #             total_pay = basic_salary + allowance

    #             # leave calculation
    #             leave_ids = self.env['hr.leave']
    #             leave_ids_approval_state = self.env['hr.leave']
    #             leave_ids_noairticket = self.env['hr.leave']
    #             last_date_new = False
    #             last_date = False
    #             amount = 0.0
    #             accrued_leave_amount = 0.0
    #             allocation_days = 0.0
    #             leave_days = 0.0
    #             accrued_leave_days = 0.0

    #             passage_accrued = 0.0
    #             passage_daily_rate = 0.0
    #             passage_days = 0.0

    #             accural_ids = self.env['hr.leave.allocation'].search(
    #                 [('employee_id', '=', employee.id), ('allocation_type', '=', 'accrual'),
    #                  ('state', '=', 'validate')])
                
    #             print('accural_ids+++++++++++++', accural_ids)
    #             holiday_status_ids = accural_ids.mapped('holiday_status_id')
    #             print('holiday_status_ids++++++++++++', holiday_status_ids)
    #             for holiday_status_id in holiday_status_ids:
    #                 take_leave_ids = self.env['hr.leave'].search(
    #                     [('employee_id', '=', employee.id), ('holiday_status_id', '=', holiday_status_id.id),
    #                      ('air_ticket', '=', 'company'),
    #                      ('request_date_from', '<', datetime.datetime.now().strftime('%Y-%m-%d'))])
    #                 leave_ids |= take_leave_ids
    #                 take_leave_state_ids = self.env['hr.leave'].search(
    #                     [('employee_id', '=', employee.id), ('holiday_status_id', '=', holiday_status_id.id),
    #                      ('state', 'in', ['validate1', 'validate']),
    #                      ('request_date_from', '<', datetime.datetime.now().strftime('%Y-%m-%d'))])
    #                 print('take_leave_state_ids++++++++++++++', take_leave_state_ids)
    #                 leave_ids_approval_state |= take_leave_state_ids
    #             if leave_ids_noairticket:
    #                 last_date_new = str(max(leave_ids_noairticket.mapped('request_date_from')))
    #             # not leave_ids take hire date
    #             if leave_ids:
    #                 # last_date = str(max(leave_ids.mapped('request_date_to')))
    #                 last_date = str(max(leave_ids.mapped('request_date_from')))
    #                 # passage_accured calculation
    #                 passage_last_date = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()
    #                 passage_days = (date - passage_last_date).days
    #                 if travel_benefit_month == 12:
    #                     passage_daily_rate = (travel_sector_amount / 365)
    #                 if travel_benefit_month == 24:
    #                     passage_daily_rate = (travel_sector_amount / 730)
    #                 passage_accrued = (passage_days * passage_daily_rate * travel_benefit_ticket)
    #             else:
    #                 # last_date = str(max(leave_ids.mapped('request_date_to')))
    #                 last_date = str(employee.original_hire_date)
    #                 # passage_accured calculation
    #                 passage_last_date = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()
    #                 passage_days = (date - passage_last_date).days
    #                 if travel_benefit_month == 12:
    #                     passage_daily_rate = (travel_sector_amount / 365)
    #                 if travel_benefit_month == 24:
    #                     passage_daily_rate = (travel_sector_amount / 730)
    #                 passage_accrued = (passage_days * passage_daily_rate * travel_benefit_ticket)

    #             travel_ticket = travel_sector_amount * travel_benefit_ticket
    #             if passage_accrued > travel_ticket:
    #                 new_passage_accrued = travel_sector_amount
    #             else:
    #                 new_passage_accrued = passage_accrued

    #             for holiday_status_id in holiday_status_ids:
    #                 take_leave_ids = self.env['hr.leave'].search(
    #                     [('employee_id', '=', employee.id), ('holiday_status_id', '=', holiday_status_id.id),
    #                      ('request_date_from', '<', datetime.datetime.now().strftime('%Y-%m-%d'))])
    #                 leave_ids_noairticket |= take_leave_ids

    #             if leave_ids_noairticket:
    #                 last_date_new = str(max(leave_ids_noairticket.mapped('request_date_from')))

    #             print('accural_ids+++++++++++++', accural_ids)
    #             print('leave_ids_approval_state+++++++++++++', leave_ids_approval_state)
    #             allocation_days = sum(accural_ids.mapped('number_of_days_display'))
    #             leave_days = sum(leave_ids_approval_state.mapped('number_of_days'))
    #             print('allocation_days+++++++++++++++', allocation_days)
    #             print('leave_days+++++++++++++++', leave_days)
    #             accrued_leave_days = allocation_days - leave_days

    #             amount = (gross_amount / 30) if gross_amount > 0 else 0
    #             accrued_leave_amount = (accrued_leave_days * amount)

    #             # employee gratuity_days calculation
    #             gratuity_amount = 0.0

    #             delta_date = date - company_gratuity_date
    #             gratuity_date = [company_gratuity_date + timedelta(days=i) for i in range(delta_date.days + 1)]
    #             # print("<<<<<gratuity_date>>>>>", gratuity_date)
    #             joined_date = employee.original_hire_date
    #             # print("<<<<DDDDDDDDD>>>>", date, joined_date)

    #             gratuity_days = ((date - joined_date + timedelta(days=1)).days) if date and joined_date else 0.0

    #             gratuity_unproductive_days = employee.gratuity_unproductive_days
    #             # print("<<<<<gratuity_unproductive_days>>>>>", gratuity_unproductive_days)
    #             worked_years = int(date.year) if date else 0.0 - int(joined_date.year) if joined_date else 0.0
    #             unproductive_days = self.get_unproductive_days(gratuity_date, employee)
    #             # print("<<<<<unproductive_days>>>>>", unproductive_days)
    #             total_unproductive_days = unproductive_days + gratuity_unproductive_days
    #             # print("<<<<<total_unproductive_days>>>>>", total_unproductive_days)
    #             eligible_days = gratuity_days - total_unproductive_days
    #             # print("<<<<eligible_days>>>>", eligible_days)
    #             if eligible_days < 365:
    #                 gratuity_amount = 0

    #             # if eligible_days >= 365 and eligible_days <= 1825:
    #             if eligible_days >= 0 and eligible_days <= 1825:
    #                 # print("<<<<basic_salary>>>>", basic_salary)
    #                 gratuity_amount = (basic_salary * (12 / 365)) * ((21 / 365) * eligible_days)

    #             if eligible_days > 1825:
    #                 more_then_five = worked_years - 5
    #                 up_five_year_eligible_days = eligible_days - 1825
    #                 less_five_amount = ((basic_salary * (12 / 365)) * ((21 / 365 * 1825)))
    #                 more_five_amount = ((basic_salary * (12 / 365)) * (30 / 365 * up_five_year_eligible_days))
    #                 gratuity_amount = less_five_amount + more_five_amount

    #             employee_details.append({
    #                 'employee_name': employee.name,
    #                 'original_hire_date': original_hire_date if original_hire_date else False,
    #                 'branch_code': branch_code if branch_code else False,
    #                 'emp_code': emp_code if emp_code else False,
    #                 'gratuity_days': gratuity_days if gratuity_days else 0.0,
    #                 'basic_salary': basic_salary if basic_salary else 0.0,
    #                 'allowance': allowance if allowance else 0.0,
    #                 'total_pay': total_pay if total_pay else 0.0,
    #                 'travel_benefit': travel_benefit.name if travel_benefit else False,
    #                 'tickets': travel_benefit_ticket if travel_benefit_ticket else 0.0,
    #                 'travel_sector': travel_sector_id.name if travel_sector_id else False,
    #                 'passage_accrued': round(new_passage_accrued, 2),  # Column L
    #                 'passage_allowance': round(passage_allowance, 2),  # Column M
    #                 'last_leave_date': last_date_new if last_date_new else False,
    #                 # ir-respective of air ticket company  # Column N
    #                 'leave_days': round(accrued_leave_days, 2),  # Column O
    #                 'leave_pay_accrued': 0 if accrued_leave_amount < 0 else round(accrued_leave_amount, 2),
    #                 'total_gratuity_accrued': round(gratuity_amount),
    #                 'emp_status': employee.emp_status,
    #             })

    #         sheet = workbook.add_worksheet('End Of service Benefit')
    #         format1 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
    #         format2 = workbook.add_format({'font_size': 10, 'bold': True})
    #         format3 = workbook.add_format({'font_size': 10, 'align': 'left'})
    #         format4 = workbook.add_format({'font_size': 10, 'align': 'right'})

    #         sheet.merge_range('A2:E2', 'Employees - Benefit Accrued As On : ' + date.strftime("%d-%m-%Y"), format1)
    #         sheet.merge_range('F2:I2', 'Company: ' + company_name.name, format1)
    #         sheet.write('A5', "Branch Code", format2)
    #         sheet.write('B5', "Employee Number", format2)
    #         sheet.write('C5', "Employee Name", format2)
    #         sheet.write('D5', "Originial Hire Date", format2)
    #         sheet.write('E5', "Gratuity Days", format2)
    #         sheet.write('F5', "Basic Salary", format2)
    #         sheet.write('G5', "Allowance", format2)
    #         sheet.write('H5', "Total Pay", format2)
    #         sheet.write('I5', "Travel Benefit", format2)
    #         sheet.write('J5', "Tickets", format2)
    #         sheet.write('K5', "Travel Sector", format2)
    #         sheet.write('L5', "Passage Accrued", format2)
    #         sheet.write('M5', "Passage Allowance", format2)
    #         sheet.write('N5', "Last Leave Date", format2)
    #         sheet.write('O5', "Leave Days", format2)
    #         sheet.write('P5', "Leave Pay Accrued", format2)
    #         sheet.write('Q5', "Total Gratuity Accrued", format2)
    #         sheet.write('R5', "Status", format2)

    #         row_number = 5
    #         column_number = 0
    #         for emp in employee_details:
    #             sheet.write(row_number, column_number, emp['branch_code'], format3)
    #             sheet.write(row_number, column_number + 1, emp['emp_code'], format3)
    #             sheet.write(row_number, column_number + 2, emp['employee_name'], format3)
    #             sheet.write(row_number, column_number + 3, emp['original_hire_date'], format3)
    #             sheet.write(row_number, column_number + 4, emp['gratuity_days'], format3)
    #             sheet.write(row_number, column_number + 5, emp['basic_salary'], format3)
    #             sheet.write(row_number, column_number + 6, emp['allowance'], format3)
    #             sheet.write(row_number, column_number + 7, emp['total_pay'], format3)
    #             sheet.write(row_number, column_number + 8, str(emp['travel_benefit']), format3)
    #             sheet.write(row_number, column_number + 9, int(emp['tickets']), format3)
    #             sheet.write(row_number, column_number + 10, emp['travel_sector'], format3)
    #             sheet.write(row_number, column_number + 11, emp['passage_accrued'], format3)
    #             sheet.write(row_number, column_number + 12, emp['passage_allowance'], format3)
    #             sheet.write(row_number, column_number + 13, emp['last_leave_date'], format3)
    #             sheet.write(row_number, column_number + 14, emp['leave_days'], format3)
    #             sheet.write(row_number, column_number + 15, emp['leave_pay_accrued'], format3)
    #             sheet.write(row_number, column_number + 16, emp['total_gratuity_accrued'], format3)
    #             sheet.write(row_number, column_number + 17, emp['emp_status'], format3)
    #             row_number += 1


class ProductXlsxBranch(models.AbstractModel):
    _name = 'report.pways_eosb_xls_report.eosb_xlsx_branch'
    _inherit = 'report.report_xlsx.abstract'

    def get_unproductive_days(self, gratuity_date, employee_id):
        unpaid_leave_days = 0.0
        for date in gratuity_date:
            # print("\n\n DATEEEEEEEEEE", date)
            unpaid_leave_ids = employee_id.leave_ids.filtered(lambda
                                                                  x: x.state == 'validate' and x.request_date_from >= date and x.request_date_to <= date and not x.holiday_status_id.is_paid and not x.holiday_status_id.work_entry_type_id.is_paid)
            # print("\n\n unpaid_leave_ids",unpaid_leave_ids)
            for rec in unpaid_leave_ids:
                unpaid_leave_days += 1

            attendance_ids = employee_id.attendance_ids.filtered(lambda
                                                                     x: x.check_in.date() >= date if x.check_in else None and x.check_out.date() <= date if x.check_out else None)
            # print("\n\n attendance_ids",attendance_ids)
            week_off_ids = employee_id.dayofweek_ids.filtered(lambda x: x.date == date)
            # print("\n\n week_off_ids",week_off_ids)
            public_holiday_ids = self.env['resource.calendar.leaves'].search(
                [('date_from', '<=', date), ('date_to', '>=', date), ('resource_id', '=', False)])
            # print("\n\n public_holiday_ids",public_holiday_ids)
            if not attendance_ids and not week_off_ids and not public_holiday_ids and not unpaid_leave_ids:
                unpaid_leave_days += 1
        return unpaid_leave_days

    # point no 16
    # For Branch
    def generate_xlsx_report(self, workbook, data, products=None):
        employee_details = []
        date = datetime.datetime.strptime(data.get('as_on_date'), '%Y-%m-%d').date()
        company_id = data.get('company_id')
        branch_ids = data.get('branch_ids')
        company_name = self.env['res.company'].browse(company_id)
        company_gratuity_date = company_name.gratuity_date
        if not company_gratuity_date:
            raise ValidationError(_("Please set gratuity date in employee setting."))
        if date:
            domain = [('date_start', '<=', date), ('state', '=', 'open'), ('company_id', '=', int(company_id))]
            if branch_ids:
                domain.append(('branch_id', 'in', branch_ids))
            contract_ids = self.env['hr.contract'].search(domain)

            for branch in contract_ids.mapped('branch_id'):
                print('branch+++++++++++++++++', branch)

                total_emp = 0
                passage_accrued_total = 0
                # passage_allowance_total = 0
                leave_pay_accrued_total = 0
                total_gratuity_accrued_total = 0
                print('contract_ids++++++++++++++', contract_ids, contract_ids.mapped('employee_id'))
                for employee in contract_ids.mapped('employee_id'):
                    if branch.code == employee.branch_id.code:
                        print('\nemployee++++++++++++++++', employee.id, employee.name, employee.branch_id.code)
                        passage_allowance = 0.0
                        travel_benefit = employee.travel_benefit
                        travel_benefit_ticket = travel_benefit.tickets
                        travel_benefit_month = travel_benefit.month

                        travel_sector_id = employee.travel_sector_id
                        travel_sector_amount = travel_sector_id.amount
                        if travel_benefit_month > 0:
                            # passage_allowance = ((travel_benefit_ticket * (travel_sector_amount / travel_benefit_month)))
                            # passage_allowance = (((travel_sector_amount * travel_benefit_ticket) / travel_benefit_month))
                            passage_allowance = travel_sector_amount * travel_benefit_ticket

                        contract_id = contract_ids.filtered(lambda x: x.employee_id == employee and x.state == 'open')
                        allowance = sum(
                            contract_id.allowance_ids.filtered(lambda x: x.category_id.code == 'ALW').mapped('amount'))

                        basic_salary = contract_id[-1].wage
                        gross_amount = contract_id[-1].gross_amount
                        net_amount = contract_id[-1].net_amount
                        total_pay = basic_salary + allowance

                        # leave calculation
                        leave_ids = self.env['hr.leave']
                        leave_ids_approval_state = self.env['hr.leave']
                        leave_ids_noairticket = self.env['hr.leave']
                        last_date = False
                        amount = 0.0
                        accrued_leave_amount = 0.0
                        allocation_days = 0.0
                        leave_days = 0.0
                        accrued_leave_days = 0.0

                        passage_accrued = 0.0
                        passage_daily_rate = 0.0
                        passage_days = 0.0

                        accural_ids = self.env['hr.leave.allocation'].search(
                            [('employee_id', '=', employee.id), ('allocation_type', '=', 'accrual'),
                             ('state', '=', 'validate')])
                        print('accural_ids+++++++++++++', accural_ids)
                        holiday_status_ids = accural_ids.mapped('holiday_status_id')
                        print('holiday_status_ids++++++++++++', holiday_status_ids)
                        for holiday_status_id in holiday_status_ids:
                            take_leave_ids = self.env['hr.leave'].search(
                                [('employee_id', '=', employee.id), ('holiday_status_id', '=', holiday_status_id.id),
                                 ('air_ticket', '=', 'company'),
                                 ('request_date_from', '<', datetime.datetime.now().strftime('%Y-%m-%d'))])
                            leave_ids |= take_leave_ids
                            take_leave_state_ids = self.env['hr.leave'].search(
                                [('employee_id', '=', employee.id), ('holiday_status_id', '=', holiday_status_id.id),
                                 ('state', 'in', ['validate1', 'validate']),
                                 ('request_date_from', '<', datetime.datetime.now().strftime('%Y-%m-%d'))])
                            print('take_leave_state_ids++++++++++++++', take_leave_state_ids)
                            leave_ids_approval_state |= take_leave_state_ids
                        # not leave_ids take hire date
                        if leave_ids:
                            # last_date = str(max(leave_ids.mapped('request_date_to')))
                            last_date = str(max(leave_ids.mapped('request_date_from')))
                            # passage_accured calculation
                            passage_last_date = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()
                            passage_days = (date - passage_last_date).days
                            if travel_benefit_month == 12:
                                passage_daily_rate = (travel_sector_amount / 365)
                            if travel_benefit_month == 24:
                                passage_daily_rate = (travel_sector_amount / 730)
                            passage_accrued = (passage_days * passage_daily_rate * travel_benefit_ticket)
                        else:
                            # last_date = str(max(leave_ids.mapped('request_date_to')))
                            last_date = str(employee.original_hire_date)
                            # passage_accured calculation
                            passage_last_date = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()
                            passage_days = (date - passage_last_date).days
                            if travel_benefit_month == 12:
                                passage_daily_rate = (travel_sector_amount / 365)
                            if travel_benefit_month == 24:
                                passage_daily_rate = (travel_sector_amount / 730)
                            passage_accrued = (passage_days * passage_daily_rate * travel_benefit_ticket)

                        travel_ticket = travel_sector_amount * travel_benefit_ticket
                        if passage_accrued > travel_ticket:
                            new_passage_accrued = travel_sector_amount
                        else:
                            new_passage_accrued = passage_accrued

                        for holiday_status_id in holiday_status_ids:
                            take_leave_ids = self.env['hr.leave'].search(
                                [('employee_id', '=', employee.id), ('holiday_status_id', '=', holiday_status_id.id),
                                 ('request_date_from', '<', datetime.datetime.now().strftime('%Y-%m-%d'))])
                            leave_ids_noairticket |= take_leave_ids

                        if leave_ids_noairticket:
                            last_date_new = str(max(leave_ids_noairticket.mapped('request_date_from')))

                        print('accural_ids+++++++++++++', accural_ids)
                        print('leave_ids_approval_state+++++++++++++', leave_ids_approval_state)
                        allocation_days = sum(accural_ids.mapped('number_of_days_display'))
                        leave_days = sum(leave_ids_approval_state.mapped('number_of_days'))
                        print('allocation_days+++++++++++++++', allocation_days)
                        print('leave_days+++++++++++++++', leave_days)
                        accrued_leave_days = allocation_days - leave_days

                        amount = (gross_amount / 30) if gross_amount > 0 else 0
                        accrued_leave_amount = (accrued_leave_days * amount)

                        # employee gratuity_days calculation
                        gratuity_amount = 0.0

                        delta_date = date - company_gratuity_date
                        gratuity_date = [company_gratuity_date + timedelta(days=i) for i in range(delta_date.days + 1)]
                        # print("<<<<<gratuity_date>>>>>", gratuity_date)
                        joined_date = employee.original_hire_date
                        # print("<<<<DDDDDDDDD>>>>", date, joined_date)
                        gratuity_days = ((date - joined_date).days) if date and joined_date else 0.0
                        # print("<<<<gratuity_days>>>>", gratuity_days)
                        gratuity_unproductive_days = employee.gratuity_unproductive_days
                        # print("<<<<<gratuity_unproductive_days>>>>>", gratuity_unproductive_days)
                        worked_years = int(date.year) if date else 0.0 - int(joined_date.year) if joined_date else 0.0
                        unproductive_days = self.get_unproductive_days(gratuity_date, employee)
                        # print("<<<<<unproductive_days>>>>>", unproductive_days)
                        total_unproductive_days = unproductive_days + gratuity_unproductive_days
                        # print("<<<<<total_unproductive_days>>>>>", total_unproductive_days)
                        eligible_days = gratuity_days - total_unproductive_days
                        # print("<<<<eligible_days>>>>", eligible_days)
                        if eligible_days < 365:
                            gratuity_amount = 0

                        # if eligible_days >= 365 and eligible_days <= 1825:
                        if eligible_days >= 0 and eligible_days <= 1825:
                            # print("<<<<basic_salary>>>>", basic_salary)
                            gratuity_amount = (basic_salary * (12 / 365)) * ((21 / 365) * eligible_days)

                        if eligible_days > 1825:
                            more_then_five = worked_years - 5
                            up_five_year_eligible_days = eligible_days - 1825
                            less_five_amount = ((basic_salary * (12 / 365)) * ((21 / 365 * 1825)))
                            more_five_amount = ((basic_salary * (12 / 365)) * (30 / 365 * up_five_year_eligible_days))
                            gratuity_amount = less_five_amount + more_five_amount

                        passage_accrued_total = passage_accrued_total + round(new_passage_accrued, 2)
                        # passage_allowance_total = passage_allowance_total + round(passage_allowance, 2)
                        leave_pay_accrued_total = leave_pay_accrued_total + round(accrued_leave_amount, 2)
                        total_gratuity_accrued_total = total_gratuity_accrued_total + round(gratuity_amount)

                        total_emp = total_emp + 1

                employee_details.append({
                    'branch_code': branch.code if branch else '',
                    'branch_name': branch.name if branch else '',
                    'no_of_emp': total_emp,
                    'passage_accrued': passage_accrued_total,
                    # 'passage_allowance': passage_allowance_total,
                    'leave_pay_accrued': leave_pay_accrued_total,
                    'total_gratuity_accrued': total_gratuity_accrued_total,
                })

            print('employee_details++++++++++++++++', employee_details)

            sheet = workbook.add_worksheet('End Of service Benefit')
            format1 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
            format2 = workbook.add_format({'font_size': 10, 'bold': True})
            format3 = workbook.add_format({'font_size': 10, 'align': 'left'})

            sheet.merge_range('A2:E2', 'Employees - Benefit Accrued As On : ' + date.strftime("%d-%m-%Y"), format1)
            sheet.merge_range('F2:I2', 'Company: ' + company_name.name, format1)
            sheet.write('A5', "Branch Code", format2)
            sheet.write('B5', "Branch Name", format2)
            sheet.write('C5', "No. of Employees", format2)
            sheet.write('D5', "Passage Accrued", format2)
            # sheet.write('C1', "Passage Allowance", format2)
            sheet.write('E5', "Leave Pay Accrued", format2)
            sheet.write('F5', "Total Gratuity Accrued", format2)

            row_number = 5
            column_number = 0
            for emp in employee_details:
                sheet.write(row_number, column_number, emp['branch_code'], format3)
                sheet.write(row_number, column_number + 1, emp['branch_name'], format3)
                sheet.write(row_number, column_number + 2, emp['no_of_emp'], format3)
                sheet.write(row_number, column_number + 3, emp['passage_accrued'], format3)
                # sheet.write(row_number, column_number + 2, emp['passage_allowance'], format3)
                sheet.write(row_number, column_number + 4, emp['leave_pay_accrued'], format3)
                sheet.write(row_number, column_number + 5, emp['total_gratuity_accrued'], format3)
                row_number += 1
