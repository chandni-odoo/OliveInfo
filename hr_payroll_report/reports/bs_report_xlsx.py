from odoo import models
from datetime import datetime
from collections import defaultdict


class BSReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.bs_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    # ═══════════════════════════════════════════════
    # Helper to build a safe Excel sheet tab name
    # ═══════════════════════════════════════════════
    def _safe_sheet_name(self, name):
        """Excel sheet names: max 31 chars, no [ ] : * ? / \\ """
        invalid_chars = ['[', ']', ':', '*', '?', '/', '\\']
        for ch in invalid_chars:
            name = name.replace(ch, '')
        name = name.strip()
        return name[:31] if name else 'Schedule'

    def _clean(self, value):
        """Coerce a value into something xlsxwriter can safely write as text."""
        if value is False or value is None:
            return ''
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, (list, tuple)):
            return value[1] if len(value) > 1 else ''
        if not isinstance(value, str):
            return str(value)
        return value
    
    def _get_net_pl_amounts(self, companies, years, report_date):
        """
        Calculate total Net P&L for each year using a DB-side aggregate
        instead of loading every matching move line into memory.
        """
        AccountMoveLine = self.env['account.move.line']
        net_pl_amounts = []

        for yr in years:
            end_date = datetime(yr, report_date.month, report_date.day).date()

            domain = [
                ('date', '<=', end_date),
                ('company_id', 'in', companies),
                ('account_id.internal_group', 'in', ['income', 'expense']),
                ('move_id.state', 'in', ['draft', 'posted']),
            ]

            read_group_res = AccountMoveLine.read_group(
                domain, ['balance:sum'], [], lazy=False
            )
            balance_sum = read_group_res[0].get('balance') if read_group_res else 0.0
            net_pl_amounts.append((balance_sum or 0.0))

        return net_pl_amounts

    # ═══════════════════════════════════════════════
    # Fetch account-level breakdown for one bs.group
    # per account, per company, for each of the 3 years
    # ═══════════════════════════════════════════════
    def _get_all_bs_account_details(self, companies, years, report_date):
        """
        Fetch account/company-level balances for EVERY bs.group in one pass
        (one read_group call per year, i.e. 3 queries total for the whole
        report) instead of one read_group call per group per year.

        Returns: {bs_group_id: [rows...]} where each row matches the shape
        _write_schedule_sheet already expects.
        """
        AccountMoveLine = self.env['account.move.line']
        Account = self.env['account.account']
        Company = self.env['res.company']

        accounts = Account.search_read(
            [('bs_group_id', '!=', False)],
            ['code', 'name', 'bs_group_id']
        )
        account_meta = {}
        for a in accounts:
            bs_group = a['bs_group_id']
            account_meta[a['id']] = {
                'code': a['code'] or '',
                'name': a['name'] or '',
                'group_id': bs_group[0] if bs_group else False,
            }

        company_names = {c.id: (c.name or '') for c in Company.browse(companies)}

        # {group_id: {(account_id, company_id): {...}}}
        group_buckets = defaultdict(dict)

        for idx, yr in enumerate(years):
            end_date = datetime(yr, report_date.month, report_date.day).date()
            domain = [
                ('date', '<=', end_date),
                ('company_id', 'in', companies),
                ('account_id.bs_group_id', '!=', False),
                ('move_id.state', 'in', ['draft', 'posted']),
            ]
            read_group_res = AccountMoveLine.read_group(
                domain, ['balance:sum'], ['account_id', 'company_id'], lazy=False
            )

            for res in read_group_res:
                account = res.get('account_id')
                company = res.get('company_id')
                if not account or not company:
                    continue

                account_id = account[0] if isinstance(account, (list, tuple)) else account
                company_id = company[0] if isinstance(company, (list, tuple)) else company

                meta = account_meta.get(account_id)
                if not meta or not meta['group_id']:
                    continue

                key = (account_id, company_id)
                bucket = group_buckets[meta['group_id']]
                if key not in bucket:
                    bucket[key] = {
                        'code': meta['code'],
                        'name': meta['name'],
                        'company': company_names.get(company_id, ''),
                        'amounts': [0.0] * len(years),
                    }
                bucket[key]['amounts'][idx] = (res.get('balance') or 0.0)

        result = {}
        for group_id, bucket in group_buckets.items():
            result[group_id] = sorted(
                bucket.values(),
                key=lambda d: ((d['code'] or ''), (d['company'] or ''))
            )
        return result

    # ═══════════════════════════════════════════════
    # Render one schedule sheet for a single group
    # Layout: Code | Account name | Company | Y0 | Y1 | Y2
    # ═══════════════════════════════════════════════
    def _write_schedule_sheet(self, workbook, group, companies, years, report_date,
                           fmt_title, fmt_header, fmt_label,
                           fmt_row_label, fmt_row_num,
                           fmt_gt_label, fmt_gt_num, details, net_pl_amounts=None):
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

        sheet.merge_range(0, 0, 0, TOTAL_COLS - 1,
                        'Comparative Statement of Financial Position', fmt_title)
        sheet.write(1, 2, 'Schedule for {}'.format(self._clean(group.name)))

        sheet.write(2, 0, 'COMPARATIVE FOR {}, {} & {}'.format(
            years[0], years[1], years[2]))
        sheet.write(2, 1, 'AS ON {}'.format(report_date.strftime('%d/%m/%y')))
        sheet.write(3, 0, 'Companies:', fmt_label)
        sheet.write(3, 1, ', '.join(self.env['res.company'].browse(companies).mapped(lambda c: c.name or '')))

        row = 5
        sheet.write(row, COL_CODE, 'Code', fmt_header)
        sheet.write(row, COL_NAME, 'Account Name', fmt_header)
        sheet.write(row, COL_COMPANY, 'Company', fmt_header)
        sheet.write(row, COL_Y0, str(years[0]), fmt_header)
        sheet.write(row, COL_Y1, str(years[1]), fmt_header)
        sheet.write(row, COL_Y2, str(years[2]), fmt_header)
        row += 1

        totals = [0.0] * len(years)

        for rec in details:
            sheet.write(row, COL_CODE, self._clean(rec.get('code')), fmt_row_label)
            sheet.write(row, COL_NAME, self._clean(rec.get('name')), fmt_row_label)
            sheet.write(row, COL_COMPANY, self._clean(rec.get('company')), fmt_row_label)
            for i, amt in enumerate(rec['amounts']):
                sheet.write(row, COL_Y0 + i, amt, fmt_row_num)
                totals[i] += amt
            row += 1
        
        # =========================================================
        # SHOW NET P&L SEPARATELY IN RETAINED EARNINGS SHEET
        # =========================================================

        if getattr(group, 'is_retained_earnings', False) and net_pl_amounts:

            sheet.write(
                row,
                COL_CODE,
                '',
                fmt_row_label
            )

            sheet.write(
                row,
                COL_NAME,
                'Net Profit / Loss',
                fmt_row_label
            )

            sheet.write(
                row,
                COL_COMPANY,
                '',
                fmt_row_label
            )

            for i, amount in enumerate(net_pl_amounts):
                sheet.write(
                    row,
                    COL_Y0 + i,
                    amount,
                    fmt_row_num
                )
            row += 1

        # old

        if not details:
            sheet.write(row, COL_CODE, 'No data for this group', fmt_row_label)
            row += 1

        sheet.merge_range(row, COL_CODE, row, COL_COMPANY, 'Total', fmt_gt_label)
        for i, amt in enumerate(totals):
            sheet.write(row, COL_Y0 + i, amt, fmt_gt_num)

    def generate_xlsx_report(self, workbook, data, wizard):

        sheet = workbook.add_worksheet('BS Report')

        # =========================================================
        # FORMATS
        # =========================================================

        num_fmt = '#,##0.00;(#,##0.00)'
        num_fmt_red = '#,##0.00;[RED](#,##0.00)'
        pct_fmt = '0%;[RED]-0%'

        fmt_header = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#FFFFFF',
            'bg_color': '#002060',
            'border': 1,
            'border_color': '#000000',
            'text_wrap': True,
        })

        fmt_header_yr = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#000000',
            'bg_color': '#FFFF00',
            'border': 1,
            'border_color': '#000000',
        })

        fmt_header_cmp = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#FFFFFF',
            'bg_color': '#7030A0',
            'border': 1,
            'border_color': '#000000',
        })

        fmt_subhdr = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#000000',
            'bg_color': '#D9D9D9',
            'border': 1,
            'border_color': '#000000',
            'text_wrap': True,
        })

        fmt_title = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 13,
        })

        fmt_label = workbook.add_format({
            'bold': True
        })

        # =========================================================
        # SECTION HEADINGS
        # =========================================================

        fmt_main_section = workbook.add_format({
            'bold': True,
            'font_size': 12,
        })

        fmt_sub_section = workbook.add_format({
            'bold': True,
            'font_size': 11,
        })

        # =========================================================
        # REGULAR ROWS
        # =========================================================

        fmt_row_label = workbook.add_format({
            'border': 1,
            'border_color': '#D0D0D0',
        })

        fmt_row_num = workbook.add_format({
            'num_format': num_fmt,
            'border': 1,
            'border_color': '#D0D0D0',
            'align': 'right',
        })

        fmt_chg_num = workbook.add_format({
            'num_format': '#,##0.00;[RED](#,##0.00)',
            'border': 1,
            'border_color': '#D0D0D0',
            'align': 'right',
        })

        fmt_chg_pct = workbook.add_format({
            'num_format': pct_fmt,
            'border': 1,
            'border_color': '#D0D0D0',
            'align': 'right',
        })

        # =========================================================
        # TOTAL ASSETS / TOTAL EQUITY & LIABILITIES
        # =========================================================

        tel_bg = '#BDD7EE'

        fmt_tel_label = workbook.add_format({
            'bold': True,
            'bg_color': tel_bg,
            'border': 1,
            'border_color': '#000000',
        })

        fmt_tel_num = workbook.add_format({
            'bold': True,
            'num_format': num_fmt,
            'bg_color': tel_bg,
            'border': 1,
            'border_color': '#000000',
            'align': 'right',
        })

        fmt_tel_chg = workbook.add_format({
            'bold': True,
            'num_format': '#,##0.00;[RED](#,##0.00)',
            'bg_color': tel_bg,
            'border': 1,
            'border_color': '#000000',
            'align': 'right',
        })

        fmt_tel_pct = workbook.add_format({
            'bold': True,
            'num_format': pct_fmt,
            'bg_color': tel_bg,
            'border': 1,
            'border_color': '#000000',
            'align': 'right',
        })

        # =========================================================
        # SUB TOTALS
        # =========================================================

        gt_bg = '#FCE4D6'

        fmt_gt_label = workbook.add_format({
            'bold': True,
            'bg_color': gt_bg,
            'border': 1,
            'border_color': '#000000',
        })

        fmt_gt_num = workbook.add_format({
            'bold': True,
            'num_format': num_fmt,
            'bg_color': gt_bg,
            'border': 1,
            'border_color': '#000000',
            'align': 'right',
        })

        fmt_gt_chg = workbook.add_format({
            'bold': True,
            'num_format': '#,##0.00;[RED](#,##0.00)',
            'bg_color': gt_bg,
            'border': 1,
            'border_color': '#000000',
            'align': 'right',
        })

        fmt_gt_pct = workbook.add_format({
            'bold': True,
            'num_format': pct_fmt,
            'bg_color': gt_bg,
            'border': 1,
            'border_color': '#000000',
            'align': 'right',
        })

        # =========================================================
        # GRAND TOTAL
        # =========================================================

        fmt_gt2_label = workbook.add_format({
            'bold': True,
            'bg_color': gt_bg,
            'border': 2,
            'border_color': '#FF0000',
        })

        fmt_gt2_num = workbook.add_format({
            'bold': True,
            'num_format': num_fmt,
            'bg_color': gt_bg,
            'border': 2,
            'border_color': '#FF0000',
            'align': 'right',
        })

        fmt_gt2_chg = workbook.add_format({
            'bold': True,
            'num_format': '#,##0.00;[RED](#,##0.00)',
            'bg_color': gt_bg,
            'border': 2,
            'border_color': '#FF0000',
            'align': 'right',
        })

        fmt_gt2_pct = workbook.add_format({
            'bold': True,
            'num_format': pct_fmt,
            'bg_color': gt_bg,
            'border': 2,
            'border_color': '#FF0000',
            'align': 'right',
        })

        fmt_empty = workbook.add_format({
            'border': 1,
            'border_color': '#D0D0D0'
        })

        # =========================================================
        # REPORT DATA
        # =========================================================

        report_date = datetime.strptime(
            data['date'],
            "%Y-%m-%d"
        ).date()

        companies = data['company_ids'] or self.env.companies.ids

        current_year = report_date.year

        years = [
            current_year,
            current_year - 1,
            current_year - 2
        ]

        n = len(years)

        # =========================================================
        # COLUMNS
        # =========================================================

        COL_PART = 0
        COL_A = 1
        COL_B = 2
        COL_C = 3
        COL_D = 4
        COL_E = 5
        COL_F = 6
        COL_G = 7

        TOTAL_COLS = 8

        # =========================================================
        # COLUMN WIDTHS
        # =========================================================

        sheet.set_column(COL_PART, COL_PART, 40)
        sheet.set_column(COL_A, COL_C, 18)
        sheet.set_column(COL_D, COL_G, 16)

        # =========================================================
        # TITLE
        # =========================================================

        sheet.merge_range(
            0,
            0,
            0,
            TOTAL_COLS - 1,
            'COMPARATIVE STATEMENT OF FINANCIAL POSITION',
            fmt_title
        )

        sheet.write(
            2,
            0,
            'COMPARATIVE STATEMENT OF FINANCIAL POSITION FOR {}, {} & {}'.format(
                years[0],
                years[1],
                years[2]
            )
        )
        sheet.write(
            2,
            1,
            'AS ON {}'.format(report_date.strftime('%d/%m/%y'))
        )
        sheet.write(3, 0, 'Companies:', fmt_label)

        sheet.write(
            3,
            1,
            ', '.join(
                self.env['res.company'].browse(companies).mapped('name')
            )
        )

        # =========================================================
        # HEADER
        # =========================================================

        row = 5

        sheet.merge_range(
            row,
            COL_PART,
            row + 2,
            COL_PART,
            'Particulars',
            fmt_header
        )

        sheet.write(row, COL_A, '', fmt_header)
        sheet.write(row, COL_B, '', fmt_header)
        sheet.write(row, COL_C, '', fmt_header)

        sheet.merge_range(
            row,
            COL_D,
            row,
            COL_E,
            'COM. FOR {} & {}'.format(years[0], years[1]),
            fmt_header_cmp
        )

        sheet.merge_range(
            row,
            COL_F,
            row,
            COL_G,
            'COM. FOR {} & {}'.format(years[1], years[2]),
            fmt_header_cmp
        )

        row += 1

        sheet.write(row, COL_A, 'A', fmt_subhdr)
        sheet.write(row, COL_B, 'B', fmt_subhdr)
        sheet.write(row, COL_C, 'C', fmt_subhdr)

        sheet.write(row, COL_D, 'D = A-B', fmt_subhdr)
        sheet.write(row, COL_E, 'E=D/B*100', fmt_subhdr)

        sheet.write(row, COL_F, 'F = B-C', fmt_subhdr)
        sheet.write(row, COL_G, 'G=F/C*100', fmt_subhdr)

        row += 1

        sheet.write(row, COL_A, str(years[0]), fmt_header_yr)
        sheet.write(row, COL_B, str(years[1]), fmt_header_yr)
        sheet.write(row, COL_C, str(years[2]), fmt_header_yr)

        sheet.write(row, COL_D, 'Absolute\nChange', fmt_header)
        sheet.write(row, COL_E, 'Percentage\nChange', fmt_header)

        sheet.write(row, COL_F, 'Absolute\nChange', fmt_header)
        sheet.write(row, COL_G, 'Percentage\nChange', fmt_header)

        sheet.set_row(row - 2, 20)
        sheet.set_row(row - 1, 20)
        sheet.set_row(row, 35)

        row += 1

        # =========================================================
        # FETCH GROUPS
        # =========================================================

        groups = self.env['bs.group'].search([], order='code, id')
        n = len(years)

        # One read_group per year for the WHOLE chart of accounts, then split
        # per group in Python — instead of one search() per group per year.
        account_group_map = {
            a['id']: (a['bs_group_id'][0] if a['bs_group_id'] else False)
            for a in self.env['account.account'].search_read(
                [('bs_group_id', '!=', False)], ['bs_group_id']
            )
        }

        group_amounts = {group.id: [0.0] * n for group in groups}

        for idx, yr in enumerate(years):
            end_date = datetime(yr, report_date.month, report_date.day).date()
            domain = [
                ('date', '<=', end_date),
                ('company_id', 'in', companies),
                ('account_id.bs_group_id', '!=', False),
                ('move_id.state', 'in', ['draft', 'posted']),
            ]
            read_group_res = self.env['account.move.line'].read_group(
                domain, ['balance:sum'], ['account_id'], lazy=False
            )
            for res in read_group_res:
                account = res.get('account_id')
                if not account:
                    continue
                account_id = account[0] if isinstance(account, (list, tuple)) else account
                group_id = account_group_map.get(account_id)
                if group_id and group_id in group_amounts:
                    group_amounts[group_id][idx] += (res.get('balance') or 0.0)

        # =========================================================
        # ADD NET P&L TO RETAINED EARNINGS
        # =========================================================

        net_pl_amounts = self._get_net_pl_amounts(
            companies,
            years,
            report_date
        )

        retained_earnings_group = self.env['bs.group'].search(
            [('is_retained_earnings', '=', True)],
            order='code, id',
            limit=1
        )

        if retained_earnings_group:

            retained_amounts = group_amounts.get(
                retained_earnings_group.id,
                [0.0] * len(years)
            )

            for i in range(len(years)):
                retained_amounts[i] += net_pl_amounts[i]

            group_amounts[retained_earnings_group.id] = retained_amounts

        # =========================================================
        # HELPERS
        # =========================================================

        def safe_pct(numerator, denominator):

            if denominator:
                return numerator / denominator

            return 0.0

        def write_row(
                r,
                label,
                vals,
                lbl_fmt,
                num_fmt_val,
                chg_fmt,
                pct_fmt_val
        ):

            a = vals[0]
            b = vals[1]
            c = vals[2]

            d = a - b
            e = safe_pct(d, b)

            f = b - c
            g = safe_pct(f, c)

            sheet.write(r, COL_PART, self._clean(label), lbl_fmt)

            sheet.write(r, COL_A, a, num_fmt_val)
            sheet.write(r, COL_B, b, num_fmt_val)
            sheet.write(r, COL_C, c, num_fmt_val)

            sheet.write(r, COL_D, d, chg_fmt)
            sheet.write(r, COL_E, e, pct_fmt_val)

            sheet.write(r, COL_F, f, chg_fmt)
            sheet.write(r, COL_G, g, pct_fmt_val)

        def write_empty_row(r):

            for c in range(TOTAL_COLS):
                sheet.write(r, c, '', fmt_empty)

        def write_section_row(r, label, fmt):

            sheet.write(r, COL_PART, label, fmt)

            for c in range(1, TOTAL_COLS):
                sheet.write(r, c, '', fmt_empty)

        # =========================================================
        # SECTION HEADINGS
        # =========================================================

        write_section_row(row, 'ASSETS', fmt_main_section)
        row += 1

        write_section_row(row, 'Non-current assets', fmt_sub_section)
        row += 1

        # =========================================================
        # ACCUMULATORS
        # =========================================================

        current_bucket = [0.0] * n       # items within a subtotal block
        section_total = [0.0] * n        # subtotals within a main section

        total_assets = [0.0] * n
        total_equity = [0.0] * n
        total_non_current_liab = [0.0] * n
        total_current_liab = [0.0] * n

        # =========================================================
        # FLAGS
        # =========================================================

        current_assets_added = False
        equity_section_added = False
        non_current_liab_added = False
        current_liab_added = False

        # =========================================================
        # LOOP
        # =========================================================

        regular_groups = []  # Store regular groups for schedule sheets

        for group in groups:

            group_name = (group.name or '').strip().lower()

            # =====================================================
            # CURRENT ASSETS heading injection
            # =====================================================

            if not current_assets_added and group_name == 'inventories':
                write_section_row(row, 'Current assets', fmt_sub_section)
                row += 1
                current_assets_added = True

            # =====================================================
            # EQUITY AND LIABILITIES heading injection
            # =====================================================

            if not equity_section_added and group_name == 'share capital':
                write_section_row(row, 'EQUITY AND LIABILITIES', fmt_main_section)
                row += 1
                write_section_row(row, 'Equity', fmt_sub_section)
                row += 1
                equity_section_added = True

            # =====================================================
            # SUBTOTAL ROW
            # =====================================================

            if getattr(group, 'is_subtotal', False):

                subtotal_vals = list(current_bucket)

                write_row(
                    row, group.name, subtotal_vals,
                    fmt_gt_label, fmt_gt_num, fmt_gt_chg, fmt_gt_pct
                )
                row += 1

                # Accumulate into section_total
                for i in range(n):
                    section_total[i] += current_bucket[i]

                # ── After "Total Equity" ──────────────────────────────
                if group_name == 'total equity':
                    total_equity = list(subtotal_vals)

                    write_section_row(row, 'Non-current liabilities', fmt_sub_section)
                    row += 1
                    non_current_liab_added = True

                # ── After "Total Non-Current Liabilities" ────────────
                elif group_name == 'total non-current liabilities':
                    total_non_current_liab = list(subtotal_vals)

                    write_section_row(row, 'Current liabilities', fmt_sub_section)
                    row += 1
                    current_liab_added = True

                # ── After "Total Current Liabilities" ────────────────
                elif group_name == 'total current liabilities':
                    total_current_liab = list(subtotal_vals)

                    # Compute and write Total Liabilities immediately
                    total_liab_vals = [
                        total_non_current_liab[i] + total_current_liab[i]
                        for i in range(n)
                    ]
                    write_row(
                        row, 'Total Liabilities', total_liab_vals,
                        fmt_tel_label, fmt_tel_num, fmt_tel_chg, fmt_tel_pct
                    )
                    row += 1

                current_bucket = [0.0] * n
                continue

            # =====================================================
            # SECTION TOTAL  (Total Assets)
            # =====================================================

            if getattr(group, 'is_section_total', False):

                # Flush any residual bucket
                for i in range(n):
                    section_total[i] += current_bucket[i]
                current_bucket = [0.0] * n

                sec_vals = list(section_total)
                write_row(
                    row, group.name, sec_vals,
                    fmt_tel_label, fmt_tel_num, fmt_tel_chg, fmt_tel_pct
                )
                row += 1

                total_assets = list(sec_vals)

                section_total = [0.0] * n

                # Spacer
                write_empty_row(row)
                row += 1
                continue

            # =====================================================
            # GRAND TOTAL  (Total Equity & Liabilities)
            # =====================================================

            if getattr(group, 'is_grand_total', False):

                total_liab_vals = [
                    total_non_current_liab[i] + total_current_liab[i]
                    for i in range(n)
                ]
                grand_vals = [
                    total_equity[i] + total_liab_vals[i]
                    for i in range(n)
                ]

                write_row(
                    row, group.name, grand_vals,
                    fmt_gt2_label, fmt_gt2_num, fmt_gt2_chg, fmt_gt2_pct
                )
                row += 1
                continue

            # =====================================================
            # REGULAR ROW
            # =====================================================

            # Get calculated values
            group_vals = list(group_amounts[group.id])

            # Reverse sign if Reverse Sign is enabled
            if group.reverse_sign:
                group_vals = [-value for value in group_vals]

            write_row(row,group.name,group_vals,fmt_row_label,fmt_row_num,fmt_chg_num,fmt_chg_pct)

            # write_row(
            #     row, group.name, group_amounts[group.id],
            #     fmt_row_label, fmt_row_num, fmt_chg_num, fmt_chg_pct
            # )

            # Store regular group for schedule sheets
            if not getattr(group, 'is_subtotal', False) and \
               not getattr(group, 'is_section_total', False) and \
               not getattr(group, 'is_grand_total', False):
                regular_groups.append(group)

            # for i in range(n):
            #     current_bucket[i] += group_amounts[group.id][i]
            for i in range(n):
                current_bucket[i] += group_vals[i]

            row += 1

        # ═══════════════════════════════════════════════
        # SCHEDULE SHEETS — one per regular group
        # (skips the subtotal / section_total / grand_total pseudo-rows)
        # ═══════════════════════════════════════════════
        used_names = set()
        all_bs_details = self._get_all_bs_account_details(companies, years, report_date)
        for group in regular_groups:
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
                all_bs_details.get(group.id, []),
                net_pl_amounts=net_pl_amounts,
            )    