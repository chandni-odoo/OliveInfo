from odoo import models
from datetime import datetime


class BillingPayrollComparisonXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.billing_payroll_comparison_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Billing Payroll Comparison Excel Report'


    def generate_xlsx_report(self, workbook, data, wizard):
        # Generate Worksheet 1: Your original report (exact same logic)
        self._generate_worksheet1(workbook, wizard)
        
        # Generate Worksheet 2: Account Wise Report
        self._generate_worksheet2(workbook, wizard)


    def _generate_worksheet1(self, workbook, wizard):
        sheet = workbook.add_worksheet("Billing Payroll Comparison")

        # Define formats
        header_fmt = workbook.add_format({'bold': True, 'align': 'left', 'bg_color': '#D9E1F2', 'border': 1})
        text_fmt = workbook.add_format({'border': 1})
        num_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        left = workbook.add_format({'align': 'left'})
        right_amount = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})

        # Write headers
        headers = [
            'Employee ID', 'Employee Name', 'Branch',
            'Payroll Batch', 'Billing Amount', 'Payroll Amount', 'Difference'
        ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_fmt)

        # Filters
        branch_ids = wizard.branch_ids.ids
        date_from = wizard.date_from
        date_to = wizard.date_to

        row = 1

        # Get employees who are tagged in invoices within the date range
        invoice_domain = [
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.invoice_date', '>=', date_from),
            ('move_id.invoice_date', '<=', date_to),
            ('employee_id', '!=', False)
        ]
        
        if branch_ids:
            invoice_domain.append(('move_id.branch_id', 'in', branch_ids))

        # Get invoice lines with employees
        invoice_lines = self.env['account.move.line'].search(invoice_domain)
        
        # Get unique employees from invoice lines
        employee_ids = invoice_lines.mapped('employee_id')
        
        for emp in employee_ids:
            # ---- BILLING AMOUNT for this specific employee ----
            emp_invoice_lines = invoice_lines.filtered(lambda l: l.employee_id.id == emp.id)
            
            billing_amount = sum(emp_invoice_lines.mapped('price_subtotal'))

            # Get branch information
            branch = ''
            if emp_invoice_lines:
                # Get unique branches from invoices related to that employee
                branches = emp_invoice_lines.mapped('move_id.branch_id')
                branch_list = []
                for br in branches:
                    branch_code = br.code or ''
                    branch_name = br.name or ''
                    if branch_code and branch_name:
                        branch_list.append(f"{branch_code} - {branch_name}")
                    else:
                        branch_list.append(branch_code or branch_name)
                branch = ', '.join(branch_list)

            # ---- PAYROLL DETAILS for the same employee ----
            payslip_domain = [
                ('employee_id', '=', emp.id),
                ('date_from', '>=', date_from),
                ('date_to', '<=', date_to),
                ('state', '=', 'done')
            ]
            
            payslips = self.env['hr.payslip'].search(payslip_domain)
            
            payroll_batch = ', '.join(payslips.mapped('payslip_run_id.name')) or ''

            # Get total net salary from payslip lines where code == 'NET'
            payroll_amount = 0.0
            for slip in payslips:
                net_line = slip.line_ids.filtered(lambda l: l.code == 'NET')
                payroll_amount += sum(net_line.mapped('total'))

            difference = billing_amount - payroll_amount

            # Write data row (we include all employees from invoices, even if they have no payroll)
            sheet.write(row, 0, emp.emp_no or '', left)
            sheet.write(row, 1, emp.name or '', left)
            sheet.write(row, 2, branch, left)
            sheet.write(row, 3, payroll_batch, left)
            sheet.write_number(row, 4, billing_amount, right_amount)
            sheet.write_number(row, 5, payroll_amount, right_amount)
            sheet.write_number(row, 6, difference, right_amount)
            row += 1

    def _generate_worksheet2(self, workbook, wizard):
        """Account Wise Report as Worksheet 2"""
        sheet = workbook.add_worksheet("Account Wise Report")

        # Define formats for Worksheet 2
        header_fmt = workbook.add_format({'bold': True, 'align': 'left', 'bg_color': '#E2EFDA', 'border': 1})
        text_fmt = workbook.add_format({'border': 1})
        num_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        left = workbook.add_format({'align': 'left'})
        right_amount = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})
        account_fmt = workbook.add_format({'align': 'left'})

        # Write headers for Worksheet 2
        headers = [
            'Employee ID', 'Employee Name', 'Branch', 'Payroll Batch',
            'Billing Account', 'Billing Amount', 'Payroll Account', 'Payroll Amount', 'Difference'
        ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_fmt)

        # Filters
        branch_ids = wizard.branch_ids.ids
        date_from = wizard.date_from
        date_to = wizard.date_to

        row = 1

        # Find the specific accounts
        billing_account = self.env['account.account'].search([
            ('code', '=', '5025.01')
        ], limit=1)
        
        payroll_account = self.env['account.account'].search([
            ('code', '=', '7010')
        ], limit=1)

        # Get employees from invoices with specific billing account (5025.01)
        invoice_domain = [
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.invoice_date', '>=', date_from),
            ('move_id.invoice_date', '<=', date_to),
            ('account_id', '=', billing_account.id) if billing_account else ('account_id.code', '=', '5025.01'),
            ('employee_id', '!=', False)
        ]
        
        if branch_ids:
            invoice_domain.append(('move_id.branch_id', 'in', branch_ids))

        # Get invoice lines with billing account 5025.01
        invoice_lines = self.env['account.move.line'].search(invoice_domain)
        
        # Get unique employees from invoice lines
        employee_ids = invoice_lines.mapped('employee_id')

        for emp in employee_ids:
            # ---- BILLING AMOUNT for specific account 5025.01 ----
            emp_invoice_lines = invoice_lines.filtered(
                lambda l: l.employee_id.id == emp.id
            )
            
            # Calculate billing amount for account 5025.01 only
            billing_amount = 0.0
            for line in emp_invoice_lines:
                if line.account_id.code == '5025.01':
                    billing_amount += line.price_subtotal

            if billing_amount == 0:
                continue  # Skip employees with no billing in this account

            # Get branch information
            branch = ''
            if emp_invoice_lines:
                branches = emp_invoice_lines.mapped('move_id.branch_id')
                branch_list = []
                for br in branches:
                    branch_code = br.code or ''
                    branch_name = br.name or ''
                    if branch_code and branch_name:
                        branch_list.append(f"{branch_code} - {branch_name}")
                    else:
                        branch_list.append(branch_code or branch_name)
                branch = ', '.join(branch_list)

            # ---- PAYROLL DETAILS for specific account 7010 ----
            payslip_domain = [
                ('employee_id', '=', emp.id),
                ('date_from', '>=', date_from),
                ('date_to', '<=', date_to),
                ('state', '=', 'done')
            ]
            
            payslips = self.env['hr.payslip'].search(payslip_domain)
            
            payroll_batch = ', '.join(payslips.mapped('payslip_run_id.name')) or ''
            
            payroll_amount = 0.0
            TARGET_CODE = '7010'
            SKIP_CODES = ['GROSS', 'NET']

            for slip in payslips:
                for line in slip.line_ids:

                    if abs(line.total) < 0.01:
                        continue

                    if line.code and line.code.upper() in SKIP_CODES:
                        continue

                    account = False

                    # 1️⃣ Salary rule debit account (highest priority)
                    if line.salary_rule_id and line.salary_rule_id.account_debit:
                        account = line.salary_rule_id.account_debit

                    # 2️⃣ Line reporting account
                    elif hasattr(line, 'reporting_account_id') and line.reporting_account_id:
                        account = line.reporting_account_id

                    # 3️⃣ Structure account ONLY if line has no account
                    elif slip.struct_id and slip.struct_id.reporting_account_id:
                        account = slip.struct_id.reporting_account_id

                    # ✅ FINAL CHECK — match ONLY 7010
                    if account and account.code == TARGET_CODE:
                        payroll_amount += line.total

            difference = billing_amount - payroll_amount

            # Write data row for Worksheet 2
            sheet.write(row, 0, emp.emp_no or '', left)
            sheet.write(row, 1, emp.name or '', left)
            sheet.write(row, 2, branch, left)
            sheet.write(row, 3, payroll_batch, left)
            
            # Billing Account info
            billing_account_name = f"{billing_account.code} - {billing_account.name}" if billing_account else "5025.01"
            sheet.write(row, 4, billing_account_name, account_fmt)
            sheet.write_number(row, 5, billing_amount, right_amount)
            
            # Payroll Account info
            payroll_account_name = f"{payroll_account.code} - {payroll_account.name}" if payroll_account else "7010"
            sheet.write(row, 6, payroll_account_name, account_fmt)
            sheet.write_number(row, 7, payroll_amount, right_amount)
            sheet.write_number(row, 8, difference, right_amount)
            row += 1

    