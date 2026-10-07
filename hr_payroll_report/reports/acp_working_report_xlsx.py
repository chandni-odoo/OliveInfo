from odoo import models
from datetime import datetime, date
from collections import defaultdict

from datetime import datetime, date

class AcpWorkingReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.acp_working_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizard):

        # -----------------------------
        # FORMATS
        # -----------------------------
        bold_grey = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D3D3D3'
        })

        left = workbook.add_format({'align': 'left'})

        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#002060',
            'font_color': 'white',
            'border': 1,
        })

        text_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter'
        })

        number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'num_format': '#,##0.00'
        })

        total_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'right',
            'num_format': '#,##0.00'
        })

        date_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'num_format': 'dd/mm/yyyy'
        })

        outstanding_label_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D3D3D3',
            'border': 1,
            'rotation': 90,
            'text_wrap': True,
        })

        # Credit note row highlight format
        credit_note_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'bg_color': '#FFF2CC',  # light yellow to distinguish credit notes
        })

        credit_note_number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'num_format': '#,##0.00',
            'bg_color': '#FFF2CC',
        })

        # -----------------------------
        # HELPER
        # -----------------------------
        def convert_date(date_obj):
            if not date_obj:
                return None
            if hasattr(date_obj, 'strftime'):
                return datetime.combine(date_obj, datetime.min.time())
            return datetime.strptime(str(date_obj), '%Y-%m-%d')

        # ============================================================
        # OPTIMIZED DATA FETCHING - SINGLE QUERIES
        # ============================================================

        # 1. Fetch all invoices in date range
        invoice_domain = [
            ('invoice_date', '>=', wizard.date_from),
            ('invoice_date', '<=', wizard.date_to),
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
        ]

        if wizard.branch_ids:
            invoice_domain.append(('branch_id', 'in', wizard.branch_ids.ids))

        invoices = self.env['account.move'].search(invoice_domain)

        if wizard.customer_ids:
            invoices = invoices.filtered(lambda inv: inv.partner_id in wizard.customer_ids)

        if wizard.exclude_legal_case:
            invoices = invoices.filtered(lambda inv: not inv.partner_id.legal_case)

        invoice_ids = invoices.ids

        if not invoice_ids:
            return

        # 2. Fetch all reconcile lines for these invoices
        reconcile_lines = self.env['account.partial.reconcile'].search([
            '|',
            ('debit_move_id.move_id', 'in', invoice_ids),
            ('credit_move_id.move_id', 'in', invoice_ids)
        ])

        # Build payment/credit-note to invoice mapping
        # For PAYMENTS
        payment_invoice_map = {}   # {payment_id: [{'invoice': inv, 'amount': amount}]}
        invoice_payment_map = {}   # {invoice_id: [{'payment': payment, 'amount': amount}]}

        # For CREDIT NOTES
        # {credit_note_id (account.move): [{'invoice': inv, 'amount': amount}]}
        credit_note_invoice_map = {}
        # {invoice_id: [{'credit_note': credit_note_move, 'amount': amount}]}
        invoice_credit_note_map = {}

        for reconcile in reconcile_lines:
            debit_move = reconcile.debit_move_id
            credit_move = reconcile.credit_move_id
            amount = reconcile.amount

            invoice_move = None
            other_move = None

            # Determine which side is the invoice
            if debit_move.move_id.move_type == 'out_invoice' and debit_move.move_id.id in invoice_ids:
                invoice_move = debit_move.move_id
                other_move = credit_move.move_id
            elif credit_move.move_id.move_type == 'out_invoice' and credit_move.move_id.id in invoice_ids:
                invoice_move = credit_move.move_id
                other_move = debit_move.move_id

            if not invoice_move or not other_move:
                continue

            # ── PAYMENT reconciliation ──────────────────────────────
            if other_move.payment_id:
                payment = other_move.payment_id

                if payment.id not in payment_invoice_map:
                    payment_invoice_map[payment.id] = []
                payment_invoice_map[payment.id].append({
                    'invoice': invoice_move,
                    'amount': amount,
                })

                if invoice_move.id not in invoice_payment_map:
                    invoice_payment_map[invoice_move.id] = []
                invoice_payment_map[invoice_move.id].append({
                    'payment': payment,
                    'amount': amount,
                })

            # ── CREDIT NOTE reconciliation ──────────────────────────
            elif other_move.move_type == 'out_refund':
                cn_move = other_move

                if cn_move.id not in credit_note_invoice_map:
                    credit_note_invoice_map[cn_move.id] = []
                credit_note_invoice_map[cn_move.id].append({
                    'invoice': invoice_move,
                    'amount': amount,
                })

                if invoice_move.id not in invoice_credit_note_map:
                    invoice_credit_note_map[invoice_move.id] = []
                invoice_credit_note_map[invoice_move.id].append({
                    'credit_note': cn_move,
                    'amount': amount,
                })

        # 3. Fetch payment records
        payment_ids = list(payment_invoice_map.keys())
        payments = (
            self.env['account.payment'].browse(payment_ids)
            if payment_ids
            else self.env['account.payment']
        )

        # 4. Fetch credit note move records
        cn_move_ids = list(credit_note_invoice_map.keys())
        credit_note_moves = (
            self.env['account.move'].browse(cn_move_ids)
            if cn_move_ids
            else self.env['account.move']
        )

        # ============================================================
        # SHEET 1 → INVOICE REPORT  (unchanged)
        # ============================================================
        sheet1 = workbook.add_worksheet('Invoice')

        for i in range(6):
            sheet1.set_column(i, i, 20)

        sheet1.merge_range(0, 0, 0, 5, 'INVOICE REPORT', bold_grey)

        sheet1.write(1, 0, 'From', bold_grey)
        sheet1.write(1, 1, str(wizard.date_from), left)

        sheet1.write(2, 0, 'To', bold_grey)
        sheet1.write(2, 1, str(wizard.date_to), left)

        sheet1.write(3, 0, 'Branches', bold_grey)
        sheet1.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)

        sheet1.write(4, 0, 'Customers', bold_grey)
        sheet1.write(4, 1, ', '.join(wizard.customer_ids.mapped('name')) or 'All', left)

        sheet1.write(5, 0, 'Exclude Legal Case', bold_grey)
        sheet1.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)

        headers1 = [
            'Invoice No', 'Customer Code', 'Customer Name',
            'Branch', 'Invoice Date', 'Invoice Amount'
        ]
        for col, head in enumerate(headers1):
            sheet1.write(7, col, head, header_format)

        row = 8
        total_invoice_amount = 0.0

        for inv in invoices:
            invoice_date = convert_date(inv.invoice_date)
            sheet1.write(row, 0, inv.name or '', text_format)
            sheet1.write(row, 1, inv.partner_id.address_no or '', text_format)
            sheet1.write(row, 2, inv.partner_id.name or '', text_format)
            sheet1.write(row, 3, inv.branch_id.name or '', text_format)
            if invoice_date:
                sheet1.write_datetime(row, 4, invoice_date, date_format)
            else:
                sheet1.write(row, 4, '', text_format)
            sheet1.write(row, 5, inv.amount_total, number_format)
            total_invoice_amount += inv.amount_total
            row += 1

        sheet1.write(row, 4, 'Total', bold_grey)
        sheet1.write(row, 5, total_invoice_amount, total_format)

        # ============================================================
        # SHEET 2 → ACP WORKINGS
        # ============================================================
        sheet2 = workbook.add_worksheet('ACP Workings')

        for i in range(9):
            sheet2.set_column(i, i, 22)

        sheet2.merge_range(0, 0, 0, 8, 'ACP WORKINGS REPORT', bold_grey)

        sheet2.write(1, 0, 'From', bold_grey)
        sheet2.write(1, 1, str(wizard.date_from), left)

        sheet2.write(2, 0, 'To', bold_grey)
        sheet2.write(2, 1, str(wizard.date_to), left)

        sheet2.write(3, 0, 'Branches', bold_grey)
        sheet2.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)

        sheet2.write(4, 0, 'Customers', bold_grey)
        sheet2.write(4, 1, ', '.join(wizard.customer_ids.mapped('name')) or 'All', left)

        sheet2.write(5, 0, 'Exclude Legal Case', bold_grey)
        sheet2.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)

        sheet2.merge_range(7, 0, 7, 8, 'Payment details & Workings', bold_grey)

        col_headers = [
            'Receipt No / Credit Note No', 'Customer Name', 'Invoice No',
            'Invoice Value', 'Invoice Date', 'Payment Date',
            'Payment Amount/Balance', 'Days', 'Weighted'
        ]
        for col, head in enumerate(col_headers):
            sheet2.write(8, col, head, header_format)

        row2 = 9
        total_payment = 0.0
        total_weighted = 0.0

        # ── A: Regular payment rows ─────────────────────────────────

        for payment in payments:
            for invoice_data in payment_invoice_map.get(payment.id, []):
                inv = invoice_data['invoice']
                payment_amount = invoice_data['amount']

                base_date = payment.date
                # days = (
                #     (base_date - inv.invoice_date).days
                #     if inv.invoice_date and base_date else 0
                # )
                days = (
                    max(0, (base_date - inv.invoice_date).days)
                    if inv.invoice_date and base_date else 0
                )
                weighted = days * payment_amount
                receipt_no = payment.receipt_number or payment.name

                invoice_date_dt = convert_date(inv.invoice_date)
                payment_date_dt = convert_date(payment.date)

                sheet2.write(row2, 0, receipt_no, text_format)
                sheet2.write(row2, 1, inv.partner_id.name or '', text_format)
                sheet2.write(row2, 2, inv.name or '', text_format)
                sheet2.write(row2, 3, inv.amount_total, number_format)

                if invoice_date_dt:
                    sheet2.write_datetime(row2, 4, invoice_date_dt, date_format)
                else:
                    sheet2.write(row2, 4, '', text_format)

                if payment_date_dt:
                    sheet2.write_datetime(row2, 5, payment_date_dt, date_format)
                else:
                    sheet2.write(row2, 5, '', text_format)

                sheet2.write(row2, 6, payment_amount, number_format)
                sheet2.write(row2, 7, days, text_format)
                sheet2.write(row2, 8, weighted, number_format)

                total_payment += payment_amount
                total_weighted += weighted
                row2 += 1

        # ── B: Credit note rows ─────────────────────────────────────
        for cn_move in credit_note_moves:
            for invoice_data in credit_note_invoice_map.get(cn_move.id, []):
                inv = invoice_data['invoice']
                cn_amount = invoice_data['amount']

                base_date = inv.invoice_date

                # days = (
                #     (base_date - inv.invoice_date).days
                #     if inv.invoice_date and base_date else 0
                # )
                days = (
                    max(0, (base_date - inv.invoice_date).days)
                    if inv.invoice_date and base_date else 0
                )
                weighted = days * cn_amount
                cn_label = '[CN] ' + (cn_move.name or '')

                invoice_date_dt = convert_date(inv.invoice_date)
                cn_date_dt = convert_date(base_date)

                sheet2.write(row2, 0, cn_label, credit_note_format)
                sheet2.write(row2, 1, inv.partner_id.name or '', credit_note_format)
                sheet2.write(row2, 2, inv.name or '', credit_note_format)
                sheet2.write(row2, 3, inv.amount_total, credit_note_number_format)

                if invoice_date_dt:
                    sheet2.write_datetime(row2, 4, invoice_date_dt, date_format)
                else:
                    sheet2.write(row2, 4, '', credit_note_format)

                if invoice_date_dt:
                    sheet2.write_datetime(row2, 5, invoice_date_dt, date_format)
                else:
                    sheet2.write(row2, 5, '', credit_note_format)

                sheet2.write(row2, 6, cn_amount, credit_note_number_format)
                sheet2.write(row2, 7, days, credit_note_number_format)
                sheet2.write(row2, 8, weighted, credit_note_number_format)

                total_payment += cn_amount
                total_weighted += weighted
                row2 += 1

        # ── Outstanding Invoices Section ────────────────────────────
        today = date.today()
        today_dt = datetime.combine(today, datetime.min.time())

        row2 += 1

        subheadline_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vleft',
            'fg_color': '#D9E1F2',
            'font_size': 11,
            'border': 1
        })

        sheet2.merge_range(row2, 0, row2, 8, 'Outstanding Invoices', subheadline_format)
        row2 += 1

        outstanding_data_start = row2

        outstanding_invoices = invoices.filtered(
            lambda inv: inv.payment_state not in ['paid', 'reversed'] and inv.amount_residual > 0
        )

        total_outstanding_balance = 0.0
        total_outstanding_weighted = 0.0
        outstanding_row_count = 0

        for inv in outstanding_invoices:
            balance = inv.amount_residual
            # days = (today - inv.invoice_date).days if inv.invoice_date else 0
            days = max(0, (today - inv.invoice_date).days) if inv.invoice_date else 0
            weighted = days * balance

            invoice_date_dt = convert_date(inv.invoice_date)

            sheet2.write(row2, 0, '', text_format)
            sheet2.write(row2, 1, inv.partner_id.name or '', text_format)
            sheet2.write(row2, 2, inv.name or '', text_format)
            sheet2.write(row2, 3, inv.amount_total, number_format)

            if invoice_date_dt:
                sheet2.write_datetime(row2, 4, invoice_date_dt, date_format)
            else:
                sheet2.write(row2, 4, '', text_format)

            sheet2.write_datetime(row2, 5, today_dt, date_format)
            sheet2.write(row2, 6, balance, number_format)
            # sheet2.write(row2, 7, days, number_format)
            sheet2.write(row2, 7, days, text_format)
            sheet2.write(row2, 8, weighted, number_format)

            total_outstanding_balance += balance
            total_outstanding_weighted += weighted
            outstanding_row_count += 1
            row2 += 1

        outstanding_data_end = row2 - 1

        grand_total_balance = total_payment + total_outstanding_balance
        grand_total_weighted = total_weighted + total_outstanding_weighted

        row2 += 1

        sheet2.write(row2, 5, 'GRAND TOTAL', bold_grey)
        sheet2.write(row2, 6, grand_total_balance, total_format)
        sheet2.write(row2, 8, grand_total_weighted, total_format)

        if outstanding_row_count > 0:
            sheet2.merge_range(
                outstanding_data_start, 0,
                outstanding_data_end, 0,
                'Outstanding\nInvoices',
                outstanding_label_format
            )

        # ── ACP CALCULATIONS ────────────────────────────────────────
        row2 += 2

        sheet2.merge_range(row2, 0, row2, 3, 'ACP CALCULATIONS', bold_grey)
        row2 += 1

        summary_headers = ['Customer', 'Total Amount', 'Weighted', 'ACP (Days)']
        for col, head in enumerate(summary_headers):
            sheet2.write(row2, col, head, header_format)
        row2 += 1

        customer_acp_map = {}

        def _ensure_partner(partner_id, partner):
            if partner_id not in customer_acp_map:
                customer_acp_map[partner_id] = {
                    'partner': partner,
                    'invoice_total': 0.0,
                    'weighted_total': 0.0,
                }

        # ── A: Payment rows ──────────────────────────────────────────
        for payment in payments:
            for invoice_data in payment_invoice_map.get(payment.id, []):
                inv = invoice_data['invoice']
                payment_amount = invoice_data['amount']

                base_date = payment.date
                # days = (
                #     (base_date - inv.invoice_date).days
                #     if inv.invoice_date and base_date else 0
                # )
                days = (
                    max(0, (base_date - inv.invoice_date).days)
                    if inv.invoice_date and base_date else 0
                )
                weighted = days * payment_amount

                _ensure_partner(inv.partner_id.id, inv.partner_id)
                customer_acp_map[inv.partner_id.id]['weighted_total'] += weighted

        # ── B: Credit note rows ──────────────────────────────────────
        for cn_move in credit_note_moves:
            for invoice_data in credit_note_invoice_map.get(cn_move.id, []):
                inv = invoice_data['invoice']
                cn_amount = invoice_data['amount']

                base_date = inv.invoice_date
                # days = (
                #     (base_date - inv.invoice_date).days
                #     if inv.invoice_date and base_date else 0
                # )
                days = (
                    max(0, (base_date - inv.invoice_date).days)
                    if inv.invoice_date and base_date else 0
                )
                weighted = days * cn_amount

                _ensure_partner(inv.partner_id.id, inv.partner_id)
                customer_acp_map[inv.partner_id.id]['weighted_total'] += weighted

        # ── C: Outstanding rows ──────────────────────────────────────
        for inv in outstanding_invoices:
            balance = inv.amount_residual
            base_date = today  # today is already date.today()
            # days = (
            #     (base_date - inv.invoice_date).days
            #     if inv.invoice_date else 0
            # )
            days = (
                max(0, (base_date - inv.invoice_date).days)
                if inv.invoice_date else 0
            )
            weighted = days * balance

            _ensure_partner(inv.partner_id.id, inv.partner_id)
            customer_acp_map[inv.partner_id.id]['weighted_total'] += weighted

        # ── D: Invoice totals ────────────────────────────────────────
        for inv in invoices:
            _ensure_partner(inv.partner_id.id, inv.partner_id)
            customer_acp_map[inv.partner_id.id]['invoice_total'] += inv.amount_total

        # ── Write to sheet ───────────────────────────────────────────
        total_acp_amount = 0.0
        total_acp_weighted = 0.0

        for data in customer_acp_map.values():
            partner = data['partner']
            total_amount = data['invoice_total']
            total_weighted_val = data['weighted_total']

            acp = (total_weighted_val / total_amount) if total_amount else 0

            sheet2.write(row2, 0, partner.name or '', text_format)
            sheet2.write(row2, 1, total_amount, number_format)
            sheet2.write(row2, 2, total_weighted_val, number_format)
            sheet2.write(row2, 3, acp, number_format)

            total_acp_amount += total_amount
            total_acp_weighted += total_weighted_val

            row2 += 1

        # ── Total row ────────────────────────────────────────────────
        sheet2.write(row2, 0, 'TOTAL', bold_grey)
        sheet2.write(row2, 1, total_acp_amount, total_format)
        sheet2.write(row2, 2, total_acp_weighted, total_format)

        # ACP total (optional but recommended)
        total_acp = (total_acp_weighted / total_acp_amount) if total_acp_amount else 0
        sheet2.write(row2, 3, total_acp, total_format)


        # ============================================================
        # SHEET 3 → CUSTOMER PAYMENTS (unchanged)
        # ============================================================
        sheet3 = workbook.add_worksheet('Customer Payments')

        for i in range(4):
            sheet3.set_column(i, i, 22)

        sheet3.merge_range(0, 0, 0, 3, 'CUSTOMER PAYMENTS', bold_grey)

        sheet3.write(1, 0, 'From', bold_grey)
        sheet3.write(1, 1, str(wizard.date_from), left)

        sheet3.write(2, 0, 'To', bold_grey)
        sheet3.write(2, 1, str(wizard.date_to), left)

        sheet3.write(3, 0, 'Branches', bold_grey)
        sheet3.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)

        sheet3.write(4, 0, 'Customers', bold_grey)
        sheet3.write(4, 1, ', '.join(wizard.customer_ids.mapped('name')) or 'All', left)

        sheet3.write(5, 0, 'Exclude Legal Case', bold_grey)
        sheet3.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)

        headers3 = ['Customer Code', 'Customer Name', 'Payment Date', 'Payment Amount']
        for col, head in enumerate(headers3):
            sheet3.write(7, col, head, header_format)

        row3 = 8
        total_payment_amount = 0.0

        for payment in payments:
            partner = payment.partner_id

            if wizard.customer_ids and partner not in wizard.customer_ids:
                continue
            if wizard.exclude_legal_case and partner.legal_case:
                continue

            payment_date_dt = convert_date(payment.date)
            amount = payment.amount

            sheet3.write(row3, 0, partner.address_no or '', text_format)
            sheet3.write(row3, 1, partner.name or '', text_format)

            if payment_date_dt:
                sheet3.write_datetime(row3, 2, payment_date_dt, date_format)
            else:
                sheet3.write(row3, 2, '', text_format)

            sheet3.write(row3, 3, amount, number_format)
            total_payment_amount += amount
            row3 += 1

        sheet3.write(row3, 2, 'TOTAL', bold_grey)
        sheet3.write(row3, 3, total_payment_amount, total_format)


# class AcpWorkingReportXlsx(models.AbstractModel):
#     _name = 'report.hr_payroll_report.acp_working_report_xlsx'
#     _inherit = 'report.report_xlsx.abstract'

#     def generate_xlsx_report(self, workbook, data, wizard):

#         # -----------------------------
#         # FORMATS
#         # -----------------------------
#         bold_grey = workbook.add_format({
#             'bold': True,
#             'align': 'center',
#             'valign': 'vcenter',
#             'bg_color': '#D3D3D3'
#         })

#         left = workbook.add_format({'align': 'left'})

#         header_format = workbook.add_format({
#             'bold': True,
#             'align': 'center',
#             'valign': 'vcenter',
#             'bg_color': '#002060',
#             'font_color': 'white',
#             'border': 1,
#         })

#         text_format = workbook.add_format({
#             'border': 1,
#             'valign': 'vcenter'
#         })

#         number_format = workbook.add_format({
#             'border': 1,
#             'align': 'right',
#             'num_format': '#,##0.00'
#         })

#         total_format = workbook.add_format({
#             'bold': True,
#             'border': 1,
#             'align': 'right',
#             'num_format': '#,##0.00'
#         })

#         date_format = workbook.add_format({
#             'border': 1,
#             'align': 'center',
#             'num_format': 'dd/mm/yyyy'
#         })

#         outstanding_label_format = workbook.add_format({
#             'bold': True,
#             'align': 'center',
#             'valign': 'vcenter',
#             'bg_color': '#D3D3D3',
#             'border': 1,
#             'rotation': 90,
#             'text_wrap': True,
#         })

#         # -----------------------------
#         # HELPER
#         # -----------------------------
#         def convert_date(date_obj):
#             if not date_obj:
#                 return None
#             if hasattr(date_obj, 'strftime'):
#                 return datetime.combine(date_obj, datetime.min.time())
#             return datetime.strptime(str(date_obj), '%Y-%m-%d')

#         # ============================================================
#         # OPTIMIZED DATA FETCHING - SINGLE QUERIES
#         # ============================================================
        
#         # 1. Fetch all invoices in date range
#         invoice_domain = [
#             ('invoice_date', '>=', wizard.date_from),
#             ('invoice_date', '<=', wizard.date_to),
#             ('state', '=', 'posted'),
#             ('move_type', '=', 'out_invoice'),
#         ]

#         if wizard.branch_ids:
#             invoice_domain.append(('branch_id', 'in', wizard.branch_ids.ids))

#         invoices = self.env['account.move'].search(invoice_domain)
        
#         # Apply customer filter
#         if wizard.customer_ids:
#             invoices = invoices.filtered(lambda inv: inv.partner_id in wizard.customer_ids)
        
#         # Apply legal case filter
#         if wizard.exclude_legal_case:
#             invoices = invoices.filtered(lambda inv: not inv.partner_id.legal_case)

#         invoice_ids = invoices.ids
        
#         if not invoice_ids:
#             # No data to report
#             return

#         # 2. Fetch all payments and their reconciled invoices in ONE GO
#         # Get all account partial reconcile lines for these invoices
#         reconcile_lines = self.env['account.partial.reconcile'].search([
#             '|',
#             ('debit_move_id.move_id', 'in', invoice_ids),
#             ('credit_move_id.move_id', 'in', invoice_ids)
#         ])
        
#         # Build payment to invoice mapping
#         payment_invoice_map = {}  # {payment_id: [{'invoice': inv, 'amount': amount}]}
#         invoice_payment_map = {}  # {invoice_id: [{'payment': payment, 'amount': amount}]}
        
#         for reconcile in reconcile_lines:
#             # Find which move is invoice and which is payment
#             debit_move = reconcile.debit_move_id
#             credit_move = reconcile.credit_move_id
            
#             invoice_move = None
#             payment_move = None
            
#             if debit_move.move_id.move_type == 'out_invoice' and debit_move.move_id.id in invoice_ids:
#                 invoice_move = debit_move.move_id
#                 payment_move = credit_move.move_id
#                 amount = reconcile.amount
#             elif credit_move.move_id.move_type == 'out_invoice' and credit_move.move_id.id in invoice_ids:
#                 invoice_move = credit_move.move_id
#                 payment_move = debit_move.move_id
#                 amount = reconcile.amount
            
#             if invoice_move and payment_move and payment_move.payment_id:
#                 payment = payment_move.payment_id
                
#                 if payment.id not in payment_invoice_map:
#                     payment_invoice_map[payment.id] = []
#                 payment_invoice_map[payment.id].append({
#                     'invoice': invoice_move,
#                     'amount': amount
#                 })
                
#                 if invoice_move.id not in invoice_payment_map:
#                     invoice_payment_map[invoice_move.id] = []
#                 invoice_payment_map[invoice_move.id].append({
#                     'payment': payment,
#                     'amount': amount
#                 })

#         # 3. Get all payments at once
#         payment_ids = list(payment_invoice_map.keys())
#         payments = self.env['account.payment'].browse(payment_ids) if payment_ids else self.env['account.payment']

#         # ============================================================
#         # SHEET 1 → INVOICE REPORT
#         # ============================================================
#         sheet1 = workbook.add_worksheet('Invoice')

#         for i in range(6):
#             sheet1.set_column(i, i, 20)

#         sheet1.merge_range(0, 0, 0, 5, 'INVOICE REPORT', bold_grey)

#         sheet1.write(1, 0, 'From', bold_grey)
#         sheet1.write(1, 1, str(wizard.date_from), left)

#         sheet1.write(2, 0, 'To', bold_grey)
#         sheet1.write(2, 1, str(wizard.date_to), left)

#         sheet1.write(3, 0, 'Branches', bold_grey)
#         sheet1.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)

#         sheet1.write(4, 0, 'Customers', bold_grey)
#         sheet1.write(4, 1, ', '.join(wizard.customer_ids.mapped('name')) or 'All', left)

#         sheet1.write(5, 0, 'Exclude Legal Case', bold_grey)
#         sheet1.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)

#         headers1 = [
#             'Invoice No', 'Customer Code', 'Customer Name',
#             'Branch', 'Invoice Date', 'Invoice Amount'
#         ]
#         for col, head in enumerate(headers1):
#             sheet1.write(7, col, head, header_format)

#         row = 8
#         total_invoice_amount = 0.0

#         for inv in invoices:
#             invoice_date = convert_date(inv.invoice_date)
#             sheet1.write(row, 0, inv.name or '', text_format)
#             sheet1.write(row, 1, inv.partner_id.address_no or '', text_format)
#             sheet1.write(row, 2, inv.partner_id.name or '', text_format)
#             sheet1.write(row, 3, inv.branch_id.name or '', text_format)
#             if invoice_date:
#                 sheet1.write_datetime(row, 4, invoice_date, date_format)
#             else:
#                 sheet1.write(row, 4, '', text_format)
#             sheet1.write(row, 5, inv.amount_total, number_format)
#             total_invoice_amount += inv.amount_total
#             row += 1

#         sheet1.write(row, 4, 'Total', bold_grey)
#         sheet1.write(row, 5, total_invoice_amount, total_format)

#         # ============================================================
#         # SHEET 2 → ACP WORKINGS
#         # ============================================================
#         sheet2 = workbook.add_worksheet('ACP Workings')

#         for i in range(9):
#             sheet2.set_column(i, i, 22)

#         sheet2.merge_range(0, 0, 0, 8, 'ACP WORKINGS REPORT', bold_grey)

#         sheet2.write(1, 0, 'From', bold_grey)
#         sheet2.write(1, 1, str(wizard.date_from), left)

#         sheet2.write(2, 0, 'To', bold_grey)
#         sheet2.write(2, 1, str(wizard.date_to), left)

#         sheet2.write(3, 0, 'Branches', bold_grey)
#         sheet2.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)

#         sheet2.write(4, 0, 'Customers', bold_grey)
#         sheet2.write(4, 1, ', '.join(wizard.customer_ids.mapped('name')) or 'All', left)

#         sheet2.write(5, 0, 'Exclude Legal Case', bold_grey)
#         sheet2.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)

#         sheet2.merge_range(7, 0, 7, 8, 'Payment details & Workings', bold_grey)

#         col_headers = [
#             'Receipt No', 'Customer Name', 'Invoice No',
#             'Invoice Value', 'Invoice Date', 'Payment Date',
#             'Payment Amount/Balance', 'Days', 'Weighted'
#         ]
#         for col, head in enumerate(col_headers):
#             sheet2.write(8, col, head, header_format)

#         # Write payment data using pre-built mapping
#         row2 = 9
#         total_payment = 0.0
#         total_weighted = 0.0

#         for payment in payments:
#             for invoice_data in payment_invoice_map.get(payment.id, []):
#                 inv = invoice_data['invoice']
#                 payment_amount = invoice_data['amount']
                
#                 days = (payment.date - inv.invoice_date).days if inv.invoice_date and payment.date else 0
#                 weighted = days * payment_amount
#                 receipt_no = payment.receipt_number or payment.name

#                 invoice_date_dt = convert_date(inv.invoice_date)
#                 payment_date_dt = convert_date(payment.date)

#                 sheet2.write(row2, 0, receipt_no, text_format)
#                 sheet2.write(row2, 1, inv.partner_id.name or '', text_format)
#                 sheet2.write(row2, 2, inv.name or '', text_format)
#                 sheet2.write(row2, 3, inv.amount_total, number_format)

#                 if invoice_date_dt:
#                     sheet2.write_datetime(row2, 4, invoice_date_dt, date_format)
#                 else:
#                     sheet2.write(row2, 4, '', text_format)

#                 if payment_date_dt:
#                     sheet2.write_datetime(row2, 5, payment_date_dt, date_format)
#                 else:
#                     sheet2.write(row2, 5, '', text_format)

#                 sheet2.write(row2, 6, payment_amount, number_format)
#                 sheet2.write(row2, 7, days, number_format)
#                 sheet2.write(row2, 8, weighted, number_format)

#                 total_payment += payment_amount
#                 total_weighted += weighted
#                 row2 += 1

#         # Outstanding Invoices Section
#         today = date.today()
#         today_dt = datetime.combine(today, datetime.min.time())

#         row2 += 1

#         subheadline_format = workbook.add_format({
#             'bold': True,
#             'align': 'left',
#             'valign': 'vleft',
#             'fg_color': '#D9E1F2',
#             'font_size': 11,
#             'border': 1
#         })

#         sheet2.merge_range(row2, 0, row2, 8, 'Outstanding Invoices', subheadline_format)
#         row2 += 1

#         outstanding_data_start = row2

#         # Find outstanding invoices
#         outstanding_invoices = invoices.filtered(
#             lambda inv: inv.payment_state not in ['paid', 'reversed'] and inv.amount_residual > 0
#         )

#         total_outstanding_balance = 0.0
#         total_outstanding_weighted = 0.0
#         outstanding_row_count = 0

#         for inv in outstanding_invoices:
#             balance = inv.amount_residual
#             days = (today - inv.invoice_date).days if inv.invoice_date else 0
#             weighted = days * balance

#             invoice_date_dt = convert_date(inv.invoice_date)

#             sheet2.write(row2, 0, '', text_format)
#             sheet2.write(row2, 1, inv.partner_id.name or '', text_format)
#             sheet2.write(row2, 2, inv.name or '', text_format)
#             sheet2.write(row2, 3, inv.amount_total, number_format)

#             if invoice_date_dt:
#                 sheet2.write_datetime(row2, 4, invoice_date_dt, date_format)
#             else:
#                 sheet2.write(row2, 4, '', text_format)

#             sheet2.write_datetime(row2, 5, today_dt, date_format)
#             sheet2.write(row2, 6, balance, number_format)
#             sheet2.write(row2, 7, days, number_format)
#             sheet2.write(row2, 8, weighted, number_format)

#             total_outstanding_balance += balance
#             total_outstanding_weighted += weighted
#             outstanding_row_count += 1
#             row2 += 1

#         outstanding_data_end = row2 - 1

#         # Grand Total
#         grand_total_balance = total_payment + total_outstanding_balance
#         grand_total_weighted = total_weighted + total_outstanding_weighted

#         row2 += 1

#         sheet2.write(row2, 5, 'GRAND TOTAL', bold_grey)
#         sheet2.write(row2, 6, grand_total_balance, total_format)
#         sheet2.write(row2, 8, grand_total_weighted, total_format)
        
#         if outstanding_row_count > 0:
#             sheet2.merge_range(
#                 outstanding_data_start, 0,
#                 outstanding_data_end, 0,
#                 'Outstanding\nInvoices',
#                 outstanding_label_format
#             )

#         # ACP CALCULATIONS
#         row2 += 2

#         sheet2.merge_range(row2, 0, row2, 3, 'ACP CALCULATIONS', bold_grey)
#         row2 += 1

#         summary_headers = ['Customer', 'Total Amount', 'Weighted', 'ACP (Days)']

#         for col, head in enumerate(summary_headers):
#             sheet2.write(row2, col, head, header_format)

#         row2 += 1

#         # Calculate ACP using pre-built mapping
#         customer_acp_map = {}

#         for inv in invoices:
#             total_payment_for_invoice = 0.0
#             total_weighted_for_invoice = 0.0
            
#             for payment_data in invoice_payment_map.get(inv.id, []):
#                 payment = payment_data['payment']
#                 payment_amount = payment_data['amount']
#                 days = (payment.date - inv.invoice_date).days if inv.invoice_date and payment.date else 0
#                 weighted = days * payment_amount
#                 total_payment_for_invoice += payment_amount
#                 total_weighted_for_invoice += weighted
            
#             if total_payment_for_invoice > 0:
#                 partner = inv.partner_id
#                 if partner.id not in customer_acp_map:
#                     customer_acp_map[partner.id] = {
#                         'partner': partner,
#                         'amount': 0.0,
#                         'weighted': 0.0
#                     }
#                 customer_acp_map[partner.id]['amount'] += total_payment_for_invoice
#                 customer_acp_map[partner.id]['weighted'] += total_weighted_for_invoice

#         # Write ACP summary
#         for data in customer_acp_map.values():
#             partner = data['partner']
#             total_amount = data['amount']
#             total_weighted = data['weighted']
#             acp = (total_weighted / total_amount) if total_amount else 0

#             sheet2.write(row2, 0, partner.name or '', text_format)
#             sheet2.write(row2, 1, total_amount, number_format)
#             sheet2.write(row2, 2, total_weighted, number_format)
#             sheet2.write(row2, 3, acp, number_format)
#             row2 += 1

#         # ============================================================
#         # SHEET 3 → CUSTOMER PAYMENTS (SUMMARY)
#         # ============================================================
#         sheet3 = workbook.add_worksheet('Customer Payments')

#         for i in range(4):
#             sheet3.set_column(i, i, 22)

#         sheet3.merge_range(0, 0, 0, 3, 'CUSTOMER PAYMENTS', bold_grey)

#         sheet3.write(1, 0, 'From', bold_grey)
#         sheet3.write(1, 1, str(wizard.date_from), left)

#         sheet3.write(2, 0, 'To', bold_grey)
#         sheet3.write(2, 1, str(wizard.date_to), left)

#         sheet3.write(3, 0, 'Branches', bold_grey)
#         sheet3.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)

#         sheet3.write(4, 0, 'Customers', bold_grey)
#         sheet3.write(4, 1, ', '.join(wizard.customer_ids.mapped('name')) or 'All', left)

#         sheet3.write(5, 0, 'Exclude Legal Case', bold_grey)
#         sheet3.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)

#         headers3 = [
#             'Customer Code',
#             'Customer Name',
#             'Payment Date',
#             'Payment Amount'
#         ]

#         for col, head in enumerate(headers3):
#             sheet3.write(7, col, head, header_format)

#         row3 = 8
#         total_payment_amount = 0.0

#         # Use pre-built payment data
#         for payment in payments:
#             partner = payment.partner_id
            
#             # Apply filters
#             if wizard.customer_ids and partner not in wizard.customer_ids:
#                 continue
#             if wizard.exclude_legal_case and partner.legal_case:
#                 continue

#             payment_date_dt = convert_date(payment.date)
#             amount = payment.amount

#             sheet3.write(row3, 0, partner.address_no or '', text_format)
#             sheet3.write(row3, 1, partner.name or '', text_format)

#             if payment_date_dt:
#                 sheet3.write_datetime(row3, 2, payment_date_dt, date_format)
#             else:
#                 sheet3.write(row3, 2, '', text_format)

#             sheet3.write(row3, 3, amount, number_format)

#             total_payment_amount += amount
#             row3 += 1

#         sheet3.write(row3, 2, 'TOTAL', bold_grey)
#         sheet3.write(row3, 3, total_payment_amount, total_format)


