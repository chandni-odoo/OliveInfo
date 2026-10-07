from odoo import models, fields
from datetime import datetime
from odoo.tools import date_utils


class PayslipReport(models.AbstractModel):
    _name = 'report.hr_payroll_report.payslip_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Payroll Report'

    def generate_xlsx_report(self, workbook, data, lines):
        payslip_batch_id = data.get('payslip_batch_id')

        domain = [
            ('payslip_run_id', '=', payslip_batch_id)
        ]
        
        slips = self.env['hr.payslip'].search(domain, order='employee_id, date_from')

        sheet = workbook.add_worksheet('Employee Payroll Report')
        
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        
        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'top'
        })
        
        date_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'top',
            'num_format': 'yyyy-mm-dd'
        })
        
        number_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0.00',
            'align': 'right'
        })
        
        headers = [
            'Emp. No.', 'Name', 'Branch', 
            'Batch', 'Date To', 'Status',
            'Salary Component', 'Amount', 
            'Employee Group', 'Debit Account'
        ]
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            if col in [1, 2, 3, 6, 9]: 
                sheet.set_column(col, col, 25)
            elif col == 4: 
                sheet.set_column(col, col, 12)
            elif col == 5:  
                sheet.set_column(col, col, 15)
            else:
                sheet.set_column(col, col, 15)
        
        row = 1
        total_lines_processed = 0
        
        for slip in slips:
            emp = slip.employee_id  
            
            emp_no = emp.emp_no or '' 
            emp_name = emp.name or ''
            branch = ''
            if hasattr(emp, 'branch_id') and emp.branch_id:
                branch_code = emp.branch_id.code or ''
                branch_name = emp.branch_id.name or ''
                if branch_code and branch_name:
                    branch = f"{branch_code} - {branch_name}"
                else:
                    branch = branch_code or branch_name
            
            emp_group = ''
            if hasattr(emp, 'category_ids') and emp.category_ids:
                emp_group = ', '.join(emp.category_ids.mapped('name'))
            elif hasattr(emp, 'employee_group_id') and emp.employee_group_id:
                emp_group = emp.employee_group_id.name
            
            batch_name = slip.payslip_run_id.name if slip.payslip_run_id else ''
            
            for line in slip.line_ids:
                if abs(line.total) < 0.01:
                    continue
                
                skip_codes = ['GROSS', 'NET']
                if line.code and line.code.upper() in skip_codes:
                    continue

                reporting_account = ''
                salary_rule = line.salary_rule_id
                
                if salary_rule and salary_rule.account_debit:
                    reporting_account = f"{salary_rule.account_debit.code or ''} {salary_rule.account_debit.name or ''}".strip()
                elif hasattr(line, 'reporting_account_id') and line.reporting_account_id:
                    reporting_account = f"{line.reporting_account_id.code or ''} {line.reporting_account_id.name or ''}".strip()
                elif slip.struct_id and slip.struct_id.reporting_account_id:
                    reporting_account = f"{slip.struct_id.reporting_account_id.code or ''} {slip.struct_id.reporting_account_id.name or ''}".strip()

                sheet.write(row, 0, emp_no, data_format)
                sheet.write(row, 1, emp_name, data_format)
                sheet.write(row, 2, branch, data_format)
                sheet.write(row, 3, batch_name, data_format)
                sheet.write(row, 4, slip.date_to or '', date_format)
                sheet.write(row, 5, slip.state or '', data_format)
                sheet.write(row, 6, line.name or '', data_format)
                sheet.write(row, 7, line.total, number_format)
                sheet.write(row, 8, emp_group, data_format)
                sheet.write(row, 9, reporting_account, data_format)
                
                row += 1
                total_lines_processed += 1
        
        if total_lines_processed == 0:
            sheet.merge_range(1, 0, 1, 9, 
                'No data found for payroll batch. Please check your filters.', 
                data_format)

# class PayslipReport(models.AbstractModel):
#     _name = 'report.hr_payroll_report.payslip_report_xlsx'
#     _inherit = 'report.report_xlsx.abstract'
#     _description = 'Payroll Report'

#     def generate_xlsx_report(self, workbook, data, lines):
#         payslip_batch_id = data.get('payslip_batch_id')

#         domain = [
#             ('payslip_run_id', '=', payslip_batch_id)
#         ]
        
#         slips = self.env['hr.payslip'].search(domain, order='employee_id, date_from')

#         sheet = workbook.add_worksheet('Employee Payroll Report')
        
#         header_format = workbook.add_format({
#             'bold': True,
#             'align': 'center',
#             'valign': 'vcenter',
#             'bg_color': '#4472C4',
#             'font_color': 'white',
#             'border': 1
#         })
        
#         data_format = workbook.add_format({
#             'border': 1,
#             'align': 'left',
#             'valign': 'top'
#         })
        
#         date_format = workbook.add_format({
#             'border': 1,
#             'align': 'left',
#             'valign': 'top',
#             'num_format': 'yyyy-mm-dd'
#         })
        
#         number_format = workbook.add_format({
#             'border': 1,
#             'num_format': '#,##0.00',
#             'align': 'right'
#         })
        
#         headers = [
#             'Emp. No.', 'Name', 'Branch', 
#             'Batch', 'Date To', 'Status',
#             'Salary Component', 'Amount', 
#             'Employee Group', 'Debit Account'
#         ]
        
#         for col, header in enumerate(headers):
#             sheet.write(0, col, header, header_format)
#             if col in [1, 2, 3, 6, 9]: 
#                 sheet.set_column(col, col, 25)
#             elif col == 4: 
#                 sheet.set_column(col, col, 12)
#             elif col == 5:  
#                 sheet.set_column(col, col, 15)
#             else:
#                 sheet.set_column(col, col, 15)
        
#         row = 1
#         total_lines_processed = 0
        
#         for slip in slips:
#             emp = slip.employee_id  
            
#             emp_no = emp.emp_no or '' 
#             emp_name = emp.name or ''
#             branch = ''
#             if hasattr(emp, 'branch_id') and emp.branch_id:
#                 branch_code = emp.branch_id.code or ''
#                 branch_name = emp.branch_id.name or ''
#                 if branch_code and branch_name:
#                     branch = f"{branch_code} - {branch_name}"
#                 else:
#                     branch = branch_code or branch_name
            
#             emp_group = ''
#             if hasattr(emp, 'category_ids') and emp.category_ids:
#                 emp_group = ', '.join(emp.category_ids.mapped('name'))
#             elif hasattr(emp, 'employee_group_id') and emp.employee_group_id:
#                 emp_group = emp.employee_group_id.name
            
#             batch_name = slip.payslip_run_id.name if slip.payslip_run_id else ''
            
#             for line in slip.line_ids:
#                 if abs(line.total) < 0.01:
#                     continue
                
#                 skip_codes = ['GROSS', 'NET']
#                 if line.code and line.code.upper() in skip_codes:
#                     continue

#                 reporting_account = ''
#                 if slip.struct_id and slip.struct_id.reporting_account_id:
#                     reporting_account = f"{slip.struct_id.reporting_account_id.code} {slip.struct_id.reporting_account_id.name}"
#                 elif hasattr(line, 'reporting_account_id') and line.reporting_account_id:
#                     reporting_account = f"{line.reporting_account_id.code} {line.reporting_account_id.name}"
#                 elif line.salary_rule_id:
#                     rule = line.salary_rule_id
#                     if hasattr(rule, 'account_debit') and rule.account_debit:
#                         reporting_account = f"{rule.account_debit.code} {rule.account_debit.name}"
#                     elif hasattr(rule, 'account_credit') and rule.account_credit:
#                         reporting_account = f"{rule.account_credit.code} {rule.account_credit.name}"

#                 sheet.write(row, 0, emp_no, data_format)
#                 sheet.write(row, 1, emp_name, data_format)
#                 sheet.write(row, 2, branch, data_format)
#                 sheet.write(row, 3, batch_name, data_format)
#                 sheet.write(row, 4, slip.date_to or '', date_format)
#                 sheet.write(row, 5, slip.state or '', data_format)
#                 sheet.write(row, 6, line.name or '', data_format)
#                 sheet.write(row, 7, line.total, number_format)
#                 sheet.write(row, 8, emp_group, data_format)
#                 sheet.write(row, 9, reporting_account, data_format)
                
#                 row += 1
#                 total_lines_processed += 1
        
#         if total_lines_processed == 0:
#             sheet.merge_range(1, 0, 1, 9, 
#                 f'No data found for payroll batch. Please check your filters.', 
#                 data_format)

