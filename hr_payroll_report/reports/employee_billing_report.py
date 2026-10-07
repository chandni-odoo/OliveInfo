from odoo import models, fields, api
from datetime import datetime


class EmployeeBillingReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.employee_billing_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Employee Billing Excel Report'

    def generate_xlsx_report(self, workbook, data, wizard):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        branch_ids = data.get('branch_ids', [])

        sheet = workbook.add_worksheet('Employee Billing Report')
        bold = workbook.add_format({'bold': True, 'align': 'left'})
        center = workbook.add_format({'align': 'center'})
        left = workbook.add_format({'align': 'left'})
        right_amount = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})

        sheet.merge_range('A1:I1', 'Employee Billing Report', bold)
        sheet.write('A3', 'Filter Date', bold)
        sheet.write('B3', f"{date_from} to {date_to}")
        sheet.write('A4', 'Branch', bold)
        branch_names = ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name'))
        sheet.write('B4', branch_names)

        headers = [
            'Employee ID', 'Employee Name', 'Account', 'Invoice Number',
            'Customer Name', 'Label', 'Branch', 'Amount'
        ]
        row = 6
        col = 0
        for header in headers:
            sheet.write(row, col, header, bold)
            col += 1

        row += 1

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

        for line in lines:
            employee = line.employee_id
            if not employee:
                continue

            label = "%s - %s - %s" % (
                line.product_id.name or '',
                employee.display_name or '',
                line.name or ''
            )

            # ✅ Fetch branch from invoice
            branch = ''
            if line.move_id.branch_id:
                branch_code = line.move_id.branch_id.code or ''
                branch_name = line.move_id.branch_id.name or ''
                if branch_code and branch_name:
                    branch = f"{branch_code} - {branch_name}"
                else:
                    branch = branch_code or branch_name

            # branch = ''
            # if employee.branch_id:
            #     branch_code = employee.branch_id.code or ''
            #     branch_name = employee.branch_id.name or ''
            #     if branch_code and branch_name:
            #         branch = f"{branch_code} - {branch_name}"
            #     else:
            #         branch = branch_code or branch_name
            
            sheet.write(row, 0, employee.emp_no or '', left)
            sheet.write(row, 1, employee.name or '', left)
            sheet.write(row, 2, line.account_id.display_name or '', left)
            sheet.write(row, 3, line.move_id.name or '', left)
            sheet.write(row, 4, line.move_id.partner_id.name or '', left)
            sheet.write(row, 5, label, left)
            sheet.write(row, 6, branch, left)
            sheet.write(row, 7, line.price_subtotal or 0.0, right_amount)
            row += 1