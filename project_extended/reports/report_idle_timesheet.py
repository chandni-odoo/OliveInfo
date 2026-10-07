# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from pytz import timezone, UTC
from datetime import timedelta
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import pytz
import datetime


class ReportIdleSheetXls(models.AbstractModel):
    _name = 'report.project_extended.report_idle_timesheet'
    _inherit = 'report.report_xlsx.abstract'

    # Point no 4 PS2 Idle Reporting
    def generate_xlsx_report(self, workbook, data, products=None):

        # from_date = datetime.datetime.strptime(data.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.datetime.strptime(data.get('date_to'), '%Y-%m-%d').date()
        end_date_with_time = datetime.datetime.strptime(data.get('date_to'), '%Y-%m-%d')
        end_date_22_59 = end_date_with_time.replace(minute=59, hour=22, second=00)
        # employee_id = data.get('employee_id')
        branch_id = self.env['res.branch'].browse(data.get('branch_id'))

        if date_to:
            format1 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
            format2 = workbook.add_format({'font_size': 10, 'bold': True})
            format3 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': True})
            format4 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
            format5 = workbook.add_format({'font_size': 10, 'align': 'left'})
            format6 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})

            sheet = workbook.add_worksheet("Idle Timesheet")

            year_line = 'Idle Timesheet' + str(date_to.strftime("%b")) + '   ' + str(
                date_to.year)
            idle_position = 'Idle Position as on ' + str(date_to)

            sheet.merge_range('D1:M1', year_line, format1)
            sheet.merge_range('D2:M2', idle_position, format1)

            sheet.merge_range('A4:A5', 'Employee ID', format1)
            sheet.merge_range('B4:B5', 'Name', format1)
            sheet.merge_range('C4:C5', 'BU Code', format1)
            sheet.merge_range('D4:D5', 'Nationality', format1)
            sheet.merge_range('E4:E5', 'QID / VISA', format1)
            sheet.merge_range('F4:F5', 'Employee HR Type', format1)
            sheet.merge_range('G4:G5', 'Vendor Name', format1)
            sheet.merge_range('H4:I4', 'Designation ', format1)
            sheet.write(4, 7, 'Trade', format1)
            sheet.merge_range('H5:H5', 'Trade', format1)
            sheet.write(4, 8, 'Skills', format1)
            sheet.merge_range('I5:I5', 'Skills', format1)
            sheet.merge_range('J4:J5', 'Idle From Date', format1)
            sheet.merge_range('K4:K5', 'Idle days Ageing ', format1)
            sheet.merge_range('L4:L5', 'Last Working Date ', format1)
            sheet.merge_range('M4:O4', 'Feature Planning Details', format1)
            sheet.write(4, 12, 'Customer Name', format1)
            sheet.merge_range('M5:M5', 'Customer Name', format1)
            sheet.write(4, 13, 'Planned Start Date', format1)
            sheet.merge_range('N5:N5', 'Planned Start Date', format1)
            sheet.write(4, 14, 'Category', format1)
            sheet.merge_range('O5:O5', 'Category', format1)

            data_list = []
            domain = []
            if branch_id:
                branch_ids = [b.id for b in branch_id]
                domain.append(('branch_id', 'in', branch_ids))
                emp = self.env['hr.employee'].search(domain)
            else:
                emp = self.env['hr.employee'].search([])

            for rec in emp.filtered(lambda x: x.emp_status == 'active' and x.billable):
                # if rec.id == 8013:
                skills = ', '.join(s.name for s in rec.product_ids)
                vals = {
                    'employee_id': rec.emp_no if rec.emp_no else '',
                    'name': rec.name if rec.name else '',
                    'bu_code': rec.branch_id.name if rec.branch_id.name else '',  # need to check bu_code
                    'nationality': rec.country_id.name if rec.country_id.name else '',
                    'qid_visa': rec.qid_no if rec.qid_no else '',
                    'employee_type': rec.hr_employee_type if rec.hr_employee_type else '',
                    'vendor_name': rec.vendor_name.name if rec.vendor_name else '',
                    'trade': rec.job_title if rec.job_title else '',
                    'employee_skill_ids': skills if rec.product_ids else '',
                }

                future_planning = self.env['planning.slot'].search(
                    [('employee_id', '=', rec.id), ('start_datetime', '>', end_date_with_time)], limit=1)
                if future_planning:
                    vals.update({
                        'customer_name': future_planning.task_id.partner_id.name if future_planning.task_id.partner_id else '',
                        'planned_start_date': future_planning.start_datetime.date(),
                        'category_ids': str(future_planning.task_id.seq_code) + ' ' + str(future_planning.task_id.name),
                    })
                else:
                    vals.update({
                        'customer_name': '',
                        'planned_start_date': '',
                        'category_ids': '',
                    })

                # print('end_date_with_time++++++++++++', end_date_with_time)
                # end_date_with_time_next_day = end_date_with_time + timedelta(days=1)
                # print('end_date_with_time_next_day+++++++++++++++++', end_date_with_time_next_day)
                total_attendance = self.env['hr.attendance'].search(
                    [('employee_id', '=', rec.id), ('check_in', '<=', end_date_22_59)], order='check_in desc')
                counter = 0
                last_duty_attendance = None
                last_on_duty_attendance = None
                for attendance in total_attendance:
                    # if attendance.status == 'on_duty':
                    if attendance.status != 'idle':
                        last_on_duty_attendance = attendance.check_in
                        break
                    if attendance.status == 'idle':
                        counter += 1
                    # last_duty_attendance = remove_5_30.date()

                new_att_date = None
                if last_on_duty_attendance:
                    new_att_date = last_on_duty_attendance + timedelta(hours=5)
                    new_att_date = new_att_date + timedelta(minutes=30)

                last_duty_attendance = new_att_date + timedelta(days=1) if new_att_date else ''

                vals.update({
                    'idle_from_date': last_duty_attendance if last_duty_attendance else '',
                    'idle_count': counter if counter else '',
                    'last_working_date': new_att_date.date() if new_att_date else '',
                })

                if total_attendance:
                    # today_5_30 = total_attendance[0].check_in + timedelta(hours=5)
                    # today_5_30 = today_5_30 + timedelta(minutes=30)
                    # if today_5_30.date() == date_to:
                    # if not total_attendance[0].status == 'on_duty':
                    if not total_attendance[0].status in ['general', 'stand_by', 'on_duty', 'training']:
                        data_list.append(vals)

            row_number = 10
            column_number = 0
            for dl in data_list:
                sheet.write(row_number, column_number + 0, dl['employee_id'], format5)
                sheet.write(row_number, column_number + 1, dl['name'], format5)
                sheet.write(row_number, column_number + 2, dl['bu_code'], format5)
                sheet.write(row_number, column_number + 3, dl['nationality'], format5)
                sheet.write(row_number, column_number + 4, dl['qid_visa'], format5)
                sheet.write(row_number, column_number + 5, dl['employee_type'], format5)
                sheet.write(row_number, column_number + 6, dl['vendor_name'], format5)
                sheet.write(row_number, column_number + 7, dl['trade'], format5)
                sheet.write(row_number, column_number + 8, dl['employee_skill_ids'], format5)
                sheet.write(row_number, column_number + 9, str(dl['idle_from_date']), format5)
                sheet.write(row_number, column_number + 10, str(dl['idle_count']), format5)
                sheet.write(row_number, column_number + 11, str(dl['last_working_date']), format5)
                sheet.write(row_number, column_number + 12, str(dl['customer_name']), format5)
                sheet.write(row_number, column_number + 13, str(dl['planned_start_date']), format5)
                sheet.write(row_number, column_number + 14, str(dl['category_ids']), format5)
                row_number += 1
