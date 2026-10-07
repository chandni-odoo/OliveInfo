from datetime import datetime
from odoo import models

class CostPlusReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.cost_plus_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizard):

        # -----------------------------
        # FORMATS
        # -----------------------------
        bold_grey = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#D3D3D3',
            'border': 1,
        })

        left = workbook.add_format({
            'align': 'left',
            'border': 1,
        })

        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#002060',
            'font_color': 'white',
            'border': 1,
        })

        header_format_red = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#FF0000',
            'font_color': 'white',
            'border': 1,
        })

        text_format = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'vcenter'
        })

        number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'num_format': '#,##0.00',
            'valign': 'vcenter'
        })

        date_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'num_format': 'dd/mm/yyyy',
            'valign': 'vcenter'
        })

        boolean_format = workbook.add_format({
            'border': 1,
            'align': 'center'
        })

        # ---------------------------------
        # SHEET
        # ---------------------------------

        sheet = workbook.add_worksheet('Cost Plus Report')

        sheet.set_column('A:A', 18)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:E', 12)
        sheet.set_column('F:F', 12)
        sheet.set_column('G:G', 25)
        sheet.set_column('H:H', 20)
        sheet.set_column('I:I', 25)
        sheet.set_column('J:M', 15)

        # ---------------------------------
        # REPORT TITLE
        # ---------------------------------

        sheet.merge_range(0, 0, 0, 12, 'COST PLUS REPORT', bold_grey)

        # ---------------------------------
        # FILTERS
        # ---------------------------------

        sheet.write(1, 0, 'From', bold_grey)
        sheet.write(1, 1, str(wizard.date_from), left)

        sheet.write(2, 0, 'To', bold_grey)
        sheet.write(2, 1, str(wizard.date_to), left)

        sheet.write(3, 0, 'Created By', bold_grey)
        sheet.write(
            3,
            1,
            wizard.user_id.name if wizard.user_id else 'All',
            left
        )

        sheet.write(4, 0, 'Employee', bold_grey)
        sheet.write(
            4,
            1,
            wizard.employee_id.name if wizard.employee_id else 'All',
            left
        )

        # ---------------------------------
        # HEADERS
        # ---------------------------------

        headers = [
            'CP Number',
            'Date',
            'Products / Services',
            'Employee',
            'Amount',
            'UOM',
            'Customer Name',
            'Sale Order',
            'Task',
            'Billing',
            'Payroll',
            'Billing Status',
            'Payroll Status'
        ]

        row = 6

        for col, head in enumerate(headers):
            sheet.write(row, col, head, header_format)

        row += 1

        # ---------------------------------
        # DOMAIN
        # ---------------------------------

        domain = [
            ('cost_plus_line_date', '>=', wizard.date_from),
            ('cost_plus_line_date', '<=', wizard.date_to),
        ]

        if wizard.user_id:
            domain.append(
                ('cost_plus_id.create_uid', '=', wizard.user_id.id)
            )

        if wizard.employee_id:
            domain.append(
                ('employee_id', '=', wizard.employee_id.id)
            )

        records = self.env['cost.plus.line'].search(domain)

        # ---------------------------------
        # DATA
        # ---------------------------------

        for rec in records:

            sheet.write(row, 0, rec.cost_plus_id.name or '', text_format)

            if rec.cost_plus_line_date:
                sheet.write_datetime(
                    row,
                    1,
                    datetime.combine(
                        rec.cost_plus_line_date,
                        datetime.min.time()
                    ),
                    date_format
                )
            else:
                sheet.write(row, 1, '', text_format)

            sheet.write(row, 2, rec.product_id.display_name or '', text_format)
            # sheet.write(row, 3, rec.employee_id.name or '', text_format)
            employee = ''
            if rec.employee_id:
                emp_no = rec.employee_id.emp_no or ''
                emp_name = rec.employee_id.name or ''
                employee = f'{emp_no} - {emp_name}' if emp_no else emp_name

            sheet.write(row, 3, employee, text_format)
            sheet.write_number(row, 4, rec.amount or 0, number_format)
            sheet.write(row, 5, rec.uom_id.name or '', text_format)
            sheet.write(row, 6, rec.partner_id.name or '', text_format)
            sheet.write(row, 7, rec.sale_order_id.name or '', text_format)
            sheet.write(row, 8, rec.task_id.name or '', text_format)
            sheet.write(row, 9, 'Yes' if rec.billing else 'No', boolean_format)
            sheet.write(row, 10, 'Yes' if rec.payroll else 'No', boolean_format)
            sheet.write(row, 11, 'Yes' if rec.billing_status else 'No', boolean_format)
            sheet.write(row, 12, 'Yes' if rec.payroll_status else 'No', boolean_format)

            row += 1