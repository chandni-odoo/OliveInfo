from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict

import logging
import re
from io import BytesIO
from odoo import models

_logger = logging.getLogger(__name__)
import xlsxwriter
import base64

from openpyxl import Workbook
from openpyxl.styles import Font
# from io import BytesIO

from datetime import date, datetime, timedelta
from pytz import timezone, UTC
import pytz

import csv
import io
import base64
import csv
import io


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    def print_bank_report_xls(self):
        active_record = self
        data = {
            'active_record': active_record.id,
        }
        return self.env.ref('pways_salary_bank_file.bank_xlsx').report_action(self, data=data)

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

    # point no 15 (2) CSV
    def print_bank_report_xls_2(self):
        print('++++++++++++++++++++CSV++++++++++++++++++++')
        sq_no = 0
        active_id = self.id
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
        ahli_employee_details = {}
        employee_details_other_bank = {}
        check_vat_list = []

        for slip in slip_ids.filtered(
                lambda x: x.employee_id.mentor_id and x.employee_id.bank_ids and x.employee_id.bank_ids[
                    0].bank_id and not x.employee_id.company_id.bank_id.is_ahli_bank and not x.employee_id.bank_ids[
                    0].bank_id.is_other):
            if (slip.employee_id.mentor_id.vat,
                slip.employee_id.bank_ids and slip.employee_id.bank_ids[0].bank_id) not in employee_details:
                employee_details[slip.employee_id.mentor_id.vat, slip.employee_id.bank_ids[0].bank_id] = slip
            else:
                employee_details[slip.employee_id.mentor_id.vat, slip.employee_id.bank_ids[0].bank_id] |= slip

        print('\nemployee_details++++++++', employee_details)

        for slip in slip_ids.filtered(
                lambda x: x.employee_id.mentor_id and x.employee_id.company_id.bank_id and x.employee_id.company_id.bank_id.is_ahli_bank and not
                x.employee_id.bank_ids[0].bank_id.is_other):
            if slip.employee_id.mentor_id.vat not in ahli_employee_details:
                ahli_employee_details[slip.employee_id.mentor_id.vat] = slip
            else:
                ahli_employee_details[slip.employee_id.mentor_id.vat] |= slip

        print('\nahli_employee_details++++++++++++++', ahli_employee_details)

        for slip in slip_ids.filtered(
                lambda x: x.employee_id.mentor_id.vat and x.employee_id.bank_ids and x.employee_id.bank_ids[
                    0].bank_id and x.employee_id.bank_ids[0].bank_id.is_other):
            if slip.employee_id.mentor_id.vat not in employee_details_other_bank:
                employee_details_other_bank[slip.employee_id.mentor_id.vat] = slip
            else:
                employee_details_other_bank[slip.employee_id.mentor_id.vat] |= slip

        print('\nemployee_details_other_bank+++', employee_details_other_bank)

        multiple_sheet = []

        # FOR EMPLOYEES NOT HAVING OTHER BANK
        for e_key, e_values in employee_details.items():
            print('e_key+++++++++', e_key, e_key[0])

            company_ids = self.env.user.company_ids
            print('company_ids++++++++++', company_ids)

            for company in company_ids:

                csv_file = io.StringIO()  # Use io.BytesIO() if you need bytes
                csv_writer = csv.writer(csv_file, delimiter=',')

                # current_company = self.env.company
                # payer_eid = current_company.bank_id.payer_eid
                # payer_qid = current_company.bank_id.payer_qid
                # current_company = company
                payer_eid = company.bank_id.payer_eid
                payer_qid = company.bank_id.payer_qid

                sq_no += 1
                total_records = len(e_values)

                total_salaries = self.get_total_salary(e_values)

                file_creation_time = time.strftime("%H%M")
                final_time = time + timedelta(minutes=sq_no)
                total_time = final_time.strftime("%H%M")

                if isinstance(e_key, str):
                    eid = e_key
                else:
                    eid = e_key[0]

                bank_details = []
                bank_details.append({
                    # 'employer_eid': e_key[0].vat,
                    'employer_eid': eid,
                    'creation_date': time.strftime("%Y%m%d"),
                    'creation_time': total_time,
                    'payer_eid': payer_eid if payer_eid else '',
                    'payer_qid': payer_qid if payer_qid else '',
                    'bank_name': company.bank_id.bic,
                    'payer_iban': company.bank_id.iban_no,
                    'salary_years': payslip_run.date_start.strftime("%Y%m"),
                    'total_salaries': round(total_salaries, 2),
                    'total_records': total_records,
                })

                header_data = ['Employer EID', 'File Creation Date', 'File Creation Time', 'Payer EID', 'Payer QID',
                               'Payer Bank Short Name', 'Payer IBAN', 'Salary Year and Month', 'Total Salaries',
                               'Total records']
                csv_writer.writerow(header_data)

                for bank in bank_details:
                    header_value = [bank['employer_eid'], bank['creation_date'], bank['creation_time'],
                                    bank['payer_eid'],
                                    bank['payer_qid'],
                                    bank['bank_name'], bank['payer_iban'], bank['salary_years'], bank['total_salaries'],
                                    bank['total_records']]
                    csv_writer.writerow(header_value)

                header1_data = ['Record ID', 'Employee QID', 'Employee Visa ID', 'Employee Name',
                                'Employee Bank Short Name', 'Employee Account', 'Salary Frequency',
                                'Number of Working Days', 'Net Salary', 'Basic Salary', 'Extra hours', 'Extra Income',
                                'Deductions', 'Payment Type', 'Notes / Comments ']

                csv_writer.writerow(header1_data)

                vals = []
                # record_id = e_key[1].seq if e_key[1].is_seq else 0
                record_id = 0
                rec_flag = True
                print('e_values++++++++++++', e_values)
                for slip in e_values:
                    if company.id == slip.employee_id.company_id.id:
                        print('slp++++++++++++', slip)
                        if rec_flag:
                            record_id = slip.employee_id.company_id.bank_id.seq if slip.employee_id.company_id.bank_id.is_seq else 0
                        account_number = self._employee_account(slip)
                        employee_bank_short_name = self.employee_bank_short_name(slip)
                        record_id += 1
                        rec_flag = False
                        overtime = self.get_overtime(slip)
                        special_ot = self.get_special_overtime(slip)
                        deduction = self._get_deduction(slip)

                        employee_qid = self.employee_qid(slip)
                        employee_visa_id = self.employee_visa_id(slip)
                        emp_qid_visa_list = []
                        if employee_qid and employee_qid != 0:
                            emp_qid_visa_list = [employee_qid, '']
                        if employee_visa_id and employee_visa_id != 0 and len(emp_qid_visa_list) < 1:
                            emp_qid_visa_list = ['', employee_visa_id]

                        net_salary = self.get_net_salary(slip)
                        extra_income = net_salary - slip.contract_id.wage
                        pay_frequency = dict(slip.employee_id._fields['pay_frequency'].selection).get(
                            slip.employee_id.pay_frequency)

                        if pay_frequency == 'Monthly':
                            pay_frequency = 'M'
                        elif pay_frequency == 'Weekly':
                            pay_frequency = 'W'
                        elif pay_frequency == 'Daily':
                            pay_frequency = 'D'
                        elif pay_frequency == 'Hourly':
                            pay_frequency = 'H'

                        print('slip.employee_id++++++++++++++++', slip.employee_id.company_id.bank_id)
                        vals.append({
                            'record_id': record_id,
                            # 'employee_qid': employee_qid,
                            # 'employee_visa_id': employee_visa_id,
                            'employee_qid': emp_qid_visa_list[0] if len(emp_qid_visa_list) > 0 else '',
                            'employee_visa_id': emp_qid_visa_list[1] if len(emp_qid_visa_list) > 0 else '',
                            'employee_name': slip.employee_id.name,
                            'employee_bank_short_name': employee_bank_short_name,
                            # 'employee_bank_short_name': slip.employee_id.company_id.bank_id.bic,
                            'employee_account': account_number,
                            'salary_frequency': pay_frequency,
                            'number_of_working_days': int(slip.attendance_days),
                            'net_salary': round(net_salary, 2),
                            'basic_salary': slip.contract_id.wage,
                            'extra_hours': 0,
                            'extra_income': round(extra_income, 2) if extra_income >= 0 else 0,
                            'deductions': round(abs(extra_income) if extra_income <= 0 else 0, 2),
                            'payment_type': "Salary",
                            'notes': slip.date_from.strftime("%B"),
                        })
                    else:
                        print('\nnselslesleselselslselseleslle')

                for val in vals:
                    header1_value = [val['record_id'], val['employee_qid'], val['employee_visa_id'],
                                     val['employee_name'],
                                     val['employee_bank_short_name'], val['employee_account'], val['salary_frequency'],
                                     val['number_of_working_days'], val['net_salary'], val['basic_salary'],
                                     val['extra_hours'], val['extra_income'],
                                     val['deductions'], val['payment_type'], val['notes']]

                    csv_writer.writerow(header1_value)

                print('vals+++++++++++++++++++', vals)
                if len(vals) > 0:
                    byte_data = csv_file.getvalue().encode('utf-8')
                    sheet_name = "SIF_%s_%s_%s_%s" % (eid, company.bank_id.bic, time.strftime("%Y%m%d"), total_time)
                    name_data = ('%s.csv' % (sheet_name), byte_data)
                    multiple_sheet.append(name_data)

        # FOR EMPLOYEES NOT HAVING OTHER BANK AND HAVING AHLI BANK
        for e_key, e_values in ahli_employee_details.items():

            print('e_key+++++++++', e_key, e_key[0])

            company_ids = self.env.user.company_ids
            print('company_ids++++++++++', company_ids)

            # for company in company_ids:
            company = self.env['res.company'].search([('bank_id.is_ahli_bank', '=', True)], limit=1)

            csv_file = io.StringIO()  # Use io.BytesIO() if you need bytes
            csv_writer = csv.writer(csv_file, delimiter=',')

            # current_company = self.env.company
            # payer_eid = current_company.bank_id.payer_eid
            # payer_qid = current_company.bank_id.payer_qid
            # current_company = company
            payer_eid = company.bank_id.payer_eid
            payer_qid = company.bank_id.payer_qid

            sq_no += 1
            total_records = len(e_values)

            total_salaries = self.get_total_salary(e_values)

            file_creation_time = time.strftime("%H%M")
            final_time = time + timedelta(minutes=sq_no)
            total_time = final_time.strftime("%H%M")

            if isinstance(e_key, str):
                eid = e_key
            else:
                eid = e_key[0]

            bank_details = []
            bank_details.append({
                # 'employer_eid': e_key[0].vat,
                'employer_eid': eid,
                'creation_date': time.strftime("%Y%m%d"),
                'creation_time': total_time,
                'payer_eid': payer_eid if payer_eid else '',
                'payer_qid': payer_qid if payer_qid else '',
                'bank_name': company.bank_id.bic,
                'payer_iban': company.bank_id.iban_no,
                'salary_years': payslip_run.date_start.strftime("%Y%m"),
                'total_salaries': round(total_salaries, 2),
                'total_records': total_records,
            })

            header_data = ['Employer EID', 'File Creation Date', 'File Creation Time', 'Payer EID', 'Payer QID',
                           'Payer Bank Short Name', 'Payer IBAN', 'Salary Year and Month', 'Total Salaries',
                           'Total records']
            csv_writer.writerow(header_data)

            for bank in bank_details:
                header_value = [bank['employer_eid'], bank['creation_date'], bank['creation_time'],
                                bank['payer_eid'],
                                bank['payer_qid'],
                                bank['bank_name'], bank['payer_iban'], bank['salary_years'], bank['total_salaries'],
                                bank['total_records']]
                csv_writer.writerow(header_value)

            header1_data = ['Record ID', 'Employee QID', 'Employee Visa ID', 'Employee Name',
                            'Employee Bank Short Name', 'Employee Account', 'Salary Frequency',
                            'Number of Working Days', 'Net Salary', 'Basic Salary', 'Extra hours', 'Extra Income',
                            'Deductions', 'Payment Type', 'Notes / Comments ']

            csv_writer.writerow(header1_data)

            vals = []
            # record_id = e_key[1].seq if e_key[1].is_seq else 0
            record_id = 0
            rec_flag = True
            print('e_values++++++++++++', e_values)
            for slip in e_values:
                print('slp++++++++++++', slip)
                if rec_flag:
                    # record_id = slip.employee_id.company_id.bank_id.seq if slip.employee_id.company_id.bank_id.is_seq else 0
                    record_id = company.bank_id.seq if company.bank_id.is_seq else 0
                account_number = self._employee_account(slip)
                employee_bank_short_name = self.employee_bank_short_name(slip)
                record_id += 1
                rec_flag = False
                overtime = self.get_overtime(slip)
                special_ot = self.get_special_overtime(slip)
                deduction = self._get_deduction(slip)

                employee_qid = self.employee_qid(slip)
                employee_visa_id = self.employee_visa_id(slip)
                emp_qid_visa_list = []
                if employee_qid and employee_qid != 0:
                    emp_qid_visa_list = [employee_qid, '']
                if employee_visa_id and employee_visa_id != 0 and len(emp_qid_visa_list) < 1:
                    emp_qid_visa_list = ['', employee_visa_id]

                net_salary = self.get_net_salary(slip)
                extra_income = net_salary - slip.contract_id.wage
                pay_frequency = dict(slip.employee_id._fields['pay_frequency'].selection).get(
                    slip.employee_id.pay_frequency)

                if pay_frequency == 'Monthly':
                    pay_frequency = 'M'
                elif pay_frequency == 'Weekly':
                    pay_frequency = 'W'
                elif pay_frequency == 'Daily':
                    pay_frequency = 'D'
                elif pay_frequency == 'Hourly':
                    pay_frequency = 'H'

                print('slip.employee_id++++++++++++++++', slip.employee_id.company_id.bank_id)
                vals.append({
                    'record_id': record_id,
                    # 'employee_qid': employee_qid,
                    # 'employee_visa_id': employee_visa_id,
                    'employee_qid': emp_qid_visa_list[0] if len(emp_qid_visa_list) > 0 else '',
                    'employee_visa_id': emp_qid_visa_list[1] if len(emp_qid_visa_list) > 0 else '',
                    'employee_name': slip.employee_id.name,
                    'employee_bank_short_name': employee_bank_short_name,
                    # 'employee_bank_short_name': slip.employee_id.company_id.bank_id.bic,
                    'employee_account': account_number,
                    'salary_frequency': pay_frequency,
                    'number_of_working_days': int(slip.attendance_days),
                    'net_salary': round(net_salary, 2),
                    'basic_salary': slip.contract_id.wage,
                    'extra_hours': 0,
                    'extra_income': round(extra_income, 2) if extra_income >= 0 else 0,
                    'deductions': round(abs(extra_income) if extra_income <= 0 else 0, 2),
                    'payment_type': "Salary",
                    'notes': slip.date_from.strftime("%B"),
                })

            for val in vals:
                header1_value = [val['record_id'], val['employee_qid'], val['employee_visa_id'],
                                 val['employee_name'],
                                 val['employee_bank_short_name'], val['employee_account'], val['salary_frequency'],
                                 val['number_of_working_days'], val['net_salary'], val['basic_salary'],
                                 val['extra_hours'], val['extra_income'],
                                 val['deductions'], val['payment_type'], val['notes']]

                csv_writer.writerow(header1_value)

            print('vals+++++++++++++++++++', vals)
            if len(vals) > 0:
                byte_data = csv_file.getvalue().encode('utf-8')
                sheet_name = "SIF_%s_%s_%s_%s" % (eid, company.bank_id.bic, time.strftime("%Y%m%d"), total_time)
                name_data = ('%s.csv' % (sheet_name), byte_data)
                multiple_sheet.append(name_data)

        # FOR EMPLOYEES HAVING OTHER BANK
        if employee_details_other_bank:
            for e_key, e_values in employee_details_other_bank.items():

                company_ids = self.env.user.company_ids
                for company in company_ids:
                    csv_file = io.StringIO()  # Use io.BytesIO() if you need bytes
                    csv_writer = csv.writer(csv_file, delimiter=',')

                    # current_company = self.env.company
                    # payer_eid = current_company.bank_id.payer_eid
                    # payer_qid = current_company.bank_id.payer_qid
                    # current_company = company
                    payer_eid = company.bank_id.payer_eid
                    payer_qid = company.bank_id.payer_qid

                    sq_no += 1
                    total_records = len(e_values)

                    # total_salaries = sum(e_values.mapped('contract_id').mapped('net_amount'))
                    # print('\n\ntotal_salaries++++++++++++++++++', total_salaries)
                    total_salaries = self.get_total_salary(e_values)

                    final_time = time + timedelta(minutes=sq_no)
                    total_time = final_time.strftime("%H%M")

                    bank_details = []
                    bank_details.append({
                        'employer_eid': e_key,
                        'creation_date': time.strftime("%Y%m%d"),
                        'creation_time': total_time,
                        # 'payer_eid': e_key[0].vat,
                        'payer_eid': payer_eid if payer_eid else '',
                        'payer_qid': payer_qid if payer_qid else '',
                        'bank_name': company.bank_id.bic,
                        'payer_iban': company.bank_id.iban_no,
                        'salary_years': payslip_run.date_start.strftime("%Y%m"),
                        'total_salaries': round(total_salaries, 2),
                        'total_records': total_records,
                    })

                    header_data = ['Employer EID', 'File Creation Date', 'File Creation Time', 'Payer EID', 'Payer QID',
                                   'Payer Bank Short Name', 'Payer IBAN', 'Salary Year and Month', 'Total Salaries',
                                   'Total records']
                    csv_writer.writerow(header_data)

                    for bank in bank_details:
                        header_value = [bank['employer_eid'], bank['creation_date'], bank['creation_time'],
                                        bank['payer_eid'],
                                        bank['payer_qid'],
                                        bank['bank_name'], bank['payer_iban'], bank['salary_years'],
                                        bank['total_salaries'],
                                        bank['total_records']]
                        csv_writer.writerow(header_value)

                    header1_data = ['Record ID', 'Employee QID', 'Employee Visa ID', 'Employee Name',
                                    'Employee Bank Short Name', 'Employee Account', 'Salary Frequency',
                                    'Number of Working Days', 'Net Salary', 'Basic Salary', 'Extra hours',
                                    'Extra Income',
                                    'Deductions', 'Payment Type', 'Notes / Comments ']

                    csv_writer.writerow(header1_data)

                    rec_flag = False
                    record_id = 0
                    vals = []
                    # record_id = e_key[1].seq if e_key[1].is_seq else 0
                    print('e_values++++++++++++', e_values)

                    for slip in e_values:
                        if company.id == slip.employee_id.company_id.id:
                            if not rec_flag:
                                record_id = slip.employee_id.company_id.bank_id.seq if slip.employee_id.company_id.bank_id.is_seq else 0
                                print('record_id++++++++++++++', record_id)
                            account_number = self._employee_account(slip)
                            employee_bank_short_name = self.employee_bank_short_name(slip)
                            record_id += 1
                            rec_flag = True
                            overtime = self.get_overtime(slip)
                            special_ot = self.get_special_overtime(slip)
                            deduction = self._get_deduction(slip)

                            employee_qid = self.employee_qid(slip)
                            employee_visa_id = self.employee_visa_id(slip)
                            emp_qid_visa_list = []
                            if employee_qid and employee_qid != 0:
                                emp_qid_visa_list = [employee_qid, '']
                            if employee_visa_id and employee_visa_id != 0 and len(emp_qid_visa_list) < 0:
                                emp_qid_visa_list = ['', employee_visa_id]

                            net_salary = self.get_net_salary(slip)
                            extra_income = net_salary - slip.contract_id.wage
                            pay_frequency = dict(slip.employee_id._fields['pay_frequency'].selection).get(
                                slip.employee_id.pay_frequency)

                            if pay_frequency == 'Monthly':
                                pay_frequency = 'M'
                            elif pay_frequency == 'Weekly':
                                pay_frequency = 'W'
                            elif pay_frequency == 'Daily':
                                pay_frequency = 'D'
                            elif pay_frequency == 'Hourly':
                                pay_frequency = 'H'

                            vals.append({
                                'record_id': record_id,
                                # 'employee_qid': employee_qid,
                                # 'employee_visa_id': employee_visa_id,
                                'employee_qid': emp_qid_visa_list[0] if len(emp_qid_visa_list) > 0 else '',
                                'employee_visa_id': emp_qid_visa_list[1] if len(emp_qid_visa_list) > 0 else '',
                                'employee_name': slip.employee_id.name,
                                # 'employee_bank_short_name': slip.employee_id.company_id.bank_id.bic,
                                'employee_bank_short_name': employee_bank_short_name,
                                'employee_account': account_number,
                                'salary_frequency': pay_frequency,
                                'number_of_working_days': int(slip.attendance_days),
                                'net_salary': round(net_salary, 2),
                                'basic_salary': slip.contract_id.wage,
                                'extra_hours': 0,
                                'extra_income': round(extra_income, 2) if extra_income >= 0 else 0,
                                'deductions': round(abs(extra_income) if extra_income <= 0 else 0, 2),
                                'payment_type': "Salary",
                                'notes': slip.date_from.strftime("%B"),
                            })

                    for val in vals:
                        header1_value = [val['record_id'], val['employee_qid'], val['employee_visa_id'],
                                         val['employee_name'],
                                         val['employee_bank_short_name'], val['employee_account'],
                                         val['salary_frequency'],
                                         val['number_of_working_days'], val['net_salary'], val['basic_salary'],
                                         val['extra_hours'], val['extra_income'],
                                         val['deductions'], val['payment_type'], val['notes']]

                        csv_writer.writerow(header1_value)

                    if len(vals) > 0:
                        byte_data = csv_file.getvalue().encode('utf-8')
                        sheet_name = "SIF_%s_%s_%s_%s" % (
                            e_key, company.bank_id.bic, time.strftime("%Y%m%d"), total_time)
                        name_data = ('%s.csv' % (sheet_name), byte_data)
                        multiple_sheet.append(name_data)

        # after loop
        self.payroll_batch_id.message_post(body='message_ept', attachments=multiple_sheet)

        tab_id = []
        mail_id = self.env['mail.message'].search(
            [('model', '=', 'payroll.batch'), ('res_id', '=', self.payroll_batch_id.id)],
            order='date desc', limit=1)
        if mail_id:
            tab_id = mail_id.attachment_ids.ids

        url = '/web/binary/download_sheet?tab_id=%s' % tab_id
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    # point no 15 (2) XLSX
    def print_bank_report_xls_2_o(self):
        sq_no = 0
        active_id = self.id
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
        employee_details_other_bank = {}
        print('slip_ids++++++++++++', slip_ids)

        for slip in slip_ids.filtered(
                lambda x: x.employee_id.mentor_id and x.employee_id.bank_ids and x.employee_id.bank_ids[
                    0].bank_id and not x.employee_id.bank_ids[0].bank_id.is_other):
            if (slip.employee_id.mentor_id,
                slip.employee_id.bank_ids and slip.employee_id.bank_ids[0].bank_id) not in employee_details:
                employee_details[slip.employee_id.mentor_id, slip.employee_id.bank_ids[0].bank_id] = slip
            else:
                employee_details[slip.employee_id.mentor_id, slip.employee_id.bank_ids[0].bank_id] |= slip

        for slip in slip_ids.filtered(
                lambda x: x.employee_id.mentor_id and x.employee_id.bank_ids and x.employee_id.bank_ids[
                    0].bank_id and x.employee_id.bank_ids[0].bank_id.is_other):
            if (slip.employee_id.mentor_id,
                slip.employee_id.bank_ids and slip.employee_id.bank_ids[0].bank_id) not in employee_details_other_bank:
                employee_details_other_bank[slip.employee_id.mentor_id, slip.employee_id.bank_ids[0].bank_id] = slip
            else:
                employee_details_other_bank[slip.employee_id.mentor_id, slip.employee_id.bank_ids[0].bank_id] |= slip

        multiple_sheet = []

        # FOR EMPLOYEES NOT HAVING OTHER BANK
        for e_key, e_values in employee_details.items():

            current_company = self.env.company
            payer_eid = current_company.bank_id.payer_eid
            payer_qid = current_company.bank_id.payer_qid

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
                # 'payer_eid': e_key[0].vat,
                'payer_eid': payer_eid if payer_eid else '',
                'payer_qid': payer_qid if payer_qid else '',
                'bank_name': company.bank_id.bic,
                'payer_iban': company.bank_id.iban_no,
                'salary_years': payslip_run.date_start.strftime("%Y%m"),
                'total_salaries': total_salaries,
                'total_records': total_records,
            })
            final_time = time + timedelta(minutes=sq_no)
            total_time = final_time.strftime("%H%M")
            # sheet_name = "SIF_%s_%s_%s_%s" % (
            #     e_key[0].vat, company.bank_id.bic, time.strftime("%Y%m%d"), total_time)

            workbook = Workbook()
            worksheet = workbook.active

            worksheet['A1'] = 'Employer EID'
            worksheet['B1'] = 'File Creation Date'
            worksheet['C1'] = 'File Creation Time'
            worksheet['D1'] = 'Payer EID'
            worksheet['E1'] = 'Payer QID'
            worksheet['F1'] = 'Payer Bank Short Name'
            worksheet['G1'] = 'Payer IBAN'
            worksheet['H1'] = 'Salary Year and Month'
            worksheet['I1'] = 'Total Salaries'
            worksheet['J1'] = 'Total records'

            worksheet['A1'].font = Font(bold=True)
            worksheet['B1'].font = Font(bold=True)
            worksheet['C1'].font = Font(bold=True)
            worksheet['D1'].font = Font(bold=True)
            worksheet['E1'].font = Font(bold=True)
            worksheet['F1'].font = Font(bold=True)
            worksheet['G1'].font = Font(bold=True)
            worksheet['H1'].font = Font(bold=True)
            worksheet['I1'].font = Font(bold=True)
            worksheet['J1'].font = Font(bold=True)

            row_number = 2
            column_number = 0
            for bank in bank_details:
                worksheet['A' + str(row_number)] = bank['employer_eid']
                worksheet['B' + str(row_number)] = bank['creation_date']
                worksheet['C' + str(row_number)] = bank['creation_time']
                worksheet['D' + str(row_number)] = bank['payer_eid']
                worksheet['E' + str(row_number)] = bank['payer_qid']
                worksheet['F' + str(row_number)] = bank['bank_name']
                worksheet['G' + str(row_number)] = bank['payer_iban']
                worksheet['H' + str(row_number)] = bank['salary_years']
                worksheet['I' + str(row_number)] = bank['total_salaries']
                worksheet['J' + str(row_number)] = bank['total_records']
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
                extra_income = net_salary - slip.contract_id.wage
                pay_frequency = dict(slip.employee_id._fields['pay_frequency'].selection).get(
                    slip.employee_id.pay_frequency)
                print('pay_frequency+++++++++++++++++++', pay_frequency)

                if pay_frequency == 'Monthly':
                    pay_frequency = 'M'
                elif pay_frequency == 'Weekly':
                    pay_frequency = 'W'
                elif pay_frequency == 'Daily':
                    pay_frequency = 'D'
                elif pay_frequency == 'Hourly':
                    pay_frequency = 'H'

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

                worksheet['A3'] = 'Record ID'
                worksheet['B3'] = 'Employee QID'
                worksheet['C3'] = 'Employee Visa ID'
                worksheet['D3'] = 'Employee Name'
                worksheet['E3'] = 'Employee Bank Short Name'
                worksheet['F3'] = 'Employee Account'
                worksheet['G3'] = 'Salary Frequency'
                worksheet['H3'] = 'Number of Working Days'
                worksheet['I3'] = 'Net Salary'
                worksheet['J3'] = 'Basic Salary'
                worksheet['K3'] = 'Extra hours'
                worksheet['L3'] = 'Extra Income'
                worksheet['M3'] = 'Deductions'
                worksheet['N3'] = 'Payment Type'
                worksheet['O3'] = 'Notes / Comments '

                worksheet['A3'].font = Font(bold=True)
                worksheet['B3'].font = Font(bold=True)
                worksheet['C3'].font = Font(bold=True)
                worksheet['D3'].font = Font(bold=True)
                worksheet['E3'].font = Font(bold=True)
                worksheet['F3'].font = Font(bold=True)
                worksheet['G3'].font = Font(bold=True)
                worksheet['H3'].font = Font(bold=True)
                worksheet['I3'].font = Font(bold=True)
                worksheet['J3'].font = Font(bold=True)
                worksheet['K3'].font = Font(bold=True)
                worksheet['L3'].font = Font(bold=True)
                worksheet['M3'].font = Font(bold=True)
                worksheet['N3'].font = Font(bold=True)
                worksheet['O3'].font = Font(bold=True)

                row_number = 4
                column_number = 0
                for val in vals:
                    worksheet['A' + str(row_number)] = val['record_id']
                    worksheet['B' + str(row_number)] = val['employee_qid']
                    worksheet['C' + str(row_number)] = val['employee_visa_id']
                    worksheet['D' + str(row_number)] = val['employee_name']
                    worksheet['E' + str(row_number)] = val['employee_bank_short_name']
                    worksheet['F' + str(row_number)] = val['employee_account']
                    worksheet['G' + str(row_number)] = val['salary_frequency']
                    worksheet['H' + str(row_number)] = val['number_of_working_days']
                    worksheet['I' + str(row_number)] = val['net_salary']
                    worksheet['J' + str(row_number)] = val['basic_salary']
                    worksheet['K' + str(row_number)] = val['extra_hours']
                    worksheet['L' + str(row_number)] = val['extra_income']
                    worksheet['M' + str(row_number)] = val['deductions']
                    worksheet['N' + str(row_number)] = val['payment_type']
                    worksheet['O' + str(row_number)] = val['notes']
                    row_number += 1

            # Save the workbook to a BytesIO object
            bytes_io = BytesIO()
            workbook.save(bytes_io)
            bytes_data = bytes_io.getvalue()

            sheet_name = "SIF_%s_%s_%s_%s" % (e_key[0].vat, company.bank_id.bic, time.strftime("%Y%m%d"), total_time)
            name_data = ('%s.xlsx' % (sheet_name), bytes_data)
            multiple_sheet.append(name_data)

        print('employee_details_other_bank++++++++++++++++', employee_details_other_bank)
        # FOR EMPLOYEES HAVING OTHER BANK
        for e_key, e_values in employee_details_other_bank.items():

            current_company = self.env.company
            payer_eid = current_company.bank_id.payer_eid
            payer_qid = current_company.bank_id.payer_qid

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
                # 'payer_eid': e_key[0].vat,
                'payer_eid': payer_eid if payer_eid else '',
                'payer_qid': payer_qid if payer_qid else '',
                'bank_name': company.bank_id.bic,
                'payer_iban': company.bank_id.iban_no,
                'salary_years': payslip_run.date_start.strftime("%Y%m"),
                'total_salaries': total_salaries,
                'total_records': total_records,
            })
            final_time = time + timedelta(minutes=sq_no)
            total_time = final_time.strftime("%H%M")
            # sheet_name = "SIF_%s_%s_%s_%s" % (
            #     e_key[0].vat, company.bank_id.bic, time.strftime("%Y%m%d"), total_time)

            workbook = Workbook()
            worksheet = workbook.active

            worksheet['A1'] = 'Employer EID'
            worksheet['B1'] = 'File Creation Date'
            worksheet['C1'] = 'File Creation Time'
            worksheet['D1'] = 'Payer EID'
            worksheet['E1'] = 'Payer QID'
            worksheet['F1'] = 'Payer Bank Short Name'
            worksheet['G1'] = 'Payer IBAN'
            worksheet['H1'] = 'Salary Year and Month'
            worksheet['I1'] = 'Total Salaries'
            worksheet['J1'] = 'Total records'

            worksheet['A1'].font = Font(bold=True)
            worksheet['B1'].font = Font(bold=True)
            worksheet['C1'].font = Font(bold=True)
            worksheet['D1'].font = Font(bold=True)
            worksheet['E1'].font = Font(bold=True)
            worksheet['F1'].font = Font(bold=True)
            worksheet['G1'].font = Font(bold=True)
            worksheet['H1'].font = Font(bold=True)
            worksheet['I1'].font = Font(bold=True)
            worksheet['J1'].font = Font(bold=True)

            row_number = 2
            column_number = 0
            for bank in bank_details:
                worksheet['A' + str(row_number)] = bank['employer_eid']
                worksheet['B' + str(row_number)] = bank['creation_date']
                worksheet['C' + str(row_number)] = bank['creation_time']
                worksheet['D' + str(row_number)] = bank['payer_eid']
                worksheet['E' + str(row_number)] = bank['payer_qid']
                worksheet['F' + str(row_number)] = bank['bank_name']
                worksheet['G' + str(row_number)] = bank['payer_iban']
                worksheet['H' + str(row_number)] = bank['salary_years']
                worksheet['I' + str(row_number)] = bank['total_salaries']
                worksheet['J' + str(row_number)] = bank['total_records']
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
                extra_income = net_salary - slip.contract_id.wage
                pay_frequency = dict(slip.employee_id._fields['pay_frequency'].selection).get(
                    slip.employee_id.pay_frequency)
                print('pay_frequency+++++++++++++++++++', pay_frequency)

                if pay_frequency == 'Monthly':
                    pay_frequency = 'M'
                elif pay_frequency == 'Weekly':
                    pay_frequency = 'W'
                elif pay_frequency == 'Daily':
                    pay_frequency = 'D'
                elif pay_frequency == 'Hourly':
                    pay_frequency = 'H'

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

                worksheet['A3'] = 'Record ID'
                worksheet['B3'] = 'Employee QID'
                worksheet['C3'] = 'Employee Visa ID'
                worksheet['D3'] = 'Employee Name'
                worksheet['E3'] = 'Employee Bank Short Name'
                worksheet['F3'] = 'Employee Account'
                worksheet['G3'] = 'Salary Frequency'
                worksheet['H3'] = 'Number of Working Days'
                worksheet['I3'] = 'Net Salary'
                worksheet['J3'] = 'Basic Salary'
                worksheet['K3'] = 'Extra hours'
                worksheet['L3'] = 'Extra Income'
                worksheet['M3'] = 'Deductions'
                worksheet['N3'] = 'Payment Type'
                worksheet['O3'] = 'Notes / Comments '

                worksheet['A3'].font = Font(bold=True)
                worksheet['B3'].font = Font(bold=True)
                worksheet['C3'].font = Font(bold=True)
                worksheet['D3'].font = Font(bold=True)
                worksheet['E3'].font = Font(bold=True)
                worksheet['F3'].font = Font(bold=True)
                worksheet['G3'].font = Font(bold=True)
                worksheet['H3'].font = Font(bold=True)
                worksheet['I3'].font = Font(bold=True)
                worksheet['J3'].font = Font(bold=True)
                worksheet['K3'].font = Font(bold=True)
                worksheet['L3'].font = Font(bold=True)
                worksheet['M3'].font = Font(bold=True)
                worksheet['N3'].font = Font(bold=True)
                worksheet['O3'].font = Font(bold=True)

                row_number = 4
                column_number = 0
                for val in vals:
                    worksheet['A' + str(row_number)] = val['record_id']
                    worksheet['B' + str(row_number)] = val['employee_qid']
                    worksheet['C' + str(row_number)] = val['employee_visa_id']
                    worksheet['D' + str(row_number)] = val['employee_name']
                    worksheet['E' + str(row_number)] = val['employee_bank_short_name']
                    worksheet['F' + str(row_number)] = val['employee_account']
                    worksheet['G' + str(row_number)] = val['salary_frequency']
                    worksheet['H' + str(row_number)] = val['number_of_working_days']
                    worksheet['I' + str(row_number)] = val['net_salary']
                    worksheet['J' + str(row_number)] = val['basic_salary']
                    worksheet['K' + str(row_number)] = val['extra_hours']
                    worksheet['L' + str(row_number)] = val['extra_income']
                    worksheet['M' + str(row_number)] = val['deductions']
                    worksheet['N' + str(row_number)] = val['payment_type']
                    worksheet['O' + str(row_number)] = val['notes']
                    row_number += 1

            # Save the workbook to a BytesIO object
            bytes_io = BytesIO()
            workbook.save(bytes_io)
            bytes_data = bytes_io.getvalue()

            sheet_name = "SIF_%s_%s_%s_%s" % (e_key[0].vat, company.bank_id.bic, time.strftime("%Y%m%d"), total_time)
            name_data = ('%s.xlsx' % (sheet_name), bytes_data)
            multiple_sheet.append(name_data)

        self.payroll_batch_id.message_post(body='message_ept', attachments=multiple_sheet)

        tab_id = []
        mail_id = self.env['mail.message'].search(
            [('model', '=', 'payroll.batch'), ('res_id', '=', self.payroll_batch_id.id)],
            order='date desc', limit=1)
        print('mail_id++++++++++++++++', mail_id)
        if mail_id:
            tab_id = mail_id.attachment_ids.ids
        print('\n\ntab_id+++++++++++++', tab_id)

        url = '/web/binary/download_sheet?tab_id=%s' % tab_id
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    def print_bank_report_other_xls(self):
        active_record = self
        data = {
            'active_record': active_record.id,
        }
        return self.env.ref('pways_salary_bank_file.bank_other_xlsx').report_action(self, data=data)


class Bank(models.Model):
    _inherit = 'res.bank'

    is_other = fields.Boolean(string="Other", help="This is for wps branch file")
    payer_eid = fields.Char('Payer EID')
    payer_qid = fields.Char('Payer QID')
    is_seq = fields.Boolean(string="Is Sequence?", help='Check this if you required the sequence')
    seq = fields.Integer(string="Sequence", help='Enter the initial required sequence')
    is_ahli_bank = fields.Boolean('Is Ahli Bank')
