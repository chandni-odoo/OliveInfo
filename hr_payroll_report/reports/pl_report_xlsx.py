from odoo import models
from datetime import date, datetime

# class PLReportXlsx(models.AbstractModel):
#     _name = 'report.hr_payroll_report.pl_report_xlsx'
#     _inherit = 'report.report_xlsx.abstract'
 
#     def generate_xlsx_report(self, workbook, data, wizard):
 
#         sheet = workbook.add_worksheet('P&L Report')
 
#         # ─────────────────────────────────────────
#         # FORMATS
#         # ─────────────────────────────────────────
#         num_fmt     = '#,##0.00;(#,##0.00)'
#         num_fmt_red = '#,##0.00;[RED](#,##0.00)'
#         pct_fmt     = '0%;[RED]-0%'
 
#         # ── Base header (dark blue) ──────────────
#         fmt_header = workbook.add_format({
#             'bold': True, 'align': 'center', 'valign': 'vcenter',
#             'font_color': '#FFFFFF', 'bg_color': '#002060',
#             'border': 1, 'border_color': '#000000',
#         })
 
#         # ── Yellow year header ───────────────────
#         fmt_header_yr = workbook.add_format({
#             'bold': True, 'align': 'center', 'valign': 'vcenter',
#             'font_color': '#000000', 'bg_color': '#FFFF00',
#             'border': 1, 'border_color': '#000000',
#         })
 
#         # ── Purple comparative header ────────────
#         fmt_header_cmp = workbook.add_format({
#             'bold': True, 'align': 'center', 'valign': 'vcenter',
#             'font_color': '#FFFFFF', 'bg_color': '#7030A0',
#             'border': 1, 'border_color': '#000000',
#         })
 
#         # ── Sub-header (A, B, C, D=A-B …) ───────
#         fmt_subhdr = workbook.add_format({
#             'bold': True, 'align': 'center', 'valign': 'vcenter',
#             'font_color': '#000000', 'bg_color': '#D9D9D9',
#             'border': 1, 'border_color': '#000000',
#         })
 
#         fmt_title = workbook.add_format({
#             'bold': True, 'align': 'center', 'font_size': 13,
#         })
#         fmt_label = workbook.add_format({'bold': True})
 
#         # ── Regular data rows ────────────────────
#         fmt_row_label = workbook.add_format({
#             'border': 1, 'border_color': '#D0D0D0',
#         })
#         fmt_row_num = workbook.add_format({
#             'num_format': num_fmt,
#             'border': 1, 'border_color': '#D0D0D0', 'align': 'right',
#         })
#         fmt_row_num_red = workbook.add_format({
#             'num_format': num_fmt_red,
#             'border': 1, 'border_color': '#D0D0D0', 'align': 'right',
#         })
 
#         # ── Change columns (D, F) ─────────────────
#         fmt_chg_num = workbook.add_format({
#             'num_format': '#,##0.00;[RED](#,##0.00)',
#             'border': 1, 'border_color': '#D0D0D0', 'align': 'right',
#         })
#         fmt_chg_pct = workbook.add_format({
#             'num_format': pct_fmt,
#             'border': 1, 'border_color': '#D0D0D0', 'align': 'right',
#         })
 
#         # ── Net Revenue row ──────────────────────
#         _net_bg = '#BDD7EE'
#         fmt_net_label = workbook.add_format({
#             'bold': True, 'bg_color': _net_bg,
#             'border': 1, 'border_color': '#000000',
#         })
#         fmt_net_num = workbook.add_format({
#             'bold': True, 'num_format': num_fmt, 'bg_color': _net_bg,
#             'border': 1, 'border_color': '#000000', 'align': 'right',
#         })
#         fmt_net_chg = workbook.add_format({
#             'bold': True, 'num_format': '#,##0.00;[RED](#,##0.00)', 'bg_color': _net_bg,
#             'border': 1, 'border_color': '#000000', 'align': 'right',
#         })
#         fmt_net_pct = workbook.add_format({
#             'bold': True, 'num_format': pct_fmt, 'bg_color': _net_bg,
#             'border': 1, 'border_color': '#000000', 'align': 'right',
#         })
 
#         # ── Grand Total 1 row ────────────────────
#         _gt_bg = '#FCE4D6'
#         fmt_gt_label = workbook.add_format({
#             'bold': True, 'bg_color': _gt_bg,
#             'border': 1, 'border_color': '#000000',
#         })
#         fmt_gt_num = workbook.add_format({
#             'bold': True, 'num_format': num_fmt, 'bg_color': _gt_bg,
#             'border': 1, 'border_color': '#000000', 'align': 'right',
#         })
#         fmt_gt_chg = workbook.add_format({
#             'bold': True, 'num_format': '#,##0.00;[RED](#,##0.00)', 'bg_color': _gt_bg,
#             'border': 1, 'border_color': '#000000', 'align': 'right',
#         })
#         fmt_gt_pct = workbook.add_format({
#             'bold': True, 'num_format': pct_fmt, 'bg_color': _gt_bg,
#             'border': 1, 'border_color': '#000000', 'align': 'right',
#         })
 
#         # ── Grand Total 2 row (red border) ───────
#         fmt_gt2_label = workbook.add_format({
#             'bold': True, 'bg_color': _gt_bg,
#             'border': 2, 'border_color': '#FF0000',
#         })
#         fmt_gt2_num = workbook.add_format({
#             'bold': True, 'num_format': num_fmt, 'bg_color': _gt_bg,
#             'border': 2, 'border_color': '#FF0000', 'align': 'right',
#         })
#         fmt_gt2_chg = workbook.add_format({
#             'bold': True, 'num_format': '#,##0.00;[RED](#,##0.00)', 'bg_color': _gt_bg,
#             'border': 2, 'border_color': '#FF0000', 'align': 'right',
#         })
#         fmt_gt2_pct = workbook.add_format({
#             'bold': True, 'num_format': pct_fmt, 'bg_color': _gt_bg,
#             'border': 2, 'border_color': '#FF0000', 'align': 'right',
#         })
 
#         # ── Net Profit for the Year (cyan) ────────
#         _np_bg = '#00B0F0'
#         fmt_np_label = workbook.add_format({
#             'bold': True, 'bg_color': _np_bg,
#             'border': 1, 'border_color': '#000000',
#         })
#         fmt_np_num = workbook.add_format({
#             'bold': True, 'num_format': num_fmt, 'bg_color': _np_bg,
#             'border': 1, 'border_color': '#000000', 'align': 'right',
#         })
#         fmt_np_chg = workbook.add_format({
#             'bold': True, 'num_format': '#,##0.00;[RED](#,##0.00)', 'bg_color': _np_bg,
#             'border': 1, 'border_color': '#000000', 'align': 'right',
#         })
#         fmt_np_pct = workbook.add_format({
#             'bold': True, 'num_format': pct_fmt, 'bg_color': _np_bg,
#             'border': 1, 'border_color': '#000000', 'align': 'right',
#         })
 
#         # ── Net Profit / Loss (light blue) ────────
#         fmt_npl_label = workbook.add_format({
#             'bold': True, 'border': 1, 'border_color': '#000000', 'bg_color': _net_bg,
#         })
#         fmt_npl_num = workbook.add_format({
#             'bold': True, 'num_format': num_fmt,
#             'border': 1, 'border_color': '#000000', 'align': 'right', 'bg_color': _net_bg,
#         })
#         fmt_npl_chg = workbook.add_format({
#             'bold': True, 'num_format': '#,##0.00;[RED](#,##0.00)',
#             'border': 1, 'border_color': '#000000', 'align': 'right', 'bg_color': _net_bg,
#         })
#         fmt_npl_pct = workbook.add_format({
#             'bold': True, 'num_format': pct_fmt,
#             'border': 1, 'border_color': '#000000', 'align': 'right', 'bg_color': _net_bg,
#         })
 
#         # ── Empty cell ────────────────────────────
#         fmt_empty = workbook.add_format({
#             'border': 1, 'border_color': '#D0D0D0',
#         })
 
#         # ─────────────────────────────────────────
#         # FILTER DATA
#         # ─────────────────────────────────────────
#         report_date  = datetime.strptime(data['date'], "%Y-%m-%d").date()
#         companies    = data['company_ids'] or self.env.companies.ids
#         current_year = report_date.year
#         years        = [current_year, current_year - 1, current_year - 2]
#         n            = len(years)   # always 3
 
#         # Column layout (0-indexed):
#         # 0=Particulars | 1=A(yr0) | 2=B(yr1) | 3=C(yr2) | 4=D=A-B | 5=E=D/B% | 6=F=B-C | 7=G=F/C%
#         COL_PART = 0
#         COL_A    = 1   # current year
#         COL_B    = 2   # current-1
#         COL_C    = 3   # current-2
#         COL_D    = 4   # absolute change AB
#         COL_E    = 5   # pct change AB
#         COL_F    = 6   # absolute change BC
#         COL_G    = 7   # pct change BC
#         TOTAL_COLS = 8
 
#         # ─────────────────────────────────────────
#         # COLUMN WIDTHS
#         # ─────────────────────────────────────────
#         sheet.set_column(COL_PART, COL_PART, 38)
#         sheet.set_column(COL_A, COL_C, 18)
#         sheet.set_column(COL_D, COL_G, 16)
 
#         # ─────────────────────────────────────────
#         # TITLE & META
#         # ─────────────────────────────────────────
#         sheet.merge_range(0, 0, 0, TOTAL_COLS - 1,
#                           'Comparative Profit & Loss Report', fmt_title) 
#         sheet.write(
#             2, 0,
#             'COMPARATIVE PROFIT & LOSS FOR {}, {} & {}'.format(
#                 years[0], years[1], years[2]
#             )
#         )
#         sheet.write(
#             2,
#             1,
#             'AS ON {}'.format(report_date.strftime('%d/%m/%y'))
#         )
#         sheet.write(3, 0, 'Companies:', fmt_label)
#         sheet.write(3, 1, ', '.join(
#             self.env['res.company'].browse(companies).mapped('name')
#         ))
 
#         # ─────────────────────────────────────────
#         # HEADER ROW 1: Comparative group labels
#         # Row layout (3 rows total):
#         #   Row 1: Particulars(merged) | blank | blank | blank | COM.2025&2024 | COM.2024&2023
#         #   Row 2: Particulars(merged) | A     | B     | C     | D=A-B | E=D/B*100 | F=B-C | G=F/C*100
#         #   Row 3: Particulars(merged) | 2025  | 2024  | 2023  | Absolute Change | % Change | Absolute Change | % Change
#         # ─────────────────────────────────────────
#         row = 5
 
#         # Particulars: merged across all 3 header rows
#         sheet.merge_range(row, COL_PART, row + 2, COL_PART, 'Particulars', fmt_header)
 
#         # Row 1: blank for year cols, comparative labels for D-G
#         sheet.write(row, COL_A, '', fmt_header)
#         sheet.write(row, COL_B, '', fmt_header)
#         sheet.write(row, COL_C, '', fmt_header)
#         cmp_label_1 = 'COM. FOR {} & {}'.format(years[0], years[1])
#         cmp_label_2 = 'COM. FOR {} & {}'.format(years[1], years[2])
#         sheet.merge_range(row, COL_D, row, COL_E, cmp_label_1, fmt_header_cmp)
#         sheet.merge_range(row, COL_F, row, COL_G, cmp_label_2, fmt_header_cmp)
 
#         # ─────────────────────────────────────────
#         # HEADER ROW 2: A, B, C labels + formula labels
#         # ─────────────────────────────────────────
#         row += 1
#         sheet.write(row, COL_A, 'A', fmt_subhdr)
#         sheet.write(row, COL_B, 'B', fmt_subhdr)
#         sheet.write(row, COL_C, 'C', fmt_subhdr)
#         sheet.write(row, COL_D, 'D = A-B',   fmt_subhdr)
#         sheet.write(row, COL_E, 'E=D/B*100', fmt_subhdr)
#         sheet.write(row, COL_F, 'F =B-C',    fmt_subhdr)
#         sheet.write(row, COL_G, 'G=F/C*100', fmt_subhdr)
 
#         # ─────────────────────────────────────────
#         # HEADER ROW 3: Year values + column labels
#         # ─────────────────────────────────────────
#         row += 1
#         sheet.write(row, COL_A, str(years[0]), fmt_header_yr)
#         sheet.write(row, COL_B, str(years[1]), fmt_header_yr)
#         sheet.write(row, COL_C, str(years[2]), fmt_header_yr)
#         sheet.write(row, COL_D, 'Absolute\nChange',    fmt_header)
#         sheet.write(row, COL_E, 'Percentage\nChange',  fmt_header)
#         sheet.write(row, COL_F, 'Absolute\nChange',    fmt_header)
#         sheet.write(row, COL_G, 'Percentage\nChange',  fmt_header)
 
#         # Set row heights for header rows
#         sheet.set_row(row - 2, 18)
#         sheet.set_row(row - 1, 18)
#         sheet.set_row(row,     30)
 
#         row += 1
 
#         # ─────────────────────────────────────────
#         # FETCH ALL GROUPS
#         # ─────────────────────────────────────────
#         groups = self.env['pl.group'].search([], order='code')
 
#         # ─────────────────────────────────────────
#         # PRE-COMPUTE ALL AMOUNTS PER GROUP PER YEAR
#         # ─────────────────────────────────────────
#         group_amounts = {}  # {group.id: [amt_yr0, amt_yr1, amt_yr2]}
 
#         for group in groups:
#             amounts = []
#             for yr in years:
#                 start_date = datetime(yr, 1, 1).date()
#                 end_date   = datetime(yr, report_date.month, report_date.day).date()
#                 domain = [
#                     ('date', '>=', start_date),
#                     ('date', '<=', end_date),
#                     ('company_id', 'in', companies),
#                     ('account_id.pl_group_id', '=', group.id),
#                     ('move_id.state', 'in', ['draft', 'posted']),
#                 ]
#                 lines = self.env['account.move.line'].search(domain)
#                 amounts.append(sum(lines.mapped('balance')) * -1)
#             group_amounts[group.id] = amounts
 
#         # ─────────────────────────────────────────
#         # ACCUMULATORS
#         # ─────────────────────────────────────────
#         before_net     = [0.0] * n
#         first_section  = [0.0] * n
#         second_section = [0.0] * n
 
#         net_revenue_vals   = [0.0] * n
#         grand_total_first  = [0.0] * n
#         grand_total_second = [0.0] * n
 
#         # ─────────────────────────────────────────
#         # PASS 1: CALCULATE TOTALS
#         # ─────────────────────────────────────────
#         _state = 0
#         for group in groups:
#             if group.is_net_revenue:
#                 net_revenue_vals = list(before_net)
#                 _state = 1
#             elif group.is_grand_total:
#                 if _state == 1:
#                     grand_total_first = list(first_section)
#                     _state = 2
#                 elif _state == 2:
#                     grand_total_second = list(second_section)
#                     _state = 3
#             else:
#                 for col in range(n):
#                     amt = group_amounts[group.id][col]
#                     if _state == 0:
#                         before_net[col] += amt
#                     elif _state == 1:
#                         first_section[col] += amt
#                     elif _state == 2:
#                         second_section[col] += amt
 
#         # ─────────────────────────────────────────
#         # HELPER: write a full data row (7 values)
#         # ─────────────────────────────────────────
#         def _safe_pct(numerator, denominator):
#             """Return percentage as decimal (e.g. 0.06 for 6%) or 0 if div-by-zero."""
#             if denominator and denominator != 0:
#                 return numerator / denominator
#             return 0.0
 
#         def write_row(r, label, vals,
#                       lbl_fmt, num_fmt_val, chg_fmt, pct_fmt_val):
#             """Write label + A, B, C, D, E, F, G columns."""
#             a, b, c = vals[0], vals[1], vals[2]
#             d = a - b
#             e = _safe_pct(d, b)
#             f = b - c
#             g = _safe_pct(f, c)
 
#             sheet.write(r, COL_PART, label,  lbl_fmt)
#             sheet.write(r, COL_A,    a,       num_fmt_val)
#             sheet.write(r, COL_B,    b,       num_fmt_val)
#             sheet.write(r, COL_C,    c,       num_fmt_val)
#             sheet.write(r, COL_D,    d,       chg_fmt)
#             sheet.write(r, COL_E,    e,       pct_fmt_val)
#             sheet.write(r, COL_F,    f,       chg_fmt)
#             sheet.write(r, COL_G,    g,       pct_fmt_val)
 
#         def write_empty_row(r):
#             for c in range(TOTAL_COLS):
#                 sheet.write(r, c, '', fmt_empty)
 
#         # ─────────────────────────────────────────
#         # PASS 2: RENDER ROWS
#         # ─────────────────────────────────────────
#         state = 0
 
#         for group in groups:
 
#             # ── NET REVENUE ROW ──────────────────
#             if group.is_net_revenue:
#                 write_row(row, group.name, net_revenue_vals,
#                           fmt_net_label, fmt_net_num, fmt_net_chg, fmt_net_pct)
#                 row += 1
#                 state = 1
#                 continue
 
#             # ── GRAND TOTAL ROWS ─────────────────
#             if group.is_grand_total:
 
#                 if state == 1:
#                     # First Grand Total
#                     write_row(row, group.name, grand_total_first,
#                               fmt_gt_label, fmt_gt_num, fmt_gt_chg, fmt_gt_pct)
#                     row += 1
 
#                     # Net profit for the year
#                     np_vals = [net_revenue_vals[i] + grand_total_first[i] for i in range(n)]
#                     write_row(row, 'Net profit for the year', np_vals,
#                               fmt_np_label, fmt_np_num, fmt_np_chg, fmt_np_pct)
#                     row += 1
 
#                     # Spacer
#                     write_empty_row(row)
#                     row += 1
 
#                     state = 2
 
#                 elif state == 2:
#                     # Second Grand Total
#                     write_row(row, group.name, grand_total_second,
#                               fmt_gt2_label, fmt_gt2_num, fmt_gt2_chg, fmt_gt2_pct)
#                     row += 1
 
#                     # Net Profit / Loss
#                     npl_vals = [
#                         net_revenue_vals[i] + grand_total_first[i] + grand_total_second[i]
#                         for i in range(n)
#                     ]
#                     write_row(row, 'Net Profit/ Loss', npl_vals,
#                               fmt_npl_label, fmt_npl_num, fmt_npl_chg, fmt_npl_pct)
#                     row += 1
 
#                     state = 3
 
#                 continue
 
#             # ── REGULAR GROUP ROW ─────────────────
#             _nf = fmt_row_num_red if state == 2 else fmt_row_num
#             write_row(row, group.name, group_amounts[group.id],
#                       fmt_row_label, _nf, fmt_chg_num, fmt_chg_pct)
#             row += 1
 
#         # ─────────────────────────────────────────
#         # SAFETY NET: missing second GT group
#         # ─────────────────────────────────────────
#         if state == 2:
#             grand_total_second = list(second_section)
 
#             write_row(row, 'Grand Total', grand_total_second,
#                       fmt_gt2_label, fmt_gt2_num, fmt_gt2_chg, fmt_gt2_pct)
#             row += 1
 
#             npl_vals = [
#                 net_revenue_vals[i] + grand_total_first[i] + grand_total_second[i]
#                 for i in range(n)
#             ]
#             write_row(row, 'Net Profit/ Loss', npl_vals,
#                       fmt_npl_label, fmt_npl_num, fmt_npl_chg, fmt_npl_pct)
#             row += 1


class PLReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.pl_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    # ═══════════════════════════════════════════════
    # NEW: helper to build a safe Excel sheet tab name
    # ═══════════════════════════════════════════════
    def _safe_sheet_name(self, name):
        """Excel sheet names: max 31 chars, no [ ] : * ? / \\ """
        invalid_chars = ['[', ']', ':', '*', '?', '/', '\\']
        for ch in invalid_chars:
            name = name.replace(ch, '')
        name = name.strip()
        return name[:31] if name else 'Schedule'
    
    def _clean(self, value):
        """Coerce a value into something xlsxwriter can safely write as text.
        Guards against False/None/bare-ids/tuples slipping through, which can
        otherwise corrupt the shared-strings table and crash at
        workbook.close() with 'TypeError: expected string or bytes-like object'.
        """
        if value is False or value is None:
            return ''
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, (list, tuple)):
            return value[1] if len(value) > 1 else ''
        if not isinstance(value, str):
            return str(value)
        return value

    # ═══════════════════════════════════════════════
    # NEW: fetch account-level breakdown for one pl.group
    # per account, per company, for each of the 3 years
    # ═══════════════════════════════════════════════
    def _get_account_details(self, group, companies, years, report_date):
        AccountMoveLine = self.env['account.move.line']
        details = {}  # {(account_id, company_id): {...}}

        for idx, yr in enumerate(years):
            start_date = datetime(yr, 1, 1).date()
            end_date = datetime(yr, report_date.month, report_date.day).date()
            domain = [
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('company_id', 'in', companies),
                ('account_id.pl_group_id', '=', group.id),
                ('move_id.state', 'in', ['draft', 'posted']),
            ]
            read_group_res = AccountMoveLine.read_group(
                domain,
                ['balance:sum'],
                ['account_id', 'company_id'],
                lazy=False,
            )
            for res in read_group_res:
                account = res.get('account_id')
                company = res.get('company_id')
                if not account or not company:
                    continue

                # Defensive: read_group group-keys for many2one fields should be
                # (id, display_name) tuples, but a record-rule/access issue on a
                # second company can occasionally return a bare id instead.
                if isinstance(account, (list, tuple)) and len(account) > 1:
                    account_id, account_name = account[0], account[1]
                else:
                    account_id = account[0] if isinstance(account, (list, tuple)) else account
                    acc_rec = self.env['account.account'].browse(account_id)
                    account_name = '[{}] {}'.format(acc_rec.code or '', acc_rec.name or '')

                if isinstance(company, (list, tuple)) and len(company) > 1:
                    company_id, company_name = company[0], company[1]
                else:
                    company_id = company[0] if isinstance(company, (list, tuple)) else company
                    company_name = self.env['res.company'].browse(company_id).name or ''

                key = (account_id, company_id)

                if key not in details:
                    # read_group's account_id label is usually "[CODE] Name"
                    if ']' in account_name and account_name.startswith('['):
                        code = account_name.split(']')[0][1:]
                        name = account_name.split(']', 1)[1].strip()
                    else:
                        acc_rec = self.env['account.account'].browse(account_id)
                        code = acc_rec.code
                        name = acc_rec.name
                    details[key] = {
                        'code': code,
                        'name': name,
                        'company': company_name,
                        'amounts': [0.0] * len(years),
                    }

                details[key]['amounts'][idx] = (res.get('balance') or 0.0) * -1

        # sort by account code, then company, to match main-report convention
        rows = sorted(
            details.values(),
            key=lambda d: ((d['code'] or ''), (d['company'] or ''))
        )
        return rows

    # ═══════════════════════════════════════════════
    # NEW: render one schedule sheet for a single group
    # Layout: Code | Account name | Company | Y0 | Y1 | Y2
    # ═══════════════════════════════════════════════
    def _write_schedule_sheet(self, workbook, group, companies, years, report_date,
                               fmt_title, fmt_header, fmt_label,
                               fmt_row_label, fmt_row_num,
                               fmt_gt_label, fmt_gt_num):
        sheet_name = self._safe_sheet_name(group.name or 'Group')
        sheet = workbook.add_worksheet(sheet_name)

        COL_CODE = 0
        COL_NAME = 1
        COL_COMPANY = 2
        COL_Y0 = 3
        COL_Y1 = 4
        COL_Y2 = 5
        TOTAL_COLS = 6

        sheet.set_column(COL_CODE, COL_CODE, 12)
        sheet.set_column(COL_NAME, COL_NAME, 35)
        sheet.set_column(COL_COMPANY, COL_COMPANY, 25)
        sheet.set_column(COL_Y0, COL_Y2, 18)

        # ── Title & meta (mirrors main sheet) ────────
        sheet.merge_range(0, 0, 0, TOTAL_COLS - 1,
                           'Comparative Profit & Loss Report', fmt_title)
        sheet.write(1, 2, 'Schedule for {}'.format(self._clean(group.name)))

        sheet.write(2, 0, 'COMPARATIVE FOR {}, {} & {}'.format(
            years[0], years[1], years[2]))
        sheet.write(2, 1, 'AS ON {}'.format(report_date.strftime('%d/%m/%y')))
        sheet.write(3, 0, 'Companies:', fmt_label)
        sheet.write(3, 1, ', '.join(self.env['res.company'].browse(companies).mapped(lambda c: c.name or '')))

        # ── Header row ────────────────────────────────
        row = 5
        sheet.write(row, COL_CODE, 'Code', fmt_header)
        sheet.write(row, COL_NAME, 'Account Name', fmt_header)
        sheet.write(row, COL_COMPANY, 'Company', fmt_header)
        sheet.write(row, COL_Y0, str(years[0]), fmt_header)
        sheet.write(row, COL_Y1, str(years[1]), fmt_header)
        sheet.write(row, COL_Y2, str(years[2]), fmt_header)
        row += 1

        # ── Data rows ─────────────────────────────────
        details = self._get_account_details(group, companies, years, report_date)
        totals = [0.0] * len(years)

        for rec in details:
            sheet.write(row, COL_CODE, self._clean(rec.get('code')), fmt_row_label)
            sheet.write(row, COL_NAME, self._clean(rec.get('name')), fmt_row_label)
            sheet.write(row, COL_COMPANY, self._clean(rec.get('company')), fmt_row_label)
            for i, amt in enumerate(rec['amounts']):
                sheet.write(row, COL_Y0 + i, amt, fmt_row_num)
                totals[i] += amt
            row += 1

        if not details:
            sheet.write(row, COL_CODE, 'No data for this group', fmt_row_label)
            row += 1

        # ── Total row ─────────────────────────────────
        sheet.merge_range(row, COL_CODE, row, COL_COMPANY, 'Total', fmt_gt_label)
        for i, amt in enumerate(totals):
            sheet.write(row, COL_Y0 + i, amt, fmt_gt_num)

    def generate_xlsx_report(self, workbook, data, wizard):

        sheet = workbook.add_worksheet('P&L Report')

        # ─────────────────────────────────────────
        # FORMATS
        # ─────────────────────────────────────────
        num_fmt     = '#,##0.00;(#,##0.00)'
        num_fmt_red = '#,##0.00;[RED](#,##0.00)'
        pct_fmt     = '0%;[RED]-0%'

        # ── Base header (dark blue) ──────────────
        fmt_header = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'font_color': '#FFFFFF', 'bg_color': '#002060',
            'border': 1, 'border_color': '#000000',
        })

        # ── Yellow year header ───────────────────
        fmt_header_yr = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'font_color': '#000000', 'bg_color': '#FFFF00',
            'border': 1, 'border_color': '#000000',
        })

        # ── Purple comparative header ────────────
        fmt_header_cmp = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'font_color': '#FFFFFF', 'bg_color': '#7030A0',
            'border': 1, 'border_color': '#000000',
        })

        # ── Sub-header (A, B, C, D=A-B …) ───────
        fmt_subhdr = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'font_color': '#000000', 'bg_color': '#D9D9D9',
            'border': 1, 'border_color': '#000000',
        })

        fmt_title = workbook.add_format({
            'bold': True, 'align': 'center', 'font_size': 13,
        })
        fmt_label = workbook.add_format({'bold': True})

        # ── Regular data rows ────────────────────
        fmt_row_label = workbook.add_format({
            'border': 1, 'border_color': '#D0D0D0',
        })
        fmt_row_num = workbook.add_format({
            'num_format': num_fmt,
            'border': 1, 'border_color': '#D0D0D0', 'align': 'right',
        })
        fmt_row_num_red = workbook.add_format({
            'num_format': num_fmt_red,
            'border': 1, 'border_color': '#D0D0D0', 'align': 'right',
        })

        # ── Change columns (D, F) ─────────────────
        fmt_chg_num = workbook.add_format({
            'num_format': '#,##0.00;[RED](#,##0.00)',
            'border': 1, 'border_color': '#D0D0D0', 'align': 'right',
        })
        fmt_chg_pct = workbook.add_format({
            'num_format': pct_fmt,
            'border': 1, 'border_color': '#D0D0D0', 'align': 'right',
        })

        # ── Net Revenue row ──────────────────────
        _net_bg = '#BDD7EE'
        fmt_net_label = workbook.add_format({
            'bold': True, 'bg_color': _net_bg,
            'border': 1, 'border_color': '#000000',
        })
        fmt_net_num = workbook.add_format({
            'bold': True, 'num_format': num_fmt, 'bg_color': _net_bg,
            'border': 1, 'border_color': '#000000', 'align': 'right',
        })
        fmt_net_chg = workbook.add_format({
            'bold': True, 'num_format': '#,##0.00;[RED](#,##0.00)', 'bg_color': _net_bg,
            'border': 1, 'border_color': '#000000', 'align': 'right',
        })
        fmt_net_pct = workbook.add_format({
            'bold': True, 'num_format': pct_fmt, 'bg_color': _net_bg,
            'border': 1, 'border_color': '#000000', 'align': 'right',
        })

        # ── Grand Total 1 row ────────────────────
        _gt_bg = '#FCE4D6'
        fmt_gt_label = workbook.add_format({
            'bold': True, 'bg_color': _gt_bg,
            'border': 1, 'border_color': '#000000',
        })
        fmt_gt_num = workbook.add_format({
            'bold': True, 'num_format': num_fmt, 'bg_color': _gt_bg,
            'border': 1, 'border_color': '#000000', 'align': 'right',
        })
        fmt_gt_chg = workbook.add_format({
            'bold': True, 'num_format': '#,##0.00;[RED](#,##0.00)', 'bg_color': _gt_bg,
            'border': 1, 'border_color': '#000000', 'align': 'right',
        })
        fmt_gt_pct = workbook.add_format({
            'bold': True, 'num_format': pct_fmt, 'bg_color': _gt_bg,
            'border': 1, 'border_color': '#000000', 'align': 'right',
        })

        # ── Grand Total 2 row (red border) ───────
        fmt_gt2_label = workbook.add_format({
            'bold': True, 'bg_color': _gt_bg,
            'border': 2, 'border_color': '#FF0000',
        })
        fmt_gt2_num = workbook.add_format({
            'bold': True, 'num_format': num_fmt, 'bg_color': _gt_bg,
            'border': 2, 'border_color': '#FF0000', 'align': 'right',
        })
        fmt_gt2_chg = workbook.add_format({
            'bold': True, 'num_format': '#,##0.00;[RED](#,##0.00)', 'bg_color': _gt_bg,
            'border': 2, 'border_color': '#FF0000', 'align': 'right',
        })
        fmt_gt2_pct = workbook.add_format({
            'bold': True, 'num_format': pct_fmt, 'bg_color': _gt_bg,
            'border': 2, 'border_color': '#FF0000', 'align': 'right',
        })

        # ── Net Profit for the Year (cyan) ────────
        _np_bg = '#00B0F0'
        fmt_np_label = workbook.add_format({
            'bold': True, 'bg_color': _np_bg,
            'border': 1, 'border_color': '#000000',
        })
        fmt_np_num = workbook.add_format({
            'bold': True, 'num_format': num_fmt, 'bg_color': _np_bg,
            'border': 1, 'border_color': '#000000', 'align': 'right',
        })
        fmt_np_chg = workbook.add_format({
            'bold': True, 'num_format': '#,##0.00;[RED](#,##0.00)', 'bg_color': _np_bg,
            'border': 1, 'border_color': '#000000', 'align': 'right',
        })
        fmt_np_pct = workbook.add_format({
            'bold': True, 'num_format': pct_fmt, 'bg_color': _np_bg,
            'border': 1, 'border_color': '#000000', 'align': 'right',
        })

        # ── Net Profit / Loss (light blue) ────────
        fmt_npl_label = workbook.add_format({
            'bold': True, 'border': 1, 'border_color': '#000000', 'bg_color': _net_bg,
        })
        fmt_npl_num = workbook.add_format({
            'bold': True, 'num_format': num_fmt,
            'border': 1, 'border_color': '#000000', 'align': 'right', 'bg_color': _net_bg,
        })
        fmt_npl_chg = workbook.add_format({
            'bold': True, 'num_format': '#,##0.00;[RED](#,##0.00)',
            'border': 1, 'border_color': '#000000', 'align': 'right', 'bg_color': _net_bg,
        })
        fmt_npl_pct = workbook.add_format({
            'bold': True, 'num_format': pct_fmt,
            'border': 1, 'border_color': '#000000', 'align': 'right', 'bg_color': _net_bg,
        })

        # ── Empty cell ────────────────────────────
        fmt_empty = workbook.add_format({
            'border': 1, 'border_color': '#D0D0D0',
        })

        # ─────────────────────────────────────────
        # FILTER DATA
        # ─────────────────────────────────────────
        report_date  = datetime.strptime(data['date'], "%Y-%m-%d").date()
        companies    = data['company_ids'] or self.env.companies.ids
        current_year = report_date.year
        years        = [current_year, current_year - 1, current_year - 2]
        n            = len(years)   # always 3

        # Column layout (0-indexed):
        # 0=Particulars | 1=A(yr0) | 2=B(yr1) | 3=C(yr2) | 4=D=A-B | 5=E=D/B% | 6=F=B-C | 7=G=F/C%
        COL_PART = 0
        COL_A    = 1   # current year
        COL_B    = 2   # current-1
        COL_C    = 3   # current-2
        COL_D    = 4   # absolute change AB
        COL_E    = 5   # pct change AB
        COL_F    = 6   # absolute change BC
        COL_G    = 7   # pct change BC
        TOTAL_COLS = 8

        # ─────────────────────────────────────────
        # COLUMN WIDTHS
        # ─────────────────────────────────────────
        sheet.set_column(COL_PART, COL_PART, 38)
        sheet.set_column(COL_A, COL_C, 18)
        sheet.set_column(COL_D, COL_G, 16)

        # ─────────────────────────────────────────
        # TITLE & META
        # ─────────────────────────────────────────
        sheet.merge_range(0, 0, 0, TOTAL_COLS - 1,
                          'Comparative Profit & Loss Report', fmt_title) 
        sheet.write(
            2, 0,
            'COMPARATIVE PROFIT & LOSS FOR {}, {} & {}'.format(
                years[0], years[1], years[2]
            )
        )
        sheet.write(
            2,
            1,
            'AS ON {}'.format(report_date.strftime('%d/%m/%y'))
        )
        sheet.write(3, 0, 'Companies:', fmt_label)
        sheet.write(3, 1, ', '.join(
            self.env['res.company'].browse(companies).mapped('name')
        ))

        # ─────────────────────────────────────────
        # HEADER ROW 1: Comparative group labels
        # ─────────────────────────────────────────
        row = 5

        sheet.merge_range(row, COL_PART, row + 2, COL_PART, 'Particulars', fmt_header)

        sheet.write(row, COL_A, '', fmt_header)
        sheet.write(row, COL_B, '', fmt_header)
        sheet.write(row, COL_C, '', fmt_header)
        cmp_label_1 = 'COM. FOR {} & {}'.format(years[0], years[1])
        cmp_label_2 = 'COM. FOR {} & {}'.format(years[1], years[2])
        sheet.merge_range(row, COL_D, row, COL_E, cmp_label_1, fmt_header_cmp)
        sheet.merge_range(row, COL_F, row, COL_G, cmp_label_2, fmt_header_cmp)

        # ─────────────────────────────────────────
        # HEADER ROW 2
        # ─────────────────────────────────────────
        row += 1
        sheet.write(row, COL_A, 'A', fmt_subhdr)
        sheet.write(row, COL_B, 'B', fmt_subhdr)
        sheet.write(row, COL_C, 'C', fmt_subhdr)
        sheet.write(row, COL_D, 'D = A-B',   fmt_subhdr)
        sheet.write(row, COL_E, 'E=D/B*100', fmt_subhdr)
        sheet.write(row, COL_F, 'F =B-C',    fmt_subhdr)
        sheet.write(row, COL_G, 'G=F/C*100', fmt_subhdr)

        # ─────────────────────────────────────────
        # HEADER ROW 3
        # ─────────────────────────────────────────
        row += 1
        sheet.write(row, COL_A, str(years[0]), fmt_header_yr)
        sheet.write(row, COL_B, str(years[1]), fmt_header_yr)
        sheet.write(row, COL_C, str(years[2]), fmt_header_yr)
        sheet.write(row, COL_D, 'Absolute\nChange',    fmt_header)
        sheet.write(row, COL_E, 'Percentage\nChange',  fmt_header)
        sheet.write(row, COL_F, 'Absolute\nChange',    fmt_header)
        sheet.write(row, COL_G, 'Percentage\nChange',  fmt_header)

        sheet.set_row(row - 2, 18)
        sheet.set_row(row - 1, 18)
        sheet.set_row(row,     30)

        row += 1

        # ─────────────────────────────────────────
        # FETCH ALL GROUPS
        # ─────────────────────────────────────────
        groups = self.env['pl.group'].search([], order='code')

        # ─────────────────────────────────────────
        # PRE-COMPUTE ALL AMOUNTS PER GROUP PER YEAR
        # ─────────────────────────────────────────
        group_amounts = {}

        for group in groups:
            amounts = []
            for yr in years:
                start_date = datetime(yr, 1, 1).date()
                end_date   = datetime(yr, report_date.month, report_date.day).date()
                domain = [
                    ('date', '>=', start_date),
                    ('date', '<=', end_date),
                    ('company_id', 'in', companies),
                    ('account_id.pl_group_id', '=', group.id),
                    ('move_id.state', 'in', ['draft', 'posted']),
                ]
                lines = self.env['account.move.line'].search(domain)
                amounts.append(sum(lines.mapped('balance')) * -1)
            group_amounts[group.id] = amounts

        # ─────────────────────────────────────────
        # ACCUMULATORS
        # ─────────────────────────────────────────
        before_net     = [0.0] * n
        first_section  = [0.0] * n
        second_section = [0.0] * n

        net_revenue_vals   = [0.0] * n
        grand_total_first  = [0.0] * n
        grand_total_second = [0.0] * n

        # ─────────────────────────────────────────
        # PASS 1: CALCULATE TOTALS
        # ─────────────────────────────────────────
        _state = 0
        for group in groups:
            if group.is_net_revenue:
                net_revenue_vals = list(before_net)
                _state = 1
            elif group.is_grand_total:
                if _state == 1:
                    grand_total_first = list(first_section)
                    _state = 2
                elif _state == 2:
                    grand_total_second = list(second_section)
                    _state = 3
            else:
                for col in range(n):
                    amt = group_amounts[group.id][col]
                    if _state == 0:
                        before_net[col] += amt
                    elif _state == 1:
                        first_section[col] += amt
                    elif _state == 2:
                        second_section[col] += amt

        # ─────────────────────────────────────────
        # HELPER: write a full data row (7 values)
        # ─────────────────────────────────────────
        def _safe_pct(numerator, denominator):
            if denominator and denominator != 0:
                return numerator / denominator
            return 0.0

        def write_row(r, label, vals,
                      lbl_fmt, num_fmt_val, chg_fmt, pct_fmt_val):
            a, b, c = vals[0], vals[1], vals[2]
            d = a - b
            e = _safe_pct(d, b)
            f = b - c
            g = _safe_pct(f, c)

            sheet.write(r, COL_PART, self._clean(label), lbl_fmt)
            sheet.write(r, COL_A,    a,       num_fmt_val)
            sheet.write(r, COL_B,    b,       num_fmt_val)
            sheet.write(r, COL_C,    c,       num_fmt_val)
            sheet.write(r, COL_D,    d,       chg_fmt)
            sheet.write(r, COL_E,    e,       pct_fmt_val)
            sheet.write(r, COL_F,    f,       chg_fmt)
            sheet.write(r, COL_G,    g,       pct_fmt_val)

        def write_empty_row(r):
            for c in range(TOTAL_COLS):
                sheet.write(r, c, '', fmt_empty)

        # ─────────────────────────────────────────
        # PASS 2: RENDER ROWS
        # ─────────────────────────────────────────
        state = 0

        for group in groups:

            if group.is_net_revenue:
                write_row(row, group.name, net_revenue_vals,
                          fmt_net_label, fmt_net_num, fmt_net_chg, fmt_net_pct)
                row += 1
                state = 1
                continue

            if group.is_grand_total:

                if state == 1:
                    write_row(row, group.name, grand_total_first,
                              fmt_gt_label, fmt_gt_num, fmt_gt_chg, fmt_gt_pct)
                    row += 1

                    np_vals = [net_revenue_vals[i] + grand_total_first[i] for i in range(n)]
                    write_row(row, 'Net profit for the year', np_vals,
                              fmt_np_label, fmt_np_num, fmt_np_chg, fmt_np_pct)
                    row += 1

                    write_empty_row(row)
                    row += 1

                    state = 2

                elif state == 2:
                    write_row(row, group.name, grand_total_second,
                              fmt_gt2_label, fmt_gt2_num, fmt_gt2_chg, fmt_gt2_pct)
                    row += 1

                    npl_vals = [
                        net_revenue_vals[i] + grand_total_first[i] + grand_total_second[i]
                        for i in range(n)
                    ]
                    write_row(row, 'Net Profit/ Loss', npl_vals,
                              fmt_npl_label, fmt_npl_num, fmt_npl_chg, fmt_npl_pct)
                    row += 1

                    state = 3

                continue

            _nf = fmt_row_num_red if state == 2 else fmt_row_num
            write_row(row, group.name, group_amounts[group.id],
                      fmt_row_label, _nf, fmt_chg_num, fmt_chg_pct)
            row += 1

        # ─────────────────────────────────────────
        # SAFETY NET: missing second GT group
        # ─────────────────────────────────────────
        if state == 2:
            grand_total_second = list(second_section)

            write_row(row, 'Grand Total', grand_total_second,
                      fmt_gt2_label, fmt_gt2_num, fmt_gt2_chg, fmt_gt2_pct)
            row += 1

            npl_vals = [
                net_revenue_vals[i] + grand_total_first[i] + grand_total_second[i]
                for i in range(n)
            ]
            write_row(row, 'Net Profit/ Loss', npl_vals,
                      fmt_npl_label, fmt_npl_num, fmt_npl_chg, fmt_npl_pct)
            row += 1

        # ═══════════════════════════════════════════════
        # NEW: SCHEDULE SHEETS — one per regular group
        # (skips the Net Revenue / Grand Total pseudo-rows,
        # since those aren't real account groups)
        # ═══════════════════════════════════════════════
        used_names = set()
        for group in groups:
            if group.is_net_revenue or group.is_grand_total:
                continue

            base_name = self._safe_sheet_name(group.name or 'Group')
            sheet_name = base_name
            suffix = 1
            while sheet_name in used_names:
                suffix += 1
                sheet_name = self._safe_sheet_name(
                    '{} {}'.format(base_name, suffix))
            used_names.add(sheet_name)

            self._write_schedule_sheet(
                workbook, group, companies, years, report_date,
                fmt_title, fmt_header, fmt_label,
                fmt_row_label, fmt_row_num,
                fmt_gt_label, fmt_gt_num,
            )
 


