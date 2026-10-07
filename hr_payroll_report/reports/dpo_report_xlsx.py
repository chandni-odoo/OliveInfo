from odoo import models
from collections import defaultdict
from datetime import datetime
 
 
class DpoReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.dpo_report_xlsx'
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
 
        # -----------------------------
        # SHEETS
        # -----------------------------
        sheet3 = workbook.add_worksheet('DPO Branch Wise')
        sheet2 = workbook.add_worksheet('DPO Summary')
        sheet1 = workbook.add_worksheet('DPO Details')
 
        # -----------------------------
        # COLUMN WIDTHS
        # -----------------------------
        for i in range(12):          # 12 columns in detail sheet
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
 
        # -----------------------------
        # HELPER: SHEET HEADER
        # -----------------------------
        def write_sheet_header(sheet, headline_text, num_cols):
            sheet.merge_range(0, 0, 0, num_cols - 1, headline_text, bold_grey)
 
            sheet.write(1, 0, 'From', bold_grey)
            sheet.write(1, 1, str(wizard.date_from), left)
 
            sheet.write(2, 0, 'To', bold_grey)
            sheet.write(2, 1, str(wizard.date_to), left)
 
            sheet.write(3, 0, 'Branches', bold_grey)
            sheet.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)
 
            sheet.write(4, 0, 'Supplier', bold_grey)
            sheet.write(4, 1, ', '.join(wizard.supplier_ids.mapped('name')) or 'All', left)
 
        write_sheet_header(sheet1, 'DPO DETAILED REPORT', 12)
        write_sheet_header(sheet2, 'DPO SUPPLIER SUMMARY REPORT', 7)
        write_sheet_header(sheet3, 'DPO BRANCH WISE REPORT', 4)
 
        # -----------------------------
        # COLUMN HEADERS
        # -----------------------------
        headers1 = [
            'Supplier Code', 'Supplier Name', 'Supplier Payment Terms', 'Branch',
            'Bill No', 'Bill Amount', 'Bill Received Date', 'Bill Due Date',
            'Payment Date', 'Payment Release Date', 'Bill Payment Status', 'Payment Made Days'
        ]
        for col, head in enumerate(headers1):
            fmt = header_format_red if col == len(headers1) - 1 else header_format
            sheet1.write(6, col, head, fmt)
 
        headers2 = [
            'Supplier Code', 'Supplier Name', 'Supplier Payment Terms', 'Branch',
            'Total Payment Days', 'Total No of Payments', 'Average'
        ]
        for col, head in enumerate(headers2):
            fmt = header_format_red if col == len(headers2) - 1 else header_format
            sheet2.write(6, col, head, fmt)
 
        headers3 = ['Branch', 'Total Days', 'No of Payments', 'Average']
        for col, head in enumerate(headers3):
            fmt = header_format_red if col == len(headers3) - 1 else header_format
            sheet3.write(6, col, head, fmt)
 
        # -----------------------------
        # DATA FETCH: vendor bills paid within the wizard date range
        # Filter on payment release date (payment_release_date) within wizard range
        # -----------------------------
        payment_domain = [
            ('date', '>=', wizard.date_from),
            ('date', '<=', wizard.date_to),
            ('state', '=', 'posted'),
            ('payment_type', '=', 'outbound'),   # only vendor payments
        ]
        payments = self.env['account.payment'].search(payment_domain)
 
        if not payments:
            return
 
        # -----------------------------
        # SHEET 1 – DETAIL DATA
        # -----------------------------
        row = 7
        alt_row = False
 
        supplier_summary = defaultdict(lambda: {
            'total_days': 0, 'count': 0,
            'name': '', 'code': '', 'terms': '', 'branch': ''
        })
        branch_summary = defaultdict(lambda: {'total_days': 0, 'count': 0})
 
        for payment in payments:
            # Find payable reconciliation lines on the payment journal entry
            payable_lines = payment.move_id.line_ids.filtered(
                lambda l: l.account_id.internal_type == 'payable'
            )
            for line in payable_lines:
                partials = line.matched_debit_ids | line.matched_credit_ids
                for partial in partials:
                    counterpart_lines = partial.debit_move_id | partial.credit_move_id
                    for counterpart_line in counterpart_lines:
                        move = counterpart_line.move_id
                        if move.move_type != 'in_invoice':   # vendor bills only
                            continue
                        bill = move
 
                        # Apply wizard filters
                        if wizard.supplier_ids and bill.partner_id not in wizard.supplier_ids:
                            continue
                        if wizard.branch_ids and bill.branch_id not in wizard.branch_ids:
                            continue
                        if not bill.invoice_date:
                            continue
 
                        # Payment Made Days = Bill Received Date - Payment Release Date
                        release_date = payment.payment_release_date
                        bill_received = bill.invoice_date
 
                        if release_date and bill_received:
                            days = (release_date - bill_received).days
                        else:
                            days = 0
 
                        invoice_date_xl  = convert_to_excel_date(bill.invoice_date)
                        due_date_xl      = convert_to_excel_date(bill.invoice_date_due)
                        payment_date_xl  = convert_to_excel_date(payment.date)
                        release_date_xl  = convert_to_excel_date(release_date)
 
                        tf  = alt_row_format     if alt_row else text_format
                        nf  = alt_number_format  if alt_row else number_format
                        inf = alt_integer_format if alt_row else integer_format
                        df  = alt_date_format    if alt_row else date_format
 
                        sheet1.write(row, 0,  bill.partner_id.address_no or '', tf)
                        sheet1.write(row, 1,  bill.partner_id.name, tf)
                        sheet1.write(row, 2,  bill.partner_id.property_supplier_payment_term_id.name or '', tf)
                        sheet1.write(row, 3,  bill.branch_id.name or '', tf)
                        sheet1.write(row, 4,  bill.name, tf)
                        sheet1.write(row, 5,  bill.amount_total, nf)
                        if invoice_date_xl:
                            sheet1.write_datetime(row, 6, invoice_date_xl, df)
                        else:
                            sheet1.write(row, 6, '', tf)
                        if due_date_xl:
                            sheet1.write_datetime(row, 7, due_date_xl, df)
                        else:
                            sheet1.write(row, 7, '', tf)
                        if payment_date_xl:
                            sheet1.write_datetime(row, 8, payment_date_xl, df)
                        else:
                            sheet1.write(row, 8, '', tf)
                        if release_date_xl:
                            sheet1.write_datetime(row, 9, release_date_xl, df)
                        else:
                            sheet1.write(row, 9, '', tf)
                        sheet1.write(row, 10, bill.payment_state, tf)
                        sheet1.write(row, 11, days, inf)
 
                        # Accumulate summaries
                        supp = bill.partner_id.id
                        supplier_summary[supp]['total_days'] += days
                        supplier_summary[supp]['count']      += 1
                        supplier_summary[supp]['name']       = bill.partner_id.name
                        supplier_summary[supp]['code']       = bill.partner_id.address_no or ''
                        supplier_summary[supp]['terms']      = bill.partner_id.property_supplier_payment_term_id.name or ''
                        supplier_summary[supp]['branch']     = bill.branch_id.name or ''
 
                        branch = bill.branch_id.name or 'No Branch'
                        branch_summary[branch]['total_days'] += days
                        branch_summary[branch]['count']      += 1
 
                        row     += 1
                        alt_row  = not alt_row
 
        # -----------------------------
        # SHEET 2 – SUPPLIER SUMMARY
        # -----------------------------
        row2    = 7
        alt_row = False
        for supp, val in supplier_summary.items():
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
        # SHEET 3 – BRANCH SUMMARY
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
 