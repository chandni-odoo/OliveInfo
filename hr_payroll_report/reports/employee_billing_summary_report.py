from odoo import models, fields, api


class EmployeeBillingSummaryReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.employee_billing_summary_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Employee Billing Summary Excel Report'

    def generate_xlsx_report(self, workbook, data, wizard):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        branch_ids = data.get('branch_ids', [])

        sheet = workbook.add_worksheet('Employee Billing Summary')
        bold = workbook.add_format({'bold': True, 'align': 'left'})
        center = workbook.add_format({'align': 'center'})
        left = workbook.add_format({'align': 'left'})
        right_amount = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})
        bold_right_amount = workbook.add_format({'bold': True, 'align': 'right', 'num_format': '#,##0.00'})

        # Header Section
        sheet.merge_range('A1:D1', 'Employee Billing Summary Report', bold)
        sheet.write('A3', 'Filter Date', bold)
        sheet.write('B3', f"{date_from} to {date_to}")
        sheet.write('A4', 'Branch', bold)
        branch_names = ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name'))
        sheet.write('B4', branch_names)

        # Table Headers
        headers = ['Employee ID', 'Employee Name', 'Branch', 'Total Billing Amount']
        row = 6
        col = 0
        for header in headers:
            sheet.write(row, col, header, bold)
            col += 1

        row += 1

        # Search invoice lines in the given date range
        domain = [
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.invoice_date', '>=', date_from),
            ('move_id.invoice_date', '<=', date_to)
        ]
        if branch_ids:
            domain += [('move_id.branch_id', 'in', branch_ids)]

        # if branch_ids:
        #     domain += [('employee_id.branch_id', 'in', branch_ids)]

        lines = self.env['account.move.line'].search(domain)

        # Group by Employee
        employee_summary = {}
        for line in lines:
            employee = line.employee_id
            if not employee:
                continue
            if employee.id not in employee_summary:
                employee_summary[employee.id] = {
                    'employee': employee,
                    'total': 0.0,
                }
            employee_summary[employee.id]['total'] += line.price_subtotal or 0.0

        # Write employee summary
        total_all = 0.0
        for emp_data in employee_summary.values():
            emp = emp_data['employee']
            total_amt = emp_data['total']

            # Combine branch code + name
            # branch = ''
            # if emp.branch_id:
            #     branch_code = emp.branch_id.code or ''
            #     branch_name = emp.branch_id.name or ''
            #     if branch_code and branch_name:
            #         branch = f"{branch_code} - {branch_name}"
            #     else:
            #         branch = branch_code or branch_name

            branch = ''
            if line.move_id.branch_id:
                branch_code = line.move_id.branch_id.code or ''
                branch_name = line.move_id.branch_id.name or ''
                if branch_code and branch_name:
                    branch = f"{branch_code} - {branch_name}"
                else:
                    branch = branch_code or branch_name

            sheet.write(row, 0, emp.emp_no or '', left)
            sheet.write(row, 1, emp.name or '', left)
            sheet.write(row, 2, branch, left)
            sheet.write(row, 3, total_amt, right_amount)

            total_all += total_amt
            row += 1

        # Grand total
        sheet.write(row, 2, 'Grand Total', bold)
        sheet.write(row, 3, total_all, bold_right_amount)