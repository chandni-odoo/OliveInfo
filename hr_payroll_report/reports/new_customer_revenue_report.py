from odoo import models, fields, api
from datetime import datetime, date
from calendar import monthrange

class NewCustomerRevenueReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.new_customer_revenue_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'New Customer Revenue Excel Report'

    def _get_customer_code(self, invoice, customer):
        return invoice.code or 'N/A'

    def _get_new_customers_for_year(self, year, branch_ids):
        """
        Returns a dict: {partner_id (int): qualifying_month (int 1-12)}

        A customer qualifies as NEW in `year` if:
          (A) No posted invoice exists before `year` (brand new), OR
          (B) Their most recent invoice before `year` was before date(year-1, 1, 1)
              meaning no invoice at all during the previous year (1+ year gap).

        The qualifying_month is the month of their FIRST posted invoice in `year`.
        """
        year = int(year)
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        prev_year_start = date(year - 1, 1, 1)  # gap threshold

        Invoice = self.env['account.move']

        # All posted customer invoices in the selected year
        base_domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', year_start),
            ('invoice_date', '<=', year_end),
        ]
        if branch_ids:
            base_domain.append(('branch_id', 'in', branch_ids))

        invoices_this_year = Invoice.search(base_domain, order='invoice_date asc')

        # Find each customer's FIRST invoice month in this year
        customer_first_month = {}  # partner_id -> first month int (1-12)
        for inv in invoices_this_year:
            pid = inv.partner_id.id
            m = inv.invoice_date.month
            if pid not in customer_first_month or m < customer_first_month[pid]:
                customer_first_month[pid] = m

        if not customer_first_month:
            return {}  # <-- returns dict, not recordset

        # Check each customer against new-customer rules
        qualifying = {}  # partner_id -> qualifying month int

        for partner_id, first_month in customer_first_month.items():
            prior = Invoice.search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('partner_id', '=', partner_id),
                ('invoice_date', '<', year_start),
            ], order='invoice_date desc', limit=1)

            if not prior:
                # Rule A: Never invoiced before → brand new
                qualifying[partner_id] = first_month
            elif prior[0].invoice_date < prev_year_start:
                # Rule B: Last invoice was more than 1 full year ago → returning new
                qualifying[partner_id] = first_month
            # else: had invoice in previous year → NOT new, skip

        return qualifying  # {partner_id: qualifying_month_int}

    def _get_customer_data(self, year, branch_ids, months):
        """
        Aggregate data for new customers per month.
        qualifying_map is passed in explicitly from generate_xlsx_report.
        """
        qualifying_map = self._get_new_customers_for_year(year, branch_ids)

        if not qualifying_map:
            return {}

        new_customer_ids = list(qualifying_map.keys())
        year_start = date(int(year), 1, 1)
        year_end = date(int(year), 12, 31)

        domain_monthly = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', year_start),
            ('invoice_date', '<=', year_end),
            ('partner_id', 'in', new_customer_ids),
            ('state', '=', 'posted'),
        ]
        if branch_ids:
            domain_monthly.append(('branch_id', 'in', branch_ids))

        invoices_monthly = self.env['account.move'].search(domain_monthly)
        invoices_ytd = self.env['account.move'].search(domain_monthly)  # same domain = full year

        customer_data = {}

        # --- Monthly ---
        for inv in invoices_monthly:
            customer = inv.partner_id
            if not inv.amount_total_signed:
                continue

            # Skip invoices before the customer's qualifying month
            qualifying_month = qualifying_map.get(customer.id)
            if qualifying_month and inv.invoice_date.month < qualifying_month:
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
                    'customer_create_date': customer.create_date,
                }

            month_str = inv.invoice_date.strftime('%b')
            if month_str in customer_data[key]['monthly_amounts']:
                customer_data[key]['monthly_amounts'][month_str] += inv.amount_total_signed

        # --- YTD ---
        for key in customer_data:
            customer_data[key]['ytd_amount'] = 0.0

        for inv in invoices_ytd:
            customer = inv.partner_id

            qualifying_month = qualifying_map.get(customer.id)
            if qualifying_month and inv.invoice_date.month < qualifying_month:
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
                    'customer_create_date': customer.create_date,
                }

            customer_data[key]['ytd_amount'] += inv.amount_total_signed

        return customer_data

    def _get_salesperson_data(self, year, branch_ids, months, qualifying_map):
        """
        Aggregate data salesperson-wise. Receives qualifying_map explicitly.
        """
        if not qualifying_map:
            return {}

        new_customer_ids = list(qualifying_map.keys())
        year_start = date(int(year), 1, 1)
        year_end = date(int(year), 12, 31)

        domain_monthly = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', year_start),
            ('invoice_date', '<=', year_end),
            ('partner_id', 'in', new_customer_ids),
            ('state', '=', 'posted'),
        ]
        if branch_ids:
            domain_monthly.append(('branch_id', 'in', branch_ids))

        invoices_monthly = self.env['account.move'].search(domain_monthly)
        invoices_ytd = self.env['account.move'].search(domain_monthly)

        salesperson_data = {}

        # --- Monthly ---
        for inv in invoices_monthly:
            sales_person = inv.invoice_user_id
            branch = inv.branch_id

            if not sales_person:
                continue

            qualifying_month = qualifying_map.get(inv.partner_id.id)
            if qualifying_month and inv.invoice_date.month < qualifying_month:
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

        # --- YTD ---
        for key in salesperson_data:
            salesperson_data[key]['ytd_amount'] = 0.0

        for inv in invoices_ytd:
            sales_person = inv.invoice_user_id
            branch = inv.branch_id

            if not sales_person:
                continue

            qualifying_month = qualifying_map.get(inv.partner_id.id)
            if qualifying_month and inv.invoice_date.month < qualifying_month:
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
        year = data.get('year')
        branch_ids = data.get('branch_ids', [])
        months = data.get('months', [])

        sheet = workbook.add_worksheet('New Customer Revenue Report')

        bold = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3'})
        left = workbook.add_format({'align': 'left'})
        right = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#002060', 'font_color': 'white'})
        header_format_red = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#FF0000', 'font_color': 'white'})

        sheet.merge_range('A1:H1', 'NEW CUSTOMER REVENUE REPORT', bold)
        sheet.write('A2', 'Year', bold)
        sheet.write('B2', year)
        sheet.write('A3', 'Branches', bold)
        branch_names = ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name')) if branch_ids else 'All Branches'
        sheet.write('B3', branch_names)

        ytd_start = date(int(year), 1, 1)
        ytd_end = date(int(year), 12, 31)
        sheet.write('A4', 'YTD Period', bold)
        sheet.write('B4', f"{ytd_start} to {ytd_end}")

        headers = ['Branch', 'Sales Person', 'CS Coordinator', 'Sector', 'Customer Code', 'Customer Name']
        headers += [m.upper() for m in months]
        headers.append('YTD TOTAL')

        row = 6
        for col, head in enumerate(headers):
            sheet.write(row, col, head, header_format_red if head == 'YTD TOTAL' else header_format)
        row += 1

        total_monthly = {m: 0.0 for m in months}
        total_ytd = 0.0

        sorted_customer_data = sorted(
            customer_data.values(),
            key=lambda x: (
                x['branch'].name if x['branch'] else '',
                x['sales_person'].name if x['sales_person'] else '',
                x['customer_name']
            )
        )

        for info in sorted_customer_data:
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

        sheet.write(row, 5, "TOTAL", bold)
        col = 6
        for m in months:
            sheet.write(row, col, total_monthly[m], right)
            col += 1
        sheet.write(row, col, total_ytd, right)

        for i in range(len(headers)):
            sheet.set_column(i, i, 18)

    def _generate_salesperson_report(self, workbook, data, salesperson_data):
        year = data.get('year')
        branch_ids = data.get('branch_ids', [])
        months = data.get('months', [])

        sheet = workbook.add_worksheet('Salesperson Wise Summary')

        bold = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3'})
        left = workbook.add_format({'align': 'left'})
        right = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#002060', 'font_color': 'white'})
        header_format_red = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#FF0000', 'font_color': 'white'})

        sheet.merge_range('A1:D1', 'SALESPERSON WISE SUMMARY - NEW CUSTOMERS', bold)
        sheet.write('A2', 'Year', bold)
        sheet.write('B2', year)
        sheet.write('A3', 'Branches', bold)
        branch_names = ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name')) if branch_ids else 'All Branches'
        sheet.write('B3', branch_names)

        ytd_start = date(int(year), 1, 1)
        ytd_end = date(int(year), 12, 31)
        sheet.write('A4', 'YTD Period', bold)
        sheet.write('B4', f"{ytd_start} to {ytd_end}")

        headers = ['Branch', 'Sales Person']
        headers += [m.upper() for m in months]
        headers.append('YTD TOTAL')

        row = 6
        for col, head in enumerate(headers):
            sheet.write(row, col, head, header_format_red if head == 'YTD TOTAL' else header_format)
        row += 1

        total_monthly = {m: 0.0 for m in months}
        total_ytd = 0.0

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

        sheet.write(row, 1, "TOTAL", bold)
        col = 2
        for m in months:
            sheet.write(row, col, total_monthly[m], right)
            col += 1
        sheet.write(row, col, total_ytd, right)

        for i in range(len(headers)):
            sheet.set_column(i, i, 18)

    # ── MAIN ENTRY POINT ────────────────────────────────────────────────────
    def generate_xlsx_report(self, workbook, data, wizard):
        year = data.get('year')
        branch_ids = data.get('branch_ids', [])
        months = data.get('months', [])

        # Compute qualifying map ONCE here and pass it explicitly
        # No self attribute assignment — avoids the AttributeError entirely
        qualifying_map = self._get_new_customers_for_year(year, branch_ids)

        customer_data = self._get_customer_data(year, branch_ids, months)
        salesperson_data = self._get_salesperson_data(year, branch_ids, months, qualifying_map)

        self._generate_main_report(workbook, data, customer_data)
        self._generate_salesperson_report(workbook, data, salesperson_data)

# class NewCustomerRevenueReportXlsx(models.AbstractModel):
#     _name = 'report.hr_payroll_report.new_customer_revenue_report_xlsx'
#     _inherit = 'report.report_xlsx.abstract'
#     _description = 'New Customer Revenue Excel Report'

#     def _get_customer_code(self, invoice, customer):
#         return invoice.code or 'N/A'

#     def _get_new_customers_for_year(self, year, branch_ids):
#         """
#         Get new customers created in the selected year
#         Customers are considered new if:
#         1. is_customer boolean field is True
#         2. Created in the selected year
#         """
#         domain = [
#             ('is_customer', '=', True),
#             ('create_date', '>=', f'{year}-01-01'),
#             ('create_date', '<=', f'{year}-12-31'),
#         ]
        
#         return self.env['res.partner'].search(domain)

#     def _get_customer_data(self, year, branch_ids, months):
#         """
#         Aggregate data for new customers per month
#         """
#         # Get new customers for the selected year
#         new_customers = self._get_new_customers_for_year(year, branch_ids)
        
#         if not new_customers:
#             return {}

#         # Calculate date ranges
#         year_start = date(int(year), 1, 1)
#         year_end = date(int(year), 12, 31)
#         ytd_end = year_end  # For YTD calculation (full year)

#         # Domain for monthly invoices for new customers
#         domain_monthly = [
#             ('move_type', '=', 'out_invoice'),
#             ('invoice_date', '>=', year_start),
#             ('invoice_date', '<=', year_end),
#             ('partner_id', 'in', new_customers.ids),
#             ('state', '=', 'posted'),
#         ]
#         if branch_ids:
#             domain_monthly.append(('branch_id', 'in', branch_ids))

#         invoices_monthly = self.env['account.move'].search(domain_monthly)

#         # Domain for YTD invoices (same as monthly for full year report)
#         domain_ytd = domain_monthly.copy()
#         invoices_ytd = self.env['account.move'].search(domain_ytd)

#         customer_data = {}

#         # --- Process monthly invoices ---
#         for inv in invoices_monthly:
#             customer = inv.partner_id
#             if not inv.amount_total_signed:
#                 continue

#             key = (customer.id, inv.branch_id.id or 0, inv.invoice_user_id.id or 0)

#             if key not in customer_data:
#                 customer_data[key] = {
#                     'branch': inv.branch_id,
#                     'sales_person': inv.invoice_user_id,
#                     'cs_coordinator': customer.cs_coordinator_id,
#                     'sector': customer.sector_id,
#                     'customer_code': self._get_customer_code(inv, customer),
#                     'customer_name': customer.name,
#                     'monthly_amounts': {m: 0.0 for m in months},
#                     'ytd_amount': 0.0,
#                     'customer_create_date': customer.create_date,
#                 }

#             month_str = inv.invoice_date.strftime('%b')
#             if month_str in customer_data[key]['monthly_amounts']:
#                 customer_data[key]['monthly_amounts'][month_str] += inv.amount_total_signed

#         # --- Process YTD invoices ---
#         # Reset YTD amounts first to ensure accurate calculation
#         for key in customer_data:
#             customer_data[key]['ytd_amount'] = 0.0

#         # Now calculate YTD amounts from YTD invoices
#         for inv in invoices_ytd:
#             customer = inv.partner_id
#             key = (customer.id, inv.branch_id.id or 0, inv.invoice_user_id.id or 0)
            
#             # If customer doesn't exist in customer_data, add them
#             if key not in customer_data:
#                 customer_data[key] = {
#                     'branch': inv.branch_id,
#                     'sales_person': inv.invoice_user_id,
#                     'cs_coordinator': customer.cs_coordinator_id,
#                     'sector': customer.sector_id,
#                     'customer_code': self._get_customer_code(inv, customer),
#                     'customer_name': customer.name,
#                     'monthly_amounts': {m: 0.0 for m in months},
#                     'ytd_amount': 0.0,
#                     'customer_create_date': customer.create_date,
#                 }
            
#             customer_data[key]['ytd_amount'] += inv.amount_total_signed

#         return customer_data

#     def _get_salesperson_data(self, year, branch_ids, months):
#         """
#         Aggregate data salesperson-wise per month for new customers
#         """
#         # Get new customers for the selected year
#         new_customers = self._get_new_customers_for_year(year, branch_ids)
        
#         if not new_customers:
#             return {}

#         # Calculate date ranges
#         year_start = date(int(year), 1, 1)
#         year_end = date(int(year), 12, 31)

#         # Domain for monthly filtered invoices
#         domain_monthly = [
#             ('move_type', '=', 'out_invoice'),
#             ('invoice_date', '>=', year_start),
#             ('invoice_date', '<=', year_end),
#             ('partner_id', 'in', new_customers.ids),
#             ('state', '=', 'posted'),
#         ]
#         if branch_ids:
#             domain_monthly.append(('branch_id', 'in', branch_ids))

#         invoices_monthly = self.env['account.move'].search(domain_monthly)

#         # Domain for YTD invoices
#         domain_ytd = domain_monthly.copy()
#         invoices_ytd = self.env['account.move'].search(domain_ytd)

#         salesperson_data = {}

#         # --- Process monthly invoices for salesperson summary ---
#         for inv in invoices_monthly:
#             sales_person = inv.invoice_user_id
#             branch = inv.branch_id
            
#             if not sales_person:
#                 continue

#             key = (sales_person.id, branch.id if branch else 0)

#             if key not in salesperson_data:
#                 salesperson_data[key] = {
#                     'branch': branch,
#                     'sales_person': sales_person,
#                     'monthly_amounts': {m: 0.0 for m in months},
#                     'ytd_amount': 0.0,
#                 }

#             month_str = inv.invoice_date.strftime('%b')
#             if month_str in salesperson_data[key]['monthly_amounts']:
#                 salesperson_data[key]['monthly_amounts'][month_str] += inv.amount_total_signed

#         # --- Process YTD invoices for salesperson summary ---
#         # Reset YTD amounts first
#         for key in salesperson_data:
#             salesperson_data[key]['ytd_amount'] = 0.0

#         # Calculate YTD amounts
#         for inv in invoices_ytd:
#             sales_person = inv.invoice_user_id
#             branch = inv.branch_id
            
#             if not sales_person:
#                 continue

#             key = (sales_person.id, branch.id if branch else 0)
            
#             if key not in salesperson_data:
#                 salesperson_data[key] = {
#                     'branch': branch,
#                     'sales_person': sales_person,
#                     'monthly_amounts': {m: 0.0 for m in months},
#                     'ytd_amount': 0.0,
#                 }
            
#             salesperson_data[key]['ytd_amount'] += inv.amount_total_signed

#         return salesperson_data

#     def _generate_main_report(self, workbook, data, customer_data):
#         """Generate the main New Customer Revenue Report sheet"""
#         year = data.get('year')
#         branch_ids = data.get('branch_ids', [])
#         months = data.get('months', [])

#         sheet = workbook.add_worksheet('New Customer Revenue Report')

#         # Formats
#         bold = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3'})
#         left = workbook.add_format({'align': 'left'})
#         right = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})
#         header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#002060', 'font_color': 'white'})
#         header_format_red = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#FF0000', 'font_color': 'white'})

#         # Title
#         sheet.merge_range('A1:H1', 'NEW CUSTOMER REVENUE REPORT', bold)
#         sheet.write('A2', 'Year', bold)
#         sheet.write('B2', year)
#         sheet.write('A3', 'Branches', bold)
#         branch_names = ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name')) if branch_ids else 'All Branches'
#         sheet.write('B3', branch_names)

#         # Add YTD period info
#         ytd_start = date(int(year), 1, 1)
#         ytd_end = date(int(year), 12, 31)
#         sheet.write('A4', 'YTD Period', bold)
#         sheet.write('B4', f"{ytd_start} to {ytd_end}")

#         # Headers
#         headers = [
#             'Branch', 'Sales Person', 'CS Coordinator', 'Sector',
#             'Customer Code', 'Customer Name'
#         ]
#         headers += [m.upper() for m in months]
#         headers.append('YTD TOTAL')

#         # Write headers
#         row = 6
#         for col, head in enumerate(headers):
#             if head == 'YTD TOTAL':
#                 sheet.write(row, col, head, header_format_red)
#             else:
#                 sheet.write(row, col, head, header_format)
#         row += 1

#         # Data
#         total_monthly = {m: 0.0 for m in months}
#         total_ytd = 0.0

#         # Sort customer data by branch, salesperson, and customer name
#         sorted_customer_data = sorted(
#             customer_data.values(), 
#             key=lambda x: (
#                 x['branch'].name if x['branch'] else '',
#                 x['sales_person'].name if x['sales_person'] else '',
#                 x['customer_name']
#             )
#         )

#         for info in sorted_customer_data:
#             sheet.write(row, 0, info['branch'].name if info['branch'] else '', left)
#             sheet.write(row, 1, info['sales_person'].name if info['sales_person'] else '', left)
#             sheet.write(row, 2, info['cs_coordinator'].name if info['cs_coordinator'] else '', left)
#             sheet.write(row, 3, info['sector'].name if info['sector'] else '', left)
#             sheet.write(row, 4, info['customer_code'], left)
#             sheet.write(row, 5, info['customer_name'], left)

#             col = 6
#             for m in months:
#                 amt = info['monthly_amounts'].get(m, 0.0)
#                 total_monthly[m] += amt
#                 sheet.write(row, col, amt, right)
#                 col += 1

#             total_ytd += info['ytd_amount']
#             sheet.write(row, col, info['ytd_amount'], right)
#             row += 1

#         # Add Grand Total Row
#         sheet.write(row, 5, "TOTAL", bold)
#         col = 6
#         for m in months:
#             sheet.write(row, col, total_monthly[m], right)
#             col += 1
#         sheet.write(row, col, total_ytd, right)

#         # Auto adjust width
#         for i in range(len(headers)):
#             sheet.set_column(i, i, 18)

#     def _generate_salesperson_report(self, workbook, data, salesperson_data):
#         """Generate the Salesperson Wise Summary sheet for new customers"""
#         year = data.get('year')
#         branch_ids = data.get('branch_ids', [])
#         months = data.get('months', [])

#         sheet = workbook.add_worksheet('Salesperson Wise Summary')

#         # Formats
#         bold = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3'})
#         left = workbook.add_format({'align': 'left'})
#         right = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})
#         header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#002060', 'font_color': 'white'})
#         header_format_red = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#FF0000', 'font_color': 'white'})

#         # Title
#         sheet.merge_range('A1:D1', 'SALESPERSON WISE SUMMARY - NEW CUSTOMERS', bold)
#         sheet.write('A2', 'Year', bold)
#         sheet.write('B2', year)
#         sheet.write('A3', 'Branches', bold)
#         branch_names = ', '.join(self.env['res.branch'].browse(branch_ids).mapped('name')) if branch_ids else 'All Branches'
#         sheet.write('B3', branch_names)

#         # Add YTD period info
#         ytd_start = date(int(year), 1, 1)
#         ytd_end = date(int(year), 12, 31)
#         sheet.write('A4', 'YTD Period', bold)
#         sheet.write('B4', f"{ytd_start} to {ytd_end}")

#         # Headers for salesperson summary
#         headers = ['Branch', 'Sales Person']
#         headers += [m.upper() for m in months]
#         headers.append('YTD TOTAL')

#         # Write headers
#         row = 6
#         for col, head in enumerate(headers):
#             if head == 'YTD TOTAL':
#                 sheet.write(row, col, head, header_format_red)
#             else:
#                 sheet.write(row, col, head, header_format)
#         row += 1

#         # Data
#         total_monthly = {m: 0.0 for m in months}
#         total_ytd = 0.0

#         # Sort salesperson data by branch and salesperson name
#         sorted_salesperson_data = sorted(
#             salesperson_data.values(), 
#             key=lambda x: (
#                 x['branch'].name if x['branch'] else '',
#                 x['sales_person'].name if x['sales_person'] else ''
#             )
#         )

#         for info in sorted_salesperson_data:
#             sheet.write(row, 0, info['branch'].name if info['branch'] else 'All Branches', left)
#             sheet.write(row, 1, info['sales_person'].name if info['sales_person'] else 'No Salesperson', left)

#             col = 2
#             for m in months:
#                 amt = info['monthly_amounts'].get(m, 0.0)
#                 total_monthly[m] += amt
#                 sheet.write(row, col, amt, right)
#                 col += 1

#             total_ytd += info['ytd_amount']
#             sheet.write(row, col, info['ytd_amount'], right)
#             row += 1

#         # Add Grand Total Row
#         sheet.write(row, 1, "TOTAL", bold)
#         col = 2
#         for m in months:
#             sheet.write(row, col, total_monthly[m], right)
#             col += 1
#         sheet.write(row, col, total_ytd, right)

#         # Auto adjust width
#         for i in range(len(headers)):
#             sheet.set_column(i, i, 18)

#     # -----------------------------
#     # MAIN XLSX GENERATION
#     # -----------------------------
#     def generate_xlsx_report(self, workbook, data, wizard):
#         year = data.get('year')
#         branch_ids = data.get('branch_ids', [])
#         months = data.get('months', [])

#         # Get data for both reports
#         customer_data = self._get_customer_data(year, branch_ids, months)
#         salesperson_data = self._get_salesperson_data(year, branch_ids, months)

#         # Generate both sheets
#         self._generate_main_report(workbook, data, customer_data)
#         self._generate_salesperson_report(workbook, data, salesperson_data)