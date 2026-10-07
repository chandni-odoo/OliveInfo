from odoo import models
from collections import defaultdict
from datetime import datetime


class AcpReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.acp_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizard):

        bold_grey = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#D3D3D3'
        })

        left = workbook.add_format({'align': 'left'})

        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#002060',
            'font_color': 'white'
        })

        header_format_red = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#FF0000',
            'font_color': 'white'
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

        integer_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'num_format': '#,##0',
            'valign': 'vcenter'
        })

        date_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'num_format': 'dd/mm/yyyy',
            'valign': 'vcenter'
        })

        avg_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'num_format': '#,##0.00',
            'valign': 'vcenter'
        })

        alt_row_format = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'vcenter'
        })

        alt_number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'num_format': '#,##0.00',
            'valign': 'vcenter'
        })

        alt_integer_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'num_format': '#,##0',
            'valign': 'vcenter'
        })

        alt_date_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'num_format': 'dd/mm/yyyy',
            'valign': 'vcenter'
        })

        
        sheet3 = workbook.add_worksheet('ACP Branch Wise')
        sheet2 = workbook.add_worksheet('ACP Summary')
        sheet1 = workbook.add_worksheet('ACP Details')

        # -----------------------------
        # COLUMN WIDTHS
        # -----------------------------
        for i in range(11):
            sheet1.set_column(i, i, 18)
        for i in range(7):
            sheet2.set_column(i, i, 18)
        for i in range(4):
            sheet3.set_column(i, i, 18)

        # -----------------------------
        # HELPER: DATE CONVERSION
        # -----------------------------
        def convert_to_excel_date(date_obj):
            if not date_obj:
                return None
            if hasattr(date_obj, 'strftime'):
                return datetime.combine(date_obj, datetime.min.time())
            return datetime.strptime(str(date_obj), '%Y-%m-%d')

        
        def write_sheet_header(sheet, headline_text, num_cols):
            sheet.merge_range(0, 0, 0, num_cols - 1, headline_text, bold_grey)

            sheet.write(1, 0, 'From', bold_grey)
            sheet.write(1, 1, str(wizard.date_from), left)

            sheet.write(2, 0, 'To', bold_grey)
            sheet.write(2, 1, str(wizard.date_to), left)

            sheet.write(3, 0, 'Branches', bold_grey)
            sheet.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)

            sheet.write(4, 0, 'Customer', bold_grey)
            sheet.write(4, 1, ', '.join(wizard.customer_ids.mapped('name')) or 'All', left)

        write_sheet_header(sheet1, 'ACP DETAILED REPORT', 11)
        write_sheet_header(sheet2, 'ACP CUSTOMER SUMMARY REPORT', 7)
        write_sheet_header(sheet3, 'ACP BRANCH WISE REPORT', 4)

        
        headers1 = [
            'Customer Code', 'Customer Name', 'Payment Terms', 'Branch',
            'Invoice No', 'Invoice Amount', 'Invoice Date', 'Due Date',
            'Payment Date', 'Payment Status', 'Payment Days'
        ]
        for col, head in enumerate(headers1):
            fmt = header_format_red if col == len(headers1) - 1 else header_format
            sheet1.write(6, col, head, fmt)

        headers2 = [
            'Customer Code', 'Customer Name', 'Payment Terms', 'Branch',
            'Total Payment Collected (Days)', 'Total No of Payments', 'Average'
        ]
        for col, head in enumerate(headers2):
            fmt = header_format_red if col == len(headers2) - 1 else header_format
            sheet2.write(6, col, head, fmt)

        headers3 = ['Branch', 'Total Days', 'No of Payments', 'Average']
        for col, head in enumerate(headers3):
            fmt = header_format_red if col == len(headers3) - 1 else header_format
            sheet3.write(6, col, head, fmt)

        
        payment_domain = [
            ('date', '>=', wizard.date_from),
            ('date', '<=', wizard.date_to),
            ('state', '=', 'posted')
        ]
        payments = self.env['account.payment'].search(payment_domain)

        if not payments:
            return

       
        row = 7
        alt_row = False

        customer_summary = defaultdict(lambda: {
            'total_days': 0, 'count': 0,
            'name': '', 'code': '', 'terms': '', 'branch': ''
        })
        branch_summary = defaultdict(lambda: {'total_days': 0, 'count': 0})

        for payment in payments:
            receivable_lines = payment.move_id.line_ids.filtered(
                lambda l: l.account_id.internal_type == 'receivable'
            )
            for line in receivable_lines:
                partials = line.matched_debit_ids | line.matched_credit_ids
                for partial in partials:
                    counterpart_lines = partial.debit_move_id | partial.credit_move_id
                    for counterpart_line in counterpart_lines:
                        move = counterpart_line.move_id
                        if move.move_type != 'out_invoice':
                            continue
                        inv = move

                        if wizard.customer_ids and inv.partner_id not in wizard.customer_ids:
                            continue
                        if wizard.branch_ids and inv.branch_id not in wizard.branch_ids:
                            continue
                        if not inv.invoice_date or not payment.date:
                            continue

                        days = (payment.date - inv.invoice_date).days
                        invoice_date  = convert_to_excel_date(inv.invoice_date)
                        due_date      = convert_to_excel_date(inv.invoice_date_due)
                        payment_date  = convert_to_excel_date(payment.date)

                        tf  = alt_row_format     if alt_row else text_format
                        nf  = alt_number_format  if alt_row else number_format
                        inf = alt_integer_format if alt_row else integer_format
                        df  = alt_date_format    if alt_row else date_format

                        sheet1.write(row, 0, inv.partner_id.address_no or '', tf)
                        sheet1.write(row, 1, inv.partner_id.name, tf)
                        sheet1.write(row, 2, inv.partner_id.property_payment_term_id.name or '', tf)
                        sheet1.write(row, 3, inv.branch_id.name or '', tf)
                        sheet1.write(row, 4, inv.name, tf)
                        sheet1.write(row, 5, inv.amount_total, nf)
                        sheet1.write_datetime(row, 6, invoice_date, df)
                        sheet1.write_datetime(row, 7, due_date, df)
                        sheet1.write_datetime(row, 8, payment_date, df)
                        sheet1.write(row, 9, inv.payment_state, tf)
                        sheet1.write(row, 10, days, inf)

                        # Accumulate summaries
                        cust = inv.partner_id.id
                        customer_summary[cust]['total_days'] += days
                        customer_summary[cust]['count']      += 1
                        customer_summary[cust]['name']       = inv.partner_id.name
                        customer_summary[cust]['code']       = inv.partner_id.address_no or ''
                        customer_summary[cust]['terms']      = inv.partner_id.property_payment_term_id.name or ''
                        customer_summary[cust]['branch']     = inv.branch_id.name or ''

                        branch = inv.branch_id.name or 'No Branch'
                        branch_summary[branch]['total_days'] += days
                        branch_summary[branch]['count']      += 1

                        row     += 1
                        alt_row  = not alt_row

        # -----------------------------
        # SHEET 2 – CUSTOMER SUMMARY (data starts row 7)
        # -----------------------------
        row2    = 7
        alt_row = False
        for cust, val in customer_summary.items():
            avg = val['total_days'] / val['count'] if val['count'] else 0
            tf  = alt_row_format     if alt_row else text_format
            inf = alt_integer_format if alt_row else integer_format
            avf = alt_number_format  if alt_row else avg_format

            sheet2.write(row2, 0, val['code'],       tf)
            sheet2.write(row2, 1, val['name'],       tf)
            sheet2.write(row2, 2, val['terms'],      tf)
            sheet2.write(row2, 3, val['branch'],     tf)
            sheet2.write(row2, 4, val['total_days'], inf)
            sheet2.write(row2, 5, val['count'],      inf)
            sheet2.write(row2, 6, avg,               avf)

            row2    += 1
            alt_row  = not alt_row

        # -----------------------------
        # SHEET 3 – BRANCH SUMMARY (data starts row 7)
        # -----------------------------
        row3    = 7
        alt_row = False
        for branch, val in branch_summary.items():
            avg = val['total_days'] / val['count'] if val['count'] else 0
            tf  = alt_row_format     if alt_row else text_format
            inf = alt_integer_format if alt_row else integer_format
            avf = alt_number_format  if alt_row else avg_format

            sheet3.write(row3, 0, branch,            tf)
            sheet3.write(row3, 1, val['total_days'], inf)
            sheet3.write(row3, 2, val['count'],      inf)
            sheet3.write(row3, 3, avg,               avf)

            row3    += 1
            alt_row  = not alt_row