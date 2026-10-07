from odoo import models, fields, api
from odoo.tools import date_utils
from odoo.exceptions import UserError
from odoo.tools.translate import _
from datetime import date
from odoo.tools import date_utils

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class BudgetVarianceReport(models.AbstractModel):
    _name = 'report.budget_customizations.report_budget_variance_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Budget Variance XLSX Report'

    def _get_actual_amount(self, budget_post, date_from, date_to, branch_ids, company_ids,
                            analytic_account_id=False, force_branch_id=False):
        """
        Unified, branch-aware actual calculator.
        Used for BOTH:
          - budget positions that already have a crossovered.budget.lines record
          - budget positions with no line (previously the only branch-filtered path)

        force_branch_id: when the budget_post (or its analytic account) has its own
        branch, we scope strictly to that branch, even if the wizard has multiple
        branches selected — otherwise a single branch's position would show actual
        for every selected branch pooled together.
        """
        acc_ids = budget_post.account_ids.ids
        if not acc_ids:
            return 0.0

        aml = self.env['account.move.line']

        domain = [
            ('account_id', 'in', acc_ids),
            ('company_id', 'in', company_ids),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('move_id.state', 'in', ['draft', 'posted']),
        ]

        if force_branch_id:
            # Scope strictly to this position's own branch.
            domain.append(('branch_id', '=', force_branch_id))
        elif branch_ids:
            domain.append(('branch_id', 'in', branch_ids))

        if analytic_account_id:
            domain.append(('analytic_account_id', '=', analytic_account_id))

        query = aml._where_calc(domain)
        aml._apply_ir_rules(query, 'read')
        from_clause, where_clause, params = query.get_sql()

        sql = f"""
            SELECT COALESCE(SUM(credit - debit), 0)
            FROM {from_clause}
            WHERE {where_clause}
        """
        self.env.cr.execute(sql, params)
        return self.env.cr.fetchone()[0] or 0.0

    @staticmethod
    def _resolve_branch_id(bp, aa):
        """Return the branch a budget position belongs to, checked on the
        position itself first, then on its analytic account."""
        if bp.branch_id:
            return bp.branch_id.id
        if aa and hasattr(aa, 'branch_id') and aa.branch_id:
            return aa.branch_id.id
        return False

    def _build_report_data(self, company_ids, branch_ids, budget_ids, date_from, date_to):

        line_domain = [
            ('company_id', 'in', company_ids),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
        ]

        if budget_ids:
            line_domain.append(('crossovered_budget_id', 'in', budget_ids))

        budget_lines = self.env['crossovered.budget.lines'].search(line_domain)

        if branch_ids:
            filtered = self.env['crossovered.budget.lines']

            for line in budget_lines:
                line_branch = False

                if hasattr(line, 'branch_id') and line.branch_id:
                    line_branch = line.branch_id.id
                elif line.analytic_account_id and hasattr(line.analytic_account_id, 'branch_id'):
                    line_branch = line.analytic_account_id.branch_id.id

                if line_branch in branch_ids:
                    filtered |= line

            budget_lines = filtered

        position_data = {}

        # PASS 1: accumulate BUDGET only from budget lines.
        # Actual is intentionally NOT taken from line.practical_amount anymore —
        # that field ignores branch/company filters entirely.
        for line in budget_lines:
            bp = line.general_budget_id
            aa = line.analytic_account_id

            key = (bp.id, aa.id if aa else None)

            if key not in position_data:
                position_data[key] = {
                    'bp': bp,
                    'aa': aa,
                    'analytic_name': aa.display_name if aa else '',
                    'budget': 0.0,
                    'actual': 0.0,
                }

            position_data[key]['budget'] += line.planned_amount

        bp_domain = [('account_ids', '!=', False),
                     ('company_id', 'in', company_ids)]

        if branch_ids:
            bp_domain.append(('branch_id', 'in', branch_ids))

        all_positions = self.env['account.budget.post'].search(bp_domain)

        existing_bp = {k[0] for k in position_data.keys()}

        for bp in all_positions:

            if branch_ids and bp.branch_id and bp.branch_id.id not in branch_ids:
                continue

            if bp.id not in existing_bp:
                position_data[(bp.id, None)] = {
                    'bp': bp,
                    'aa': False,
                    'analytic_name': '',
                    'budget': 0.0,
                    'actual': 0.0,
                }

        # PASS 2: compute ACTUAL for every position the same way, scoped to
        # that position's own branch when it has one.
        for key, vals in position_data.items():
            bp = vals['bp']
            aa = vals.get('aa')

            if not bp.account_ids:
                vals['actual'] = 0.0
                continue

            force_branch_id = self._resolve_branch_id(bp, aa)

            vals['actual'] = self._get_actual_amount(
                bp, date_from, date_to, branch_ids, company_ids,
                analytic_account_id=aa.id if aa else False,
                force_branch_id=force_branch_id,
            )

        hierarchy = {}

        for (bp_id, aa_id), vals in position_data.items():

            bp = vals['bp']

            main_group = bp.main_group_id
            sub_group = bp.sub_group_id

            if not main_group or not sub_group:
                continue

            seq = bp.sequence or 0
            budget_type = (main_group.budget_type or '').strip().lower()

            # Raw actual from Odoo (negative for expenses, positive for revenue)
            raw_actual = vals['actual']

            # CORRECTED VARIANCE CALCULATION:
            # For Revenue: Variance = Actual - Budget (positive variance is good)
            # For Expense: Variance = Budget - Actual (positive variance is good,
            #              where Actual is the positive expense amount)
            if budget_type == 'revenue':
                # Revenue: raw_actual is positive, use as-is
                variance = raw_actual - vals['budget']
            else:
                # Expense: raw_actual is negative, so -raw_actual gives positive expense amount
                # Variance = Budget - (positive expense amount)
                positive_expense = -raw_actual
                variance = vals['budget'] - positive_expense

            # Display actual (positive number for both revenue and expense)
            if budget_type == 'revenue':
                display_actual = raw_actual
            else:
                display_actual = -raw_actual

            if main_group.id not in hierarchy:
                hierarchy[main_group.id] = {
                    'name': main_group.name,
                    'sequence': seq,
                    'budget_type': main_group.budget_type,
                    'sub_groups': {},
                    'total_budget': 0.0,
                    'total_actual_raw': 0.0,      # raw Odoo actual for variance math
                    'total_actual_display': 0.0,  # sign-flipped for display
                }

            mg = hierarchy[main_group.id]

            if sub_group.id not in mg['sub_groups']:
                mg['sub_groups'][sub_group.id] = {
                    'name': sub_group.name,
                    'sequence': seq,
                    'budget_positions': [],
                    'total_budget': 0.0,
                    'total_actual_raw': 0.0,
                    'total_actual_display': 0.0,
                }

            mg['sub_groups'][sub_group.id]['budget_positions'].append({
                'name': bp.name,
                'analytic_name': vals['analytic_name'],
                # Branch and Company
                'branch_name': bp.branch_id.display_name if bp.branch_id else '',
                'company_name': bp.company_id.display_name if bp.company_id else '',
                'budget': vals['budget'],
                'actual_raw': raw_actual,
                'actual_display': display_actual,
                'variance': variance,
                'has_budget': bool(vals['budget']),
                'budget_type': budget_type,
            })

            mg['sub_groups'][sub_group.id]['total_budget'] += vals['budget']
            mg['sub_groups'][sub_group.id]['total_actual_raw'] += raw_actual
            mg['sub_groups'][sub_group.id]['total_actual_display'] += display_actual

            mg['total_budget'] += vals['budget']
            mg['total_actual_raw'] += raw_actual
            mg['total_actual_display'] += display_actual

        return hierarchy

    @staticmethod
    def _variance_pct(variance, budget):
        return variance / abs(budget) if budget else 0.0

    def generate_xlsx_report(self, workbook, data, lines):
        company_ids = data.get('company_ids', [])
        branch_ids = data.get('branch_ids', [])
        budget_ids = data.get('budget_ids', [])
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        report_level = data.get('report_level', 'level3')

        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#D3D3D3',
            'border': 1, 'align': 'center'
        })
        border_format = workbook.add_format({'border': 1})
        zero_budget_format = workbook.add_format({
            'border': 1, 'italic': True, 'font_color': '#595959'
        })
        money_format = workbook.add_format({
            'num_format': '#,##0.00_);(#,##0.00)', 'border': 1
        })
        money_zero_budget_format = workbook.add_format({
            'num_format': '#,##0.00_);(#,##0.00)', 'border': 1,
            'italic': True, 'font_color': '#595959'
        })
        percent_format = workbook.add_format({'num_format': '0.00%', 'border': 1})
        percent_zero_budget_format = workbook.add_format({
            'num_format': '0.00%', 'border': 1,
            'italic': True, 'font_color': '#595959'
        })
        sub_total_format = workbook.add_format({
            'bold': True, 'bg_color': '#CCE5FF', 'border': 1,
            'num_format': '#,##0.00_);(#,##0.00)'
        })
        sub_total_percent_format = workbook.add_format({
            'bold': True, 'bg_color': '#CCE5FF', 'border': 1,
            'num_format': '0.00%'
        })
        main_group_total_format = workbook.add_format({
            'bold': True, 'bg_color': '#99CCFF', 'border': 1,
            'num_format': '#,##0.00_);(#,##0.00)'
        })
        main_group_percent_format = workbook.add_format({
            'bold': True, 'bg_color': '#99CCFF', 'border': 1,
            'num_format': '0.00%'
        })
        grand_total_format = workbook.add_format({
            'bold': True, 'bg_color': '#0066CC', 'border': 1,
            'font_color': '#FFFFFF', 'num_format': '#,##0.00_);(#,##0.00)'
        })
        grand_total_percent_format = workbook.add_format({
            'bold': True, 'bg_color': '#0066CC', 'border': 1,
            'font_color': '#FFFFFF', 'num_format': '0.00%'
        })
        main_group_format = workbook.add_format({
            'bold': True, 'bg_color': '#E6E6E6', 'border': 1
        })
        sub_group_format = workbook.add_format({
            'bold': True, 'bg_color': '#F2F2F2', 'border': 1
        })

        sheet = workbook.add_worksheet('Budget Variance Report')

        sheet.merge_range(0, 0, 0, 6, 'BUDGET VARIANCE REPORT', bold)
        sheet.write(1, 0, 'Period:', bold)

        from_date = fields.Date.from_string(date_from).strftime('%d/%m/%Y')
        to_date = fields.Date.from_string(date_to).strftime('%d/%m/%Y')
        sheet.write(1, 1, f"{from_date} to {to_date}")

        sheet.write(2, 0, 'Companies:', bold)
        companies = self.env['res.company'].browse(company_ids)
        sheet.write(2, 1, ', '.join(companies.mapped('name')) or 'All Companies')

        sheet.write(3, 0, 'Branch:', bold)
        branches = self.env['res.branch'].browse(branch_ids)
        sheet.write(3, 1, ', '.join(branches.mapped('name')) or 'All Branches')

        sheet.write(4, 0, 'Budget:', bold)
        budgets = self.env['crossovered.budget'].browse(budget_ids)
        sheet.write(4, 1, ', '.join(budgets.mapped('name')) or 'All Budgets')

        sheet.write(5, 0, 'Report Level:', bold)
        report_level_name = dict(
            self.env['budget.variance.report.wizard']._fields['report_level'].selection
        ).get(report_level)
        sheet.write(5, 1, report_level_name)

        note_format = workbook.add_format({'italic': True, 'font_color': '#595959', 'font_size': 9})
        sheet.write(6, 0,
                    '* Italicised rows have no budget allocation; '
                    'actual amounts are computed from posted transactions.',
                    note_format)

        headers = [
            'Budget Position', 'Analytical Account', 'Branch', 'Company',
            'Budget', 'Actual', 'Variance', 'Variance %', 'Remarks'
        ]
        for col, header in enumerate(headers):
            sheet.write(7, col, header, header_format)

        row = 8

        hierarchy = self._build_report_data(
            company_ids, branch_ids, budget_ids, date_from, date_to
        )

        sorted_main_groups = sorted(
            hierarchy.values(), key=lambda x: (x['sequence'], x['name'])
        )

        for main_group in sorted_main_groups:
            budget_type = (main_group.get('budget_type') or '').strip().lower()

            sheet.write(row, 0, main_group['name'], main_group_format)
            sheet.merge_range(row, 1, row, 6, '', main_group_format)
            row += 1

            if report_level in ('level2', 'level3'):
                sorted_sub_groups = sorted(
                    main_group['sub_groups'].values(),
                    key=lambda x: (x['sequence'], x['name'])
                )

                for sub_group in sorted_sub_groups:

                    if report_level == 'level3':
                        sheet.write(row, 0, sub_group['name'], sub_group_format)
                        sheet.merge_range(row, 1, row, 6, '', sub_group_format)
                        row += 1

                    if report_level == 'level3':
                        for bp in sub_group['budget_positions']:
                            has_budget = bp['has_budget']

                            txt_fmt = border_format if has_budget else zero_budget_format
                            num_fmt = money_format if has_budget else money_zero_budget_format
                            pct_fmt = percent_format if has_budget else percent_zero_budget_format

                            # sheet.write(row, 0, bp['name'], txt_fmt)
                            # sheet.write(row, 1, bp['analytic_name'], txt_fmt)
                            # sheet.write(row, 2, bp['budget'], num_fmt)
                            # sheet.write(row, 3, bp['actual_display'], num_fmt)
                            # sheet.write(row, 4, bp['variance'], num_fmt)
                            # variance_pct = self._variance_pct(bp['variance'], bp['budget'])
                            # sheet.write(row, 5, variance_pct, pct_fmt)
                            # sheet.write(row, 6, '', txt_fmt)
                            # row += 1

                            sheet.write(row, 0, bp['name'], txt_fmt)
                            sheet.write(row, 1, bp['analytic_name'], txt_fmt)
                            sheet.write(row, 2, bp['branch_name'], txt_fmt)
                            sheet.write(row, 3, bp['company_name'], txt_fmt)

                            sheet.write(row, 4, bp['budget'], num_fmt)
                            sheet.write(row, 5, bp['actual_display'], num_fmt)
                            sheet.write(row, 6, bp['variance'], num_fmt)

                            variance_pct = self._variance_pct(bp['variance'], bp['budget'])
                            sheet.write(row, 7, variance_pct, pct_fmt)

                            sheet.write(row, 8, '', txt_fmt)

                            row += 1

                    # ── Sub-group subtotal ──
                    # Calculate variance using positive expense amounts
                    if budget_type == 'revenue':
                        sg_variance = sub_group['total_actual_display'] - sub_group['total_budget']
                    else:
                        # For expense: total_actual_display is already positive
                        sg_variance = sub_group['total_budget'] - sub_group['total_actual_display']

                    sg_pct = self._variance_pct(sg_variance, sub_group['total_budget'])
                    # sheet.write(row, 0, f"Total {sub_group['name']}", sub_total_format)
                    # sheet.write(row, 1, '', sub_total_format)
                    # sheet.write(row, 2, sub_group['total_budget'], sub_total_format)
                    # sheet.write(row, 3, sub_group['total_actual_display'], sub_total_format)
                    # sheet.write(row, 4, sg_variance, sub_total_format)
                    # sheet.write(row, 5, sg_pct, sub_total_percent_format)
                    # sheet.write(row, 6, '', sub_total_format)
                    sheet.write(row, 0, f"Total {sub_group['name']}", sub_total_format)
                    sheet.write(row, 1, '', sub_total_format)
                    sheet.write(row, 2, '', sub_total_format)
                    sheet.write(row, 3, '', sub_total_format)

                    sheet.write(row, 4, sub_group['total_budget'], sub_total_format)
                    sheet.write(row, 5, sub_group['total_actual_display'], sub_total_format)
                    sheet.write(row, 6, sg_variance, sub_total_format)
                    sheet.write(row, 7, sg_pct, sub_total_percent_format)
                    sheet.write(row, 8, '', sub_total_format)
                    row += 1

            # ── Main group total ──
            if budget_type == 'revenue':
                mg_variance = main_group['total_actual_display'] - main_group['total_budget']
            else:
                mg_variance = main_group['total_budget'] - main_group['total_actual_display']

            mg_pct = self._variance_pct(mg_variance, main_group['total_budget'])
            # sheet.write(row, 0, f"TOTAL: {main_group['name']}", main_group_total_format)
            # sheet.write(row, 1, '', main_group_total_format)
            # sheet.write(row, 2, main_group['total_budget'], main_group_total_format)
            # sheet.write(row, 3, main_group['total_actual_display'], main_group_total_format)
            # sheet.write(row, 4, mg_variance, main_group_total_format)
            # sheet.write(row, 5, mg_pct, main_group_percent_format)
            # sheet.write(row, 6, '', main_group_total_format)
            sheet.write(row, 0, f"TOTAL: {main_group['name']}", main_group_total_format)
            sheet.write(row, 1, '', main_group_total_format)
            sheet.write(row, 2, '', main_group_total_format)
            sheet.write(row, 3, '', main_group_total_format)

            sheet.write(row, 4, main_group['total_budget'], main_group_total_format)
            sheet.write(row, 5, main_group['total_actual_display'], main_group_total_format)
            sheet.write(row, 6, mg_variance, main_group_total_format)
            sheet.write(row, 7, mg_pct, main_group_percent_format)
            sheet.write(row, 8, '', main_group_total_format)
            row += 1

        # ── TOTAL: DIRECT + OTHER EXPENSES ──
        total_expense_budget = 0.0
        total_expense_actual_display = 0.0
        for mg in hierarchy.values():
            mg_name = (mg.get('name') or '').strip().lower()
            if mg_name in ('cost of revenue', 'expenses'):
                total_expense_budget += mg['total_budget']
                total_expense_actual_display += mg['total_actual_display']

        # Expense variance = Budget - Actual (Actual is positive)
        total_expense_variance = total_expense_budget - total_expense_actual_display
        total_expense_pct = (
            total_expense_variance / abs(total_expense_budget)
            if total_expense_budget else 0.0
        )
        # sheet.write(row, 0, 'TOTAL: DIRECT + OTHER EXPENSES', grand_total_format)
        # sheet.write(row, 1, '', grand_total_format)
        # sheet.write(row, 2, total_expense_budget, grand_total_format)
        # sheet.write(row, 3, total_expense_actual_display, grand_total_format)
        # sheet.write(row, 4, total_expense_variance, grand_total_format)
        # sheet.write(row, 5, total_expense_pct, grand_total_percent_format)
        # sheet.write(row, 6, '', grand_total_format)
        # row += 1

        sheet.write(row, 0, 'TOTAL: DIRECT + OTHER EXPENSES', grand_total_format)
        sheet.write(row, 1, '', grand_total_format)
        sheet.write(row, 2, '', grand_total_format)
        sheet.write(row, 3, '', grand_total_format)

        sheet.write(row, 4, total_expense_budget, grand_total_format)
        sheet.write(row, 5, total_expense_actual_display, grand_total_format)
        sheet.write(row, 6, total_expense_variance, grand_total_format)
        sheet.write(row, 7, total_expense_pct, grand_total_percent_format)
        sheet.write(row, 8, '', grand_total_format)

        row += 1

        # ── GRAND TOTAL (PROFIT / LOSS) ──
        total_revenue_budget = 0.0
        total_revenue_actual_display = 0.0
        for mg in hierarchy.values():
            if (mg.get('name') or '').strip().lower() == 'revenue':
                total_revenue_budget += mg['total_budget']
                total_revenue_actual_display += mg['total_actual_display']

        grand_total_budget = total_revenue_budget - total_expense_budget
        grand_total_actual = total_revenue_actual_display - total_expense_actual_display
        grand_total_variance = grand_total_actual - grand_total_budget
        grand_total_pct = (
            grand_total_variance / abs(grand_total_budget)
            if grand_total_budget else 0.0
        )
        # sheet.write(row, 0, 'GRAND TOTAL-PROFIT/LOSS', grand_total_format)
        # sheet.write(row, 1, '', grand_total_format)
        # sheet.write(row, 2, grand_total_budget, grand_total_format)
        # sheet.write(row, 3, grand_total_actual, grand_total_format)
        # sheet.write(row, 4, grand_total_variance, grand_total_format)
        # sheet.write(row, 5, grand_total_pct, grand_total_percent_format)
        # sheet.write(row, 6, '', grand_total_format)
        sheet.write(row, 0, 'GRAND TOTAL-PROFIT/LOSS', grand_total_format)
        sheet.write(row, 1, '', grand_total_format)
        sheet.write(row, 2, '', grand_total_format)
        sheet.write(row, 3, '', grand_total_format)

        sheet.write(row, 4, grand_total_budget, grand_total_format)
        sheet.write(row, 5, grand_total_actual, grand_total_format)
        sheet.write(row, 6, grand_total_variance, grand_total_format)
        sheet.write(row, 7, grand_total_pct, grand_total_percent_format)
        sheet.write(row, 8, '', grand_total_format)

        if report_level == 'level3':
            sheet.set_column(0, 0, 30)   # Budget Position
            sheet.set_column(1, 1, 30)   # Analytical Account
            sheet.set_column(2, 2, 20)   # Branch
            sheet.set_column(3, 3, 25)   # Company
        else:
            sheet.set_column(0, 0, 40)
            sheet.set_column(1, 3, 0)

        sheet.set_column(4, 4, 15)       # Budget
        sheet.set_column(5, 5, 15)       # Actual
        sheet.set_column(6, 6, 15)       # Variance
        sheet.set_column(7, 7, 12)       # Variance %
        sheet.set_column(8, 8, 20)       # Remarks

        # if report_level == 'level3':
        #     sheet.set_column(0, 0, 30)
        #     sheet.set_column(1, 1, 30)
        # else:
        #     sheet.set_column(0, 0, 40)
        #     sheet.set_column(1, 1, 0)

        # sheet.set_column(2, 2, 15)
        # sheet.set_column(3, 3, 15)
        # sheet.set_column(4, 4, 15)
        # sheet.set_column(5, 5, 12)
        # sheet.set_column(6, 6, 20)
        # sheet.freeze_panes(8, 0)


# class BudgetVarianceReport(models.AbstractModel):
#     _name = 'report.budget_customizations.report_budget_variance_report_xlsx'
#     _inherit = 'report.report_xlsx.abstract'
#     _description = 'Budget Variance XLSX Report'

#     def _get_actual_amount(self, budget_post, date_from, date_to, branch_ids, company_ids):
#         acc_ids = budget_post.account_ids.ids
#         if not acc_ids:
#             return 0.0

#         aml = self.env['account.move.line']

#         domain = [
#             ('account_id', 'in', acc_ids),
#             ('company_id', 'in', company_ids),
#             ('date', '>=', date_from),
#             ('date', '<=', date_to),
#             ('move_id.state', 'in', ['draft', 'posted']),
#         ]

#         if branch_ids:
#             domain.append(('branch_id', 'in', branch_ids))

#         query = aml._where_calc(domain)
#         aml._apply_ir_rules(query, 'read')
#         from_clause, where_clause, params = query.get_sql()

#         sql = f"""
#             SELECT COALESCE(SUM(credit - debit), 0)
#             FROM {from_clause}
#             WHERE {where_clause}
#         """
#         self.env.cr.execute(sql, params)
#         return self.env.cr.fetchone()[0] or 0.0

#     def _build_report_data(self, company_ids, branch_ids, budget_ids, date_from, date_to):

#         line_domain = [
#             ('company_id', 'in', company_ids),
#             ('date_from', '>=', date_from),
#             ('date_to', '<=', date_to),
#         ]

#         if budget_ids:
#             line_domain.append(('crossovered_budget_id', 'in', budget_ids))

#         budget_lines = self.env['crossovered.budget.lines'].search(line_domain)

#         if branch_ids:
#             filtered = self.env['crossovered.budget.lines']

#             for line in budget_lines:
#                 line_branch = False

#                 if hasattr(line, 'branch_id') and line.branch_id:
#                     line_branch = line.branch_id.id
#                 elif line.analytic_account_id and hasattr(line.analytic_account_id, 'branch_id'):
#                     line_branch = line.analytic_account_id.branch_id.id

#                 if line_branch in branch_ids:
#                     filtered |= line

#             budget_lines = filtered

#         position_data = {}

#         for line in budget_lines:
#             bp = line.general_budget_id
#             aa = line.analytic_account_id

#             key = (bp.id, aa.id if aa else None)

#             if key not in position_data:
#                 position_data[key] = {
#                     'bp': bp,
#                     'analytic_name': aa.display_name if aa else '',
#                     'budget': 0.0,
#                     'actual': 0.0,
#                 }

#             position_data[key]['budget'] += line.planned_amount
#             position_data[key]['actual'] += line.practical_amount

#         bp_domain = [('account_ids', '!=', False),
#                      ('company_id', 'in', company_ids),]

#         if branch_ids:
#             bp_domain.append(('branch_id', 'in', branch_ids))

#         all_positions = self.env['account.budget.post'].search(bp_domain)

#         existing_bp = {k[0] for k in position_data.keys()}

#         for bp in all_positions:

#             if branch_ids and bp.branch_id and bp.branch_id.id not in branch_ids:
#                 continue

#             if bp.id not in existing_bp:

#                 actual = self._get_actual_amount(
#                     bp, date_from, date_to, branch_ids,company_ids
#                 )

#                 position_data[(bp.id, None)] = {
#                     'bp': bp,
#                     'analytic_name': '',
#                     'budget': 0.0,
#                     'actual': actual,
#                 }

#         hierarchy = {}

#         for (bp_id, aa_id), vals in position_data.items():

#             bp = vals['bp']

#             main_group = bp.main_group_id
#             sub_group = bp.sub_group_id

#             if not main_group or not sub_group:
#                 continue

#             seq = bp.sequence or 0
#             budget_type = (main_group.budget_type or '').strip().lower()

#             # Raw actual from Odoo (negative for expenses, positive for revenue)
#             raw_actual = vals['actual']

#             # CORRECTED VARIANCE CALCULATION:
#             # For Revenue: Variance = Actual - Budget (positive variance is good)
#             # For Expense: Variance = Budget - Actual (positive variance is good, 
#             #              where Actual is the positive expense amount)
#             if budget_type == 'revenue':
#                 # Revenue: raw_actual is positive, use as-is
#                 variance = raw_actual - vals['budget']
#             else:
#                 # Expense: raw_actual is negative, so -raw_actual gives positive expense amount
#                 # Variance = Budget - (positive expense amount)
#                 positive_expense = -raw_actual
#                 variance = vals['budget'] - positive_expense

#             # Display actual (positive number for both revenue and expense)
#             if budget_type == 'revenue':
#                 display_actual = raw_actual
#             else:
#                 display_actual = -raw_actual

#             if main_group.id not in hierarchy:
#                 hierarchy[main_group.id] = {
#                     'name': main_group.name,
#                     'sequence': seq,
#                     'budget_type': main_group.budget_type,
#                     'sub_groups': {},
#                     'total_budget': 0.0,
#                     'total_actual_raw': 0.0,      # raw Odoo actual for variance math
#                     'total_actual_display': 0.0,  # sign-flipped for display
#                 }

#             mg = hierarchy[main_group.id]

#             if sub_group.id not in mg['sub_groups']:
#                 mg['sub_groups'][sub_group.id] = {
#                     'name': sub_group.name,
#                     'sequence': seq,
#                     'budget_positions': [],
#                     'total_budget': 0.0,
#                     'total_actual_raw': 0.0,
#                     'total_actual_display': 0.0,
#                 }

#             mg['sub_groups'][sub_group.id]['budget_positions'].append({
#                 'name': bp.name,
#                 'analytic_name': vals['analytic_name'],
#                 'budget': vals['budget'],
#                 'actual_raw': raw_actual,
#                 'actual_display': display_actual,
#                 'variance': variance,
#                 'has_budget': bool(vals['budget']),
#                 'budget_type': budget_type,
#             })

#             mg['sub_groups'][sub_group.id]['total_budget'] += vals['budget']
#             mg['sub_groups'][sub_group.id]['total_actual_raw'] += raw_actual
#             mg['sub_groups'][sub_group.id]['total_actual_display'] += display_actual

#             mg['total_budget'] += vals['budget']
#             mg['total_actual_raw'] += raw_actual
#             mg['total_actual_display'] += display_actual

#         return hierarchy

#     @staticmethod
#     def _variance_pct(variance, budget):
#         return variance / abs(budget) if budget else 0.0

#     def generate_xlsx_report(self, workbook, data, lines):
#         company_ids = data.get('company_ids', [])
#         branch_ids = data.get('branch_ids', [])
#         budget_ids = data.get('budget_ids', [])
#         date_from = data.get('date_from')
#         date_to = data.get('date_to')
#         report_level = data.get('report_level', 'level3')

#         bold = workbook.add_format({'bold': True})
#         header_format = workbook.add_format({
#             'bold': True, 'bg_color': '#D3D3D3',
#             'border': 1, 'align': 'center'
#         })
#         border_format = workbook.add_format({'border': 1})
#         zero_budget_format = workbook.add_format({
#             'border': 1, 'italic': True, 'font_color': '#595959'
#         })
#         money_format = workbook.add_format({
#             'num_format': '#,##0.00_);(#,##0.00)', 'border': 1
#         })
#         money_zero_budget_format = workbook.add_format({
#             'num_format': '#,##0.00_);(#,##0.00)', 'border': 1,
#             'italic': True, 'font_color': '#595959'
#         })
#         percent_format = workbook.add_format({'num_format': '0.00%', 'border': 1})
#         percent_zero_budget_format = workbook.add_format({
#             'num_format': '0.00%', 'border': 1,
#             'italic': True, 'font_color': '#595959'
#         })
#         sub_total_format = workbook.add_format({
#             'bold': True, 'bg_color': '#CCE5FF', 'border': 1,
#             'num_format': '#,##0.00_);(#,##0.00)'
#         })
#         sub_total_percent_format = workbook.add_format({
#             'bold': True, 'bg_color': '#CCE5FF', 'border': 1,
#             'num_format': '0.00%'
#         })
#         main_group_total_format = workbook.add_format({
#             'bold': True, 'bg_color': '#99CCFF', 'border': 1,
#             'num_format': '#,##0.00_);(#,##0.00)'
#         })
#         main_group_percent_format = workbook.add_format({
#             'bold': True, 'bg_color': '#99CCFF', 'border': 1,
#             'num_format': '0.00%'
#         })
#         grand_total_format = workbook.add_format({
#             'bold': True, 'bg_color': '#0066CC', 'border': 1,
#             'font_color': '#FFFFFF', 'num_format': '#,##0.00_);(#,##0.00)'
#         })
#         grand_total_percent_format = workbook.add_format({
#             'bold': True, 'bg_color': '#0066CC', 'border': 1,
#             'font_color': '#FFFFFF', 'num_format': '0.00%'
#         })
#         main_group_format = workbook.add_format({
#             'bold': True, 'bg_color': '#E6E6E6', 'border': 1
#         })
#         sub_group_format = workbook.add_format({
#             'bold': True, 'bg_color': '#F2F2F2', 'border': 1
#         })

#         sheet = workbook.add_worksheet('Budget Variance Report')

#         sheet.merge_range(0, 0, 0, 6, 'BUDGET VARIANCE REPORT', bold)
#         sheet.write(1, 0, 'Period:', bold)

#         from_date = fields.Date.from_string(date_from).strftime('%d/%m/%Y')
#         to_date = fields.Date.from_string(date_to).strftime('%d/%m/%Y')
#         sheet.write(1, 1, f"{from_date} to {to_date}")

#         sheet.write(2, 0, 'Companies:', bold)
#         companies = self.env['res.company'].browse(company_ids)
#         sheet.write(2, 1, ', '.join(companies.mapped('name')) or 'All Companies')

#         sheet.write(3, 0, 'Branch:', bold)
#         branches = self.env['res.branch'].browse(branch_ids)
#         sheet.write(3, 1, ', '.join(branches.mapped('name')) or 'All Branches')

#         sheet.write(4, 0, 'Budget:', bold)
#         budgets = self.env['crossovered.budget'].browse(budget_ids)
#         sheet.write(4, 1, ', '.join(budgets.mapped('name')) or 'All Budgets')

#         sheet.write(5, 0, 'Report Level:', bold)
#         report_level_name = dict(
#             self.env['budget.variance.report.wizard']._fields['report_level'].selection
#         ).get(report_level)
#         sheet.write(5, 1, report_level_name)

#         note_format = workbook.add_format({'italic': True, 'font_color': '#595959', 'font_size': 9})
#         sheet.write(6, 0,
#                     '* Italicised rows have no budget allocation; '
#                     'actual amounts are computed from posted transactions.',
#                     note_format)

#         headers = [
#             'Budget Position', 'Analytical Account',
#             'Budget', 'Actual', 'Variance', 'Variance %', 'Remarks'
#         ]
#         for col, header in enumerate(headers):
#             sheet.write(7, col, header, header_format)

#         row = 8

#         hierarchy = self._build_report_data(
#             company_ids, branch_ids, budget_ids, date_from, date_to
#         )

#         sorted_main_groups = sorted(
#             hierarchy.values(), key=lambda x: (x['sequence'], x['name'])
#         )

#         for main_group in sorted_main_groups:
#             budget_type = (main_group.get('budget_type') or '').strip().lower()

#             sheet.write(row, 0, main_group['name'], main_group_format)
#             sheet.merge_range(row, 1, row, 6, '', main_group_format)
#             row += 1

#             if report_level in ('level2', 'level3'):
#                 sorted_sub_groups = sorted(
#                     main_group['sub_groups'].values(),
#                     key=lambda x: (x['sequence'], x['name'])
#                 )

#                 for sub_group in sorted_sub_groups:

#                     if report_level == 'level3':
#                         sheet.write(row, 0, sub_group['name'], sub_group_format)
#                         sheet.merge_range(row, 1, row, 6, '', sub_group_format)
#                         row += 1

#                     if report_level == 'level3':
#                         for bp in sub_group['budget_positions']:
#                             has_budget = bp['has_budget']

#                             txt_fmt = border_format if has_budget else zero_budget_format
#                             num_fmt = money_format if has_budget else money_zero_budget_format
#                             pct_fmt = percent_format if has_budget else percent_zero_budget_format

#                             sheet.write(row, 0, bp['name'], txt_fmt)
#                             sheet.write(row, 1, bp['analytic_name'], txt_fmt)
#                             sheet.write(row, 2, bp['budget'], num_fmt)
#                             sheet.write(row, 3, bp['actual_display'], num_fmt)
#                             sheet.write(row, 4, bp['variance'], num_fmt)
#                             variance_pct = self._variance_pct(bp['variance'], bp['budget'])
#                             sheet.write(row, 5, variance_pct, pct_fmt)
#                             sheet.write(row, 6, '', txt_fmt)
#                             row += 1

#                     # ── Sub-group subtotal ──
#                     # Calculate variance using positive expense amounts
#                     if budget_type == 'revenue':
#                         sg_variance = sub_group['total_actual_display'] - sub_group['total_budget']
#                     else:
#                         # For expense: total_actual_display is already positive
#                         sg_variance = sub_group['total_budget'] - sub_group['total_actual_display']

#                     sg_pct = self._variance_pct(sg_variance, sub_group['total_budget'])
#                     sheet.write(row, 0, f"Total {sub_group['name']}", sub_total_format)
#                     sheet.write(row, 1, '', sub_total_format)
#                     sheet.write(row, 2, sub_group['total_budget'], sub_total_format)
#                     sheet.write(row, 3, sub_group['total_actual_display'], sub_total_format)
#                     sheet.write(row, 4, sg_variance, sub_total_format)
#                     sheet.write(row, 5, sg_pct, sub_total_percent_format)
#                     sheet.write(row, 6, '', sub_total_format)
#                     row += 1

#             # ── Main group total ──
#             if budget_type == 'revenue':
#                 mg_variance = main_group['total_actual_display'] - main_group['total_budget']
#             else:
#                 mg_variance = main_group['total_budget'] - main_group['total_actual_display']

#             mg_pct = self._variance_pct(mg_variance, main_group['total_budget'])
#             sheet.write(row, 0, f"TOTAL: {main_group['name']}", main_group_total_format)
#             sheet.write(row, 1, '', main_group_total_format)
#             sheet.write(row, 2, main_group['total_budget'], main_group_total_format)
#             sheet.write(row, 3, main_group['total_actual_display'], main_group_total_format)
#             sheet.write(row, 4, mg_variance, main_group_total_format)
#             sheet.write(row, 5, mg_pct, main_group_percent_format)
#             sheet.write(row, 6, '', main_group_total_format)
#             row += 1

#         # ── TOTAL: DIRECT + OTHER EXPENSES ──
#         total_expense_budget = 0.0
#         total_expense_actual_display = 0.0
#         for mg in hierarchy.values():
#             mg_name = (mg.get('name') or '').strip().lower()
#             if mg_name in ('cost of revenue', 'expenses'):
#                 total_expense_budget += mg['total_budget']
#                 total_expense_actual_display += mg['total_actual_display']

#         # Expense variance = Budget - Actual (Actual is positive)
#         total_expense_variance = total_expense_budget - total_expense_actual_display
#         total_expense_pct = (
#             total_expense_variance / abs(total_expense_budget)
#             if total_expense_budget else 0.0
#         )
#         sheet.write(row, 0, 'TOTAL: DIRECT + OTHER EXPENSES', grand_total_format)
#         sheet.write(row, 1, '', grand_total_format)
#         sheet.write(row, 2, total_expense_budget, grand_total_format)
#         sheet.write(row, 3, total_expense_actual_display, grand_total_format)
#         sheet.write(row, 4, total_expense_variance, grand_total_format)
#         sheet.write(row, 5, total_expense_pct, grand_total_percent_format)
#         sheet.write(row, 6, '', grand_total_format)
#         row += 1

#         # ── GRAND TOTAL (PROFIT / LOSS) ──
#         total_revenue_budget = 0.0
#         total_revenue_actual_display = 0.0
#         for mg in hierarchy.values():
#             if (mg.get('name') or '').strip().lower() == 'revenue':
#                 total_revenue_budget += mg['total_budget']
#                 total_revenue_actual_display += mg['total_actual_display']

#         grand_total_budget = total_revenue_budget - total_expense_budget
#         grand_total_actual = total_revenue_actual_display - total_expense_actual_display
#         grand_total_variance = grand_total_actual - grand_total_budget
#         grand_total_pct = (
#             grand_total_variance / abs(grand_total_budget)
#             if grand_total_budget else 0.0
#         )
#         sheet.write(row, 0, 'GRAND TOTAL-PROFIT/LOSS', grand_total_format)
#         sheet.write(row, 1, '', grand_total_format)
#         sheet.write(row, 2, grand_total_budget, grand_total_format)
#         sheet.write(row, 3, grand_total_actual, grand_total_format)
#         sheet.write(row, 4, grand_total_variance, grand_total_format)
#         sheet.write(row, 5, grand_total_pct, grand_total_percent_format)
#         sheet.write(row, 6, '', grand_total_format)

#         if report_level == 'level3':
#             sheet.set_column(0, 0, 30)
#             sheet.set_column(1, 1, 30)
#         else:
#             sheet.set_column(0, 0, 40)
#             sheet.set_column(1, 1, 0)

#         sheet.set_column(2, 2, 15)
#         sheet.set_column(3, 3, 15)
#         sheet.set_column(4, 4, 15)
#         sheet.set_column(5, 5, 12)
#         sheet.set_column(6, 6, 20)
#         sheet.freeze_panes(8, 0)





