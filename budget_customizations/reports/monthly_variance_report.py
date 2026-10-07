from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class MonthlyVarianceReport(models.AbstractModel):
    _name = 'report.budget_customizations.monthly_variance_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Monthly Variance XLSX Report'

    # ─────────────────────────────────────────────────────────────────────────
    # FIELD DETECTION
    # ─────────────────────────────────────────────────────────────────────────

    def _has_field(self, model_name, field_name):
        return field_name in self.env[model_name]._fields

    def _has_aml_branch(self):
        return self._has_field('account.move.line', 'branch_id')

    def _has_aml_analytic_account(self):
        return self._has_field('account.move.line', 'analytic_account_id')

    def _has_aml_analytic_distribution(self):
        return self._has_field('account.move.line', 'analytic_distribution')

    # ─────────────────────────────────────────────────────────────────────────
    # DATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _get_month_dates(self, report_date):
        report_dt = datetime.strptime(str(report_date), '%Y-%m-%d')
        return report_dt.replace(day=1).date(), report_dt.date()

    def _get_ytd_dates(self, report_date):
        report_dt = datetime.strptime(str(report_date), '%Y-%m-%d')
        return report_dt.replace(month=1, day=1).date(), report_dt.date()

    def _get_previous_year_dates(self, report_date):
        report_dt    = datetime.strptime(str(report_date), '%Y-%m-%d')
        prev_year_dt = report_dt - relativedelta(years=1)
        return (
            prev_year_dt.replace(month=1, day=1).date(), prev_year_dt.date(),
            prev_year_dt.replace(day=1).date(),          prev_year_dt.date()
        )

    def _get_previous_month_dates(self, report_date):
        report_dt = datetime.strptime(str(report_date), '%Y-%m-%d')
        prev_month_end   = report_dt.replace(day=1) - relativedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)
        return prev_month_start.date(), prev_month_end.date()

    # ─────────────────────────────────────────────────────────────────────────
    # BRANCH RESOLUTION
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_branch_id(self, bp, aa):
        """
        Return the branch a budget position belongs to, checked on the
        position itself first, then on its analytic account.
        """
        bp_branch = getattr(bp, 'branch_id', False)
        if bp_branch:
            return bp_branch.id
        aa_branch = getattr(aa, 'branch_id', False) if aa else False
        if aa_branch:
            return aa_branch.id
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # ACTUAL CALCULATOR  (same logic as BudgetVarianceReport)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_actual_amount(self, budget_post, date_from, date_to,
                           branch_ids, company_ids,
                           analytic_account_id=False,
                           force_branch_id=False):
        """
        Branch + company + analytic aware actual for a budget post.

        Returns SIGNED amount using credit - debit convention:
            expense account -> negative number
            revenue account -> positive number
        """
        acc_ids = budget_post.account_ids.ids
        if not acc_ids:
            return 0.0

        aml = self.env['account.move.line']

        domain = [
            ('account_id', 'in', acc_ids),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('move_id.state', 'in', ['draft', 'posted']),
        ]
        if company_ids:
            domain.append(('company_id', 'in', company_ids))

        if self._has_aml_branch():
            if force_branch_id:
                domain.append(('branch_id', '=', force_branch_id))
            elif branch_ids:
                domain.append(('branch_id', 'in', branch_ids))

        if analytic_account_id:
            if self._has_aml_analytic_account():
                domain.append(('analytic_account_id', '=', analytic_account_id))
            elif self._has_aml_analytic_distribution():
                domain.append(('analytic_distribution', 'in', [analytic_account_id]))

        if self._has_field('account.move.line', 'parent_state'):
            domain.append(('parent_state', 'in', ['draft', 'posted']))

        query = aml._where_calc(domain)
        aml._apply_ir_rules(query, 'read')
        from_clause, where_clause, params = query.get_sql()

        sql = (
            "SELECT COALESCE(SUM(credit - debit), 0) "
            "FROM " + from_clause + " WHERE " + where_clause
        )
        self.env.cr.execute(sql, params)
        return self.env.cr.fetchone()[0] or 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # ACTUAL FOR BUDGET POSITIONS
    # ─────────────────────────────────────────────────────────────────────────

    def _get_actual_for_position(self, budget_post, date_from, date_to,
                                 branch_ids=None, company_ids=None,
                                 analytic_account_id=False,
                                 force_branch_id=False):
        return self._get_actual_amount(
            budget_post, date_from, date_to,
            branch_ids or [], company_ids or [],
            analytic_account_id=analytic_account_id,
            force_branch_id=force_branch_id,
        )

    def _get_actual_for_budget_positions(self, bp_ids, date_from, date_to,
                                         branch_ids=None, company_ids=None,
                                         analytic_pairs=None):
        """
        Sum actuals across a set of (bp, aa) pairs.
        When analytic_pairs given, each pair is scoped to its own branch.
        """
        total = 0.0
        BudgetPost = self.env['account.budget.post']
        AnalyticAccount = self.env['account.analytic.account']

        if analytic_pairs:
            for bp_id, aa_id in analytic_pairs:
                bp = BudgetPost.browse(bp_id)
                if not bp.exists():
                    continue
                aa = AnalyticAccount.browse(aa_id) if aa_id else False
                force_branch_id = self._resolve_branch_id(bp, aa)
                total += self._get_actual_amount(
                    bp, date_from, date_to,
                    branch_ids or [], company_ids or [],
                    analytic_account_id=aa.id if aa else False,
                    force_branch_id=force_branch_id,
                )
            return total

        for bp_id in bp_ids:
            bp = BudgetPost.browse(bp_id)
            if not bp.exists():
                continue
            force_branch_id = self._resolve_branch_id(bp, False)
            total += self._get_actual_amount(
                bp, date_from, date_to,
                branch_ids or [], company_ids or [],
                force_branch_id=force_branch_id,
            )
        return total

    # ─────────────────────────────────────────────────────────────────────────
    # BUDGET DATA
    # ─────────────────────────────────────────────────────────────────────────

    def _get_budget_data(self, domain, date_from, date_to,
                        branch_ids=None, include_zero_budget=True,
                        company_ids=None):
        period_domain = domain + [
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
        ]
        budget_lines = self.env['crossovered.budget.lines'].search(period_domain)

        budget_data = {}

        # PASS 1 — budget lines
        for line in budget_lines:
            bp = line.general_budget_id
            if not bp:
                continue
            aa = getattr(line, 'analytic_account_id', False)

            key = (bp.name or '').strip().lower()
            if key not in budget_data:
                main_group  = getattr(bp, 'main_group_id', False)
                budget_type = (
                    getattr(main_group, 'budget_type', 'expense') or 'expense'
                ).lower()
                budget_data[key] = {
                    'name':           bp.name,
                    'bp':             bp,
                    'bp_ids':         set(),
                    'analytic_pairs': set(),
                    'budget':         0.0,
                    'actual_raw':     0.0,
                    'actual':         0.0,
                    'has_budget':     True,
                    'main_group':     main_group,
                    'sub_group':      getattr(bp, 'sub_group_id', False),
                    'sequence':       getattr(bp, 'sequence', 0) or 0,
                    'budget_type':    budget_type,
                }

            budget_data[key]['bp_ids'].add(bp.id)
            budget_data[key]['analytic_pairs'].add((bp.id, aa.id if aa else None))
            budget_data[key]['budget'] += line.planned_amount

        # PASS 2 — actuals for budgeted posts
        for key, data in budget_data.items():
            raw_actual = self._get_actual_for_budget_positions(
                data['bp_ids'], date_from, date_to,
                branch_ids=branch_ids, company_ids=company_ids,
                analytic_pairs=data['analytic_pairs'],
            )
            data['actual_raw'] = raw_actual

        # PASS 3 — include every budget post that has accounts
        #          (budgeted or not, this is what fills in the "no budget" rows)
        if include_zero_budget:
            bp_domain = [('account_ids', '!=', False)]
            if company_ids and self._has_field('account.budget.post', 'company_id'):
                bp_domain.append(('company_id', 'in', company_ids))
            if branch_ids and self._has_field('account.budget.post', 'branch_id'):
                bp_domain.append(('branch_id', 'in', branch_ids))

            all_positions = self.env['account.budget.post'].search(bp_domain)

            for bp in all_positions:
                key = (bp.name or '').strip().lower()
                if key in budget_data and bp.id in budget_data[key]['bp_ids']:
                    continue

                # Skip completely empty rows (no accounts touched at all)
                raw_actual = self._get_actual_for_position(
                    bp, date_from, date_to,
                    branch_ids=branch_ids, company_ids=company_ids,
                    force_branch_id=self._resolve_branch_id(bp, False),
                )

                main_group  = getattr(bp, 'main_group_id', False)
                sub_group   = getattr(bp, 'sub_group_id', False)
                budget_type = (
                    getattr(main_group, 'budget_type', 'expense') or 'expense'
                ).lower()

                if key not in budget_data:
                    # If the post has no main_group / sub_group, park it under
                    # an "Uncategorised" bucket so it still appears in the report.
                    budget_data[key] = {
                        'name':           bp.name,
                        'bp':             bp,
                        'bp_ids':         set(),
                        'analytic_pairs': set(),
                        'budget':         0.0,
                        'actual_raw':     0.0,
                        'actual':         0.0,
                        'has_budget':     False,
                        'main_group':     main_group,
                        'sub_group':      sub_group,
                        'sequence':       getattr(bp, 'sequence', 0) or 0,
                        'budget_type':    budget_type,
                    }
                budget_data[key]['bp_ids'].add(bp.id)
                budget_data[key]['actual_raw'] += raw_actual

        # PASS 4 — display actual + variance
        for d in budget_data.values():
            budget_type = (d.get('budget_type') or 'expense').lower()
            raw = d['actual_raw']
            if budget_type == 'revenue':
                d['actual']   = raw
                d['variance'] = raw - d['budget']
            else:
                d['actual']   = -raw
                d['variance'] = d['budget'] - d['actual']

        return budget_data

    # ─────────────────────────────────────────────────────────────────────────
    # CONSOLIDATED DATA
    # ─────────────────────────────────────────────────────────────────────────

    def _get_consolidated_data(self, domain, report_date, branch_ids=None,
                               company_ids=None):
        month_from,   month_to   = self._get_month_dates(report_date)
        ytd_from,     ytd_to     = self._get_ytd_dates(report_date)
        ytd_from_prev, ytd_to_prev, month_from_prev, month_to_prev = \
            self._get_previous_year_dates(report_date)
        prev_month_from, prev_month_to = self._get_previous_month_dates(report_date)

        ytd_data          = self._get_budget_data(domain, ytd_from,        ytd_to,        branch_ids, company_ids=company_ids)
        monthly_data      = self._get_budget_data(domain, month_from,      month_to,      branch_ids, company_ids=company_ids)
        ytd_prev_data     = self._get_budget_data(domain, ytd_from_prev,   ytd_to_prev,   branch_ids, company_ids=company_ids)
        monthly_prev_data = self._get_budget_data(domain, month_from_prev, month_to_prev, branch_ids, company_ids=company_ids)
        prev_month_data   = self._get_budget_data(domain, prev_month_from, prev_month_to, branch_ids, company_ids=company_ids)

        all_positions = set(
            list(ytd_data) + list(monthly_data) +
            list(ytd_prev_data) + list(monthly_prev_data) + list(prev_month_data)
        )

        consolidated = {}
        for pid in all_positions:
            meta = (
                ytd_data.get(pid) or monthly_data.get(pid) or
                ytd_prev_data.get(pid) or monthly_prev_data.get(pid) or {}
            )
            name = meta.get('name', '')
            if not name:
                continue

            consolidated[pid] = {
                'name':                name,
                'has_budget':          (
                    ytd_data.get(pid, {}).get('has_budget', False) or
                    monthly_data.get(pid, {}).get('has_budget', False)
                ),
                'main_group':          meta.get('main_group', False),
                'sub_group':           meta.get('sub_group', False),
                'sequence':            meta.get('sequence', 0),
                'budget_type':         meta.get('budget_type', 'expense'),
                'ytd_budget':          ytd_data.get(pid, {}).get('budget',   0),
                'ytd_actual':          ytd_data.get(pid, {}).get('actual',   0),
                'ytd_variance':        ytd_data.get(pid, {}).get('variance', 0),
                'ytd_prev_actual':     ytd_prev_data.get(pid, {}).get('actual',   0),
                'monthly_budget':      monthly_data.get(pid, {}).get('budget',   0),
                'monthly_actual':      monthly_data.get(pid, {}).get('actual',   0),
                'monthly_variance':    monthly_data.get(pid, {}).get('variance', 0),
                'prev_month_actual':   prev_month_data.get(pid, {}).get('actual',   0),
                'monthly_prev_actual': monthly_prev_data.get(pid, {}).get('actual', 0),
            }
        return consolidated

    # ─────────────────────────────────────────────────────────────────────────
    # FORMATS
    # ─────────────────────────────────────────────────────────────────────────

    def _build_formats(self, workbook):
        num_fmt = '#,##0_);(#,##0)'

        def mfmt(bg=None, fc=None, bold_=False, italic_=False, border=1,
                 num_format=None):
            f = {'num_format': num_format or num_fmt, 'border': border}
            if bg:      f['bg_color']   = bg
            if fc:      f['font_color'] = fc
            if bold_:   f['bold']       = True
            if italic_: f['italic']     = True
            return workbook.add_format(f)

        def tfmt(bg=None, bold_=False, fc=None, italic_=False, border=1):
            f = {'border': border}
            if bg:      f['bg_color']   = bg
            if bold_:   f['bold']       = True
            if fc:      f['font_color'] = fc
            if italic_: f['italic']     = True
            return workbook.add_format(f)

        return {
            'bold':      workbook.add_format({'bold': True}),
            'title':     workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center'}),
            'subtitle':  workbook.add_format({'bold': True, 'font_size': 12, 'align': 'center'}),
            'header':    workbook.add_format({
                             'bold': True, 'bg_color': '#D3D3D3', 'border': 1,
                             'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
                         }),
            'border':    workbook.add_format({'border': 1}),
            'note':      workbook.add_format({'italic': True, 'font_color': '#595959', 'font_size': 9}),

            'det_text':       tfmt(),
            'det_text_zero':  tfmt(fc='#595959', italic_=True),
            'det_money':      mfmt(),
            'det_money_neg':  mfmt(fc='red'),
            'det_zero_pos':   mfmt(fc='#595959', italic_=True),
            'det_zero_neg':   mfmt(fc='red',      italic_=True),

            'sub_text':       tfmt(bg='#CCE5FF', bold_=True),
            'sub_money':      mfmt(bg='#CCE5FF', bold_=True),
            'sub_money_neg':  mfmt(bg='#CCE5FF', bold_=True, fc='red'),

            'main_text':      tfmt(bg='#99CCFF', bold_=True),
            'main_money':     mfmt(bg='#99CCFF', bold_=True),
            'main_money_neg': mfmt(bg='#99CCFF', bold_=True, fc='red'),

            'net_text':       tfmt(bg='#ADD8E6', bold_=True),
            'net_money':      mfmt(bg='#ADD8E6', bold_=True),
            'net_money_neg':  mfmt(bg='#ADD8E6', bold_=True, fc='red'),

            'grand_text':      tfmt(bg='#0066CC', bold_=True, fc='#FFFFFF'),
            'grand_money':     mfmt(bg='#0066CC', bold_=True, fc='#FFFFFF'),
            'grand_money_neg': workbook.add_format({
                                   'bold': True, 'bg_color': '#0066CC', 'border': 1,
                                   'font_color': '#FF9999', 'num_format': num_fmt,
                               }),

            'total_pos': workbook.add_format({
                             'bold': True, 'bg_color': '#D3D3D3', 'border': 1,
                             'num_format': num_fmt,
                         }),
            'total_neg': workbook.add_format({
                             'bold': True, 'bg_color': '#D3D3D3', 'border': 1,
                             'num_format': num_fmt, 'font_color': 'red',
                         }),

            'mg_label': workbook.add_format({
                             'bold': True, 'bg_color': '#E6E6E6', 'border': 1,
                         }),
            'sg_label': workbook.add_format({
                             'bold': True, 'bg_color': '#F2F2F2', 'border': 1,
                             'indent': 1,
                         }),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # VARIANCE SUMMARY HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    _SUM_KEYS = [
        'ytd_budget', 'ytd_actual', 'ytd_variance',
        'ytd_prev_actual',
        'monthly_budget', 'monthly_actual',
        'prev_month_actual', 'monthly_variance',
        'monthly_prev_actual',
    ]
    _SUM_COL = {
        'ytd_budget':          2,
        'ytd_actual':          3,
        'ytd_variance':        4,
        'ytd_prev_actual':     5,
        'monthly_budget':      6,
        'monthly_actual':      7,
        'prev_month_actual':   8,
        'monthly_variance':    9,
        'monthly_prev_actual': 10,
    }
    _SUM_VAR_KEYS = {'ytd_variance', 'monthly_variance'}

    def _zero_sum_vals(self):
        return {k: 0.0 for k in self._SUM_KEYS}

    def _add_sum_vals(self, a, b, budget_type='expense'):
        r = {k: a.get(k, 0.0) + b.get(k, 0.0) for k in self._SUM_KEYS}
        if budget_type == 'revenue':
            r['ytd_variance']     = r['ytd_actual']     - r['ytd_budget']
            r['monthly_variance'] = r['monthly_actual'] - r['monthly_budget']
        else:
            r['ytd_variance']     = r['ytd_budget']     - r['ytd_actual']
            r['monthly_variance'] = r['monthly_budget'] - r['monthly_actual']
        return r

    def _sub_sum_vals(self, a, b, budget_type='expense'):
        r = {k: a.get(k, 0.0) - b.get(k, 0.0) for k in self._SUM_KEYS}
        if budget_type == 'revenue':
            r['ytd_variance']     = r['ytd_actual']     - r['ytd_budget']
            r['monthly_variance'] = r['monthly_actual'] - r['monthly_budget']
        else:
            r['ytd_variance']     = r['ytd_budget']     - r['ytd_actual']
            r['monthly_variance'] = r['monthly_budget'] - r['monthly_actual']
        return r

    def _write_sum_money_cell(self, sheet, row, key, value, pos_fmt, neg_fmt):
        col = self._SUM_COL[key]
        if key in self._SUM_VAR_KEYS and value < 0:
            sheet.write(row, col, value, neg_fmt)
        else:
            sheet.write(row, col, value, pos_fmt)

    def _write_sum_row(self, sheet, row, label, vals, text_fmt, money_fmt, money_neg_fmt):
        sheet.write(row, 0, label, text_fmt)
        for k in self._SUM_KEYS:
            self._write_sum_money_cell(sheet, row, k, vals[k], money_fmt, money_neg_fmt)

    # ─────────────────────────────────────────────────────────────────────────
    # SHEET 1 – VARIANCE SUMMARY
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_variance_summary_sheet(self, workbook, data, report_date, fmt):
        NUM_COLS   = 11
        HEADER_ROW = 6

        sheet = workbook.add_worksheet('Variance Summary')

        report_dt      = datetime.strptime(report_date, '%Y-%m-%d')
        report_month   = report_dt.strftime('%b %y')
        prev_month_lbl = (report_dt - relativedelta(months=1)).strftime('%b %y')
        prev_year_dt   = report_dt - relativedelta(years=1)
        prev_year_lbl  = prev_year_dt.strftime('%b %y')
        prev_year_full = prev_year_dt.strftime('%b %Y')

        company_ids  = data.get('company_ids', [])
        branch_ids   = data.get('branch_ids',  [])
        budget_ids   = data.get('budget_ids',  [])

        companies    = self.env['res.company'].browse(company_ids)
        company_name = ' & '.join(companies.mapped('name')) or 'All Companies'

        sheet.merge_range(0, 0, 0, NUM_COLS - 1, company_name.upper(), fmt['title'])
        sheet.merge_range(
            1, 0, 1, NUM_COLS - 1,
            'Operational Results for the month of %s - Consolidated' % report_month,
            fmt['subtitle']
        )

        sheet.write(2, 0, 'Companies:', fmt['bold'])
        sheet.write(2, 1, company_name)

        sheet.write(3, 0, 'Branch:', fmt['bold'])
        sheet.write(3, 1,
            ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name'))
            if branch_ids else 'All Branches'
        )

        sheet.write(4, 0, 'Budget:', fmt['bold'])
        sheet.write(4, 1,
            ', '.join(self.env['crossovered.budget'].browse(budget_ids).mapped('name'))
            if budget_ids else 'All Budgets'
        )

        headers = [
            'Particulars',
            'Analytical Account',
            'YTD (%s)\nBudget' % report_month,
            'YTD (%s)\nActual' % report_month,
            'YTD\nVariance',
            'YTD (%s)\nActual' % prev_year_full,
            'Budget\n(%s)' % report_month,
            'Actual\n(%s)' % report_month,
            'Actual\n(%s)' % prev_month_lbl,
            'Variance',
            'Actual\n(%s)' % prev_year_lbl,
        ]
        for col, hdr in enumerate(headers):
            sheet.write(HEADER_ROW, col, hdr, fmt['header'])
        sheet.set_row(HEADER_ROW, 30)

        domain = []
        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        if budget_ids:
            domain.append(('crossovered_budget_id', 'in', budget_ids))
        if branch_ids:
            if self._has_field('crossovered.budget.lines', 'branch_id'):
                domain.append(('branch_id', 'in', branch_ids))
            elif self._has_field('account.analytic.account', 'branch_id'):
                domain.append(('analytic_account_id.branch_id', 'in', branch_ids))

        month_from,      month_to      = self._get_month_dates(report_date)
        ytd_from,        ytd_to        = self._get_ytd_dates(report_date)
        prev_month_from, prev_month_to = self._get_previous_month_dates(report_date)
        ytd_from_prev, ytd_to_prev, month_from_prev, month_to_prev = \
            self._get_previous_year_dates(report_date)

        ytd_data          = self._get_budget_data(domain, ytd_from,        ytd_to,        branch_ids, company_ids=company_ids)
        monthly_data      = self._get_budget_data(domain, month_from,      month_to,      branch_ids, company_ids=company_ids)
        prev_month_data   = self._get_budget_data(domain, prev_month_from, prev_month_to, branch_ids, company_ids=company_ids)
        ytd_prev_data     = self._get_budget_data(domain, ytd_from_prev,   ytd_to_prev,   branch_ids, company_ids=company_ids)
        monthly_prev_data = self._get_budget_data(domain, month_from_prev, month_to_prev, branch_ids, company_ids=company_ids)

        def _build_mg_totals():
            mg_totals = {}
            all_ids = set(
                list(ytd_data) + list(monthly_data) + list(prev_month_data) +
                list(ytd_prev_data) + list(monthly_prev_data)
            )
            for pid in all_ids:
                ytd_row  = ytd_data.get(pid, {})
                mon_row  = monthly_data.get(pid, {})
                prv_row  = prev_month_data.get(pid, {})
                ytdp_row = ytd_prev_data.get(pid, {})
                monp_row = monthly_prev_data.get(pid, {})
                meta = ytd_row or mon_row or ytdp_row or {}
                mg   = meta.get('main_group', False)
                mg_name = (mg.name.strip() if mg and mg.name else 'Uncategorised')
                key = mg_name.lower()
                if key not in mg_totals:
                    mg_totals[key] = {
                        '_name': mg_name,
                        'budget_type': (meta.get('budget_type', 'expense') or 'expense').lower(),
                    }
                    mg_totals[key].update(self._zero_sum_vals())
                mg_totals[key]['ytd_budget']          += ytd_row.get('budget', 0)
                mg_totals[key]['ytd_actual']           += ytd_row.get('actual', 0)
                mg_totals[key]['monthly_budget']       += mon_row.get('budget', 0)
                mg_totals[key]['monthly_actual']       += mon_row.get('actual', 0)
                mg_totals[key]['prev_month_actual']    += prv_row.get('actual', 0)
                mg_totals[key]['ytd_prev_actual']      += ytdp_row.get('actual', 0)
                mg_totals[key]['monthly_prev_actual']  += monp_row.get('actual', 0)

            for v in mg_totals.values():
                if v.get('budget_type') == 'revenue':
                    v['ytd_variance']     = v['ytd_actual']     - v['ytd_budget']
                    v['monthly_variance'] = v['monthly_actual'] - v['monthly_budget']
                else:
                    v['ytd_variance']     = v['ytd_budget']     - v['ytd_actual']
                    v['monthly_variance'] = v['monthly_budget'] - v['monthly_actual']
            return mg_totals

        def _build_expense_sg_totals():
            sg_totals = {}
            all_ids = set(
                list(ytd_data) + list(monthly_data) + list(prev_month_data) +
                list(ytd_prev_data) + list(monthly_prev_data)
            )
            for pid in all_ids:
                ytd_row  = ytd_data.get(pid, {})
                mon_row  = monthly_data.get(pid, {})
                prv_row  = prev_month_data.get(pid, {})
                ytdp_row = ytd_prev_data.get(pid, {})
                monp_row = monthly_prev_data.get(pid, {})
                meta = ytd_row or mon_row or ytdp_row or {}
                mg   = meta.get('main_group', False)
                if not mg or (mg.name or '').strip().lower() != 'expenses':
                    continue
                sg      = meta.get('sub_group', False)
                sg_name = (sg.name.strip() if sg and sg.name else 'Other Expenses')
                key     = sg_name.lower()
                if key not in sg_totals:
                    sg_totals[key] = {
                        '_name': sg_name,
                        '_seq':  getattr(sg, 'sequence', 0) or 0,
                    }
                    sg_totals[key].update(self._zero_sum_vals())
                sg_totals[key]['ytd_budget']          += ytd_row.get('budget', 0)
                sg_totals[key]['ytd_actual']           += ytd_row.get('actual', 0)
                sg_totals[key]['monthly_budget']       += mon_row.get('budget', 0)
                sg_totals[key]['monthly_actual']       += mon_row.get('actual', 0)
                sg_totals[key]['prev_month_actual']    += prv_row.get('actual', 0)
                sg_totals[key]['ytd_prev_actual']      += ytdp_row.get('actual', 0)
                sg_totals[key]['monthly_prev_actual']  += monp_row.get('actual', 0)

            for v in sg_totals.values():
                v['ytd_variance']     = v['ytd_budget']     - v['ytd_actual']
                v['monthly_variance'] = v['monthly_budget'] - v['monthly_actual']
            return sg_totals

        mg_totals = _build_mg_totals()
        zero      = self._zero_sum_vals()

        def _mg(name_lower):
            return {k: v for k, v in mg_totals.get(name_lower, zero).items()
                    if k in self._SUM_KEYS}

        rev_vals  = _mg('revenue')
        cor_vals  = _mg('cost of revenue')
        exp_vals  = _mg('expenses')

        row = HEADER_ROW + 1

        self._write_sum_row(sheet, row, 'TOTAL: Revenue',
                            rev_vals, fmt['main_text'],
                            fmt['main_money'], fmt['main_money_neg'])
        row += 1

        self._write_sum_row(sheet, row, 'TOTAL: Cost of Revenue',
                            cor_vals, fmt['main_text'],
                            fmt['main_money'], fmt['main_money_neg'])
        row += 1

        net_rev_vals = self._sub_sum_vals(rev_vals, cor_vals, budget_type='revenue')
        self._write_sum_row(sheet, row, 'Net Revenue',
                            net_rev_vals, fmt['net_text'],
                            fmt['net_money'], fmt['net_money_neg'])
        row += 1

        sg_totals   = _build_expense_sg_totals()
        DEPR_KEY    = 'depreciation'
        dep_vals    = zero.copy()
        op_exp_vals = zero.copy()

        for sg_key, sgv in sorted(sg_totals.items(),
                                  key=lambda x: (x[1].get('_seq', 0), x[1]['_name'])):
            s_vals = {k: sgv[k] for k in self._SUM_KEYS}
            if sg_key == DEPR_KEY:
                dep_vals = s_vals
            else:
                self._write_sum_row(sheet, row, sgv['_name'],
                                    s_vals, fmt['det_text'],
                                    fmt['det_money'], fmt['det_money_neg'])
                row += 1
                op_exp_vals = self._add_sum_vals(op_exp_vals, s_vals, budget_type='expense')

        self._write_sum_row(sheet, row, 'OPERATING EXPENSES',
                            op_exp_vals, fmt['net_text'],
                            fmt['net_money'], fmt['net_money_neg'])
        row += 1

        op_profit_vals = self._sub_sum_vals(rev_vals, op_exp_vals, budget_type='revenue')
        self._write_sum_row(sheet, row,
                            'OPERATING PROFIT (Before Depreciation)',
                            op_profit_vals, fmt['net_text'],
                            fmt['net_money'], fmt['net_money_neg'])
        sheet.set_row(row, 30)
        row += 1

        ros_pct_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#ADD8E6', 'border': 1,
            'num_format': '0.00%',
        })
        ros_pct_neg_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#ADD8E6', 'border': 1,
            'num_format': '0.00%', 'font_color': 'red',
        })
        sheet.merge_range(row, 0, row, 1, 'OPERATING ROS%', fmt['net_text'])
        for k in self._SUM_KEYS:
            rev_v = rev_vals.get(k, 0.0)
            prf_v = op_profit_vals.get(k, 0.0)
            pct   = (prf_v / rev_v) if rev_v else 0.0
            neg   = (k in self._SUM_VAR_KEYS and pct < 0)
            sheet.write(row, self._SUM_COL[k], pct,
                        ros_pct_neg_fmt if neg else ros_pct_fmt)
        row += 1

        self._write_sum_row(sheet, row, 'Depreciation',
                            dep_vals, fmt['det_text'],
                            fmt['det_money'], fmt['det_money_neg'])
        row += 1

        self._write_sum_row(sheet, row, 'TOTAL: Expenses',
                            exp_vals, fmt['main_text'],
                            fmt['main_money'], fmt['main_money_neg'])
        row += 1

        direct_exp_vals = self._add_sum_vals(cor_vals, exp_vals, budget_type='expense')
        sheet.merge_range(row, 0, row, 1,
                          'TOTAL: DIRECT + OTHER EXPENSES', fmt['grand_text'])
        for k in self._SUM_KEYS:
            self._write_sum_money_cell(sheet, row, k, direct_exp_vals[k],
                                       fmt['grand_money'], fmt['grand_money_neg'])
        row += 1

        grand_vals = self._sub_sum_vals(rev_vals, direct_exp_vals, budget_type='revenue')
        sheet.merge_range(row, 0, row, 1, 'GRAND TOTAL', fmt['grand_text'])
        for k in self._SUM_KEYS:
            self._write_sum_money_cell(sheet, row, k, grand_vals[k],
                                       fmt['grand_money'], fmt['grand_money_neg'])

        sheet.set_column(0,  0,  35)
        sheet.set_column(1,  1,   0)
        sheet.set_column(2,  2,  15)
        sheet.set_column(3,  3,  15)
        sheet.set_column(4,  4,  15)
        sheet.set_column(5,  5,  20)
        sheet.set_column(6,  6,  15)
        sheet.set_column(7,  7,  15)
        sheet.set_column(8,  8,  15)
        sheet.set_column(9,  9,  15)
        sheet.set_column(10, 10, 18)
        sheet.freeze_panes(HEADER_ROW + 1, 0)

    # ─────────────────────────────────────────────────────────────────────────
    # SHEET 2 – VARIANCE REPORT (flat)
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_main_variance_sheet(self, workbook, data, report_date, fmt):
        company_ids = data.get('company_ids', [])
        branch_ids  = data.get('branch_ids',  [])
        budget_ids  = data.get('budget_ids',  [])

        domain = []
        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        if budget_ids:
            domain.append(('crossovered_budget_id', 'in', budget_ids))
        if branch_ids:
            if self._has_field('crossovered.budget.lines', 'branch_id'):
                domain.append(('branch_id', 'in', branch_ids))
            elif self._has_field('account.analytic.account', 'branch_id'):
                domain.append(('analytic_account_id.branch_id', 'in', branch_ids))

        month_from, month_to = self._get_month_dates(report_date)
        ytd_from,   ytd_to   = self._get_ytd_dates(report_date)

        monthly_data = self._get_budget_data(domain, month_from, month_to, branch_ids, company_ids=company_ids)
        ytd_data     = self._get_budget_data(domain, ytd_from,   ytd_to,   branch_ids, company_ids=company_ids)

        sheet = workbook.add_worksheet('Variance Report')

        report_month = datetime.strptime(report_date, '%Y-%m-%d').strftime('%b %Y')

        NUM_COLS = 8

        sheet.merge_range(0, 0, 0, NUM_COLS - 1,
                        'Variance Report for the month of %s' % report_month,
                        fmt['title'])

        companies = self.env['res.company'].browse(company_ids)
        sheet.write(1, 0, 'Companies:', fmt['bold'])
        sheet.write(1, 1, ', '.join(companies.mapped('name')) or 'All Companies')

        sheet.write(2, 0, 'Branch:', fmt['bold'])
        branch_names = (
            ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name'))
            if branch_ids else 'All Branches'
        )
        sheet.write(2, 1, branch_names)

        sheet.write(3, 0, 'Budget:', fmt['bold'])
        budget_names = (
            ', '.join(self.env['crossovered.budget'].browse(budget_ids).mapped('name'))
            if budget_ids else 'All Budgets'
        )
        sheet.write(3, 1, budget_names)

        sheet.write(4, 0,
                    '* Italicised rows have no budget allocation; '
                    'actual amounts are from posted transactions.',
                    fmt['note'])

        headers = [
            'Particulars', 'Budget', 'Actual', 'Variance',
            'Reasons for Variance', 'YTD Budget', 'YTD Actual', 'YTD Variance',
        ]
        for col, hdr in enumerate(headers):
            sheet.write(5, col, hdr, fmt['header'])

        row = 6

        all_ids = set(list(monthly_data.keys()) + list(ytd_data.keys()))

        _BLANK_MG_ID = -1
        _BLANK_SG_ID = -1

        hierarchy = {}

        for pid in all_ids:
            m    = monthly_data.get(pid, {})
            y    = ytd_data.get(pid, {})
            meta = m or y
            if not meta.get('name'):
                continue

            mg  = meta.get('main_group', False)
            sg  = meta.get('sub_group', False)

            if mg and mg.id:
                mg_id, mg_name = mg.id, mg.name.strip() or 'Uncategorised'
                mg_seq = getattr(mg, 'sequence', 0) or 0
                mg_budget_type = (getattr(mg, 'budget_type', 'expense') or 'expense').lower()
            else:
                mg_id, mg_name, mg_seq = _BLANK_MG_ID, 'Uncategorised', 9999
                mg_budget_type = 'expense'

            if mg_id not in hierarchy:
                hierarchy[mg_id] = {
                    'name': mg_name, 'sequence': mg_seq,
                    'budget_type': mg_budget_type,
                    'sub_groups': {}, 'sub_group_totals': {},
                    'monthly_budget': 0.0, 'monthly_actual': 0.0, 'monthly_variance': 0.0,
                    'ytd_budget':     0.0, 'ytd_actual':     0.0, 'ytd_variance':     0.0,
                }

            if sg and sg.id:
                sg_id, sg_name = sg.id, sg.name.strip() or 'General'
                sg_seq = getattr(sg, 'sequence', 0) or 0
            else:
                sg_id, sg_name, sg_seq = _BLANK_SG_ID, 'General', 9999

            mg_node = hierarchy[mg_id]

            if sg_id not in mg_node['sub_groups']:
                mg_node['sub_groups'][sg_id] = {
                    'name': sg_name, 'sequence': sg_seq,
                    'budget_positions': [],
                    'budget_type': mg_budget_type,
                }
                mg_node['sub_group_totals'][sg_id] = {
                    'name': sg_name,
                    'budget_type': mg_budget_type,
                    'monthly_budget': 0.0, 'monthly_actual': 0.0, 'monthly_variance': 0.0,
                    'ytd_budget':     0.0, 'ytd_actual':     0.0, 'ytd_variance':     0.0,
                }

            bp_row = {
                'name':             meta['name'],
                'has_budget':       m.get('has_budget', False) or y.get('has_budget', False),
                'sequence':         meta.get('sequence', 0) or 0,
                'monthly_budget':   m.get('budget',   0.0),
                'monthly_actual':   m.get('actual',   0.0),
                'monthly_variance': m.get('variance', 0.0),
                'ytd_budget':       y.get('budget',   0.0),
                'ytd_actual':       y.get('actual',   0.0),
                'ytd_variance':     y.get('variance', 0.0),
            }
            mg_node['sub_groups'][sg_id]['budget_positions'].append(bp_row)

            sgt = mg_node['sub_group_totals'][sg_id]
            for src in ('monthly_budget', 'monthly_actual', 'ytd_budget', 'ytd_actual'):
                sgt[src]     += bp_row[src]
                mg_node[src] += bp_row[src]

        for mg_node in hierarchy.values():
            is_revenue = mg_node.get('budget_type', 'expense') == 'revenue'
            if is_revenue:
                mg_node['monthly_variance'] = mg_node['monthly_actual'] - mg_node['monthly_budget']
                mg_node['ytd_variance']     = mg_node['ytd_actual']     - mg_node['ytd_budget']
            else:
                mg_node['monthly_variance'] = mg_node['monthly_budget'] - mg_node['monthly_actual']
                mg_node['ytd_variance']     = mg_node['ytd_budget']     - mg_node['ytd_actual']

            for sgt in mg_node['sub_group_totals'].values():
                is_rev_sg = sgt.get('budget_type', 'expense') == 'revenue'
                if is_rev_sg:
                    sgt['monthly_variance'] = sgt['monthly_actual'] - sgt['monthly_budget']
                    sgt['ytd_variance']     = sgt['ytd_actual']     - sgt['ytd_budget']
                else:
                    sgt['monthly_variance'] = sgt['monthly_budget'] - sgt['monthly_actual']
                    sgt['ytd_variance']     = sgt['ytd_budget']     - sgt['ytd_actual']

        def _write_detail_row(r, bp):
            has_budget = bp.get('has_budget', False)
            t_fmt = fmt['det_text'] if has_budget else fmt['det_text_zero']
            m_fmt = fmt['det_money']
            z_fmt = fmt['det_zero_pos']

            sheet.write(r, 0, '        ' + bp['name'], t_fmt)
            sheet.write(r, 1, bp['monthly_budget'], m_fmt if has_budget else z_fmt)
            sheet.write(r, 2, bp['monthly_actual'], m_fmt if has_budget else z_fmt)
            mv = bp['monthly_variance']
            sheet.write(r, 3, mv,
                        (fmt['det_money_neg'] if mv < 0 else fmt['det_money'])
                        if has_budget else
                        (fmt['det_zero_neg']  if mv < 0 else fmt['det_zero_pos']))
            sheet.write(r, 4, '', fmt['border'])
            sheet.write(r, 5, bp['ytd_budget'], m_fmt if has_budget else z_fmt)
            sheet.write(r, 6, bp['ytd_actual'], m_fmt if has_budget else z_fmt)
            yv = bp['ytd_variance']
            sheet.write(r, 7, yv,
                        (fmt['det_money_neg'] if yv < 0 else fmt['det_money'])
                        if has_budget else
                        (fmt['det_zero_neg']  if yv < 0 else fmt['det_zero_pos']))

        def _write_sg_total(r, label, sgt):
            sheet.write(r, 0, '    ' + label, fmt['sub_text'])
            sheet.write(r, 1, sgt['monthly_budget'], fmt['sub_money'])
            sheet.write(r, 2, sgt['monthly_actual'], fmt['sub_money'])
            mv = sgt['monthly_variance']
            sheet.write(r, 3, mv, fmt['sub_money_neg'] if mv < 0 else fmt['sub_money'])
            sheet.write(r, 4, '', fmt['sub_text'])
            sheet.write(r, 5, sgt['ytd_budget'], fmt['sub_money'])
            sheet.write(r, 6, sgt['ytd_actual'], fmt['sub_money'])
            yv = sgt['ytd_variance']
            sheet.write(r, 7, yv, fmt['sub_money_neg'] if yv < 0 else fmt['sub_money'])

        def _write_mg_total(r, label, mg):
            sheet.write(r, 0, label, fmt['main_text'])
            sheet.write(r, 1, mg['monthly_budget'], fmt['main_money'])
            sheet.write(r, 2, mg['monthly_actual'], fmt['main_money'])
            mv = mg['monthly_variance']
            sheet.write(r, 3, mv, fmt['main_money_neg'] if mv < 0 else fmt['main_money'])
            sheet.write(r, 4, '', fmt['main_text'])
            sheet.write(r, 5, mg['ytd_budget'], fmt['main_money'])
            sheet.write(r, 6, mg['ytd_actual'], fmt['main_money'])
            yv = mg['ytd_variance']
            sheet.write(r, 7, yv, fmt['main_money_neg'] if yv < 0 else fmt['main_money'])

        FIXED_MG_ORDER = ['revenue', 'cost of revenue', 'expenses']

        def _mg_sort_key(mg_node):
            name_lower = (mg_node.get('name') or '').strip().lower()
            try:
                return (FIXED_MG_ORDER.index(name_lower), 0, '')
            except ValueError:
                return (999, mg_node.get('sequence', 0), mg_node.get('name', ''))

        grand_total = {
            'monthly_budget': 0.0, 'monthly_actual': 0.0, 'monthly_variance': 0.0,
            'ytd_budget':     0.0, 'ytd_actual':     0.0, 'ytd_variance':     0.0,
        }
        rev_totals        = dict.fromkeys(('monthly_budget', 'monthly_actual', 'ytd_budget', 'ytd_actual'), 0.0)
        direct_exp_totals = dict.fromkeys(('monthly_budget', 'monthly_actual', 'ytd_budget', 'ytd_actual'), 0.0)

        for mg_node in sorted(hierarchy.values(), key=_mg_sort_key):
            sheet.write(row, 0, mg_node['name'].upper(), fmt['mg_label'])
            blank_mg_fmt = workbook.add_format({'bg_color': '#E6E6E6', 'border': 1})
            for c in range(1, NUM_COLS):
                sheet.write(row, c, '', blank_mg_fmt)
            row += 1

            sg_items = sorted(
                [
                    (sg_id, sg, mg_node['sub_group_totals'].get(sg_id, {}))
                    for sg_id, sg in mg_node['sub_groups'].items()
                ],
                key=lambda x: (x[1].get('sequence', 0), x[1].get('name', ''))
            )

            for sg_id, sg, sgt in sg_items:
                sheet.write(row, 0, sg['name'], fmt['sg_label'])
                blank_sg_fmt = workbook.add_format({'bg_color': '#F2F2F2', 'border': 1})
                for c in range(1, NUM_COLS):
                    sheet.write(row, c, '', blank_sg_fmt)
                row += 1

                for bp in sorted(
                    sg['budget_positions'],
                    key=lambda x: (x.get('sequence', 0), x.get('name', ''))
                ):
                    _write_detail_row(row, bp)
                    row += 1

                _write_sg_total(row, 'Total: %s' % sg['name'], sgt)
                row += 1

            _write_mg_total(row, 'TOTAL: %s' % mg_node['name'], mg_node)
            row += 1

            name_lower = (mg_node.get('name') or '').strip().lower()
            target = rev_totals if name_lower == 'revenue' else direct_exp_totals
            for k in ('monthly_budget', 'monthly_actual', 'ytd_budget', 'ytd_actual'):
                target[k] += mg_node[k]

        for k in ('monthly_budget', 'monthly_actual', 'ytd_budget', 'ytd_actual'):
            grand_total[k] = rev_totals[k] - direct_exp_totals[k]

        grand_total['monthly_variance'] = grand_total['monthly_actual'] - grand_total['monthly_budget']
        grand_total['ytd_variance']     = grand_total['ytd_actual']     - grand_total['ytd_budget']

        sheet.write(row, 0, 'GRAND TOTAL', fmt['grand_text'])
        sheet.write(row, 1, grand_total['monthly_budget'], fmt['grand_money'])
        sheet.write(row, 2, grand_total['monthly_actual'], fmt['grand_money'])
        mv = grand_total['monthly_variance']
        sheet.write(row, 3, mv, fmt['grand_money_neg'] if mv < 0 else fmt['grand_money'])
        sheet.write(row, 4, '', fmt['grand_text'])
        sheet.write(row, 5, grand_total['ytd_budget'], fmt['grand_money'])
        sheet.write(row, 6, grand_total['ytd_actual'], fmt['grand_money'])
        yv = grand_total['ytd_variance']
        sheet.write(row, 7, yv, fmt['grand_money_neg'] if yv < 0 else fmt['grand_money'])

        sheet.set_column(0, 0, 35)
        sheet.set_column(1, 3, 15)
        sheet.set_column(4, 4, 40)
        sheet.set_column(5, 7, 15)
        sheet.freeze_panes(6, 0)

    # ─────────────────────────────────────────────────────────────────────────
    # CONSOLIDATED SHEET HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    _CON_KEYS = [
        'ytd_budget', 'ytd_actual', 'ytd_variance',
        'ytd_prev_actual',
        'monthly_budget', 'monthly_actual',
        'prev_month_actual', 'monthly_variance',
        'monthly_prev_actual',
    ]
    _CON_COL = {
        'ytd_budget':          1,
        'ytd_actual':          2,
        'ytd_variance':        3,
        'ytd_prev_actual':     4,
        'monthly_budget':      5,
        'monthly_actual':      6,
        'prev_month_actual':   7,
        'monthly_variance':    8,
        'monthly_prev_actual': 9,
    }
    _CON_VAR_KEYS = {'ytd_variance', 'monthly_variance'}

    def _zero_con_vals(self):
        return {k: 0.0 for k in self._CON_KEYS}

    def _add_con_vals(self, a, b, budget_type='expense'):
        r = {k: a.get(k, 0.0) + b.get(k, 0.0) for k in self._CON_KEYS}
        if budget_type == 'revenue':
            r['ytd_variance']     = r['ytd_actual']     - r['ytd_budget']
            r['monthly_variance'] = r['monthly_actual'] - r['monthly_budget']
        else:
            r['ytd_variance']     = r['ytd_budget']     - r['ytd_actual']
            r['monthly_variance'] = r['monthly_budget'] - r['monthly_actual']
        return r

    def _sub_con_vals(self, a, b, budget_type='revenue'):
        r = {k: a.get(k, 0.0) - b.get(k, 0.0) for k in self._CON_KEYS}
        if budget_type == 'revenue':
            r['ytd_variance']     = r['ytd_actual']     - r['ytd_budget']
            r['monthly_variance'] = r['monthly_actual'] - r['monthly_budget']
        else:
            r['ytd_variance']     = r['ytd_budget']     - r['ytd_actual']
            r['monthly_variance'] = r['monthly_budget'] - r['monthly_actual']
        return r

    def _build_consolidated_hierarchy(self, consolidated_data):
        _BLANK_ID    = -1
        _BLANK_SG_ID = -1

        hierarchy = {}

        for pid, d in consolidated_data.items():
            mg  = d.get('main_group', False)
            sg  = d.get('sub_group', False)
            seq = d.get('sequence',   0) or 0

            if mg and mg.id:
                mg_id   = mg.id
                mg_name = mg.name.strip() or 'Uncategorised'
                mg_seq  = getattr(mg, 'sequence', 0) or 0
                mg_budget_type = (getattr(mg, 'budget_type', 'expense') or 'expense').lower()
            else:
                mg_id   = _BLANK_ID
                mg_name = 'Uncategorised'
                mg_seq  = 9999
                mg_budget_type = 'expense'

            if mg_id not in hierarchy:
                hierarchy[mg_id] = {
                    'name':             mg_name,
                    'sequence':         mg_seq,
                    'budget_type':      mg_budget_type,
                    'sub_groups':       {},
                    'sub_group_totals': {},
                }
                hierarchy[mg_id].update(self._zero_con_vals())

            if sg and sg.id:
                sg_id   = sg.id
                sg_name = sg.name.strip() or 'General'
                sg_seq  = getattr(sg, 'sequence', 0) or 0
            else:
                sg_id   = _BLANK_SG_ID
                sg_name = 'General'
                sg_seq  = 9999

            mg_node = hierarchy[mg_id]

            if sg_id not in mg_node['sub_groups']:
                mg_node['sub_groups'][sg_id] = {
                    'name':             sg_name,
                    'sequence':         sg_seq,
                    'budget_positions': [],
                }
                mg_node['sub_group_totals'][sg_id] = {
                    'name': sg_name,
                    'budget_type': mg_budget_type,
                }
                mg_node['sub_group_totals'][sg_id].update(self._zero_con_vals())

            bp_row = {
                'name':                d['name'],
                'has_budget':          d.get('has_budget', False),
                'sequence':            seq,
                'ytd_budget':          d['ytd_budget'],
                'ytd_actual':          d['ytd_actual'],
                'ytd_variance':        d['ytd_variance'],
                'ytd_prev_actual':     d['ytd_prev_actual'],
                'monthly_budget':      d['monthly_budget'],
                'monthly_actual':      d['monthly_actual'],
                'prev_month_actual':   d['prev_month_actual'],
                'monthly_variance':    d['monthly_variance'],
                'monthly_prev_actual': d['monthly_prev_actual'],
            }
            mg_node['sub_groups'][sg_id]['budget_positions'].append(bp_row)

            sgt = mg_node['sub_group_totals'][sg_id]
            for k in self._CON_KEYS:
                sgt[k]     += d.get(k, 0.0)
                mg_node[k] += d.get(k, 0.0)

        for mg_node in hierarchy.values():
            is_revenue = mg_node.get('budget_type', 'expense') == 'revenue'
            if is_revenue:
                mg_node['ytd_variance'] = mg_node['ytd_actual'] - mg_node['ytd_budget']
                mg_node['monthly_variance'] = mg_node['monthly_actual'] - mg_node['monthly_budget']
            else:
                mg_node['ytd_variance'] = mg_node['ytd_budget'] - mg_node['ytd_actual']
                mg_node['monthly_variance'] = mg_node['monthly_budget'] - mg_node['monthly_actual']

            for sgt in mg_node['sub_group_totals'].values():
                is_rev_sg = sgt.get('budget_type', 'expense') == 'revenue'
                if is_rev_sg:
                    sgt['ytd_variance'] = sgt['ytd_actual'] - sgt['ytd_budget']
                    sgt['monthly_variance'] = sgt['monthly_actual'] - sgt['monthly_budget']
                else:
                    sgt['ytd_variance'] = sgt['ytd_budget'] - sgt['ytd_actual']
                    sgt['monthly_variance'] = sgt['monthly_budget'] - sgt['monthly_actual']

        return hierarchy

    def _write_con_money_cell(self, sheet, row, key, value, pos_fmt, neg_fmt):
        col = self._CON_COL[key]
        if key in self._CON_VAR_KEYS and value < 0:
            sheet.write(row, col, value, neg_fmt)
        else:
            sheet.write(row, col, value, pos_fmt)

    def _write_con_data_row(self, sheet, row, vals,
                            text_fmt, money_fmt, money_neg_fmt, label):
        sheet.write(row, 0, label, text_fmt)
        for k in self._CON_KEYS:
            self._write_con_money_cell(sheet, row, k, vals[k], money_fmt, money_neg_fmt)

    # ─────────────────────────────────────────────────────────────────────────
    # SHEET 3 – CONSOLIDATED OPERATIONAL RESULTS
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_consolidated_sheet(self, workbook, data, report_date, fmt):
        NUM_COLS   = 10
        HEADER_ROW = 6

        sheet = workbook.add_worksheet('Consolidated Operational Results')

        report_dt       = datetime.strptime(report_date, '%Y-%m-%d')
        report_month    = report_dt.strftime('%b %y')
        prev_month_lbl  = (report_dt - relativedelta(months=1)).strftime('%b %y')
        prev_year_dt    = report_dt - relativedelta(years=1)
        prev_year_lbl   = prev_year_dt.strftime('%b %y')
        prev_year_label = prev_year_dt.strftime('%b %Y')

        company_ids  = data.get('company_ids', [])
        branch_ids   = data.get('branch_ids',  [])
        budget_ids   = data.get('budget_ids',  [])

        companies    = self.env['res.company'].browse(company_ids)
        company_name = ' & '.join(companies.mapped('name')) or 'All Companies'

        sheet.merge_range(0, 0, 0, NUM_COLS - 1, company_name.upper(), fmt['title'])
        sheet.merge_range(
            1, 0, 1, NUM_COLS - 1,
            'Operational Results for the month of %s - Consolidated' % report_month,
            fmt['subtitle']
        )

        sheet.write(2, 0, 'Companies:', fmt['bold'])
        sheet.write(2, 1, company_name)

        sheet.write(3, 0, 'Branch:', fmt['bold'])
        branch_names = ', '.join(
            self.env['res.branch'].browse(branch_ids).mapped('name')
        ) if branch_ids else 'All Branches'
        sheet.write(3, 1, branch_names)

        sheet.write(4, 0, 'Budget:', fmt['bold'])
        budget_names = ', '.join(
            self.env['crossovered.budget'].browse(budget_ids).mapped('name')
        ) if budget_ids else 'All Budgets'
        sheet.write(4, 1, budget_names)

        sheet.write(5, 0,
                    '* Italicised rows have no budget allocation; '
                    'actual amounts are from posted transactions.',
                    fmt['note'])

        headers = [
            'Particulars',
            'YTD (%s)\nBudget' % report_month,
            'YTD (%s)\nActual' % report_month,
            'YTD\nVariance',
            'YTD\n(%s)\nActual' % prev_year_label,
            'Budget\n(%s)' % report_month,
            'Actual\n(%s)' % report_month,
            'Actual\n(%s)' % prev_month_lbl,
            'Variance',
            'Actual\n(%s)' % prev_year_lbl,
        ]
        for col, hdr in enumerate(headers):
            sheet.write(HEADER_ROW, col, hdr, fmt['header'])
        sheet.set_row(HEADER_ROW, 36)

        domain = []
        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        if branch_ids:
            if self._has_field('crossovered.budget.lines', 'branch_id'):
                domain.append(('branch_id', 'in', branch_ids))
            elif self._has_field('account.analytic.account', 'branch_id'):
                domain.append(('analytic_account_id.branch_id', 'in', branch_ids))
        if budget_ids:
            domain.append(('crossovered_budget_id', 'in', budget_ids))

        consolidated_data = self._get_consolidated_data(
            domain, report_date, branch_ids, company_ids=company_ids
        )
        hierarchy = self._build_consolidated_hierarchy(consolidated_data)

        FIXED_MAIN_GROUP_ORDER = ['revenue', 'cost of revenue', 'expenses']

        def get_main_group_order(mg_node):
            mg_name_lower = (mg_node.get('name') or '').strip().lower()
            try:
                return FIXED_MAIN_GROUP_ORDER.index(mg_name_lower)
            except ValueError:
                return 999

        mg_label_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#E6E6E6', 'border': 1,
        })
        sg_label_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'indent': 1,
        })

        def _write_detail(r, bp):
            has_budget = bp.get('has_budget', False)
            if has_budget:
                sheet.write(r, 0, '    ' + bp['name'], fmt['det_text'])
            else:
                sheet.write(r, 0, '    ' + bp['name'], fmt['det_text_zero'])
            for k in self._CON_KEYS:
                v = bp[k]
                if k in self._CON_VAR_KEYS:
                    if has_budget:
                        neg_f = fmt['det_money_neg']
                        pos_f = fmt['det_money']
                    else:
                        neg_f = fmt['det_zero_neg']
                        pos_f = fmt['det_zero_pos']
                    sheet.write(r, self._CON_COL[k], v, neg_f if v < 0 else pos_f)
                else:
                    sheet.write(r, self._CON_COL[k], v, fmt['det_money'])

        def _write_subtotal(r, label, vals, text_f, money_f, money_neg_f):
            sheet.write(r, 0, label, text_f)
            for k in self._CON_KEYS:
                v = vals[k]
                sheet.write(
                    r, self._CON_COL[k], v,
                    money_neg_f if (k in self._CON_VAR_KEYS and v < 0) else money_f
                )

        def _write_grand_row(r, label, vals):
            sheet.write(r, 0, label, fmt['grand_text'])
            for k in self._CON_KEYS:
                v = vals[k]
                sheet.write(
                    r, self._CON_COL[k], v,
                    fmt['grand_money_neg'] if (k in self._CON_VAR_KEYS and v < 0)
                    else fmt['grand_money']
                )

        row = HEADER_ROW + 1

        grand_total_vals = self._zero_con_vals()

        sorted_main_groups = sorted(
            hierarchy.values(),
            key=lambda x: (get_main_group_order(x), x.get('sequence', 0), x.get('name', ''))
        )

        for mg_node in sorted_main_groups:
            sheet.write(row, 0, mg_node['name'].upper(), mg_label_fmt)
            blank_mg = workbook.add_format({'bg_color': '#E6E6E6', 'border': 1})
            for c in range(1, NUM_COLS):
                sheet.write(row, c, '', blank_mg)
            row += 1

            mg_running = self._zero_con_vals()
            mg_running['budget_type'] = mg_node.get('budget_type', 'expense')

            sg_items = sorted(
                [
                    (sg_id, sg, mg_node['sub_group_totals'].get(sg_id, {}))
                    for sg_id, sg in mg_node['sub_groups'].items()
                ],
                key=lambda x: (x[1].get('sequence', 0), x[1].get('name', ''))
            )

            for sg_id, sg, sgt in sg_items:
                sheet.write(row, 0, sg['name'], sg_label_fmt)
                blank_sg = workbook.add_format({'bg_color': '#F2F2F2', 'border': 1})
                for c in range(1, NUM_COLS):
                    sheet.write(row, c, '', blank_sg)
                row += 1

                sg_running = self._zero_con_vals()
                sg_running['budget_type'] = mg_node.get('budget_type', 'expense')

                for bp in sorted(
                    sg['budget_positions'],
                    key=lambda x: (x.get('sequence', 0), x.get('name', ''))
                ):
                    _write_detail(row, bp)
                    for k in self._CON_KEYS:
                        sg_running[k] += bp[k]
                    row += 1

                _is_rev = mg_node.get('budget_type', 'expense') == 'revenue'
                if _is_rev:
                    sg_running['ytd_variance']     = sg_running['ytd_actual']     - sg_running['ytd_budget']
                    sg_running['monthly_variance'] = sg_running['monthly_actual'] - sg_running['monthly_budget']
                else:
                    sg_running['ytd_variance']     = sg_running['ytd_budget']     - sg_running['ytd_actual']
                    sg_running['monthly_variance'] = sg_running['monthly_budget'] - sg_running['monthly_actual']

                _write_subtotal(
                    row, 'Total: %s' % sg['name'], sg_running,
                    fmt['sub_text'], fmt['sub_money'], fmt['sub_money_neg']
                )
                row += 1

                mg_running = self._add_con_vals(
                    mg_running, sg_running,
                    budget_type=mg_node.get('budget_type', 'expense')
                )

            _write_subtotal(
                row, 'TOTAL: %s' % mg_node['name'], mg_running,
                fmt['main_text'], fmt['main_money'], fmt['main_money_neg']
            )
            row += 1

            grand_total_vals = self._add_con_vals(
                grand_total_vals, mg_running,
                budget_type=mg_node.get('budget_type', 'expense')
            )

        EXPENSE_NAMES = {'cost of revenue', 'expenses'}
        direct_exp_vals = self._zero_con_vals()
        for mg_node in hierarchy.values():
            if (mg_node.get('name') or '').strip().lower() in EXPENSE_NAMES:
                direct_exp_vals = self._add_con_vals(
                    direct_exp_vals,
                    {k: mg_node[k] for k in self._CON_KEYS},
                    budget_type='expense'
                )

        _write_grand_row(row, 'TOTAL: DIRECT + OTHER EXPENSES', direct_exp_vals)
        row += 1

        rev_vals = self._zero_con_vals()
        for mg_node in hierarchy.values():
            if (mg_node.get('name') or '').strip().lower() == 'revenue':
                rev_vals = self._add_con_vals(
                    rev_vals,
                    {k: mg_node[k] for k in self._CON_KEYS},
                    budget_type='revenue'
                )

        profit_vals = self._sub_con_vals(rev_vals, direct_exp_vals, budget_type='revenue')
        _write_grand_row(row, 'GRAND TOTAL – PROFIT / LOSS', profit_vals)

        sheet.set_column(0,  0,  35)
        sheet.set_column(1,  1,  15)
        sheet.set_column(2,  2,  15)
        sheet.set_column(3,  3,  15)
        sheet.set_column(4,  4,  20)
        sheet.set_column(5,  5,  15)
        sheet.set_column(6,  6,  15)
        sheet.set_column(7,  7,  15)
        sheet.set_column(8,  8,  15)
        sheet.set_column(9,  9,  18)
        sheet.freeze_panes(HEADER_ROW + 1, 0)

    # ─────────────────────────────────────────────────────────────────────────
    # ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────

    def generate_xlsx_report(self, workbook, data, lines):
        report_date       = data.get('report_date')
        show_consolidated = data.get('show_consolidated', True)

        fmt = self._build_formats(workbook)

        self._generate_variance_summary_sheet(workbook, data, report_date, fmt)
        self._generate_main_variance_sheet(workbook, data, report_date, fmt)
        if show_consolidated:
            self._generate_consolidated_sheet(workbook, data, report_date, fmt)


# class MonthlyVarianceReport(models.AbstractModel):
#     _name = 'report.budget_customizations.monthly_variance_xlsx'
#     _inherit = 'report.report_xlsx.abstract'
#     _description = 'Monthly Variance XLSX Report'

#     # ─────────────────────────────────────────────────────────────────────────
#     # DATE HELPERS
#     # ─────────────────────────────────────────────────────────────────────────

#     def _get_month_dates(self, report_date):
#         report_dt = datetime.strptime(str(report_date), '%Y-%m-%d')
#         return report_dt.replace(day=1).date(), report_dt.date()

#     def _get_ytd_dates(self, report_date):
#         report_dt = datetime.strptime(str(report_date), '%Y-%m-%d')
#         return report_dt.replace(month=1, day=1).date(), report_dt.date()

#     def _get_previous_year_dates(self, report_date):
#         report_dt    = datetime.strptime(str(report_date), '%Y-%m-%d')
#         prev_year_dt = report_dt - relativedelta(years=1)
#         return (
#             prev_year_dt.replace(month=1, day=1).date(), prev_year_dt.date(),
#             prev_year_dt.replace(day=1).date(),          prev_year_dt.date()
#         )
    
#     def _get_previous_month_dates(self, report_date):
#         report_dt = datetime.strptime(str(report_date), '%Y-%m-%d')
#         prev_month_end   = report_dt.replace(day=1) - relativedelta(days=1)
#         prev_month_start = prev_month_end.replace(day=1)
#         return prev_month_start.date(), prev_month_end.date()
    
    
#     def _get_actual_for_position(self, budget_post, date_from, date_to, branch_ids=None, company_ids=None):
#         """Return (credit-debit) for all accounts of budget_post."""
#         acc_ids = budget_post.account_ids.ids
#         if not acc_ids:
#             return 0.0

#         aml_obj = self.env['account.move.line']
#         domain = [
#             ('account_id', 'in', acc_ids),
#             ('date', '>=', date_from),
#             ('date', '<=', date_to),
#             ('move_id.state', 'in', ['draft', 'posted']),
#         ]
#         if branch_ids:
#             domain.append(('branch_id', 'in', branch_ids))

#         if company_ids:
#             domain.append(
#                 ('company_id', 'in', company_ids)
#             )

#         where_query = aml_obj._where_calc(domain)
#         aml_obj._apply_ir_rules(where_query, 'read')
#         from_clause, where_clause, where_clause_params = where_query.get_sql()
#         sql = (
#             "SELECT COALESCE(SUM(credit) - SUM(debit), 0.0) "
#             "FROM " + from_clause + " WHERE " + where_clause
#         )
#         self.env.cr.execute(sql, where_clause_params)
#         return self.env.cr.fetchone()[0] or 0.0


#     def _get_actual_for_budget_positions(self,bp_ids,date_from,date_to,branch_ids=None,company_ids=None):
#         total_actual = 0.0
#         BudgetPost = self.env['account.budget.post']
#         for bp_id in bp_ids:
#             bp = BudgetPost.browse(bp_id)
#             if not bp.exists():
#                 continue
#             total_actual += self._get_actual_for_position(bp,date_from,date_to,branch_ids,company_ids)
#         return total_actual

#     def _get_budget_data(self, domain, date_from, date_to,
#                      branch_ids=None, include_zero_budget=True, company_ids=None):
#         period_domain = domain + [
#             ('date_from', '>=', date_from),
#             ('date_to', '<=', date_to),
#         ]
#         budget_lines = self.env['crossovered.budget.lines'].search(period_domain)

#         budget_data = {}
#         for line in budget_lines:
#             bp = line.general_budget_id
#             key = (bp.name or '').strip().lower()          # <-- was: bp.id
#             if key not in budget_data:
#                 main_group = getattr(bp, 'main_group_id', False)
#                 budget_type = getattr(main_group, 'budget_type', 'expense') or 'expense'

#                 budget_data[key] = {
#                     'name':         bp.name,
#                     'bp':           bp,
#                     'bp_ids':       set(),                  # <-- track contributing posts
#                     'budget':       0.0,
#                     'actual_raw':   0.0,
#                     'actual':       0.0,
#                     'has_budget':   True,
#                     'main_group':   main_group,
#                     'sub_group':    getattr(bp, 'sub_group_id', False),
#                     'sequence':     getattr(bp, 'sequence', 0) or 0,
#                     'budget_type':  budget_type,
#                 }
#             budget_data[key]['bp_ids'].add(bp.id)
#             budget_data[key]['budget']     += line.planned_amount
#             # budget_data[key]['actual_raw'] += line.practical_amount

#         # ---------------------------------------------------------
#         # 2. Calculate ACTUAL directly from account.move.line
#         #    This includes BOTH draft + posted.
#         # ---------------------------------------------------------
#         for key, data in budget_data.items():
#             raw_actual = self._get_actual_for_budget_positions(data['bp_ids'],date_from,date_to,branch_ids,company_ids)
#             data['actual_raw'] = raw_actual

#         if include_zero_budget:
#             bp_domain = [('account_ids', '!=', False)]
#             if branch_ids:
#                 bp_domain = [
#                     ('account_ids', '!=', False),
#                     ('branch_id', 'in', branch_ids),
#                 ]
#             all_positions = self.env['account.budget.post'].search(bp_domain)

#             for bp in all_positions:
#                 if branch_ids and bp.branch_id and bp.branch_id.id not in branch_ids:
#                     continue

#                 key = (bp.name or '').strip().lower()       # <-- same key logic
#                 if key in budget_data and bp.id in budget_data[key]['bp_ids']:
#                     continue                                 # already counted via budget lines

#                 raw_actual = self._get_actual_for_position(bp, date_from, date_to, branch_ids)
#                 main_group = getattr(bp, 'main_group_id', False)
#                 budget_type = getattr(main_group, 'budget_type', 'expense') or 'expense'

#                 if key not in budget_data:
#                     budget_data[key] = {
#                         'name':        bp.name,
#                         'bp':          bp,
#                         'bp_ids':      set(),
#                         'budget':      0.0,
#                         'actual_raw':  0.0,
#                         'actual':      0.0,
#                         'has_budget':  False,
#                         'main_group':  main_group,
#                         'sub_group':   getattr(bp, 'sub_group_id', False),
#                         'sequence':    getattr(bp, 'sequence', 0) or 0,
#                         'budget_type': budget_type,
#                     }
#                 budget_data[key]['bp_ids'].add(bp.id)
#                 budget_data[key]['actual_raw'] += raw_actual

#         for d in budget_data.values():
#             budget_type = d.get('budget_type', '').lower()
#             raw_actual = d['actual_raw']
#             if budget_type == 'revenue':
#                 d['actual'] = raw_actual
#             else:
#                 d['actual'] = -raw_actual
#             if budget_type == 'revenue':
#                 d['variance'] = d['actual'] - d['budget']
#             else:
#                 d['variance'] = d['budget'] - d['actual']

#         return budget_data

#     # ─────────────────────────────────────────────────────────────────────────
#     # CONSOLIDATED DATA (multi-period, flat)
#     # ─────────────────────────────────────────────────────────────────────────

#     def _get_consolidated_data(self, domain, report_date, branch_ids=None):
#         """Return flat dict keyed by budget_post id with all period columns."""
#         month_from,   month_to   = self._get_month_dates(report_date)
#         ytd_from,     ytd_to     = self._get_ytd_dates(report_date)
#         ytd_from_prev, ytd_to_prev, month_from_prev, month_to_prev = \
#             self._get_previous_year_dates(report_date)
#         prev_month_from, prev_month_to = self._get_previous_month_dates(report_date)

#         ytd_data          = self._get_budget_data(domain, ytd_from,        ytd_to,        branch_ids)
#         monthly_data      = self._get_budget_data(domain, month_from,      month_to,      branch_ids)
#         ytd_prev_data     = self._get_budget_data(domain, ytd_from_prev,   ytd_to_prev,   branch_ids)
#         monthly_prev_data = self._get_budget_data(domain, month_from_prev, month_to_prev, branch_ids)
#         prev_month_data   = self._get_budget_data(domain, prev_month_from, prev_month_to, branch_ids)

#         all_positions = set(
#             list(ytd_data) + list(monthly_data) +
#             list(ytd_prev_data) + list(monthly_prev_data) + list(prev_month_data)
#         )

#         consolidated = {}
#         for pid in all_positions:
#             meta = (
#                 ytd_data.get(pid) or monthly_data.get(pid) or
#                 ytd_prev_data.get(pid) or monthly_prev_data.get(pid) or {}
#             )
#             name = meta.get('name', '')
#             if not name:
#                 continue
                
#             consolidated[pid] = {
#                 'name':               name,
#                 'has_budget':         (
#                     ytd_data.get(pid, {}).get('has_budget', False) or
#                     monthly_data.get(pid, {}).get('has_budget', False)
#                 ),
#                 'main_group':         meta.get('main_group', False),
#                 'sub_group':          meta.get('sub_group', False),
#                 'sequence':           meta.get('sequence', 0),
#                 'budget_type':        meta.get('budget_type', 'expense'),
#                 # period columns (using display actual)
#                 'ytd_budget':         ytd_data.get(pid, {}).get('budget',   0),
#                 'ytd_actual':         ytd_data.get(pid, {}).get('actual',   0),
#                 'ytd_variance':       ytd_data.get(pid, {}).get('variance', 0),
#                 'ytd_prev_actual':    ytd_prev_data.get(pid, {}).get('actual',   0),
#                 'monthly_budget':     monthly_data.get(pid, {}).get('budget',   0),
#                 'monthly_actual':     monthly_data.get(pid, {}).get('actual',   0),
#                 'monthly_variance':   monthly_data.get(pid, {}).get('variance', 0),
#                 'prev_month_actual':  prev_month_data.get(pid, {}).get('actual',   0),
#                 'monthly_prev_actual':monthly_prev_data.get(pid, {}).get('actual', 0),
#             }
#         return consolidated

#     # ─────────────────────────────────────────────────────────────────────────
#     # SHARED FORMAT BUILDER
#     # ─────────────────────────────────────────────────────────────────────────

#     def _build_formats(self, workbook):
#         num_fmt = '#,##0_);(#,##0)'

#         def mfmt(bg=None, fc=None, bold_=False, italic_=False, border=1,
#                  num_format=None):
#             f = {'num_format': num_format or num_fmt, 'border': border}
#             if bg:     f['bg_color']   = bg
#             if fc:     f['font_color'] = fc
#             if bold_:  f['bold']       = True
#             if italic_:f['italic']     = True
#             return workbook.add_format(f)

#         def tfmt(bg=None, bold_=False, fc=None, italic_=False, border=1):
#             f = {'border': border}
#             if bg:     f['bg_color']   = bg
#             if bold_:  f['bold']       = True
#             if fc:     f['font_color'] = fc
#             if italic_:f['italic']     = True
#             return workbook.add_format(f)

#         return {
#             'bold':      workbook.add_format({'bold': True}),
#             'title':     workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center'}),
#             'subtitle':  workbook.add_format({'bold': True, 'font_size': 12, 'align': 'center'}),
#             'header':    workbook.add_format({
#                              'bold': True, 'bg_color': '#D3D3D3', 'border': 1,
#                              'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
#                          }),
#             'border':    workbook.add_format({'border': 1}),
#             'note':      workbook.add_format({'italic': True, 'font_color': '#595959', 'font_size': 9}),

#             'det_text':       tfmt(),
#             'det_text_zero':  tfmt(fc='#595959', italic_=True),
#             'det_money':      mfmt(),
#             'det_money_neg':  mfmt(fc='red'),
#             'det_zero_pos':   mfmt(fc='#595959', italic_=True),
#             'det_zero_neg':   mfmt(fc='red',      italic_=True),

#             'sub_text':       tfmt(bg='#CCE5FF', bold_=True),
#             'sub_money':      mfmt(bg='#CCE5FF', bold_=True),
#             'sub_money_neg':  mfmt(bg='#CCE5FF', bold_=True, fc='red'),

#             'main_text':      tfmt(bg='#99CCFF', bold_=True),
#             'main_money':     mfmt(bg='#99CCFF', bold_=True),
#             'main_money_neg': mfmt(bg='#99CCFF', bold_=True, fc='red'),

#             'net_text':       tfmt(bg='#ADD8E6', bold_=True),
#             'net_money':      mfmt(bg='#ADD8E6', bold_=True),
#             'net_money_neg':  mfmt(bg='#ADD8E6', bold_=True, fc='red'),

#             'grand_text':      tfmt(bg='#0066CC', bold_=True, fc='#FFFFFF'),
#             'grand_money':     mfmt(bg='#0066CC', bold_=True, fc='#FFFFFF'),
#             'grand_money_neg': workbook.add_format({
#                                    'bold': True, 'bg_color': '#0066CC', 'border': 1,
#                                    'font_color': '#FF9999', 'num_format': num_fmt,
#                                }),

#             'total_pos': workbook.add_format({
#                              'bold': True, 'bg_color': '#D3D3D3', 'border': 1,
#                              'num_format': num_fmt,
#                          }),
#             'total_neg': workbook.add_format({
#                              'bold': True, 'bg_color': '#D3D3D3', 'border': 1,
#                              'num_format': num_fmt, 'font_color': 'red',
#                          }),

#             'mg_label': workbook.add_format({
#                              'bold': True, 'bg_color': '#E6E6E6', 'border': 1,
#                          }),
#             'sg_label': workbook.add_format({
#                              'bold': True, 'bg_color': '#F2F2F2', 'border': 1,
#                              'indent': 1,
#                          }),
#         }

#     # ─────────────────────────────────────────────────────────────────────────
#     # VARIANCE SUMMARY HELPERS
#     # ─────────────────────────────────────────────────────────────────────────

#     _SUM_KEYS = [
#         'ytd_budget', 'ytd_actual', 'ytd_variance',
#         'ytd_prev_actual',
#         'monthly_budget', 'monthly_actual',
#         'prev_month_actual', 'monthly_variance',
#         'monthly_prev_actual',
#     ]
#     _SUM_COL = {
#         'ytd_budget':          2,
#         'ytd_actual':          3,
#         'ytd_variance':        4,
#         'ytd_prev_actual':     5,
#         'monthly_budget':      6,
#         'monthly_actual':      7,
#         'prev_month_actual':   8,
#         'monthly_variance':    9,
#         'monthly_prev_actual': 10,
#     }
#     _SUM_VAR_KEYS = {'ytd_variance', 'monthly_variance'}

#     def _zero_sum_vals(self):
#         return {k: 0.0 for k in self._SUM_KEYS}

#     def _add_sum_vals(self, a, b):
#         r = {k: a[k] + b[k] for k in self._SUM_KEYS}
#         # Recalculate variance based on budget_type
#         budget_type = a.get('budget_type', 'expense')
#         if budget_type == 'revenue':
#             r['ytd_variance'] = r['ytd_actual'] - r['ytd_budget']
#             r['monthly_variance'] = r['monthly_actual'] - r['monthly_budget']
#         else:
#             r['ytd_variance'] = r['ytd_budget'] - r['ytd_actual']
#             r['monthly_variance'] = r['monthly_budget'] - r['monthly_actual']
#         return r

#     def _sub_sum_vals(self, a, b):
#         r = {k: a[k] - b[k] for k in self._SUM_KEYS}
#         r['ytd_variance'] = r['ytd_actual'] - r['ytd_budget']
#         r['monthly_variance'] = r['monthly_actual'] - r['monthly_budget']
#         return r

#     def _write_sum_money_cell(self, sheet, row, key, value, pos_fmt, neg_fmt):
#         col = self._SUM_COL[key]
#         if key in self._SUM_VAR_KEYS and value < 0:
#             sheet.write(row, col, value, neg_fmt)
#         else:
#             sheet.write(row, col, value, pos_fmt)

#     def _write_sum_row(self, sheet, row, label, vals, text_fmt, money_fmt, money_neg_fmt):
#         sheet.write(row, 0, label, text_fmt)
#         for k in self._SUM_KEYS:
#             self._write_sum_money_cell(sheet, row, k, vals[k], money_fmt, money_neg_fmt)

#     # ─────────────────────────────────────────────────────────────────────────
#     # SHEET 1 – VARIANCE SUMMARY
#     # ─────────────────────────────────────────────────────────────────────────

#     def _generate_variance_summary_sheet(self, workbook, data, report_date, fmt):
#         NUM_COLS   = 11
#         HEADER_ROW = 6

#         sheet = workbook.add_worksheet('Variance Summary')

#         report_dt      = datetime.strptime(report_date, '%Y-%m-%d')
#         report_month   = report_dt.strftime('%b %y')
#         prev_month_lbl = (report_dt - relativedelta(months=1)).strftime('%b %y')
#         prev_year_dt   = report_dt - relativedelta(years=1)
#         prev_year_lbl  = prev_year_dt.strftime('%b %y')
#         prev_year_full = prev_year_dt.strftime('%b %Y')

#         company_ids  = data.get('company_ids', [])
#         branch_ids   = data.get('branch_ids',  [])
#         budget_ids   = data.get('budget_ids',  [])

#         companies    = self.env['res.company'].browse(company_ids)
#         company_name = ' & '.join(companies.mapped('name')) or 'All Companies'

#         sheet.merge_range(0, 0, 0, NUM_COLS - 1, company_name.upper(), fmt['title'])
#         sheet.merge_range(
#             1, 0, 1, NUM_COLS - 1,
#             f'Operational Results for the month of {report_month} - Consolidated',
#             fmt['subtitle']
#         )

#         sheet.write(2, 0, 'Companies:', fmt['bold'])
#         sheet.write(2, 1, company_name)

#         sheet.write(3, 0, 'Branch:', fmt['bold'])
#         sheet.write(3, 1,
#             ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name'))
#             if branch_ids else 'All Branches'
#         )

#         sheet.write(4, 0, 'Budget:', fmt['bold'])
#         sheet.write(4, 1,
#             ', '.join(self.env['crossovered.budget'].browse(budget_ids).mapped('name'))
#             if budget_ids else 'All Budgets'
#         )

#         headers = [
#             'Particulars',
#             'Analytical Account',
#             f'YTD ({report_month})\nBudget',
#             f'YTD ({report_month})\nActual',
#             'YTD\nVariance',
#             f'YTD ({prev_year_full})\nActual',
#             f'Budget\n({report_month})',
#             f'Actual\n({report_month})',
#             f'Actual\n({prev_month_lbl})',
#             'Variance',
#             f'Actual\n({prev_year_lbl})',
#         ]
#         for col, hdr in enumerate(headers):
#             sheet.write(HEADER_ROW, col, hdr, fmt['header'])
#         sheet.set_row(HEADER_ROW, 30)

#         domain = [('company_id', 'in', company_ids)]
#         if budget_ids:
#             domain.append(('crossovered_budget_id', 'in', budget_ids))
#         if branch_ids:
#             if 'branch_id' in self.env['crossovered.budget.lines']._fields:
#                 domain.append(('branch_id', 'in', branch_ids))
#             elif 'branch_id' in self.env['account.analytic.account']._fields:
#                 domain.append(('analytic_account_id.branch_id', 'in', branch_ids))

#         month_from,      month_to      = self._get_month_dates(report_date)
#         ytd_from,        ytd_to        = self._get_ytd_dates(report_date)
#         prev_month_from, prev_month_to = self._get_previous_month_dates(report_date)
#         ytd_from_prev, ytd_to_prev, month_from_prev, month_to_prev = \
#             self._get_previous_year_dates(report_date)

#         ytd_data          = self._get_budget_data(domain, ytd_from,        ytd_to,        branch_ids)
#         monthly_data      = self._get_budget_data(domain, month_from,      month_to,      branch_ids)
#         prev_month_data   = self._get_budget_data(domain, prev_month_from, prev_month_to, branch_ids)
#         ytd_prev_data     = self._get_budget_data(domain, ytd_from_prev,   ytd_to_prev,   branch_ids)
#         monthly_prev_data = self._get_budget_data(domain, month_from_prev, month_to_prev, branch_ids)

#         def _build_mg_totals():
#             mg_totals = {}
#             all_ids = set(
#                 list(ytd_data) + list(monthly_data) + list(prev_month_data) +
#                 list(ytd_prev_data) + list(monthly_prev_data)
#             )
#             for pid in all_ids:
#                 ytd_row  = ytd_data.get(pid, {})
#                 mon_row  = monthly_data.get(pid, {})
#                 prv_row  = prev_month_data.get(pid, {})
#                 ytdp_row = ytd_prev_data.get(pid, {})
#                 monp_row = monthly_prev_data.get(pid, {})
#                 meta = ytd_row or mon_row or ytdp_row or {}
#                 mg   = meta.get('main_group', False)
#                 mg_name = (mg.name.strip() if mg and mg.name else 'Uncategorised')
#                 key = mg_name.lower()
#                 if key not in mg_totals:
#                     mg_totals[key] = {
#                         '_name': mg_name, 
#                         'budget_type': meta.get('budget_type', 'expense'), 
#                         **self._zero_sum_vals()
#                     }
#                 mg_totals[key]['ytd_budget']          += ytd_row.get('budget', 0)
#                 mg_totals[key]['ytd_actual']           += ytd_row.get('actual', 0)
#                 mg_totals[key]['monthly_budget']       += mon_row.get('budget', 0)
#                 mg_totals[key]['monthly_actual']       += mon_row.get('actual', 0)
#                 mg_totals[key]['prev_month_actual']    += prv_row.get('actual', 0)
#                 mg_totals[key]['ytd_prev_actual']      += ytdp_row.get('actual', 0)
#                 mg_totals[key]['monthly_prev_actual']  += monp_row.get('actual', 0)

#             for key, v in mg_totals.items():
#                 mg_name_lower = v.get('_name', '').strip().lower()
#                 is_revenue = (mg_name_lower == 'revenue')
#                 if is_revenue:
#                     v['ytd_variance'] = v['ytd_actual'] - v['ytd_budget']
#                     v['monthly_variance'] = v['monthly_actual'] - v['monthly_budget']
#                 else:
#                     v['ytd_variance'] = v['ytd_budget'] - v['ytd_actual']
#                     v['monthly_variance'] = v['monthly_budget'] - v['monthly_actual']
#             return mg_totals

#         def _build_expense_sg_totals():
#             sg_totals = {}
#             all_ids = set(
#                 list(ytd_data) + list(monthly_data) + list(prev_month_data) +
#                 list(ytd_prev_data) + list(monthly_prev_data)
#             )
#             for pid in all_ids:
#                 ytd_row  = ytd_data.get(pid, {})
#                 mon_row  = monthly_data.get(pid, {})
#                 prv_row  = prev_month_data.get(pid, {})
#                 ytdp_row = ytd_prev_data.get(pid, {})
#                 monp_row = monthly_prev_data.get(pid, {})
#                 meta = ytd_row or mon_row or ytdp_row or {}
#                 mg   = meta.get('main_group', False)
#                 if not mg or (mg.name or '').strip().lower() != 'expenses':
#                     continue
#                 sg      = meta.get('sub_group', False)
#                 sg_name = (sg.name.strip() if sg and sg.name else 'Other Expenses')
#                 key     = sg_name.lower()
#                 if key not in sg_totals:
#                     sg_totals[key] = {
#                         '_name': sg_name,
#                         '_seq':  getattr(sg, 'sequence', 0) or 0,
#                         **self._zero_sum_vals(),
#                     }
#                 sg_totals[key]['ytd_budget']          += ytd_row.get('budget', 0)
#                 sg_totals[key]['ytd_actual']           += ytd_row.get('actual', 0)
#                 sg_totals[key]['monthly_budget']       += mon_row.get('budget', 0)
#                 sg_totals[key]['monthly_actual']       += mon_row.get('actual', 0)
#                 sg_totals[key]['prev_month_actual']    += prv_row.get('actual', 0)
#                 sg_totals[key]['ytd_prev_actual']      += ytdp_row.get('actual', 0)
#                 sg_totals[key]['monthly_prev_actual']  += monp_row.get('actual', 0)

#             for v in sg_totals.values():
#                 v['ytd_variance'] = v['ytd_budget'] - v['ytd_actual']
#                 v['monthly_variance'] = v['monthly_budget'] - v['monthly_actual']
#             return sg_totals

#         mg_totals = _build_mg_totals()
#         zero      = self._zero_sum_vals()

#         def _mg(name_lower):
#             return {k: v for k, v in mg_totals.get(name_lower, zero).items()
#                     if k in self._SUM_KEYS}

#         rev_vals  = _mg('revenue')
#         cor_vals  = _mg('cost of revenue')
#         exp_vals  = _mg('expenses')

#         row = HEADER_ROW + 1

#         self._write_sum_row(sheet, row, 'TOTAL: Revenue',
#                             rev_vals, fmt['main_text'],
#                             fmt['main_money'], fmt['main_money_neg'])
#         row += 1

#         self._write_sum_row(sheet, row, 'TOTAL: Cost of Revenue',
#                             cor_vals, fmt['main_text'],
#                             fmt['main_money'], fmt['main_money_neg'])
#         row += 1

#         net_rev_vals = self._sub_sum_vals(rev_vals, cor_vals)
#         self._write_sum_row(sheet, row, 'Net Revenue',
#                             net_rev_vals, fmt['net_text'],
#                             fmt['net_money'], fmt['net_money_neg'])
#         row += 1

#         sg_totals   = _build_expense_sg_totals()
#         DEPR_KEY    = 'depreciation'
#         dep_vals    = zero.copy()
#         op_exp_vals = zero.copy()

#         for sg_key, sgv in sorted(sg_totals.items(),
#                                   key=lambda x: (x[1].get('_seq', 0), x[1]['_name'])):
#             s_vals = {k: sgv[k] for k in self._SUM_KEYS}
#             if sg_key == DEPR_KEY:
#                 dep_vals = s_vals
#             else:
#                 self._write_sum_row(sheet, row, sgv['_name'],
#                                     s_vals, fmt['det_text'],
#                                     fmt['det_money'], fmt['det_money_neg'])
#                 row += 1
#                 op_exp_vals = self._add_sum_vals(op_exp_vals, s_vals)

#         self._write_sum_row(sheet, row, 'OPERATING EXPENSES',
#                             op_exp_vals, fmt['net_text'],
#                             fmt['net_money'], fmt['net_money_neg'])
#         row += 1

#         op_profit_vals = self._sub_sum_vals(rev_vals, op_exp_vals)
#         self._write_sum_row(sheet, row,
#                             'OPERATING PROFIT (Before Depreciation)',
#                             op_profit_vals, fmt['net_text'],
#                             fmt['net_money'], fmt['net_money_neg'])
#         sheet.set_row(row, 30)
#         row += 1

#         ros_pct_fmt = workbook.add_format({
#             'bold': True, 'bg_color': '#ADD8E6', 'border': 1,
#             'num_format': '0.00%',
#         })
#         ros_pct_neg_fmt = workbook.add_format({
#             'bold': True, 'bg_color': '#ADD8E6', 'border': 1,
#             'num_format': '0.00%', 'font_color': 'red',
#         })
#         sheet.merge_range(row, 0, row, 1, 'OPERATING ROS%', fmt['net_text'])
#         for k in self._SUM_KEYS:
#             rev_v = rev_vals.get(k, 0.0)
#             prf_v = op_profit_vals.get(k, 0.0)
#             pct   = (prf_v / rev_v) if rev_v else 0.0
#             neg   = (k in self._SUM_VAR_KEYS and pct < 0)
#             sheet.write(row, self._SUM_COL[k], pct,
#                         ros_pct_neg_fmt if neg else ros_pct_fmt)
#         row += 1

#         self._write_sum_row(sheet, row, 'Depreciation',
#                             dep_vals, fmt['det_text'],
#                             fmt['det_money'], fmt['det_money_neg'])
#         row += 1

#         self._write_sum_row(sheet, row, 'TOTAL: Expenses',
#                             exp_vals, fmt['main_text'],
#                             fmt['main_money'], fmt['main_money_neg'])
#         row += 1

#         direct_exp_vals = self._add_sum_vals(cor_vals, exp_vals)
#         sheet.merge_range(row, 0, row, 1,
#                           'TOTAL: DIRECT + OTHER EXPENSES', fmt['grand_text'])
#         for k in self._SUM_KEYS:
#             self._write_sum_money_cell(sheet, row, k, direct_exp_vals[k],
#                                        fmt['grand_money'], fmt['grand_money_neg'])
#         row += 1

#         grand_vals = self._sub_sum_vals(rev_vals, direct_exp_vals)
#         sheet.merge_range(row, 0, row, 1, 'GRAND TOTAL', fmt['grand_text'])
#         for k in self._SUM_KEYS:
#             self._write_sum_money_cell(sheet, row, k, grand_vals[k],
#                                        fmt['grand_money'], fmt['grand_money_neg'])

#         sheet.set_column(0,  0,  35)
#         sheet.set_column(1,  1,   0)
#         sheet.set_column(2,  2,  15)
#         sheet.set_column(3,  3,  15)
#         sheet.set_column(4,  4,  15)
#         sheet.set_column(5,  5,  20)
#         sheet.set_column(6,  6,  15)
#         sheet.set_column(7,  7,  15)
#         sheet.set_column(8,  8,  15)
#         sheet.set_column(9,  9,  15)
#         sheet.set_column(10, 10, 18)
#         sheet.freeze_panes(HEADER_ROW + 1, 0)

#     # ─────────────────────────────────────────────────────────────────────────
#     # SHEET 2 – VARIANCE REPORT (flat)
#     # ─────────────────────────────────────────────────────────────────────────

#     def _generate_main_variance_sheet(self, workbook, data, report_date, fmt):
#         company_ids = data.get('company_ids', [])
#         branch_ids  = data.get('branch_ids',  [])
#         budget_ids  = data.get('budget_ids',  [])

#         domain = [('company_id', 'in', company_ids)]
#         if budget_ids:
#             domain.append(('crossovered_budget_id', 'in', budget_ids))
#         if branch_ids:
#             if 'branch_id' in self.env['crossovered.budget.lines']._fields:
#                 domain.append(('branch_id', 'in', branch_ids))
#             elif 'branch_id' in self.env['account.analytic.account']._fields:
#                 domain.append(('analytic_account_id.branch_id', 'in', branch_ids))

#         month_from, month_to = self._get_month_dates(report_date)
#         ytd_from,   ytd_to   = self._get_ytd_dates(report_date)

#         monthly_data = self._get_budget_data(domain, month_from, month_to, branch_ids)
#         ytd_data     = self._get_budget_data(domain, ytd_from,   ytd_to,   branch_ids)

#         sheet = workbook.add_worksheet('Variance Report')

#         report_month = datetime.strptime(report_date, '%Y-%m-%d').strftime('%b %Y')

#         NUM_COLS = 8

#         sheet.merge_range(0, 0, 0, NUM_COLS - 1,
#                         f'Variance Report for the month of {report_month}',
#                         fmt['title'])

#         companies = self.env['res.company'].browse(company_ids)
#         sheet.write(1, 0, 'Companies:', fmt['bold'])
#         sheet.write(1, 1, ', '.join(companies.mapped('name')) or 'All Companies')

#         sheet.write(2, 0, 'Branch:', fmt['bold'])
#         branch_names = (
#             ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name'))
#             if branch_ids else 'All Branches'
#         )
#         sheet.write(2, 1, branch_names)

#         sheet.write(3, 0, 'Budget:', fmt['bold'])
#         budget_names = (
#             ', '.join(self.env['crossovered.budget'].browse(budget_ids).mapped('name'))
#             if budget_ids else 'All Budgets'
#         )
#         sheet.write(3, 1, budget_names)

#         sheet.write(4, 0,
#                     '* Italicised rows have no budget allocation; '
#                     'actual amounts are from posted transactions.',
#                     fmt['note'])

#         headers = [
#             'Particulars', 'Budget', 'Actual', 'Variance',
#             'Reasons for Variance', 'YTD Budget', 'YTD Actual', 'YTD Variance',
#         ]
#         for col, hdr in enumerate(headers):
#             sheet.write(5, col, hdr, fmt['header'])

#         row = 6

#         all_ids = set(list(monthly_data.keys()) + list(ytd_data.keys()))

#         _BLANK_MG_ID = -1
#         _BLANK_SG_ID = -1

#         hierarchy = {}

#         for pid in all_ids:
#             m    = monthly_data.get(pid, {})
#             y    = ytd_data.get(pid, {})
#             meta = m or y
#             if not meta.get('name'):
#                 continue

#             mg  = meta.get('main_group', False)
#             sg  = meta.get('sub_group', False)

#             if mg and mg.id:
#                 mg_id, mg_name = mg.id, mg.name.strip() or 'Uncategorised'
#                 mg_seq = getattr(mg, 'sequence', 0) or 0
#                 mg_budget_type = getattr(mg, 'budget_type', 'expense') or 'expense'
#             else:
#                 mg_id, mg_name, mg_seq = _BLANK_MG_ID, 'Uncategorised', 9999
#                 mg_budget_type = 'expense'

#             if mg_id not in hierarchy:
#                 hierarchy[mg_id] = {
#                     'name': mg_name, 'sequence': mg_seq,
#                     'budget_type': mg_budget_type,
#                     'sub_groups': {}, 'sub_group_totals': {},
#                     'monthly_budget': 0.0, 'monthly_actual': 0.0, 'monthly_variance': 0.0,
#                     'ytd_budget':     0.0, 'ytd_actual':     0.0, 'ytd_variance':     0.0,
#                 }

#             if sg and sg.id:
#                 sg_id, sg_name = sg.id, sg.name.strip() or 'General'
#                 sg_seq = getattr(sg, 'sequence', 0) or 0
#             else:
#                 sg_id, sg_name, sg_seq = _BLANK_SG_ID, 'General', 9999

#             mg_node = hierarchy[mg_id]

#             if sg_id not in mg_node['sub_groups']:
#                 mg_node['sub_groups'][sg_id] = {
#                     'name': sg_name, 'sequence': sg_seq,
#                     'budget_positions': [],
#                     'budget_type': mg_budget_type,
#                 }
#                 mg_node['sub_group_totals'][sg_id] = {
#                     'name': sg_name,
#                     'budget_type': mg_budget_type,
#                     'monthly_budget': 0.0, 'monthly_actual': 0.0, 'monthly_variance': 0.0,
#                     'ytd_budget':     0.0, 'ytd_actual':     0.0, 'ytd_variance':     0.0,
#                 }

#             bp_row = {
#                 'name':             meta['name'],
#                 'has_budget':       m.get('has_budget', False) or y.get('has_budget', False),
#                 'sequence':         meta.get('sequence', 0) or 0,
#                 'monthly_budget':   m.get('budget',   0.0),
#                 'monthly_actual':   m.get('actual',   0.0),
#                 'monthly_variance': m.get('variance', 0.0),
#                 'ytd_budget':       y.get('budget',   0.0),
#                 'ytd_actual':       y.get('actual',   0.0),
#                 'ytd_variance':     y.get('variance', 0.0),
#             }
#             mg_node['sub_groups'][sg_id]['budget_positions'].append(bp_row)

#             sgt = mg_node['sub_group_totals'][sg_id]
#             for src, dest in [
#                 ('monthly_budget', 'monthly_budget'),
#                 ('monthly_actual', 'monthly_actual'),
#                 ('ytd_budget',     'ytd_budget'),
#                 ('ytd_actual',     'ytd_actual'),
#             ]:
#                 sgt[dest]     += bp_row[src]
#                 mg_node[dest] += bp_row[src]

#         for mg_node in hierarchy.values():
#             is_revenue = mg_node.get('budget_type', 'expense').lower() == 'revenue'
#             if is_revenue:
#                 mg_node['monthly_variance'] = mg_node['monthly_actual'] - mg_node['monthly_budget']
#                 mg_node['ytd_variance']     = mg_node['ytd_actual']     - mg_node['ytd_budget']
#             else:
#                 mg_node['monthly_variance'] = mg_node['monthly_budget'] - mg_node['monthly_actual']
#                 mg_node['ytd_variance']     = mg_node['ytd_budget']     - mg_node['ytd_actual']

#             for sgt in mg_node['sub_group_totals'].values():
#                 is_rev_sg = sgt.get('budget_type', 'expense').lower() == 'revenue'
#                 if is_rev_sg:
#                     sgt['monthly_variance'] = sgt['monthly_actual'] - sgt['monthly_budget']
#                     sgt['ytd_variance']     = sgt['ytd_actual']     - sgt['ytd_budget']
#                 else:
#                     sgt['monthly_variance'] = sgt['monthly_budget'] - sgt['monthly_actual']
#                     sgt['ytd_variance']     = sgt['ytd_budget']     - sgt['ytd_actual']

#         def _write_detail_row(r, bp):
#             has_budget = bp.get('has_budget', False)
#             t_fmt = fmt['det_text'] if has_budget else fmt['det_text_zero']
#             m_fmt = fmt['det_money']
#             z_fmt = fmt['det_zero_pos']

#             sheet.write(r, 0, '        ' + bp['name'], t_fmt)
#             sheet.write(r, 1, bp['monthly_budget'], m_fmt if has_budget else z_fmt)
#             sheet.write(r, 2, bp['monthly_actual'], m_fmt if has_budget else z_fmt)
#             mv = bp['monthly_variance']
#             sheet.write(r, 3, mv,
#                         (fmt['det_money_neg'] if mv < 0 else fmt['det_money'])
#                         if has_budget else
#                         (fmt['det_zero_neg']  if mv < 0 else fmt['det_zero_pos']))
#             sheet.write(r, 4, '', fmt['border'])
#             sheet.write(r, 5, bp['ytd_budget'], m_fmt if has_budget else z_fmt)
#             sheet.write(r, 6, bp['ytd_actual'], m_fmt if has_budget else z_fmt)
#             yv = bp['ytd_variance']
#             sheet.write(r, 7, yv,
#                         (fmt['det_money_neg'] if yv < 0 else fmt['det_money'])
#                         if has_budget else
#                         (fmt['det_zero_neg']  if yv < 0 else fmt['det_zero_pos']))

#         def _write_sg_total(r, label, sgt):
#             sheet.write(r, 0, '    ' + label, fmt['sub_text'])
#             sheet.write(r, 1, sgt['monthly_budget'], fmt['sub_money'])
#             sheet.write(r, 2, sgt['monthly_actual'], fmt['sub_money'])
#             mv = sgt['monthly_variance']
#             sheet.write(r, 3, mv, fmt['sub_money_neg'] if mv < 0 else fmt['sub_money'])
#             sheet.write(r, 4, '', fmt['sub_text'])
#             sheet.write(r, 5, sgt['ytd_budget'], fmt['sub_money'])
#             sheet.write(r, 6, sgt['ytd_actual'], fmt['sub_money'])
#             yv = sgt['ytd_variance']
#             sheet.write(r, 7, yv, fmt['sub_money_neg'] if yv < 0 else fmt['sub_money'])

#         def _write_mg_total(r, label, mg):
#             sheet.write(r, 0, label, fmt['main_text'])
#             sheet.write(r, 1, mg['monthly_budget'], fmt['main_money'])
#             sheet.write(r, 2, mg['monthly_actual'], fmt['main_money'])
#             mv = mg['monthly_variance']
#             sheet.write(r, 3, mv, fmt['main_money_neg'] if mv < 0 else fmt['main_money'])
#             sheet.write(r, 4, '', fmt['main_text'])
#             sheet.write(r, 5, mg['ytd_budget'], fmt['main_money'])
#             sheet.write(r, 6, mg['ytd_actual'], fmt['main_money'])
#             yv = mg['ytd_variance']
#             sheet.write(r, 7, yv, fmt['main_money_neg'] if yv < 0 else fmt['main_money'])

#         FIXED_MG_ORDER = ['revenue', 'cost of revenue', 'expenses']

#         def _mg_sort_key(mg_node):
#             name_lower = (mg_node.get('name') or '').strip().lower()
#             try:
#                 return (FIXED_MG_ORDER.index(name_lower), 0, '')
#             except ValueError:
#                 return (999, mg_node.get('sequence', 0), mg_node.get('name', ''))

#         grand_total = {
#             'monthly_budget': 0.0, 'monthly_actual': 0.0, 'monthly_variance': 0.0,
#             'ytd_budget':     0.0, 'ytd_actual':     0.0, 'ytd_variance':     0.0,
#         }
#         # new
#         rev_totals      = dict.fromkeys(('monthly_budget', 'monthly_actual', 'ytd_budget', 'ytd_actual'), 0.0)
#         direct_exp_totals = dict.fromkeys(('monthly_budget', 'monthly_actual', 'ytd_budget', 'ytd_actual'), 0.0)

#         for mg_node in sorted(hierarchy.values(), key=_mg_sort_key):
#             sheet.write(row, 0, mg_node['name'].upper(), fmt['mg_label'])
#             blank_mg_fmt = workbook.add_format({'bg_color': '#E6E6E6', 'border': 1})
#             for c in range(1, NUM_COLS):
#                 sheet.write(row, c, '', blank_mg_fmt)
#             row += 1

#             sg_items = sorted(
#                 [
#                     (sg_id, sg, mg_node['sub_group_totals'].get(sg_id, {}))
#                     for sg_id, sg in mg_node['sub_groups'].items()
#                 ],
#                 key=lambda x: (x[1].get('sequence', 0), x[1].get('name', ''))
#             )

#             for sg_id, sg, sgt in sg_items:
#                 sheet.write(row, 0, sg['name'], fmt['sg_label'])
#                 blank_sg_fmt = workbook.add_format({'bg_color': '#F2F2F2', 'border': 1})
#                 for c in range(1, NUM_COLS):
#                     sheet.write(row, c, '', blank_sg_fmt)
#                 row += 1

#                 for bp in sorted(
#                     sg['budget_positions'],
#                     key=lambda x: (x.get('sequence', 0), x.get('name', ''))
#                 ):
#                     _write_detail_row(row, bp)
#                     row += 1

#                 _write_sg_total(row, f'Total: {sg["name"]}', sgt)
#                 row += 1

#             _write_mg_total(row, f'TOTAL: {mg_node["name"]}', mg_node)
#             row += 1
#             # new
#             name_lower = (mg_node.get('name') or '').strip().lower()
#             target = rev_totals if name_lower == 'revenue' else direct_exp_totals
#             for k in ('monthly_budget', 'monthly_actual', 'ytd_budget', 'ytd_actual'):
#                 target[k] += mg_node[k]

#             # for k in ('monthly_budget', 'monthly_actual', 'ytd_budget', 'ytd_actual'):
#             #     grand_total[k] += mg_node[k]
#         for k in ('monthly_budget', 'monthly_actual', 'ytd_budget', 'ytd_actual'):
#             grand_total[k] = rev_totals[k] - direct_exp_totals[k]

#         grand_total['monthly_variance'] = grand_total['monthly_actual'] - grand_total['monthly_budget']
#         grand_total['ytd_variance']     = grand_total['ytd_actual']     - grand_total['ytd_budget']

#         sheet.write(row, 0, 'GRAND TOTAL', fmt['grand_text'])
#         sheet.write(row, 1, grand_total['monthly_budget'], fmt['grand_money'])
#         sheet.write(row, 2, grand_total['monthly_actual'], fmt['grand_money'])
#         mv = grand_total['monthly_variance']
#         sheet.write(row, 3, mv, fmt['grand_money_neg'] if mv < 0 else fmt['grand_money'])
#         sheet.write(row, 4, '', fmt['grand_text'])
#         sheet.write(row, 5, grand_total['ytd_budget'], fmt['grand_money'])
#         sheet.write(row, 6, grand_total['ytd_actual'], fmt['grand_money'])
#         yv = grand_total['ytd_variance']
#         sheet.write(row, 7, yv, fmt['grand_money_neg'] if yv < 0 else fmt['grand_money'])

#         sheet.set_column(0, 0, 35)
#         sheet.set_column(1, 3, 15)
#         sheet.set_column(4, 4, 40)
#         sheet.set_column(5, 7, 15)
#         sheet.freeze_panes(6, 0)

#     # ─────────────────────────────────────────────────────────────────────────
#     # CONSOLIDATED SHEET HELPERS
#     # ─────────────────────────────────────────────────────────────────────────

#     _CON_KEYS = [
#         'ytd_budget', 'ytd_actual', 'ytd_variance',
#         'ytd_prev_actual',
#         'monthly_budget', 'monthly_actual',
#         'prev_month_actual', 'monthly_variance',
#         'monthly_prev_actual',
#     ]
#     _CON_COL = {
#         'ytd_budget':          1,
#         'ytd_actual':          2,
#         'ytd_variance':        3,
#         'ytd_prev_actual':     4,
#         'monthly_budget':      5,
#         'monthly_actual':      6,
#         'prev_month_actual':   7,
#         'monthly_variance':    8,
#         'monthly_prev_actual': 9,
#     }
#     _CON_VAR_KEYS = {'ytd_variance', 'monthly_variance'}

#     def _zero_con_vals(self):
#         return {k: 0.0 for k in self._CON_KEYS}

#     def _add_con_vals(self, a, b):
#         r = {k: a[k] + b[k] for k in self._CON_KEYS}
#         budget_type = a.get('budget_type', 'expense')
#         if budget_type == 'revenue':
#             r['ytd_variance'] = r['ytd_actual'] - r['ytd_budget']
#             r['monthly_variance'] = r['monthly_actual'] - r['monthly_budget']
#         else:
#             r['ytd_variance'] = r['ytd_budget'] - r['ytd_actual']
#             r['monthly_variance'] = r['monthly_budget'] - r['monthly_actual']
#         return r

#     def _sub_con_vals(self, a, b):
#         r = {k: a[k] - b[k] for k in self._CON_KEYS}
#         r['ytd_variance'] = r['ytd_actual'] - r['ytd_budget']
#         r['monthly_variance'] = r['monthly_actual'] - r['monthly_budget']
#         return r

#     def _build_consolidated_hierarchy(self, consolidated_data):
#         _BLANK_ID    = -1
#         _BLANK_SG_ID = -1

#         hierarchy = {}

#         for pid, d in consolidated_data.items():
#             mg  = d.get('main_group', False)
#             sg  = d.get('sub_group', False)
#             seq = d.get('sequence',   0) or 0

#             if mg and mg.id:
#                 mg_id   = mg.id
#                 mg_name = mg.name.strip() or 'Uncategorised'
#                 mg_seq  = getattr(mg, 'sequence', 0) or 0
#                 mg_budget_type = getattr(mg, 'budget_type', 'expense') or 'expense'
#             else:
#                 mg_id   = _BLANK_ID
#                 mg_name = 'Uncategorised'
#                 mg_seq  = 9999
#                 mg_budget_type = 'expense'

#             if mg_id not in hierarchy:
#                 hierarchy[mg_id] = {
#                     'name':             mg_name,
#                     'sequence':         mg_seq,
#                     'budget_type':      mg_budget_type,
#                     'sub_groups':       {},
#                     'sub_group_totals': {},
#                     **self._zero_con_vals(),
#                 }

#             if sg and sg.id:
#                 sg_id   = sg.id
#                 sg_name = sg.name.strip() or 'General'
#                 sg_seq  = getattr(sg, 'sequence', 0) or 0
#             else:
#                 sg_id   = _BLANK_SG_ID
#                 sg_name = 'General'
#                 sg_seq  = 9999

#             mg_node = hierarchy[mg_id]

#             if sg_id not in mg_node['sub_groups']:
#                 mg_node['sub_groups'][sg_id] = {
#                     'name':             sg_name,
#                     'sequence':         sg_seq,
#                     'budget_positions': [],
#                 }
#                 mg_node['sub_group_totals'][sg_id] = {
#                     'name': sg_name,
#                     'budget_type': mg_budget_type,
#                     **self._zero_con_vals(),
#                 }

#             bp_row = {
#                 'name':                d['name'],
#                 'has_budget':          d.get('has_budget', False),
#                 'sequence':            seq,
#                 'ytd_budget':          d['ytd_budget'],
#                 'ytd_actual':          d['ytd_actual'],
#                 'ytd_variance':        d['ytd_variance'],
#                 'ytd_prev_actual':     d['ytd_prev_actual'],
#                 'monthly_budget':      d['monthly_budget'],
#                 'monthly_actual':      d['monthly_actual'],
#                 'prev_month_actual':   d['prev_month_actual'],
#                 'monthly_variance':    d['monthly_variance'],
#                 'monthly_prev_actual': d['monthly_prev_actual'],
#             }
#             mg_node['sub_groups'][sg_id]['budget_positions'].append(bp_row)

#             sgt = mg_node['sub_group_totals'][sg_id]
#             for k in self._CON_KEYS:
#                 sgt[k]     += d.get(k, 0.0)
#                 mg_node[k] += d.get(k, 0.0)

#         for mg_node in hierarchy.values():
#             is_revenue = mg_node.get('budget_type', 'expense').lower() == 'revenue'
#             if is_revenue:
#                 mg_node['ytd_variance'] = mg_node['ytd_actual'] - mg_node['ytd_budget']
#                 mg_node['monthly_variance'] = mg_node['monthly_actual'] - mg_node['monthly_budget']
#             else:
#                 mg_node['ytd_variance'] = mg_node['ytd_budget'] - mg_node['ytd_actual']
#                 mg_node['monthly_variance'] = mg_node['monthly_budget'] - mg_node['monthly_actual']

#             for sgt in mg_node['sub_group_totals'].values():
#                 is_rev_sg = sgt.get('budget_type', 'expense').lower() == 'revenue'
#                 if is_rev_sg:
#                     sgt['ytd_variance'] = sgt['ytd_actual'] - sgt['ytd_budget']
#                     sgt['monthly_variance'] = sgt['monthly_actual'] - sgt['monthly_budget']
#                 else:
#                     sgt['ytd_variance'] = sgt['ytd_budget'] - sgt['ytd_actual']
#                     sgt['monthly_variance'] = sgt['monthly_budget'] - sgt['monthly_actual']

#         return hierarchy

#     def _write_con_money_cell(self, sheet, row, key, value, pos_fmt, neg_fmt):
#         col = self._CON_COL[key]
#         if key in self._CON_VAR_KEYS and value < 0:
#             sheet.write(row, col, value, neg_fmt)
#         else:
#             sheet.write(row, col, value, pos_fmt)

#     def _write_con_data_row(self, sheet, row, vals,
#                             text_fmt, money_fmt, money_neg_fmt, label):
#         sheet.write(row, 0, label, text_fmt)
#         for k in self._CON_KEYS:
#             self._write_con_money_cell(sheet, row, k, vals[k], money_fmt, money_neg_fmt)

#     # ─────────────────────────────────────────────────────────────────────────
#     # SHEET 3 – CONSOLIDATED OPERATIONAL RESULTS
#     # ─────────────────────────────────────────────────────────────────────────

#     def _generate_consolidated_sheet(self, workbook, data, report_date, fmt):
#         NUM_COLS   = 10
#         HEADER_ROW = 6

#         sheet = workbook.add_worksheet('Consolidated Operational Results')

#         report_dt       = datetime.strptime(report_date, '%Y-%m-%d')
#         report_month    = report_dt.strftime('%b %y')
#         prev_month_lbl  = (report_dt - relativedelta(months=1)).strftime('%b %y')
#         prev_year_dt    = report_dt - relativedelta(years=1)
#         prev_year_lbl   = prev_year_dt.strftime('%b %y')
#         prev_year_label = prev_year_dt.strftime('%b %Y')

#         company_ids  = data.get('company_ids', [])
#         branch_ids   = data.get('branch_ids',  [])
#         budget_ids   = data.get('budget_ids',  [])

#         companies    = self.env['res.company'].browse(company_ids)
#         company_name = ' & '.join(companies.mapped('name')) or 'All Companies'

#         sheet.merge_range(0, 0, 0, NUM_COLS - 1, company_name.upper(), fmt['title'])
#         sheet.merge_range(
#             1, 0, 1, NUM_COLS - 1,
#             f'Operational Results for the month of {report_month} - Consolidated',
#             fmt['subtitle']
#         )

#         sheet.write(2, 0, 'Companies:', fmt['bold'])
#         sheet.write(2, 1, company_name)

#         sheet.write(3, 0, 'Branch:', fmt['bold'])
#         branch_names = ', '.join(
#             self.env['res.branch'].browse(branch_ids).mapped('name')
#         ) if branch_ids else 'All Branches'
#         sheet.write(3, 1, branch_names)

#         sheet.write(4, 0, 'Budget:', fmt['bold'])
#         budget_names = ', '.join(
#             self.env['crossovered.budget'].browse(budget_ids).mapped('name')
#         ) if budget_ids else 'All Budgets'
#         sheet.write(4, 1, budget_names)

#         sheet.write(5, 0,
#                     '* Italicised rows have no budget allocation; '
#                     'actual amounts are from posted transactions.',
#                     fmt['note'])

#         headers = [
#             'Particulars',
#             f'YTD ({report_month})\nBudget',
#             f'YTD ({report_month})\nActual',
#             'YTD\nVariance',
#             f'YTD\n({prev_year_label})\nActual',
#             f'Budget\n({report_month})',
#             f'Actual\n({report_month})',
#             f'Actual\n({prev_month_lbl})',
#             'Variance',
#             f'Actual\n({prev_year_lbl})',
#         ]
#         for col, hdr in enumerate(headers):
#             sheet.write(HEADER_ROW, col, hdr, fmt['header'])
#         sheet.set_row(HEADER_ROW, 36)

#         domain = [('company_id', 'in', company_ids)]
#         if branch_ids:
#             if 'branch_id' in self.env['crossovered.budget.lines']._fields:
#                 domain.append(('branch_id', 'in', branch_ids))
#             elif 'branch_id' in self.env['account.analytic.account']._fields:
#                 domain.append(('analytic_account_id.branch_id', 'in', branch_ids))
#         if budget_ids:
#             domain.append(('crossovered_budget_id', 'in', budget_ids))

#         consolidated_data = self._get_consolidated_data(domain, report_date, branch_ids)
#         hierarchy         = self._build_consolidated_hierarchy(consolidated_data)

#         FIXED_MAIN_GROUP_ORDER = ['revenue', 'cost of revenue', 'expenses']
        
#         def get_main_group_order(mg_node):
#             mg_name_lower = (mg_node.get('name') or '').strip().lower()
#             try:
#                 return FIXED_MAIN_GROUP_ORDER.index(mg_name_lower)
#             except ValueError:
#                 return 999

#         mg_label_fmt = workbook.add_format({
#             'bold': True, 'bg_color': '#E6E6E6', 'border': 1,
#         })
#         sg_label_fmt = workbook.add_format({
#             'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'indent': 1,
#         })

#         def _write_detail(r, bp):
#             has_budget = bp.get('has_budget', False)
#             if has_budget:
#                 sheet.write(r, 0, '    ' + bp['name'], fmt['det_text'])
#             else:
#                 sheet.write(r, 0, '    ' + bp['name'], fmt['det_text_zero'])
#             for k in self._CON_KEYS:
#                 v = bp[k]
#                 if k in self._CON_VAR_KEYS:
#                     if has_budget:
#                         neg_f = fmt['det_money_neg']
#                         pos_f = fmt['det_money']
#                     else:
#                         neg_f = fmt['det_zero_neg']
#                         pos_f = fmt['det_zero_pos']
#                     sheet.write(r, self._CON_COL[k], v, neg_f if v < 0 else pos_f)
#                 else:
#                     sheet.write(r, self._CON_COL[k], v, fmt['det_money'])

#         def _write_subtotal(r, label, vals, text_f, money_f, money_neg_f):
#             sheet.write(r, 0, label, text_f)
#             for k in self._CON_KEYS:
#                 v = vals[k]
#                 sheet.write(
#                     r, self._CON_COL[k], v,
#                     money_neg_f if (k in self._CON_VAR_KEYS and v < 0) else money_f
#                 )

#         def _write_grand_row(r, label, vals):
#             sheet.write(r, 0, label, fmt['grand_text'])
#             for k in self._CON_KEYS:
#                 v = vals[k]
#                 sheet.write(
#                     r, self._CON_COL[k], v,
#                     fmt['grand_money_neg'] if (k in self._CON_VAR_KEYS and v < 0)
#                     else fmt['grand_money']
#                 )

#         row = HEADER_ROW + 1

#         grand_total_vals = self._zero_con_vals()

#         sorted_main_groups = sorted(
#             hierarchy.values(),
#             key=lambda x: (get_main_group_order(x), x.get('sequence', 0), x.get('name', ''))
#         )

#         for mg_node in sorted_main_groups:
#             sheet.write(row, 0, mg_node['name'].upper(), mg_label_fmt)
#             blank_mg = workbook.add_format({'bg_color': '#E6E6E6', 'border': 1})
#             for c in range(1, NUM_COLS):
#                 sheet.write(row, c, '', blank_mg)
#             row += 1

#             mg_running = self._zero_con_vals()
#             mg_running['budget_type'] = mg_node.get('budget_type', 'expense')

#             sg_items = sorted(
#                 [
#                     (sg_id, sg, mg_node['sub_group_totals'].get(sg_id, {}))
#                     for sg_id, sg in mg_node['sub_groups'].items()
#                 ],
#                 key=lambda x: (x[1].get('sequence', 0), x[1].get('name', ''))
#             )

#             for sg_id, sg, sgt in sg_items:
#                 sheet.write(row, 0, sg['name'], sg_label_fmt)
#                 blank_sg = workbook.add_format({'bg_color': '#F2F2F2', 'border': 1})
#                 for c in range(1, NUM_COLS):
#                     sheet.write(row, c, '', blank_sg)
#                 row += 1

#                 sg_running = self._zero_con_vals()

#                 for bp in sorted(
#                     sg['budget_positions'],
#                     key=lambda x: (x.get('sequence', 0), x.get('name', ''))
#                 ):
#                     _write_detail(row, bp)
#                     for k in self._CON_KEYS:
#                         sg_running[k] += bp[k]
#                     row += 1

#                 _is_rev = mg_node.get('budget_type', 'expense').lower() == 'revenue'
#                 if _is_rev:
#                     sg_running['ytd_variance'] = sg_running['ytd_actual'] - sg_running['ytd_budget']
#                     sg_running['monthly_variance'] = sg_running['monthly_actual'] - sg_running['monthly_budget']
#                 else:
#                     sg_running['ytd_variance'] = sg_running['ytd_budget'] - sg_running['ytd_actual']
#                     sg_running['monthly_variance'] = sg_running['monthly_budget'] - sg_running['monthly_actual']

#                 _write_subtotal(
#                     row, f'Total: {sg["name"]}', sg_running,
#                     fmt['sub_text'], fmt['sub_money'], fmt['sub_money_neg']
#                 )
#                 row += 1

#                 mg_running = self._add_con_vals(mg_running, sg_running)

#             _write_subtotal(
#                 row, f'TOTAL: {mg_node["name"]}', mg_running,
#                 fmt['main_text'], fmt['main_money'], fmt['main_money_neg']
#             )
#             row += 1

#             grand_total_vals = self._add_con_vals(grand_total_vals, mg_running)

#         EXPENSE_NAMES = {'cost of revenue', 'expenses'}
#         direct_exp_vals = self._zero_con_vals()
#         for mg_node in hierarchy.values():
#             if (mg_node.get('name') or '').strip().lower() in EXPENSE_NAMES:
#                 direct_exp_vals = self._add_con_vals(
#                     direct_exp_vals,
#                     {k: mg_node[k] for k in self._CON_KEYS}
#                 )

#         _write_grand_row(row, 'TOTAL: DIRECT + OTHER EXPENSES', direct_exp_vals)
#         row += 1

#         rev_vals = self._zero_con_vals()
#         for mg_node in hierarchy.values():
#             if (mg_node.get('name') or '').strip().lower() == 'revenue':
#                 rev_vals = self._add_con_vals(
#                     rev_vals,
#                     {k: mg_node[k] for k in self._CON_KEYS}
#                 )

#         profit_vals = self._sub_con_vals(rev_vals, direct_exp_vals)
#         _write_grand_row(row, 'GRAND TOTAL – PROFIT / LOSS', profit_vals)

#         sheet.set_column(0,  0,  35)
#         sheet.set_column(1,  1,  15)
#         sheet.set_column(2,  2,  15)
#         sheet.set_column(3,  3,  15)
#         sheet.set_column(4,  4,  20)
#         sheet.set_column(5,  5,  15)
#         sheet.set_column(6,  6,  15)
#         sheet.set_column(7,  7,  15)
#         sheet.set_column(8,  8,  15)
#         sheet.set_column(9,  9,  18)
#         sheet.freeze_panes(HEADER_ROW + 1, 0)

#     # ─────────────────────────────────────────────────────────────────────────
#     # ENTRY POINT
#     # ─────────────────────────────────────────────────────────────────────────

#     def generate_xlsx_report(self, workbook, data, lines):
#         report_date       = data.get('report_date')
#         show_consolidated = data.get('show_consolidated', True)

#         fmt = self._build_formats(workbook)

#         self._generate_variance_summary_sheet(workbook, data, report_date, fmt)
#         self._generate_main_variance_sheet(workbook, data, report_date, fmt)
#         if show_consolidated:
#             self._generate_consolidated_sheet(workbook, data, report_date, fmt)



            
 

    