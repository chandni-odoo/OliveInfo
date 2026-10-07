import calendar
from datetime import date

from odoo import fields, models


class BudgetSpreadReport(models.AbstractModel):
    _name = "report.budget_customizations.report_budget_spread_report_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Budget Spread XLSX Report"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_month_range(self, date_from_str, date_to_str):
        """Return list of (year, month) tuples covering date_from → date_to."""
        d_from = fields.Date.from_string(date_from_str)
        d_to = fields.Date.from_string(date_to_str)
        months = []
        y, m = d_from.year, d_from.month
        while (y, m) <= (d_to.year, d_to.month):
            months.append((y, m))
            m += 1
            if m > 12:
                m = 1
                y += 1
        return months

    def _month_label(self, year, month):
        return calendar.month_abbr[month]  # "Jan", "Feb", …

    def _overlap_amount(self, line, year, month):
        """
        Proportional spread of line.planned_amount into (year, month)
        based on calendar-day overlap.
        """
        line_from = fields.Date.from_string(line.date_from)
        line_to = fields.Date.from_string(line.date_to)
        month_start = date(year, month, 1)
        month_end = date(year, month, calendar.monthrange(year, month)[1])

        overlap_start = max(line_from, month_start)
        overlap_end = min(line_to, month_end)

        if overlap_start > overlap_end:
            return 0.0

        total_days = (line_to - line_from).days + 1
        overlap_days = (overlap_end - overlap_start).days + 1

        if total_days <= 0:
            return 0.0

        return line.planned_amount * overlap_days / total_days

    # ------------------------------------------------------------------
    # Workbook formats
    # ------------------------------------------------------------------

    def _build_formats(self, workbook):
        f = {}
        f["bold"] = workbook.add_format({"bold": True})
        f["title"] = workbook.add_format({
            "bold": True,
            "font_size": 14,
            "align": "center",
            "valign": "vcenter",
        })
        f["header"] = workbook.add_format({
            "bold": True,
            "bg_color": "#1F4E79",
            "font_color": "#FFFFFF",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        })
        f["main_group"] = workbook.add_format({
            "bold": True,
            "bg_color": "#E6E6E6",
            "border": 1,
            "align": "left",
        })
        f["main_group_num"] = workbook.add_format({
            "bold": True,
            "bg_color": "#E6E6E6",
            "border": 1,
            "num_format": "#,##0.00"
        })
        f["sub_group"] = workbook.add_format({
            "bold": True,
            "bg_color": "#F2F2F2",
            "border": 1,
            "align": "left",
        })
        f["sub_group_num"] = workbook.add_format({
            "bold": True,
            "bg_color": "#F2F2F2",
            "border": 1,
            "num_format": "#,##0.00"
        })
        f["budget_line"] = workbook.add_format({
            "border": 1,
            "align": "left",
        })
        f["budget_line_num"] = workbook.add_format({
            "border": 1,
            "num_format": "#,##0.00"
        })
        f["sub_total"] = workbook.add_format({
            "bold": True,
            "bg_color": "#CCE5FF",
            "border": 1,
            "align": "left",
        })
        f["sub_total_num"] = workbook.add_format({
            "bold": True,
            "bg_color": "#CCE5FF",
            "border": 1,
            "num_format": "#,##0.00"
        })
        f["main_total"] = workbook.add_format({
            "bold": True,
            "bg_color": "#99CCFF",
            "border": 1,
            "align": "left",
        })
        f["main_total_num"] = workbook.add_format({
            "bold": True,
            "bg_color": "#99CCFF",
            "border": 1,
            "num_format": "#,##0.00"
        })
        f["grand_total"] = workbook.add_format({
            "bold": True,
            "bg_color": "#0066CC",
            "font_color": "#FFFFFF",
            "border": 1,
            "align": "left",
        })
        f["grand_total_num"] = workbook.add_format({
            "bold": True,
            "bg_color": "#0066CC",
            "font_color": "#FFFFFF",
            "border": 1,
            "num_format": "#,##0.00"
        })
        f["border"] = workbook.add_format({"border": 1})
        f["num"] = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        return f

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def _collect_data(self, data):
        """
        Returns (hierarchy dict, months list).

        hierarchy = {
            main_group_id: {
                name, sequence, budget_type,
                sub_groups: {
                    sub_group_id: {
                        name, sequence,
                        positions: {
                            position_key: {
                                name, analytic_name,
                                budget_by_month: {(y,m): float},
                            }
                        },
                        budget_by_month,
                    }
                },
                budget_by_month,
            }
        }
        """
        company_ids = data.get("company_ids", [])
        branch_ids = data.get("branch_ids", [])
        budget_ids = data.get("budget_ids", [])
        date_from = data.get("date_from")
        date_to = data.get("date_to")

        months = self._get_month_range(date_from, date_to)

        domain = [
            ("company_id", "in", company_ids),
            ("date_from", ">=", date_from),
            ("date_to", "<=", date_to),
        ]
        if budget_ids:
            domain.append(("crossovered_budget_id", "in", budget_ids))
        if branch_ids:
            bl_fields = self.env["crossovered.budget.lines"]._fields
            if "branch_id" in bl_fields:
                domain.append(("branch_id", "in", branch_ids))
            else:
                domain.append(("analytic_account_id.branch_id", "in", branch_ids))

        budget_lines = self.env["crossovered.budget.lines"].search(domain)

        hierarchy = {}

        for line in budget_lines:
            bp = line.general_budget_id
            aa = line.analytic_account_id
            mg = bp.main_group_id
            sg = bp.sub_group_id

            position_key = (
                bp.name.strip().lower(),
                aa.display_name.strip().lower() if aa else "",
            )

            if mg.id not in hierarchy:
                hierarchy[mg.id] = {
                    "name": mg.name,
                    "sequence": bp.sequence or 0,
                    "budget_type": mg.budget_type or "expense",
                    "sub_groups": {},
                    "budget_by_month": {m: 0.0 for m in months},
                }

            if sg.id not in hierarchy[mg.id]["sub_groups"]:
                hierarchy[mg.id]["sub_groups"][sg.id] = {
                    "name": sg.name,
                    "sequence": bp.sequence or 0,
                    "positions": {},
                    "budget_by_month": {m: 0.0 for m in months},
                }

            sg_data = hierarchy[mg.id]["sub_groups"][sg.id]

            if position_key not in sg_data["positions"]:
                sg_data["positions"][position_key] = {
                    "name": bp.name,
                    "analytic_name": aa.display_name if aa else "",
                    "budget_by_month": {m: 0.0 for m in months},
                }

            pos = sg_data["positions"][position_key]

            for ym in months:
                y, m = ym
                bamt = self._overlap_amount(line, y, m)

                pos["budget_by_month"][ym] += bamt
                sg_data["budget_by_month"][ym] += bamt
                hierarchy[mg.id]["budget_by_month"][ym] += bamt

        return hierarchy, months

    # ------------------------------------------------------------------
    # Shared utilities
    # ------------------------------------------------------------------

    def _write_report_header(self, sheet, f, data, months, title):
        from_date = fields.Date.from_string(data["date_from"]).strftime("%d/%m/%Y")
        to_date = fields.Date.from_string(data["date_to"]).strftime("%d/%m/%Y")

        total_cols = 2 + len(months)
        sheet.merge_range(0, 0, 0, total_cols, title, f["title"])
        sheet.write(1, 0, "Period:", f["bold"])
        sheet.write(1, 1, f"{from_date} to {to_date}")
        sheet.write(2, 0, "Companies:", f["bold"])
        companies = self.env["res.company"].browse(data.get("company_ids", []))
        sheet.write(2, 1, ", ".join(companies.mapped("name")) or "All Companies")
        sheet.write(3, 0, "Branch:", f["bold"])
        branches = self.env["res.branch"].browse(data.get("branch_ids", []))
        sheet.write(3, 1, ", ".join(branches.mapped("name")) or "All Branches")
        sheet.write(4, 0, "Budget:", f["bold"])
        budgets = self.env["crossovered.budget"].browse(data.get("budget_ids", []))
        sheet.write(4, 1, ", ".join(budgets.mapped("name")) or "All Budgets")

    def _write_num_row(self, sheet, row, col_start, months, by_month_dict, fmt):
        total = 0.0
        col = col_start
        for ym in months:
            v = by_month_dict.get(ym, 0.0)
            sheet.write(row, col, v, fmt)
            total += v
            col += 1
        sheet.write(row, col, total, fmt)

    def _fill_empty(self, sheet, row, col_start, num_cols, fmt):
        for c in range(col_start, col_start + num_cols):
            sheet.write(row, c, "", fmt)

    # ------------------------------------------------------------------
    # Sheet 1: Budget Spread Summary (Amounts alongside positions)
    # ------------------------------------------------------------------

    def _write_summary_sheet(self, workbook, data, hierarchy, months):
        f = self._build_formats(workbook)
        sheet = workbook.add_worksheet("Budget Spread Report")
        sheet.set_zoom(85)

        self._write_report_header(sheet, f, data, months, "BUDGET SPREAD REPORT")

        # Row 7: column headers
        sheet.write(7, 0, "Budget Position", f["header"])
        for idx, (y, m) in enumerate(months):
            sheet.write(7, 1 + idx, self._month_label(y, m), f["header"])
        sheet.write(7, 1 + len(months), "Total", f["header"])

        month_col_start = 1
        num_data_cols = len(months) + 1

        row = 8

        revenue_budget = {ym: 0.0 for ym in months}
        expense_budget = {ym: 0.0 for ym in months}

        sorted_mg = sorted(hierarchy.values(), key=lambda x: (x["sequence"], x["name"]))

        for mg in sorted_mg:
            mg_name_lower = (mg.get("name") or "").strip().lower()
            
            # For Revenue group, show header first (no numbers)
            if mg_name_lower == "revenue":
                sheet.write(row, 0, mg["name"], f["main_group"])
                self._fill_empty(sheet, row, month_col_start, num_data_cols, f["main_group"])
                row += 1
            
            sorted_sg = sorted(
                mg["sub_groups"].values(), key=lambda x: (x["sequence"], x["name"])
            )

            for sg in sorted_sg:
                # Write sub group with its budget amount directly
                sheet.write(row, 0, sg["name"], f["sub_group"])
                self._write_num_row(sheet, row, month_col_start, months,
                                    sg["budget_by_month"], f["sub_group_num"])
                row += 1

            # Write main group total
            if mg_name_lower == "revenue":
                total_label = f"TOTAL: {mg['name']}"
                for ym in months:
                    revenue_budget[ym] += mg["budget_by_month"][ym]
            elif mg_name_lower in ("cost of revenue", "variable cost"):
                total_label = f"TOTAL: Cost of Revenue"
                for ym in months:
                    expense_budget[ym] += mg["budget_by_month"][ym]
            elif mg_name_lower in ("expenses", "operating expenses"):
                total_label = f"TOTAL: Expenses"
                for ym in months:
                    expense_budget[ym] += mg["budget_by_month"][ym]
            else:
                total_label = f"TOTAL: {mg['name']}"
                for ym in months:
                    expense_budget[ym] += mg["budget_by_month"][ym]
            
            sheet.write(row, 0, total_label, f["main_total"])
            self._write_num_row(sheet, row, month_col_start, months,
                                mg["budget_by_month"], f["main_total_num"])
            row += 1

        # Grand total rows
        sheet.write(row, 0, "TOTAL: DIRECT + OTHER EXPENSES", f["grand_total"])
        self._write_num_row(sheet, row, month_col_start, months,
                            expense_budget, f["grand_total_num"])
        row += 1

        # Gross Profit/Loss
        gp_budget = {ym: revenue_budget[ym] - expense_budget[ym] for ym in months}
        sheet.write(row, 0, "GRAND TOTAL-PROFIT/LOSS", f["grand_total"])
        self._write_num_row(sheet, row, month_col_start, months,
                            gp_budget, f["grand_total_num"])

        # Column widths & freeze
        sheet.set_column(0, 0, 35)
        for c in range(1, 1 + len(months) + 1):
            sheet.set_column(c, c, 14)
        sheet.freeze_panes(8, 1)
        sheet.autofilter(7, 0, 7, len(months) + 1)

    # ------------------------------------------------------------------
    # Sheet 2: Budget Spread Details (Exactly as you had it)
    # ------------------------------------------------------------------

    def _write_details_sheet(self, workbook, data, hierarchy, months):
        f = self._build_formats(workbook)
        sheet = workbook.add_worksheet("Budget Details")
        sheet.set_zoom(85)

        self._write_report_header(sheet, f, data, months, "BUDGET SPREAD REPORT - DETAILS")

        # Row 7: column headers
        sheet.write(7, 0, "Budget Position", f["header"])
        sheet.write(7, 1, "Analytical Account", f["header"])
        for idx, (y, m) in enumerate(months):
            sheet.write(7, 2 + idx, self._month_label(y, m), f["header"])
        sheet.write(7, 2 + len(months), "Total", f["header"])

        month_col_start = 2
        num_data_cols = len(months) + 1

        row = 8

        revenue_budget = {ym: 0.0 for ym in months}
        expense_budget = {ym: 0.0 for ym in months}

        sorted_mg = sorted(hierarchy.values(), key=lambda x: (x["sequence"], x["name"]))

        for mg in sorted_mg:
            # Main group header
            sheet.write(row, 0, mg["name"], f["main_group"])
            sheet.write(row, 1, "", f["main_group"])
            self._fill_empty(sheet, row, month_col_start, num_data_cols, f["main_group"])
            row += 1

            sorted_sg = sorted(
                mg["sub_groups"].values(), key=lambda x: (x["sequence"], x["name"])
            )

            for sg in sorted_sg:
                # Sub group header
                sheet.write(row, 0, f"  {sg['name']}", f["sub_group"])
                sheet.write(row, 1, "", f["sub_group"])
                self._fill_empty(sheet, row, month_col_start, num_data_cols, f["sub_group"])
                row += 1

                # Each budget position
                for pos in sg["positions"].values():
                    sheet.write(row, 0, pos["name"], f["budget_line"])
                    sheet.write(row, 1, pos["analytic_name"], f["budget_line"])
                    self._write_num_row(sheet, row, month_col_start, months,
                                        pos["budget_by_month"], f["budget_line_num"])
                    row += 1

                # Sub group subtotal
                sheet.write(row, 0, f"Subtotal {sg['name']}", f["sub_total"])
                sheet.write(row, 1, "", f["sub_total"])
                self._write_num_row(sheet, row, month_col_start, months,
                                    sg["budget_by_month"], f["sub_total_num"])
                row += 1

            # Main group total
            sheet.write(row, 0, f"Total {mg['name']}", f["main_total"])
            sheet.write(row, 1, "", f["main_total"])
            self._write_num_row(sheet, row, month_col_start, months,
                                mg["budget_by_month"], f["main_total_num"])
            row += 1

            # Accumulate for grand totals
            name_lower = (mg.get("name") or "").strip().lower()
            if name_lower in ("cost of revenue", "expenses"):
                for ym in months:
                    expense_budget[ym] += mg["budget_by_month"][ym]
            elif name_lower == "revenue":
                for ym in months:
                    revenue_budget[ym] += mg["budget_by_month"][ym]

        # Grand total rows
        sheet.write(row, 0, "TOTAL DIRECT + OTHER EXPENSES", f["grand_total"])
        sheet.write(row, 1, "", f["grand_total"])
        self._write_num_row(sheet, row, month_col_start, months,
                            expense_budget, f["grand_total_num"])
        row += 1

        # Gross Profit/Loss
        gp_budget = {ym: revenue_budget[ym] - expense_budget[ym] for ym in months}
        sheet.write(row, 0, "GROSS PROFIT/LOSS", f["grand_total"])
        sheet.write(row, 1, "", f["grand_total"])
        self._write_num_row(sheet, row, month_col_start, months,
                            gp_budget, f["grand_total_num"])

        # Column widths & freeze
        sheet.set_column(0, 0, 35)
        sheet.set_column(1, 1, 30)
        for c in range(2, 2 + len(months) + 1):
            sheet.set_column(c, c, 14)
        sheet.freeze_panes(8, 2)
        sheet.autofilter(7, 0, 7, 2 + len(months))

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def generate_xlsx_report(self, workbook, data, lines):
        hierarchy, months = self._collect_data(data)
        self._write_summary_sheet(workbook, data, hierarchy, months)
        self._write_details_sheet(workbook, data, hierarchy, months)