# -*- coding: utf-8 -*-
from odoo import models
from datetime import date, datetime, timedelta
from pytz import timezone, UTC
import pytz

from openpyxl import Workbook
from io import BytesIO


class ProductXlsx(models.AbstractModel):
    _name = 'report.pways_salary_bank_file.bank_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_deduction(self, slip):
        deduction = 0
        slip_ids = slip.line_ids.filtered(lambda x: x.category_id.code == 'DED' and x.total != 0)
        deduction = sum(slip_ids.mapped('total'))
        return deduction

    def get_overtime(self, slip):
        overtime = 0.0
        date_from = slip.date_from
        date_to = slip.date_to
        overtime_ids = self.env['bt.hr.overtime'].search([
            ('state', '=', 'validate'),
            ('start_date', '>=', date_from),
            ('start_date', '<=', date_to),
            ('employee_id', '=', slip.employee_id.id),
            ('ot_type_id.code', 'in', ('NOD', 'RAMD')),
        ])
        if overtime_ids:
            overtime = round(sum(overtime_ids.mapped('overtime_hours')), 2)
        return overtime

    def get_special_overtime(self, slip):
        special_ot = 0.0
        date_from = slip.date_from
        date_to = slip.date_to
        overtime_ids = self.env['bt.hr.overtime'].search([
            ('state', '=', 'validate'),
            ('start_date', '>=', date_from),
            ('start_date', '<=', date_to),
            ('employee_id', '=', slip.employee_id.id),
            ('ot_type_id.code', 'not in', ('NOD', 'RAMD')),
        ])
        if overtime_ids:
            special_ot = round(sum(overtime_ids.mapped('overtime_hours')), 2)
        return special_ot

    def _employee_account(self, slip):
        account_number = ""
        employee_id = slip.employee_id
        iban_no = employee_id.bank_ids.mapped('iban_no')
        if iban_no:
            account_number = iban_no[0]
        return account_number

    def employee_bank_short_name(self, slip):
        employee_bank_short_name = "NA"
        employee_id = slip.employee_id
        bank_id = employee_id.bank_ids.mapped('bank_id')
        if bank_id:
            employee_bank_short_name = bank_id[0].bic or "NA"
        return employee_bank_short_name

    def get_extra_income(self, slip):
        extra_income = 0
        extra_income = sum(slip.input_line_ids.mapped('amount'))
        return extra_income

    def employee_qid(self, slip):
        employee_qid = 0
        document_ids = slip.employee_id.ducument_line_ids.filtered(lambda x: x.document_line_id.national_id)
        if document_ids:
            employee_qid = document_ids[0].document_number
        return employee_qid

    def employee_visa_id(self, slip):
        employee_visa_id = 0
        document_ids = slip.employee_id.ducument_line_ids.filtered(lambda x: x.document_line_id.visa_id)
        if document_ids:
            employee_visa_id = document_ids[0].document_number
        return employee_visa_id

    def get_net_salary(self, slip):
        net_salary = 0
        line_ids = slip.line_ids.filtered(lambda x: x.category_id.code == "NET")
        if line_ids:
            net_salary = sum(line_ids.mapped('total'))
        return net_salary

    def get_total_salary(self, e_values):
        total = 0
        for slip in e_values:
            total = total + self.get_net_salary(slip)
        return total

    # def to_zip_file(self, payslip_run, multiple_sheet, workbook):
    #     print('inside zip file')
    #     print('payslip_run+++++++++++++', payslip_run)
    #     print('multiple_sheet+++++++++++++', multiple_sheet)
    #     print('workbook+++++++++++++', workbook)
    #
    #     f_list = []
    #     for sheet in multiple_sheet:
    #         name_data = ('%s.pdf' % ("Surtex Packing List"), sheet)
    #         f_list.append(name_data)
    #
    #     payslip_run.payroll_batch_id.message_post(body='message_ept', attachments=f_list)
    #
    #     tab_id = []
    #     mail_id = self.env['mail.message'].search(
    #         [('model', '=', 'payroll.batch'), ('res_id', '=', payslip_run.payroll_batch_id.id)],
    #         order='date desc', limit=1)
    #     print('mail_id++++++++++++++++', mail_id)

    # point no 15
    def generate_xlsx_report(self, workbook, data, products):
        print('data.get++++++++++++', data.get('active_record'))
        print('data.workbook++++++++++++', workbook, type(workbook))
        print('data.++++++++++++', data)
        print('data.products++++++++++++', products)
        if data.get('active_record'):
            sq_no = 0
            active_id = data.get('active_record')
            vals = []
            bank_details = []
            payslip_run = self.env['hr.payslip.run'].browse(int(active_id))
            user = payslip_run.env['res.users'].browse(self.env.uid)
            slip_ids = self.env['hr.payslip.run'].browse(int(active_id)).slip_ids
            company = payslip_run.env.company
            if user.tz:
                tz = pytz.timezone(user.tz) or pytz.utc
                time = pytz.utc.localize(datetime.now()).astimezone(tz)
            else:
                time = datetime.now()
            employee_details = {}
            print('slip_ids++++++++++++', slip_ids)
            for slip in slip_ids.filtered(
                    lambda x: x.employee_id.mentor_id and x.employee_id.bank_ids and x.employee_id.bank_ids[
                        0].bank_id and not x.employee_id.bank_ids[0].bank_id.is_other):
                if (slip.employee_id.mentor_id,
                    slip.employee_id.bank_ids and slip.employee_id.bank_ids[0].bank_id) not in employee_details:
                    employee_details[slip.employee_id.mentor_id, slip.employee_id.bank_ids[0].bank_id] = slip
                else:
                    employee_details[slip.employee_id.mentor_id, slip.employee_id.bank_ids[0].bank_id] |= slip

            multiple_sheet = []
            for e_key, e_values in employee_details.items():

                sq_no += 1
                total_records = len(e_values)

                # total_salaries = sum(e_values.mapped('contract_id').mapped('net_amount'))
                # print('\n\ntotal_salaries++++++++++++++++++', total_salaries)
                total_salaries = self.get_total_salary(e_values)

                bank_details = []
                bank_details.append({
                    'employer_eid': e_key[0].vat,
                    'creation_date': time.strftime("%Y%m%d"),
                    'creation_time': time.strftime("%H%M"),
                    'payer_eid': e_key[0].vat,
                    'payer_qid': '',
                    'bank_name': company.bank_id.bic,
                    'payer_iban': company.bank_id.iban_no,
                    'salary_years': payslip_run.date_start.strftime("%Y%m"),
                    'total_salaries': total_salaries,
                    'total_records': total_records,
                })
                final_time = time + timedelta(minutes=sq_no)
                total_time = final_time.strftime("%H%M")
                sheet_name = "SIF_%s_%s_%s_%s" % (
                    e_key[0].vat, company.bank_id.bic, time.strftime("%Y%m%d"), total_time)
                sheet = workbook.add_worksheet(sheet_name)
                format1 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True, 'bg_color': '#D3D3D3'})
                format2 = workbook.add_format({'font_size': 10, 'bold': True, 'bg_color': '#D3D3D3'})
                format3 = workbook.add_format({'font_size': 10, 'align': 'left'})
                format4 = workbook.add_format({'font_size': 10, 'align': 'left'})
                format1.set_align('center')

                sheet.write('A1', "Employer EID", format2)
                sheet.write('B1', "File Creation Date", format2)
                sheet.write('C1', "File Creation Time", format2)
                sheet.write('D1', "Payer EID", format2)
                sheet.write('E1', "Payer QID", format2)
                sheet.write('F1', "Payer Bank Short Name", format2)
                sheet.write('G1', "Payer IBAN", format2)
                sheet.write('H1', "Salary Year and Month", format2)
                sheet.write('I1', "Total Salaries", format2)
                sheet.write('J1', "Total records", format2)

                row_number = 1
                column_number = 0
                for bank in bank_details:
                    sheet.write(row_number, column_number, bank['employer_eid'], format3)
                    sheet.write(row_number, column_number + 1, bank['creation_date'], format4)
                    sheet.write(row_number, column_number + 2, bank['creation_time'], format4)
                    sheet.write(row_number, column_number + 3, bank['payer_eid'], format3)
                    sheet.write(row_number, column_number + 4, bank['payer_qid'], format3)
                    sheet.write(row_number, column_number + 5, bank['bank_name'], format3)
                    sheet.write(row_number, column_number + 6, bank['payer_iban'], format3)
                    sheet.write(row_number, column_number + 7, bank['salary_years'], format4)
                    sheet.write(row_number, column_number + 8, bank['total_salaries'], format4)
                    sheet.write(row_number, column_number + 9, bank['total_records'], format4)
                    row_number += 1

                vals = []
                record_id = 0
                for slip in e_values:
                    account_number = self._employee_account(slip)
                    employee_bank_short_name = self.employee_bank_short_name(slip)
                    record_id += 1
                    overtime = self.get_overtime(slip)
                    special_ot = self.get_special_overtime(slip)
                    deduction = self._get_deduction(slip)

                    employee_qid = self.employee_qid(slip)
                    employee_visa_id = self.employee_visa_id(slip)
                    if employee_qid and employee_qid != 0:
                        emp_qid_visa_list = [employee_qid, '']
                    if employee_visa_id and employee_visa_id != 0:
                        emp_qid_visa_list = ['', employee_visa_id]

                    net_salary = self.get_net_salary(slip)
                    print('net_salary++++++++++++++++++++++', net_salary)
                    extra_income = net_salary - slip.contract_id.wage
                    pay_frequency = dict(slip.employee_id._fields['pay_frequency'].selection).get(
                        slip.employee_id.pay_frequency)
                    vals.append({
                        'record_id': record_id,
                        # 'employee_qid': employee_qid,
                        # 'employee_visa_id': employee_visa_id,
                        'employee_qid': emp_qid_visa_list[0],
                        'employee_visa_id': emp_qid_visa_list[1],
                        'employee_name': slip.employee_id.name,
                        'employee_bank_short_name': employee_bank_short_name,
                        'employee_account': account_number,
                        'salary_frequency': pay_frequency,
                        'number_of_working_days': slip.present_day,
                        'net_salary': net_salary,
                        'basic_salary': slip.contract_id.wage,
                        'extra_hours': 0,
                        'extra_income': extra_income if extra_income >= 0 else 0,
                        'deductions': abs(extra_income) if extra_income <= 0 else 0,
                        'payment_type': "Salary",
                        'notes': slip.date_from.strftime("%B"),
                    })
                sheet.write('A3', "Record ID", format2)
                sheet.write('B3', "Employee QID", format2)
                sheet.write('C3', "Employee Visa ID", format2)
                sheet.write('D3', "Employee Name", format2)
                sheet.write('E3', "Employee Bank Short Name", format2)
                sheet.write('F3', "Employee Account", format2)
                sheet.write('G3', "Salary Frequency", format2)
                sheet.write('H3', "Number of Working Days", format2)
                sheet.write('I3', "Net Salary", format2)
                sheet.write('J3', "Basic Salary", format2)
                sheet.write('K3', "Extra hours", format2)
                sheet.write('L3', "Extra Income", format2)
                sheet.write('M3', "Deductions", format2)
                sheet.write('N3', "Payment Type", format2)
                sheet.write('O3', "Notes / Comments ", format2)

                row_number = 3
                column_number = 0
                for val in vals:
                    sheet.write(row_number, column_number, val['record_id'], format4)
                    sheet.write(row_number, column_number + 1, val['employee_qid'], format3)
                    sheet.write(row_number, column_number + 2, val['employee_visa_id'], format4)
                    sheet.write(row_number, column_number + 3, val['employee_name'], format3)
                    sheet.write(row_number, column_number + 4, val['employee_bank_short_name'], format3)
                    sheet.write(row_number, column_number + 5, val['employee_account'], format4)
                    sheet.write(row_number, column_number + 6, val['salary_frequency'], format3)
                    sheet.write(row_number, column_number + 7, val['number_of_working_days'], format4)
                    sheet.write(row_number, column_number + 8, val['net_salary'], format4)
                    sheet.write(row_number, column_number + 9, val['basic_salary'], format4)
                    sheet.write(row_number, column_number + 10, val['extra_hours'], format4)
                    sheet.write(row_number, column_number + 11, val['extra_income'], format4)
                    sheet.write(row_number, column_number + 12, val['deductions'], format4)
                    sheet.write(row_number, column_number + 13, val['payment_type'], format3)
                    sheet.write(row_number, column_number + 14, val['notes'], format3)
                    row_number += 1

