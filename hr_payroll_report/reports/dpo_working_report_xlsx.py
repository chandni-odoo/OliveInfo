from odoo import models
from datetime import datetime, date

class DpoWorkingReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.dpo_working_report_xlsx'
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
 
        # Vendor credit note row highlight format (light orange to distinguish from ACP's yellow)
        credit_note_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'bg_color': '#FCE4D6',  # light orange for vendor credit notes
        })
 
        credit_note_number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'num_format': '#,##0.00',
            'bg_color': '#FCE4D6',
        })
 
        subheadline_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'fg_color': '#D9E1F2',
            'font_size': 11,
            'border': 1
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
 
        # 1. Fetch all bills in date range
        bill_domain = [
            ('invoice_date', '>=', wizard.date_from),
            ('invoice_date', '<=', wizard.date_to),
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
        ]
 
        if wizard.branch_ids:
            bill_domain.append(('branch_id', 'in', wizard.branch_ids.ids))
 
        bills = self.env['account.move'].search(bill_domain)
 
        if wizard.supplier_ids:
            bills = bills.filtered(lambda b: b.partner_id in wizard.supplier_ids)
 
        if wizard.exclude_legal_case:
            bills = bills.filtered(lambda b: not b.partner_id.legal_case)
 
        bill_ids = bills.ids
 
        if not bill_ids:
            return
 
        # 2. Fetch all reconcile lines for these bills
        reconcile_lines = self.env['account.partial.reconcile'].search([
            '|',
            ('debit_move_id.move_id', 'in', bill_ids),
            ('credit_move_id.move_id', 'in', bill_ids)
        ])
 
        # Build payment/credit-note to bill mapping
        # For PAYMENTS
        payment_bill_map = {}   # {payment_id: [{'bill': bill, 'amount': amount}]}
        bill_payment_map = {}   # {bill_id: [{'payment': payment, 'amount': amount}]}
 
        # For CREDIT NOTES (vendor refunds = in_refund)
        # {credit_note_id (account.move): [{'bill': bill, 'amount': amount}]}
        credit_note_bill_map = {}
        # {bill_id: [{'credit_note': credit_note_move, 'amount': amount}]}
        bill_credit_note_map = {}
 
        for reconcile in reconcile_lines:
            debit_move = reconcile.debit_move_id
            credit_move = reconcile.credit_move_id
            amount = reconcile.amount
 
            bill_move = None
            other_move = None
 
            # Determine which side is the bill
            if debit_move.move_id.move_type == 'in_invoice' and debit_move.move_id.id in bill_ids:
                bill_move = debit_move.move_id
                other_move = credit_move.move_id
            elif credit_move.move_id.move_type == 'in_invoice' and credit_move.move_id.id in bill_ids:
                bill_move = credit_move.move_id
                other_move = debit_move.move_id
 
            if not bill_move or not other_move:
                continue
 
            # ── PAYMENT reconciliation ──────────────────────────────
            if other_move.payment_id:
                payment = other_move.payment_id
 
                if payment.id not in payment_bill_map:
                    payment_bill_map[payment.id] = []
                payment_bill_map[payment.id].append({
                    'bill': bill_move,
                    'amount': amount,
                })
 
                if bill_move.id not in bill_payment_map:
                    bill_payment_map[bill_move.id] = []
                bill_payment_map[bill_move.id].append({
                    'payment': payment,
                    'amount': amount,
                })
 
            # ── CREDIT NOTE reconciliation (vendor refund = in_refund) ──
            elif other_move.move_type == 'in_refund':
                cn_move = other_move
 
                if cn_move.id not in credit_note_bill_map:
                    credit_note_bill_map[cn_move.id] = []
                credit_note_bill_map[cn_move.id].append({
                    'bill': bill_move,
                    'amount': amount,
                })
 
                if bill_move.id not in bill_credit_note_map:
                    bill_credit_note_map[bill_move.id] = []
                bill_credit_note_map[bill_move.id].append({
                    'credit_note': cn_move,
                    'amount': amount,
                })
 
        # 3. Fetch payment records
        payment_ids = list(payment_bill_map.keys())
        payments = (
            self.env['account.payment'].browse(payment_ids)
            if payment_ids
            else self.env['account.payment']
        )
 
        # 4. Fetch credit note move records
        cn_move_ids = list(credit_note_bill_map.keys())
        credit_note_moves = (
            self.env['account.move'].browse(cn_move_ids)
            if cn_move_ids
            else self.env['account.move']
        )
 
        # ============================================================
        # SHEET 1 → BILL REPORT
        # ============================================================
        sheet1 = workbook.add_worksheet('Bills')
 
        for i in range(6):
            sheet1.set_column(i, i, 20)
 
        sheet1.merge_range(0, 0, 0, 5, 'BILL REPORT', bold_grey)
 
        sheet1.write(1, 0, 'From', bold_grey)
        sheet1.write(1, 1, str(wizard.date_from), left)
 
        sheet1.write(2, 0, 'To', bold_grey)
        sheet1.write(2, 1, str(wizard.date_to), left)
 
        sheet1.write(3, 0, 'Branches', bold_grey)
        sheet1.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)
 
        sheet1.write(4, 0, 'Suppliers', bold_grey)
        sheet1.write(4, 1, ', '.join(wizard.supplier_ids.mapped('name')) or 'All', left)
 
        sheet1.write(5, 0, 'Exclude Legal Case', bold_grey)
        sheet1.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)
 
        headers1 = [
            'Bill No', 'Supplier Code', 'Supplier Name',
            'Branch', 'Bill Date', 'Bill Amount'
        ]
        for col, head in enumerate(headers1):
            sheet1.write(7, col, head, header_format)
 
        row = 8
        total_bill_amount = 0.0
 
        for bill in bills:
            bill_date = convert_date(bill.invoice_date)
            sheet1.write(row, 0, bill.name or '', text_format)
            sheet1.write(row, 1, bill.partner_id.address_no or '', text_format)
            sheet1.write(row, 2, bill.partner_id.name or '', text_format)
            sheet1.write(row, 3, bill.branch_id.name or '', text_format)
            if bill_date:
                sheet1.write_datetime(row, 4, bill_date, date_format)
            else:
                sheet1.write(row, 4, '', text_format)
            sheet1.write(row, 5, bill.amount_total, number_format)
            total_bill_amount += bill.amount_total
            row += 1
 
        sheet1.write(row, 4, 'Total', bold_grey)
        sheet1.write(row, 5, total_bill_amount, total_format)
 
        # ============================================================
        # SHEET 2 → DPO WORKINGS
        # ============================================================
        sheet2 = workbook.add_worksheet('DPO Workings')
 
        for i in range(9):
            sheet2.set_column(i, i, 22)
 
        sheet2.merge_range(0, 0, 0, 8, 'DPO WORKINGS REPORT', bold_grey)
 
        sheet2.write(1, 0, 'From', bold_grey)
        sheet2.write(1, 1, str(wizard.date_from), left)
 
        sheet2.write(2, 0, 'To', bold_grey)
        sheet2.write(2, 1, str(wizard.date_to), left)
 
        sheet2.write(3, 0, 'Branches', bold_grey)
        sheet2.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)
 
        sheet2.write(4, 0, 'Suppliers', bold_grey)
        sheet2.write(4, 1, ', '.join(wizard.supplier_ids.mapped('name')) or 'All', left)
 
        sheet2.write(5, 0, 'Exclude Legal Case', bold_grey)
        sheet2.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)
 
        sheet2.merge_range(7, 0, 7, 8, 'Payment details & Workings', bold_grey)
 
        col_headers = [
            'Payment Ref / Credit Note No', 'Supplier Name', 'Bill No',
            'Bill Value', 'Bill Date', 'Payment Date',
            'Payment Amount/Balance', 'Days', 'Weighted'
        ]
        for col, head in enumerate(col_headers):
            sheet2.write(8, col, head, header_format)
 
        row2 = 9
        total_payment = 0.0
        total_weighted = 0.0
 
        # ── A: Regular payment rows ─────────────────────────────────
        for payment in payments:
            for bill_data in payment_bill_map.get(payment.id, []):
                bill = bill_data['bill']
                payment_amount = bill_data['amount']
 
                base_date = payment.payment_release_date
                # days = (
                #     (base_date - bill.invoice_date).days
                #     if bill.invoice_date and base_date else 0
                # )
                days = (
                    max(0, (base_date - bill.invoice_date).days)
                    if bill.invoice_date and base_date else 0
                )
                weighted = days * payment_amount
 
                bill_date_dt = convert_date(bill.invoice_date)
                payment_date_dt = convert_date(payment.payment_release_date)
 
                sheet2.write(row2, 0, payment.name or '', text_format)
                sheet2.write(row2, 1, bill.partner_id.name or '', text_format)
                sheet2.write(row2, 2, bill.name or '', text_format)
                sheet2.write(row2, 3, bill.amount_total, number_format)
 
                if bill_date_dt:
                    sheet2.write_datetime(row2, 4, bill_date_dt, date_format)
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
 
        # ── B: Credit note rows (vendor refunds) ────────────────────
        for cn_move in credit_note_moves:
            for bill_data in credit_note_bill_map.get(cn_move.id, []):
                bill = bill_data['bill']
                cn_amount = bill_data['amount']
 
                # Credit notes applied on the bill date → days = 0
                base_date = bill.invoice_date
                # days = (
                #     (base_date - bill.invoice_date).days
                #     if bill.invoice_date and base_date else 0
                # )
                days = (
                    max(0, (base_date - bill.invoice_date).days)
                    if bill.invoice_date and base_date else 0
                )
                weighted = days * cn_amount
                cn_label = '[CN] ' + (cn_move.name or '')
 
                bill_date_dt = convert_date(bill.invoice_date)
 
                sheet2.write(row2, 0, cn_label, credit_note_format)
                sheet2.write(row2, 1, bill.partner_id.name or '', credit_note_format)
                sheet2.write(row2, 2, bill.name or '', credit_note_format)
                sheet2.write(row2, 3, bill.amount_total, credit_note_number_format)
 
                if bill_date_dt:
                    sheet2.write_datetime(row2, 4, bill_date_dt, date_format)
                else:
                    sheet2.write(row2, 4, '', credit_note_format)
 
                # Payment date column → show CN invoice date (same as ACP concept)
                if bill_date_dt:
                    sheet2.write_datetime(row2, 5, bill_date_dt, date_format)
                else:
                    sheet2.write(row2, 5, '', credit_note_format)
 
                sheet2.write(row2, 6, cn_amount, credit_note_number_format)
                sheet2.write(row2, 7, days, credit_note_number_format)
                sheet2.write(row2, 8, weighted, credit_note_number_format)
 
                total_payment += cn_amount
                total_weighted += weighted
                row2 += 1
 
        # ── Outstanding Bills Section ───────────────────────────────
        today = date.today()
        today_dt = datetime.combine(today, datetime.min.time())
 
        row2 += 1
 
        sheet2.merge_range(row2, 0, row2, 8, 'Outstanding Payable Invoices', subheadline_format)
        row2 += 1
 
        outstanding_data_start = row2
 
        outstanding_bills = bills.filtered(
            lambda b: b.payment_state not in ['paid', 'reversed'] and b.amount_residual > 0
        )
 
        total_outstanding_balance = 0.0
        total_outstanding_weighted = 0.0
        outstanding_row_count = 0
 
        for bill in outstanding_bills:
            balance = bill.amount_residual
            # days = (today - bill.invoice_date).days if bill.invoice_date else 0
            days = max(0, (today - bill.invoice_date).days) if bill.invoice_date else 0
            weighted = days * balance
 
            bill_date_dt = convert_date(bill.invoice_date)
 
            sheet2.write(row2, 0, '', text_format)
            sheet2.write(row2, 1, bill.partner_id.name or '', text_format)
            sheet2.write(row2, 2, bill.name or '', text_format)
            sheet2.write(row2, 3, bill.amount_total, number_format)
 
            if bill_date_dt:
                sheet2.write_datetime(row2, 4, bill_date_dt, date_format)
            else:
                sheet2.write(row2, 4, '', text_format)
 
            sheet2.write_datetime(row2, 5, today_dt, date_format)
            sheet2.write(row2, 6, balance, number_format)
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
                'Outstanding\nPayable\nInvoices',
                outstanding_label_format
            )
 
        # ── DPO CALCULATIONS ────────────────────────────────────────
        row2 += 2
 
        sheet2.merge_range(row2, 0, row2, 3, 'DPO CALCULATIONS', bold_grey)
        row2 += 1
 
        summary_headers = ['Supplier', 'Total Amount', 'Weighted', 'DPO (Days)']
        for col, head in enumerate(summary_headers):
            sheet2.write(row2, col, head, header_format)
        row2 += 1
 
        supplier_dpo_map = {}
 
        def _ensure_partner(partner_id, partner):
            if partner_id not in supplier_dpo_map:
                supplier_dpo_map[partner_id] = {
                    'partner': partner,
                    'bill_total': 0.0,
                    'weighted_total': 0.0,
                }
 
        # ── A: Payment rows ──────────────────────────────────────────
        for payment in payments:
            for bill_data in payment_bill_map.get(payment.id, []):
                bill = bill_data['bill']
                payment_amount = bill_data['amount']
 
                base_date = payment.payment_release_date
                # days = (
                #     (base_date - bill.invoice_date).days
                #     if bill.invoice_date and base_date else 0
                # )
                days = (
                    max(0, (base_date - bill.invoice_date).days)
                    if bill.invoice_date and base_date else 0
                )
                weighted = days * payment_amount
 
                _ensure_partner(bill.partner_id.id, bill.partner_id)
                supplier_dpo_map[bill.partner_id.id]['weighted_total'] += weighted
 
        # ── B: Credit note rows ──────────────────────────────────────
        for cn_move in credit_note_moves:
            for bill_data in credit_note_bill_map.get(cn_move.id, []):
                bill = bill_data['bill']
                cn_amount = bill_data['amount']
 
                base_date = bill.invoice_date
                # days = (
                #     (base_date - bill.invoice_date).days
                #     if bill.invoice_date and base_date else 0
                # )
                days = (
                    max(0, (base_date - bill.invoice_date).days)
                    if bill.invoice_date and base_date else 0
                )
                weighted = days * cn_amount
 
                _ensure_partner(bill.partner_id.id, bill.partner_id)
                supplier_dpo_map[bill.partner_id.id]['weighted_total'] += weighted
 
        # ── C: Outstanding rows ──────────────────────────────────────
        for bill in outstanding_bills:
            balance = bill.amount_residual
            base_date = today
            # days = (
            #     (base_date - bill.invoice_date).days
            #     if bill.invoice_date else 0
            # )
            days = (
                max(0, (base_date - bill.invoice_date).days)
                if bill.invoice_date else 0
            )
            weighted = days * balance
 
            _ensure_partner(bill.partner_id.id, bill.partner_id)
            supplier_dpo_map[bill.partner_id.id]['weighted_total'] += weighted
 
        # ── D: Bill totals ───────────────────────────────────────────
        for bill in bills:
            _ensure_partner(bill.partner_id.id, bill.partner_id)
            supplier_dpo_map[bill.partner_id.id]['bill_total'] += bill.amount_total
 
        # ── Write to sheet ───────────────────────────────────────────
        total_dpo_amount = 0.0
        total_dpo_weighted = 0.0
 
        for data in supplier_dpo_map.values():
            partner = data['partner']
            total_amount = data['bill_total']
            total_weighted_val = data['weighted_total']
 
            dpo = (total_weighted_val / total_amount) if total_amount else 0
 
            sheet2.write(row2, 0, partner.name or '', text_format)
            sheet2.write(row2, 1, total_amount, number_format)
            sheet2.write(row2, 2, total_weighted_val, number_format)
            sheet2.write(row2, 3, dpo, number_format)
 
            total_dpo_amount += total_amount
            total_dpo_weighted += total_weighted_val
 
            row2 += 1
 
        # ── Total row ────────────────────────────────────────────────
        sheet2.write(row2, 0, 'TOTAL', bold_grey)
        sheet2.write(row2, 1, total_dpo_amount, total_format)
        sheet2.write(row2, 2, total_dpo_weighted, total_format)

        # dpo total (optional but recommended)
        total_dpo = (total_dpo_weighted / total_dpo_amount) if total_dpo_amount else 0
        sheet2.write(row2, 3, total_dpo, total_format)
 
        # ============================================================
        # SHEET 3 → SUPPLIER PAYMENTS
        # ============================================================
        sheet3 = workbook.add_worksheet('Supplier Payments')
 
        for i in range(4):
            sheet3.set_column(i, i, 22)
 
        sheet3.merge_range(0, 0, 0, 3, 'SUPPLIER PAYMENTS', bold_grey)
 
        sheet3.write(1, 0, 'From', bold_grey)
        sheet3.write(1, 1, str(wizard.date_from), left)
 
        sheet3.write(2, 0, 'To', bold_grey)
        sheet3.write(2, 1, str(wizard.date_to), left)
 
        sheet3.write(3, 0, 'Branches', bold_grey)
        sheet3.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)
 
        sheet3.write(4, 0, 'Suppliers', bold_grey)
        sheet3.write(4, 1, ', '.join(wizard.supplier_ids.mapped('name')) or 'All', left)
 
        sheet3.write(5, 0, 'Exclude Legal Case', bold_grey)
        sheet3.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)
 
        headers3 = ['Supplier Code', 'Supplier Name', 'Payment Date', 'Payment Amount']
        for col, head in enumerate(headers3):
            sheet3.write(7, col, head, header_format)
 
        row3 = 8
        total_payment_amount = 0.0
 
        for payment in payments:
            partner = payment.partner_id
 
            if wizard.supplier_ids and partner not in wizard.supplier_ids:
                continue
            if wizard.exclude_legal_case and partner.legal_case:
                continue
 
            # payment_date_dt = convert_date(payment.date)
            payment_date_dt = convert_date(payment.payment_release_date)
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
 


# class DpoWorkingReportXlsx(models.AbstractModel):
#     _name = 'report.hr_payroll_report.dpo_working_report_xlsx'
#     _inherit = 'report.report_xlsx.abstract'

#     def generate_xlsx_report(self, workbook, data, wizard):

#         # ---------------- FORMATS ----------------
#         bold_grey = workbook.add_format({
#             'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3'
#         })

#         left = workbook.add_format({'align': 'left'})

#         header_format = workbook.add_format({
#             'bold': True, 'align': 'center', 'valign': 'vcenter',
#             'bg_color': '#002060', 'font_color': 'white', 'border': 1,
#         })

#         text_format = workbook.add_format({'border': 1})
#         number_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0.00'})
#         total_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'right', 'num_format': '#,##0.00'})
#         date_format = workbook.add_format({'border': 1, 'align': 'center', 'num_format': 'dd/mm/yyyy'})

#         outstanding_label_format = workbook.add_format({
#             'bold': True, 'align': 'center', 'valign': 'vcenter',
#             'bg_color': '#D3D3D3', 'border': 1, 'rotation': 90, 'text_wrap': True,
#         })

#         # ---------------- HELPER ----------------
#         def convert_date(d):
#             if not d:
#                 return None
#             return datetime.combine(d, datetime.min.time())

#         # ============================================================
#         # FETCH BILLS
#         # ============================================================
#         domain = [
#             ('invoice_date', '>=', wizard.date_from),
#             ('invoice_date', '<=', wizard.date_to),
#             ('state', '=', 'posted'),
#             ('move_type', '=', 'in_invoice'),
#         ]

#         if wizard.branch_ids:
#             domain.append(('branch_id', 'in', wizard.branch_ids.ids))

#         bills = self.env['account.move'].search(domain)

#         if wizard.supplier_ids:
#             bills = bills.filtered(lambda b: b.partner_id in wizard.supplier_ids)

#         if wizard.exclude_legal_case:
#             bills = bills.filtered(lambda b: not b.partner_id.legal_case)

#         if not bills:
#             return

#         bill_ids = bills.ids

#         # ============================================================
#         # RECONCILIATION
#         # ============================================================
#         reconciles = self.env['account.partial.reconcile'].search([
#             '|',
#             ('debit_move_id.move_id', 'in', bill_ids),
#             ('credit_move_id.move_id', 'in', bill_ids)
#         ])

#         payment_bill_map = {}
#         bill_payment_map = {}

#         for rec in reconciles:
#             debit = rec.debit_move_id
#             credit = rec.credit_move_id

#             bill = None
#             payment_move = None

#             if debit.move_id.move_type == 'in_invoice' and debit.move_id.id in bill_ids:
#                 bill = debit.move_id
#                 payment_move = credit.move_id
#             elif credit.move_id.move_type == 'in_invoice' and credit.move_id.id in bill_ids:
#                 bill = credit.move_id
#                 payment_move = debit.move_id
#             else:
#                 continue

#             if payment_move.payment_id:
#                 payment = payment_move.payment_id
#                 amt = rec.amount

#                 payment_bill_map.setdefault(payment.id, []).append({'bill': bill, 'amount': amt})
#                 bill_payment_map.setdefault(bill.id, []).append({'payment': payment, 'amount': amt})

#         payments = self.env['account.payment'].browse(list(payment_bill_map.keys()))

#         # ============================================================
#         # SHEET 1 → BILL REPORT
#         # ============================================================
#         sheet1 = workbook.add_worksheet('Bills')

#         for i in range(6):
#             sheet1.set_column(i, i, 20)

#         sheet1.merge_range(0, 0, 0, 5, 'BILL REPORT', bold_grey)

#         # Filters
#         sheet1.write(1, 0, 'From', bold_grey)
#         sheet1.write(1, 1, str(wizard.date_from), left)
#         sheet1.write(2, 0, 'To', bold_grey)
#         sheet1.write(2, 1, str(wizard.date_to), left)
#         sheet1.write(3, 0, 'Branches', bold_grey)
#         sheet1.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)
#         sheet1.write(4, 0, 'Suppliers', bold_grey)
#         sheet1.write(4, 1, ', '.join(wizard.supplier_ids.mapped('name')) or 'All', left)
#         sheet1.write(5, 0, 'Exclude Legal Case', bold_grey)
#         sheet1.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)

#         headers = ['Bill No', 'Supplier Code', 'Supplier Name', 'Branch', 'Bill Date', 'Bill Amount']
#         for col, h in enumerate(headers):
#             sheet1.write(7, col, h, header_format)

#         row = 8
#         total_bill = 0

#         for b in bills:
#             sheet1.write(row, 0, b.name or '', text_format)
#             sheet1.write(row, 1, b.partner_id.address_no or '', text_format)
#             sheet1.write(row, 2, b.partner_id.name or '', text_format)
#             sheet1.write(row, 3, b.branch_id.name or '', text_format)

#             if b.invoice_date:
#                 sheet1.write_datetime(row, 4, convert_date(b.invoice_date), date_format)

#             sheet1.write(row, 5, b.amount_total, number_format)

#             total_bill += b.amount_total
#             row += 1

#         sheet1.write(row, 4, 'Total', bold_grey)
#         sheet1.write(row, 5, total_bill, total_format)

#         # ============================================================
#         # SHEET 2 → DPO WORKINGS
#         # ============================================================
#         sheet2 = workbook.add_worksheet('DPO Workings')

#         for i in range(9):
#             sheet2.set_column(i, i, 22)

#         sheet2.merge_range(0, 0, 0, 8, 'DPO WORKINGS REPORT', bold_grey)

#         # Filters (FIXED)
#         sheet2.write(1, 0, 'From', bold_grey)
#         sheet2.write(1, 1, str(wizard.date_from), left)
#         sheet2.write(2, 0, 'To', bold_grey)
#         sheet2.write(2, 1, str(wizard.date_to), left)
#         sheet2.write(3, 0, 'Branches', bold_grey)
#         sheet2.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)
#         sheet2.write(4, 0, 'Suppliers', bold_grey)
#         sheet2.write(4, 1, ', '.join(wizard.supplier_ids.mapped('name')) or 'All', left)
#         sheet2.write(5, 0, 'Exclude Legal Case', bold_grey)
#         sheet2.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)

#         sheet2.merge_range(7, 0, 7, 8, 'Payment details & Workings', bold_grey)

#         headers = [
#             'Payment Ref', 'Supplier Name', 'Bill No',
#             'Bill Value', 'Bill Date', 'Payment Date',
#             'Paid Amount/Balance', 'Days', 'Weighted'
#         ]

#         for col, h in enumerate(headers):
#             sheet2.write(8, col, h, header_format)

#         row2 = 9
#         total_paid = 0
#         total_weighted = 0

#         for payment in payments:
#             for line in payment_bill_map.get(payment.id, []):
#                 bill = line['bill']
#                 amt = line['amount']

#                 days = (payment.date - bill.invoice_date).days if payment.date and bill.invoice_date else 0
#                 weighted = days * amt

#                 sheet2.write(row2, 0, payment.name or '', text_format)
#                 sheet2.write(row2, 1, bill.partner_id.name or '', text_format)
#                 sheet2.write(row2, 2, bill.name or '', text_format)
#                 sheet2.write(row2, 3, bill.amount_total, number_format)

#                 if bill.invoice_date:
#                     sheet2.write_datetime(row2, 4, convert_date(bill.invoice_date), date_format)

#                 if payment.date:
#                     sheet2.write_datetime(row2, 5, convert_date(payment.date), date_format)

#                 sheet2.write(row2, 6, amt, number_format)
#                 sheet2.write(row2, 7, days, number_format)
#                 sheet2.write(row2, 8, weighted, number_format)

#                 total_paid += amt
#                 total_weighted += weighted
#                 row2 += 1

#         # Outstanding (same ACP logic)
#         today = date.today()
#         today_dt = datetime.combine(today, datetime.min.time())

#         row2 += 1
#         start = row2

#         outstanding = bills.filtered(lambda b: b.amount_residual > 0)

#         for b in outstanding:
#             bal = b.amount_residual
#             days = (today - b.invoice_date).days if b.invoice_date else 0
#             weighted = days * bal

#             sheet2.write(row2, 1, b.partner_id.name or '', text_format)
#             sheet2.write(row2, 2, b.name or '', text_format)
#             sheet2.write(row2, 3, b.amount_total, number_format)
#             sheet2.write_datetime(row2, 4, convert_date(b.invoice_date), date_format)
#             sheet2.write_datetime(row2, 5, today_dt, date_format)
#             sheet2.write(row2, 6, bal, number_format)
#             sheet2.write(row2, 7, days, number_format)
#             sheet2.write(row2, 8, weighted, number_format)

#             total_paid += bal
#             total_weighted += weighted
#             row2 += 1

#         end = row2 - 1

#         sheet2.merge_range(start, 0, end, 0, 'Outstanding Payable Invoices', outstanding_label_format)

#         # Grand Total
#         row2 += 1
#         sheet2.write(row2, 5, 'GRAND TOTAL', bold_grey)
#         sheet2.write(row2, 6, total_paid, total_format)
#         sheet2.write(row2, 8, total_weighted, total_format)

#         # ============================================================
#         # DPO CALCULATION (FIXED)
#         # ============================================================
#         row2 += 2
#         sheet2.merge_range(row2, 0, row2, 3, 'DPO CALCULATIONS', bold_grey)
#         row2 += 1

#         headers = ['Supplier', 'Total Amount', 'Weighted', 'DPO (Days)']
#         for col, h in enumerate(headers):
#             sheet2.write(row2, col, h, header_format)

#         row2 += 1

#         supplier_map = {}

#         for bill in bills:
#             for pay in bill_payment_map.get(bill.id, []):
#                 payment = pay['payment']
#                 amt = pay['amount']

#                 days = (payment.date - bill.invoice_date).days if payment.date and bill.invoice_date else 0
#                 weighted = days * amt

#                 supplier_map.setdefault(bill.partner_id.id, {
#                     'name': bill.partner_id.name,
#                     'amount': 0,
#                     'weighted': 0
#                 })

#                 supplier_map[bill.partner_id.id]['amount'] += amt
#                 supplier_map[bill.partner_id.id]['weighted'] += weighted

#         for sup in supplier_map.values():
#             dpo = sup['weighted'] / sup['amount'] if sup['amount'] else 0

#             sheet2.write(row2, 0, sup['name'], text_format)
#             sheet2.write(row2, 1, sup['amount'], number_format)
#             sheet2.write(row2, 2, sup['weighted'], number_format)
#             sheet2.write(row2, 3, dpo, number_format)
#             row2 += 1

#         # ============================================================
#         # SHEET 3 → SUPPLIER PAYMENTS
#         # ============================================================
#         sheet3 = workbook.add_worksheet('Supplier Payments')

#         for i in range(4):
#             sheet3.set_column(i, i, 22)

#         sheet3.merge_range(0, 0, 0, 3, 'SUPPLIER PAYMENTS', bold_grey)

#         # Filters (FIXED)
#         sheet3.write(1, 0, 'From', bold_grey)
#         sheet3.write(1, 1, str(wizard.date_from), left)
#         sheet3.write(2, 0, 'To', bold_grey)
#         sheet3.write(2, 1, str(wizard.date_to), left)
#         sheet3.write(3, 0, 'Branches', bold_grey)
#         sheet3.write(3, 1, ', '.join(wizard.branch_ids.mapped('name')) or 'All', left)
#         sheet3.write(4, 0, 'Suppliers', bold_grey)
#         sheet3.write(4, 1, ', '.join(wizard.supplier_ids.mapped('name')) or 'All', left)
#         sheet3.write(5, 0, 'Exclude Legal Case', bold_grey)
#         sheet3.write(5, 1, 'Yes' if wizard.exclude_legal_case else 'No', left)

#         headers = ['Supplier Code', 'Supplier Name', 'Payment Date', 'Payment Amount']

#         for col, h in enumerate(headers):
#             sheet3.write(7, col, h, header_format)

#         row3 = 8
#         total = 0

#         for payment in payments:
#             partner = payment.partner_id

#             if wizard.supplier_ids and partner not in wizard.supplier_ids:
#                 continue
#             if wizard.exclude_legal_case and partner.legal_case:
#                 continue

#             if payment.date:
#                 sheet3.write_datetime(row3, 2, convert_date(payment.date), date_format)

#             sheet3.write(row3, 0, partner.address_no or '', text_format)
#             sheet3.write(row3, 1, partner.name or '', text_format)
#             sheet3.write(row3, 3, payment.amount, number_format)

#             total += payment.amount
#             row3 += 1

#         sheet3.write(row3, 2, 'TOTAL', bold_grey)
#         sheet3.write(row3, 3, total, total_format)