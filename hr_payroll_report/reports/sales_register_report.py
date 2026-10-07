from odoo import models, fields
from datetime import datetime, date
from calendar import monthrange
from dateutil.relativedelta import relativedelta

class SalesRegisterReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.sales_register_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Sales Register Excel Report'

    def _get_customer_code(self, invoice, customer):
        return invoice.code or 'N/A'

    def _get_customer_data(self, date_from, date_to, branch_ids, months):
        """
        Aggregate data per customer per month
        Based on account.move (invoice) totals
        """
        # Convert string dates to date objects
        date_from_obj = fields.Date.from_string(date_from)
        date_to_obj = fields.Date.from_string(date_to)
        
        # Calculate YTD start date (January 1st of the year from date_from)
        ytd_start = date(date_from_obj.year, 1, 1)

        # Domain for monthly filtered invoices (selected period)
        domain_monthly = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', date_from_obj),
            ('invoice_date', '<=', date_to_obj),
            ('state', '=', 'posted'),
        ]
        if branch_ids:
            domain_monthly.append(('branch_id', 'in', branch_ids))

        invoices_monthly = self.env['account.move'].search(domain_monthly)

        # Domain for YTD invoices (January 1st to selected date_to)
        domain_ytd = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', ytd_start),
            ('invoice_date', '<=', date_to_obj),
            ('state', '=', 'posted'),
        ]
        if branch_ids:
            domain_ytd.append(('branch_id', 'in', branch_ids))

        invoices_ytd = self.env['account.move'].search(domain_ytd)

        customer_data = {}

        # --- Process monthly invoices ---
        for inv in invoices_monthly:
            customer = inv.partner_id
            if not inv.amount_total_signed:
                continue

            key = (customer.id, inv.branch_id.id or 0, inv.invoice_user_id.id or 0)

            if key not in customer_data:
                customer_data[key] = {
                    'branch': inv.branch_id,
                    'sales_person': inv.invoice_user_id,
                    'cs_coordinator': customer.cs_coordinator_id,
                    'sector': customer.sector_id,
                    'customer_code': self._get_customer_code(inv, customer),
                    'customer_name': customer.name,
                    'monthly_amounts': {m: 0.0 for m in months},
                    'ytd_amount': 0.0,
                }

            month_str = inv.invoice_date.strftime('%b')
            if month_str in customer_data[key]['monthly_amounts']:
                customer_data[key]['monthly_amounts'][month_str] += inv.amount_total_signed

        # --- Process YTD invoices ---
        # Reset YTD amounts first to ensure accurate calculation
        for key in customer_data:
            customer_data[key]['ytd_amount'] = 0.0

        # Now calculate YTD amounts from YTD invoices
        for inv in invoices_ytd:
            customer = inv.partner_id
            key = (customer.id, inv.branch_id.id or 0, inv.invoice_user_id.id or 0)
            
            # If customer doesn't exist in customer_data, add them
            if key not in customer_data:
                customer_data[key] = {
                    'branch': inv.branch_id,
                    'sales_person': inv.invoice_user_id,
                    'cs_coordinator': customer.cs_coordinator_id,
                    'sector': customer.sector_id,
                    'customer_code': self._get_customer_code(inv, customer),
                    'customer_name': customer.name,
                    'monthly_amounts': {m: 0.0 for m in months},
                    'ytd_amount': 0.0,
                }
            
            customer_data[key]['ytd_amount'] += inv.amount_total_signed

        return customer_data
    

    def _get_salesperson_data(self, date_from, date_to, branch_ids, months):
        """
        Aggregate data salesperson-wise per month
        """
        # Convert string dates to date objects
        date_from_obj = fields.Date.from_string(date_from)
        date_to_obj = fields.Date.from_string(date_to)
        
        # Calculate YTD start date (January 1st of the year from date_from)
        ytd_start = date(date_from_obj.year, 1, 1)

        # Domain for monthly filtered invoices (selected period)
        domain_monthly = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', date_from_obj),
            ('invoice_date', '<=', date_to_obj),
            ('state', '=', 'posted'),
        ]
        if branch_ids:
            domain_monthly.append(('branch_id', 'in', branch_ids))

        invoices_monthly = self.env['account.move'].search(domain_monthly)

        # Domain for YTD invoices (January 1st to selected date_to)
        domain_ytd = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', ytd_start),
            ('invoice_date', '<=', date_to_obj),
            ('state', '=', 'posted'),
        ]
        if branch_ids:
            domain_ytd.append(('branch_id', 'in', branch_ids))

        invoices_ytd = self.env['account.move'].search(domain_ytd)

        salesperson_data = {}

        # --- Process monthly invoices for salesperson summary ---
        for inv in invoices_monthly:
            sales_person = inv.invoice_user_id
            branch = inv.branch_id
            
            if not sales_person:
                continue

            key = (sales_person.id, branch.id if branch else 0)

            if key not in salesperson_data:
                salesperson_data[key] = {
                    'branch': branch,
                    'sales_person': sales_person,
                    'monthly_amounts': {m: 0.0 for m in months},
                    'ytd_amount': 0.0,
                }

            month_str = inv.invoice_date.strftime('%b')
            if month_str in salesperson_data[key]['monthly_amounts']:
                salesperson_data[key]['monthly_amounts'][month_str] += inv.amount_total_signed

        # --- Process YTD invoices for salesperson summary ---
        # Reset YTD amounts first
        for key in salesperson_data:
            salesperson_data[key]['ytd_amount'] = 0.0

        # Calculate YTD amounts
        for inv in invoices_ytd:
            sales_person = inv.invoice_user_id
            branch = inv.branch_id
            
            if not sales_person:
                continue

            key = (sales_person.id, branch.id if branch else 0)
            
            if key not in salesperson_data:
                salesperson_data[key] = {
                    'branch': branch,
                    'sales_person': sales_person,
                    'monthly_amounts': {m: 0.0 for m in months},
                    'ytd_amount': 0.0,
                }
            
            salesperson_data[key]['ytd_amount'] += inv.amount_total_signed

        return salesperson_data

    def _generate_main_report(self, workbook, data, customer_data):
        """Generate the main Sales Register Report sheet"""
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        branch_ids = data.get('branch_ids', [])
        months = data.get('months', [])

        sheet = workbook.add_worksheet('Sales Register Report')

        # Formats
        bold = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3'})
        left = workbook.add_format({'align': 'left'})
        right = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#002060', 'font_color': 'white'})
        header_format_red = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#FF0000', 'font_color': 'white'})

        # Title
        sheet.merge_range('A1:H1', 'SALES REGISTER REPORT', bold)
        sheet.write('A2', 'Period', bold)
        sheet.write('B2', f"{date_from} to {date_to}")
        sheet.write('A3', 'Branches', bold)
        branch_names = ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name')) if branch_ids else 'All Branches'
        sheet.write('B3', branch_names)

        # Add YTD period info
        date_from_obj = fields.Date.from_string(date_from)
        ytd_start = date(date_from_obj.year, 1, 1)
        sheet.write('A4', 'YTD Period', bold)
        sheet.write('B4', f"{ytd_start} to {date_to}")

        # Headers
        headers = [
            'Branch', 'Sales Person', 'CS Coordinator', 'Sector',
            'Customer Code', 'Customer Name'
        ]
        headers += [m.upper() for m in months]
        headers.append('YTD TOTAL')

        # Write headers
        row = 6
        for col, head in enumerate(headers):
            if head == 'YTD TOTAL':
                sheet.write(row, col, head, header_format_red)
            else:
                sheet.write(row, col, head, header_format)
        row += 1

        # Data
        total_monthly = {m: 0.0 for m in months}
        total_ytd = 0.0

        for key, info in customer_data.items():
            sheet.write(row, 0, info['branch'].name if info['branch'] else '', left)
            sheet.write(row, 1, info['sales_person'].name if info['sales_person'] else '', left)
            sheet.write(row, 2, info['cs_coordinator'].name if info['cs_coordinator'] else '', left)
            sheet.write(row, 3, info['sector'].name if info['sector'] else '', left)
            sheet.write(row, 4, info['customer_code'], left)
            sheet.write(row, 5, info['customer_name'], left)

            col = 6
            for m in months:
                amt = info['monthly_amounts'].get(m, 0.0)
                total_monthly[m] += amt
                sheet.write(row, col, amt, right)
                col += 1

            total_ytd += info['ytd_amount']
            sheet.write(row, col, info['ytd_amount'], right)
            row += 1

        # Add Grand Total Row
        sheet.write(row, 5, "TOTAL", bold)
        col = 6
        for m in months:
            sheet.write(row, col, total_monthly[m], right)
            col += 1
        sheet.write(row, col, total_ytd, right)

        # Auto adjust width
        for i in range(len(headers)):
            sheet.set_column(i, i, 18)

    def _generate_salesperson_report(self, workbook, data, salesperson_data):
        """Generate the Salesperson Wise Summary sheet"""
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        branch_ids = data.get('branch_ids', [])
        months = data.get('months', [])

        sheet = workbook.add_worksheet('Salesperson Wise Summary')

        # Formats
        bold = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3'})
        left = workbook.add_format({'align': 'left'})
        right = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#002060', 'font_color': 'white'})
        header_format_red = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#FF0000', 'font_color': 'white'})


        # Title
        sheet.merge_range('A1:D1', 'SALESPERSON WISE SUMMARY REPORT', bold)
        sheet.write('A2', 'Period', bold)
        sheet.write('B2', f"{date_from} to {date_to}")
        sheet.write('A3', 'Branches', bold)
        branch_names = ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name')) if branch_ids else 'All Branches'
        sheet.write('B3', branch_names)

        # Add YTD period info
        date_from_obj = fields.Date.from_string(date_from)
        ytd_start = date(date_from_obj.year, 1, 1)
        sheet.write('A4', 'YTD Period', bold)
        sheet.write('B4', f"{ytd_start} to {date_to}")

        # Headers for salesperson summary
        headers = ['Branch', 'Sales Person']
        headers += [m.upper() for m in months]
        headers.append('YTD TOTAL')

        # Write headers
        row = 6
        for col, head in enumerate(headers):
            if head == 'YTD TOTAL':
                sheet.write(row, col, head, header_format_red)
            else:
                sheet.write(row, col, head, header_format)
        row += 1

        # Data
        total_monthly = {m: 0.0 for m in months}
        total_ytd = 0.0

        # Sort salesperson data by branch and salesperson name
        sorted_salesperson_data = sorted(
            salesperson_data.values(), 
            key=lambda x: (
                x['branch'].name if x['branch'] else '',
                x['sales_person'].name if x['sales_person'] else ''
            )
        )

        for info in sorted_salesperson_data:
            sheet.write(row, 0, info['branch'].name if info['branch'] else 'All Branches', left)
            sheet.write(row, 1, info['sales_person'].name if info['sales_person'] else 'No Salesperson', left)

            col = 2
            for m in months:
                amt = info['monthly_amounts'].get(m, 0.0)
                total_monthly[m] += amt
                sheet.write(row, col, amt, right)
                col += 1

            total_ytd += info['ytd_amount']
            sheet.write(row, col, info['ytd_amount'], right)
            row += 1

        # Add Grand Total Row
        sheet.write(row, 1, "TOTAL", bold)
        col = 2
        for m in months:
            sheet.write(row, col, total_monthly[m], right)
            col += 1
        sheet.write(row, col, total_ytd, right)

        # Auto adjust width
        for i in range(len(headers)):
            sheet.set_column(i, i, 18)

    def _generate_comparison_report(self, workbook, data):
        date_to = fields.Date.from_string(data.get('date_to'))
        branch_ids = data.get('branch_ids', [])

        # Determine two months
        current_month = date_to.strftime('%b')     # e.g. AUG
        prev_month_date = date_to - relativedelta(months=1)
        previous_month = prev_month_date.strftime('%b')  # e.g. JUL

        months = [previous_month, current_month]

        # Build domain
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', prev_month_date.replace(day=1)),
            ('invoice_date', '<=', date_to),
            ('state', '=', 'posted'),
        ]
        if branch_ids:
            domain.append(('branch_id', 'in', branch_ids))

        invoices = self.env['account.move'].search(domain)

        # Aggregate by Customer
        customer_data = {}

        for inv in invoices:
            customer = inv.partner_id
            key = (customer.id, inv.branch_id.id or 0, inv.invoice_user_id.id or 0)

            if key not in customer_data:
                customer_data[key] = {
                    'branch': inv.branch_id,
                    'sales_person': inv.invoice_user_id,
                    'cs_coordinator': customer.cs_coordinator_id,
                    'sector': customer.sector_id,
                    'customer_code': customer.ref or inv.ref or inv.name or '',
                    'customer_name': customer.name,
                    'monthly_amounts': {previous_month: 0.0, current_month: 0.0},
                }

            month_str = inv.invoice_date.strftime('%b')
            if month_str in customer_data[key]['monthly_amounts']:
                customer_data[key]['monthly_amounts'][month_str] += inv.amount_total_signed

        # Create sheet
        sheet = workbook.add_worksheet('Sales Register Comparison')

        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#002060', 'font_color': 'white'})
        header_format_red = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#FF0000', 'font_color': 'white'})
        left = workbook.add_format({'align': 'left'})
        right = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})
        bold = workbook.add_format({'bold': True})

        # Title
        sheet.merge_range('A1:H1', 'SALES REGISTER COMPARISON', bold)

        sheet.write('A2', 'Month', bold)
        sheet.write('B2', f"{previous_month} & {current_month}")

        sheet.write('A3', 'Branches', bold)
        branches = ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name')) if branch_ids else 'All Branches'
        sheet.write('B3', branches)

        # Headers
        headers = [
            'Branch', 'Sales Person', 'CS Coordinator', 'Sector',
            'Customer Code', 'Customer Name',
            previous_month.upper(),
            current_month.upper(),
            'COMPARISON'
        ]

        row = 5
        for col, h in enumerate(headers):
            if h == 'COMPARISON':
                sheet.write(row, col, h, header_format_red)
            else:
                sheet.write(row, col, h, header_format)
        row += 1

        # Write content
        for info in customer_data.values():
            sheet.write(row, 0, info['branch'].name if info['branch'] else '', left)
            sheet.write(row, 1, info['sales_person'].name if info['sales_person'] else '', left)
            sheet.write(row, 2, info['cs_coordinator'].name if info['cs_coordinator'] else '', left)
            sheet.write(row, 3, info['sector'].name if info['sector'] else '', left)
            sheet.write(row, 4, info['customer_code'], left)
            sheet.write(row, 5, info['customer_name'], left)

            prev_val = info['monthly_amounts'][previous_month]
            curr_val = info['monthly_amounts'][current_month]

            sheet.write(row, 6, prev_val, right)
            sheet.write(row, 7, curr_val, right)

            diff = curr_val - prev_val
            sheet.write(row, 8, diff, right)

            row += 1

        sheet.merge_range(row, 0, row, 5, 'TOTAL', bold)

        prev_month_total = sum(info['monthly_amounts'][previous_month] for info in customer_data.values())
        curr_month_total = sum(info['monthly_amounts'][current_month] for info in customer_data.values())
        diff_total = curr_month_total - prev_month_total

        sheet.write(row, 6, prev_month_total, right)
        sheet.write(row, 7, curr_month_total, right)
        sheet.write(row, 8, diff_total, right)

        for i in range(len(headers)):
            sheet.set_column(i, i, 18)

    # -----------------------------
    # MAIN XLSX GENERATION
    # -----------------------------
    def generate_xlsx_report(self, workbook, data, wizard):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        branch_ids = data.get('branch_ids', [])
        months = data.get('months', [])

        # Get data for both reports
        customer_data = self._get_customer_data(date_from, date_to, branch_ids, months)
        salesperson_data = self._get_salesperson_data(date_from, date_to, branch_ids, months)

        # Generate both sheets
        self._generate_main_report(workbook, data, customer_data)
        self._generate_salesperson_report(workbook, data, salesperson_data)
        self._generate_comparison_report(workbook, data)