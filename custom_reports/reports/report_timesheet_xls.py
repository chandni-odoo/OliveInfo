# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from pytz import timezone, UTC
from datetime import timedelta
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import pytz
import datetime


class ReportClientXls(models.AbstractModel):
    _name = 'report.custom_reports.report_client_timesheet'
    _inherit = 'report.report_xlsx.abstract'

    def getColumnName(self, column):
        result = ''
        while column > 0:
            index = (column - 1) % 26
            result += chr(index + ord('A'))
            column = (column - 1) // 26

        return result[::-1]

    # point no 1 PS2 Client Timesheet
    def generate_xlsx_report(self, workbook, data, products=None):
        print('data++++++++++++++, data', data)

        from_date = datetime.datetime.strptime(data.get('start_to'), '%Y-%m-%d').date()
        to_date = datetime.datetime.strptime(data.get('end_to'), '%Y-%m-%d').date()
        vendor_id = data.get('vendor_id')
        task_id = self.env['project.task'].browse(int(data.get('task_id')))

        colmun_list = []
        total_list = []

        if from_date and to_date:

            delta_date = to_date - from_date
            all_days = [from_date + timedelta(days=i) for i in range(delta_date.days + 1)]

            format1 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
            format2 = workbook.add_format({'font_size': 10, 'bold': True})
            format3 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': True})
            format4 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
            format5 = workbook.add_format({'font_size': 10, 'align': 'center'})
            format55 = workbook.add_format({'font_size': 10, 'align': 'left'})
            format6 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
            format7 = workbook.add_format({'font_size': 10, 'bold': True, 'color': 'red'})

            sheet = workbook.add_worksheet("Client Timesheet")

            sheet.merge_range('G1:K1', task_id.partner_id.name, format1)
            sale_line_name = str(task_id.seq_code) + ' / ' + task_id.sale_line_id.name
            year_line = 'MAN HOURS CALCULATION SHEET - ' + str(from_date.strftime("%b")) + ' ' + str(
                from_date.year) + ' - ' + str(sale_line_name)
            sheet.merge_range('D3:Q3', year_line, format1)
            sheet.merge_range('A6:B6', task_id.name, format1)

            sheet.merge_range('A7:A8', 'S. No.', format1)
            sheet.merge_range('B7:B8', 'EMP#', format1)
            sheet.merge_range('C7:C8', 'LOCATION', format1)
            sheet.merge_range('D7:D8', 'NAME', format1)

            row_number = 6
            column_number = 4
            for spec_date in all_days:
                if spec_date.strftime("%A") == 'Friday':
                    sheet.write(row_number, column_number, spec_date.strftime("%d"), format7)
                    sheet.write(row_number + 1, column_number, spec_date.strftime("%A"), format7)
                else:
                    sheet.write(row_number, column_number, spec_date.strftime("%d"), format2)
                    sheet.write(row_number + 1, column_number, spec_date.strftime("%A"), format2)
                column_number += 1

            normal = str(self.getColumnName(column_number + 1)) + '7:' + str(
                self.getColumnName(column_number + 1)) + '8'
            ot = str(self.getColumnName(column_number + 2)) + '7:' + str(self.getColumnName(column_number + 2)) + '8'
            sp_ot = str(self.getColumnName(column_number + 3)) + '7:' + str(self.getColumnName(column_number + 3)) + '8'
            total = str(self.getColumnName(column_number + 4)) + '7:' + str(self.getColumnName(column_number + 4)) + '8'

            sheet.merge_range(normal, 'Normal HRS', format1)
            sheet.merge_range(ot, 'OT HRS', format1)
            sheet.merge_range(sp_ot, 'SP OT HRS', format1)
            sheet.merge_range(total, 'Total HRS', format1)

            employee_details = {}
            employee_list = []

            for timesheet in task_id.timesheet_ids:
                employee_details.update({
                    timesheet.employee_id: timesheet
                })
                employee_list.append(timesheet.employee_id)

            print('employee_list+++++++++++++', list(set(employee_list)))
            seq = 1
            emp_list = []
            (v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, v12, v13, v14, v15, v16, v17, v18, v19, v20, v21, v22, v23,
             v24, v25, v26, v27, v28, v29, v30, v31) = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                                        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                                        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                                        0.0)

            final_total_normal_hrs = 0
            final_overtime_hrs = 0
            final_special_overtime_hrs = 0
            final_total_hrs = 0
            for emp in list(set(employee_list)):
                fill_date = []
                worked_hours_list = []

                account_analytic_line = self.env['account.analytic.line'].search(
                    [('employee_id', '=', emp.id), ('task_id', '=', task_id.id)])
                for date in account_analytic_line:
                    fill_date.append(date.date)

                emp_list.append({
                    's_no': seq,
                    'emp_code': emp.emp_no if emp.emp_no else '',
                    'location': task_id.partner_location_id.name if task_id.partner_location_id.name else '',
                    'emp_name': emp.name if emp.name else '',
                })
                seq += 1

                normal_hrs = self.env['account.analytic.line'].search(
                    [('employee_id', '=', emp.id), ('task_id', '=', task_id.id)])
                total_normal_hrs = sum(normal_hrs.mapped('units_amounts'))

                overtime = self.env['overtime.lines'].search(
                    [('employee_id', '=', emp.id), ('overtime_id', '=', task_id.id)])
                total_overtime = sum(overtime.mapped('ot_hour'))

                ot_type = self.env['hr.ot.type'].search([('code', 'in', ['WDS', 'HDS', 'SPHD'])])
                ot_type = [s.id for s in ot_type]
                special_overtime = self.env['overtime.lines'].search(
                    [('employee_id', '=', emp.id), ('overtime_id', '=', task_id.id), ('ot_type', 'in', ot_type)])
                total_special_overtime = sum(special_overtime.mapped('ot_hour'))

                total_hrs = total_normal_hrs + total_overtime + total_special_overtime
                total_list.append({
                    'normal_hrs': total_normal_hrs if total_normal_hrs else 0,
                    'ot_hrs': total_overtime if total_overtime else 0,
                    'sp_ot_hrs': total_special_overtime if total_special_overtime else 0,
                    'total_hrs': total_hrs if total_hrs else 0,
                })

                final_total_normal_hrs += total_normal_hrs
                final_overtime_hrs += total_overtime
                final_special_overtime_hrs += total_special_overtime
                final_total_hrs += total_hrs

                # dynamic days column and data
                row_number = 9
                column_number = 4
                for spec_date in all_days:
                    if spec_date.strftime("%A") == 'Friday':
                        sheet.write(row_number, column_number, spec_date.strftime("%d"), format7)
                    else:
                        sheet.write(row_number, column_number, spec_date.strftime("%d"), format2)
                    column_number += 1
                    worked_hours = ''

                    if spec_date in fill_date:
                        account_analytic_line = self.env['account.analytic.line'].search(
                            [('employee_id', '=', emp.id), ('task_id', '=', task_id.id), ('date', '=', spec_date)],
                        )
                        worked_hours = sum(account_analytic_line.mapped('units_amounts'))
                    else:
                        worked_hours = ''

                    if spec_date.strftime("%d") == '01':
                        v1 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '02':
                        v2 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '03':
                        v3 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '04':
                        v4 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '05':
                        v5 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '06':
                        v6 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '07':
                        v7 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '08':
                        v8 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '09':
                        v9 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '10':
                        v10 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '11':
                        v11 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '12':
                        v12 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '13':
                        v13 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '14':
                        v14 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '15':
                        v15 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '16':
                        v16 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '17':
                        v17 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '18':
                        v18 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '19':
                        v19 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '20':
                        v20 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '21':
                        v21 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '22':
                        v22 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '23':
                        v23 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '24':
                        v24 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '25':
                        v25 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '26':
                        v26 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '27':
                        v27 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '28':
                        v28 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '39':
                        v29 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '30':
                        v30 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '31':
                        v31 += + worked_hours if worked_hours else 0.0

                    worked_hours_list.append(worked_hours)
                colmun_list.append(worked_hours_list)

            row_number = 9
            column_number = 0
            for val in emp_list:
                sheet.write(row_number, column_number, val['s_no'], format55)
                sheet.write(row_number, column_number + 1, val['emp_code'], format55)
                sheet.write(row_number, column_number + 2, val['location'], format55)
                sheet.write(row_number, column_number + 3, val['emp_name'], format55)
                row_number += 1

            row_number = 9
            for val_list in colmun_list:
                column_number = 4
                for val in val_list:
                    sheet.write(row_number, column_number, str(round(val, 2)) if val else '', format5)
                    column_number += 1
                row_number += 1

            row_number = 9
            for total_leave in total_list:
                sheet.write(row_number, column_number,
                            round(total_leave['normal_hrs'], 2) if total_leave['normal_hrs'] else 0, format5)
                sheet.write(row_number, column_number + 1,
                            round(total_leave['ot_hrs'], 2) if total_leave['ot_hrs'] else 0, format5)
                sheet.write(row_number, column_number + 2,
                            round(total_leave['sp_ot_hrs'], 2) if total_leave['sp_ot_hrs'] else 0, format5)
                sheet.write(row_number, column_number + 3,
                            round(total_leave['total_hrs'], 2) if total_leave['total_hrs'] else 0, format5)
                row_number += 1

            all_total = 'A' + str(row_number + 2) + ':D' + str(row_number + 2)
            sheet.merge_range(all_total, 'TOTAL WORKING HRS.', format1)

            column_number = 3
            sheet.write(row_number + 1, column_number + 1, round(v1, 2), format1)
            sheet.write(row_number + 1, column_number + 2, round(v2, 2), format1)
            sheet.write(row_number + 1, column_number + 3, round(v3, 2), format1)
            sheet.write(row_number + 1, column_number + 4, round(v4, 2), format1)
            sheet.write(row_number + 1, column_number + 5, round(v5, 2), format1)
            sheet.write(row_number + 1, column_number + 6, round(v6, 2), format1)
            sheet.write(row_number + 1, column_number + 7, round(v7, 2), format1)
            sheet.write(row_number + 1, column_number + 8, round(v8, 2), format1)
            sheet.write(row_number + 1, column_number + 9, round(v9, 2), format1)
            sheet.write(row_number + 1, column_number + 10, round(v10, 2), format1)
            sheet.write(row_number + 1, column_number + 11, round(v11, 2), format1)
            sheet.write(row_number + 1, column_number + 12, round(v12, 2), format1)
            sheet.write(row_number + 1, column_number + 13, round(v13, 2), format1)
            sheet.write(row_number + 1, column_number + 14, round(v14, 2), format1)
            sheet.write(row_number + 1, column_number + 15, round(v15, 2), format1)
            sheet.write(row_number + 1, column_number + 16, round(v16, 2), format1)
            sheet.write(row_number + 1, column_number + 17, round(v17, 2), format1)
            sheet.write(row_number + 1, column_number + 18, round(v18, 2), format1)
            sheet.write(row_number + 1, column_number + 19, round(v19, 2), format1)
            sheet.write(row_number + 1, column_number + 20, round(v20, 2), format1)
            sheet.write(row_number + 1, column_number + 21, round(v21, 2), format1)
            sheet.write(row_number + 1, column_number + 22, round(v22, 2), format1)
            sheet.write(row_number + 1, column_number + 23, round(v23, 2), format1)
            sheet.write(row_number + 1, column_number + 24, round(v24, 2), format1)
            sheet.write(row_number + 1, column_number + 25, round(v25, 2), format1)
            sheet.write(row_number + 1, column_number + 26, round(v26, 2), format1)
            sheet.write(row_number + 1, column_number + 27, round(v27, 2), format1)
            sheet.write(row_number + 1, column_number + 28, round(v28, 2), format1)
            c_no = column_number + 28
            if len(all_days) > 28:
                sheet.write(row_number + 1, column_number + 29, round(v29, 2), format1)
                sheet.write(row_number + 1, column_number + 30, round(v30, 2), format1)
                c_no = column_number + 30
                if len(all_days) > 30:
                    sheet.write(row_number + 1, column_number + 31, round(v31, 2), format1)
                    c_no = column_number + 31

            sheet.write(row_number + 1, c_no + 1, round(final_total_normal_hrs, 2), format1)
            sheet.write(row_number + 1, c_no + 2, round(final_overtime_hrs, 2), format1)
            sheet.write(row_number + 1, c_no + 3, round(final_special_overtime_hrs, 2), format1)
            sheet.write(row_number + 1, c_no + 4, round(final_total_hrs, 2), format1)


class ReportVendorXls(models.AbstractModel):
    _name = 'report.custom_reports.report_vendor_timesheet'
    _inherit = 'report.report_xlsx.abstract'

    def getColumnName(self, column):
        result = ''
        while column > 0:
            index = (column - 1) % 26
            result += chr(index + ord('A'))
            column = (column - 1) // 26

        return result[::-1]

    # point no 1 PS2 Vendor Timesheet
    def generate_xlsx_report(self, workbook, data, products=None):
        print('data++++++++++++++, data', data)

        from_date = datetime.datetime.strptime(data.get('start_to'), '%Y-%m-%d').date()
        to_date = datetime.datetime.strptime(data.get('end_to'), '%Y-%m-%d').date()
        task_id = self.env['project.task'].browse(int(data.get('task_id')))
        vendor_id = self.env['res.partner'].browse(int(data.get('vendor_id')))

        colmun_list = []
        total_list = []

        if from_date and to_date:

            delta_date = to_date - from_date
            all_days = [from_date + timedelta(days=i) for i in range(delta_date.days + 1)]

            format1 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
            format2 = workbook.add_format({'font_size': 10, 'bold': True})
            format7 = workbook.add_format({'font_size': 10, 'bold': True, 'color': 'red'})
            format3 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': True})
            format4 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
            format5 = workbook.add_format({'font_size': 10, 'align': 'center'})
            format55 = workbook.add_format({'font_size': 10, 'align': 'left'})
            format6 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})

            sheet = workbook.add_worksheet("Vendor Timesheet")

            # sheet.merge_range('G1:K1', task_id.partner_id.name, format1)
            sheet.merge_range('G1:K1', vendor_id.name, format1)
            # sheet.merge_range('M1:N1', vendor_id.name, format1)
            sale_line_name = str(task_id.seq_code) + ' / ' + task_id.sale_line_id.name
            year_line = 'MAN HOURS CALCULATION SHEET - ' + str(from_date.strftime("%b")) + ' ' + str(
                from_date.year) + ' - ' + str(sale_line_name)
            sheet.merge_range('D3:Q3', year_line, format1)
            sheet.merge_range('A6:B6', task_id.name, format1)

            sheet.merge_range('A7:A8', 'S. No.', format1)
            sheet.merge_range('B7:B8', 'EMP#', format1)
            sheet.merge_range('C7:C8', 'Vendor EMP#', format1)
            sheet.merge_range('D7:D8', 'NAME', format1)
            sheet.merge_range('E7:E8', 'Area', format1)

            row_number = 6
            column_number = 5
            for spec_date in all_days:
                if spec_date.strftime("%A") == 'Friday':
                    sheet.write(row_number, column_number, spec_date.strftime("%d"), format7)
                    sheet.write(row_number + 1, column_number, spec_date.strftime("%A"), format7)
                else:
                    sheet.write(row_number, column_number, spec_date.strftime("%d"), format2)
                    sheet.write(row_number + 1, column_number, spec_date.strftime("%A"), format2)
                column_number += 1

            normal = str(self.getColumnName(column_number + 1)) + '7:' + str(
                self.getColumnName(column_number + 1)) + '8'

            sheet.merge_range(normal, 'Total HRS', format1)

            employee_details = {}
            employee_list = []

            for timesheet in task_id.timesheet_ids.filtered(lambda m: m.employee_id.vendor_name.id == vendor_id.id):
                employee_details.update({
                    timesheet.employee_id: timesheet
                })
                employee_list.append(timesheet.employee_id)

            seq = 1
            emp_list = []
            (v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, v12, v13, v14, v15, v16, v17, v18, v19, v20, v21, v22, v23,
             v24, v25, v26, v27, v28, v29, v30, v31) = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                                        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                                        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                                        0.0)

            final_total_normal_hrs = 0

            print('employee_list+++++++++++++++++', employee_list)

            for emp in list(set(employee_list)):
                fill_date = []
                worked_hours_list = []

                account_analytic_line = self.env['account.analytic.line'].search(
                    [('employee_id', '=', emp.id), ('task_id', '=', task_id.id)])
                for date in account_analytic_line:
                    fill_date.append(date.date)

                emp_list.append({
                    's_no': seq,
                    'emp_code': emp.emp_no if emp.emp_no else '',
                    'emp_vendor_code': emp.vendor_employee_id if emp.emp_no else '',
                    'emp_name': emp.name if emp.name else '',
                    'location': task_id.partner_location_id.name if task_id.partner_location_id.name else '',
                })
                seq += 1

                normal_hrs = self.env['account.analytic.line'].search(
                    [('employee_id', '=', emp.id), ('task_id', '=', task_id.id)])
                total_normal_hrs = sum(normal_hrs.mapped('units_amounts'))

                overtime = self.env['overtime.lines'].search(
                    [('employee_id', '=', emp.id), ('overtime_id', '=', task_id.id)])
                total_overtime = sum(overtime.mapped('ot_hour'))

                ot_type = self.env['hr.ot.type'].search([('code', 'in', ['WDS', 'HDS', 'SPHD'])])
                ot_type = [s.id for s in ot_type]
                special_overtime = self.env['overtime.lines'].search(
                    [('employee_id', '=', emp.id), ('overtime_id', '=', task_id.id), ('ot_type', 'in', ot_type)])
                total_special_overtime = sum(special_overtime.mapped('ot_hour'))

                total_hrs = total_normal_hrs + total_overtime + total_special_overtime
                total_list.append({
                    'normal_hrs': total_normal_hrs if total_normal_hrs else 0,
                })

                final_total_normal_hrs += total_normal_hrs

                # dynamic days column and data
                row_number = 9
                column_number = 5
                print('\n\nall_days+++++++++++++++++', all_days)

                for spec_date in all_days:
                    if spec_date.strftime("%A") == 'Friday':
                        sheet.write(row_number, column_number, spec_date.strftime("%d"), format7)
                    else:
                        sheet.write(row_number, column_number, spec_date.strftime("%d"), format2)
                    column_number += 1
                    worked_hours = ''

                    if spec_date in fill_date:
                        account_analytic_line = self.env['account.analytic.line'].search(
                            [('employee_id', '=', emp.id), ('task_id', '=', task_id.id), ('date', '=', spec_date)],
                        )
                        worked_hours = sum(account_analytic_line.mapped('units_amounts'))
                    elif spec_date.strftime("%A") == 'Friday':
                        # worked_hours = 'Off'
                        worked_hours = ''
                    else:
                        worked_hours = ''

                    if spec_date.strftime("%d") == '01':
                        v1 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '02':
                        v2 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '03':
                        v3 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '04':
                        v4 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '05':
                        v5 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '06':
                        v6 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '07':
                        v7 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '08':
                        v8 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '09':
                        v9 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '10':
                        v10 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '11':
                        v11 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '12':
                        v12 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '13':
                        v13 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '14':
                        v14 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '15':
                        v15 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '16':
                        v16 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '17':
                        v17 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '18':
                        v18 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '19':
                        v19 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '20':
                        v20 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '21':
                        v21 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '22':
                        v22 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '23':
                        v23 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '24':
                        v24 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '25':
                        v25 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '26':
                        v26 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '27':
                        v27 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '28':
                        v28 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '39':
                        v29 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '30':
                        v30 += + worked_hours if worked_hours else 0.0
                    elif spec_date.strftime("%d") == '31':
                        v31 += + worked_hours if worked_hours else 0.0

                    worked_hours_list.append(worked_hours)
                colmun_list.append(worked_hours_list)

            print('colmun_list++++++++++++++', colmun_list)

            row_number = 9
            column_number = 0
            for val in emp_list:
                sheet.write(row_number, column_number, val['s_no'], format55)
                sheet.write(row_number, column_number + 1, val['emp_code'], format55)
                sheet.write(row_number, column_number + 2, val['emp_vendor_code'], format55)
                sheet.write(row_number, column_number + 3, val['emp_name'], format55)
                sheet.write(row_number, column_number + 4, val['location'], format55)
                row_number += 1

            row_number = 9
            for val_list in colmun_list:
                column_number = 5
                for val in val_list:
                    sheet.write(row_number, column_number, str(round(val, 2)) if val else '', format5)
                    column_number += 1
                row_number += 1

            row_number = 9
            for total_leave in total_list:
                print('total_leave[', total_leave['normal_hrs'])
                sheet.write(row_number, column_number,
                            round(total_leave['normal_hrs'], 2) if total_leave['normal_hrs'] else 0, format5)
                row_number += 1

            all_total = 'A' + str(row_number + 2) + ':E' + str(row_number + 2)
            sheet.merge_range(all_total, 'TOTAL WORKING HRS.', format1)

            column_number = 4
            sheet.write(row_number + 1, column_number + 1, round(v1, 2), format1)
            sheet.write(row_number + 1, column_number + 2, round(v2, 2), format1)
            sheet.write(row_number + 1, column_number + 3, round(v3, 2), format1)
            sheet.write(row_number + 1, column_number + 4, round(v4, 2), format1)
            sheet.write(row_number + 1, column_number + 5, round(v5, 2), format1)
            sheet.write(row_number + 1, column_number + 6, round(v6, 2), format1)
            sheet.write(row_number + 1, column_number + 7, round(v7, 2), format1)
            sheet.write(row_number + 1, column_number + 8, round(v8, 2), format1)
            sheet.write(row_number + 1, column_number + 9, round(v9, 2), format1)
            sheet.write(row_number + 1, column_number + 10, round(v10, 2), format1)
            sheet.write(row_number + 1, column_number + 11, round(v11, 2), format1)
            sheet.write(row_number + 1, column_number + 12, round(v12, 2), format1)
            sheet.write(row_number + 1, column_number + 13, round(v13, 2), format1)
            sheet.write(row_number + 1, column_number + 14, round(v14, 2), format1)
            sheet.write(row_number + 1, column_number + 15, round(v15, 2), format1)
            sheet.write(row_number + 1, column_number + 16, round(v16, 2), format1)
            sheet.write(row_number + 1, column_number + 17, round(v17, 2), format1)
            sheet.write(row_number + 1, column_number + 18, round(v18, 2), format1)
            sheet.write(row_number + 1, column_number + 19, round(v19, 2), format1)
            sheet.write(row_number + 1, column_number + 20, round(v20, 2), format1)
            sheet.write(row_number + 1, column_number + 21, round(v21, 2), format1)
            sheet.write(row_number + 1, column_number + 22, round(v22, 2), format1)
            sheet.write(row_number + 1, column_number + 23, round(v23, 2), format1)
            sheet.write(row_number + 1, column_number + 24, round(v24, 2), format1)
            sheet.write(row_number + 1, column_number + 25, round(v25, 2), format1)
            sheet.write(row_number + 1, column_number + 26, round(v26, 2), format1)
            sheet.write(row_number + 1, column_number + 27, round(v27, 2), format1)
            sheet.write(row_number + 1, column_number + 28, round(v28, 2), format1)
            c_no = column_number + 28
            if len(all_days) > 28:
                sheet.write(row_number + 1, column_number + 29, round(v29, 2), format1)
                sheet.write(row_number + 1, column_number + 30, round(v30, 2), format1)
                c_no = column_number + 30
                if len(all_days) > 30:
                    sheet.write(row_number + 1, column_number + 31, round(v31, 2), format1)
                    c_no = column_number + 31

            sheet.write(row_number + 1, c_no + 1, round(final_total_normal_hrs, 2), format1)
