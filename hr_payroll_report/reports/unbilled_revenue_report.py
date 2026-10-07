from odoo import models, fields, api


class UnbilledRevenueReportXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_report.unbilled_revenue_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Unbilled Revenue Excel Report'


    def _get_unbilled_value(self, task, date_from=None, date_to=None):
        """Return unbilled value for the selected date range."""

        if not date_from or not date_to:
            return task.unbilled_value or 0.0
        
        # Convert to date objects
        date_from = fields.Date.from_string(date_from)
        date_to = fields.Date.from_string(date_to)
        last_invoice_date = task.last_invoice_date

        if not task.last_invoice_date:
            return 0.0
        
        if task.branch_for == 'es':
            # ES Branch Calculation - use date_from and date_to instead of last_invoice_date
            valid_trips = task.trip_sheet_ids.filtered(
                lambda t: 
                    t.date_from and
                    date_from <= fields.Datetime.to_datetime(t.date_from).date() <= date_to and
                    fields.Datetime.to_datetime(t.date_from).date() > last_invoice_date and
                    not t.non_billable and 
                    (not t.remark or t.remark != 'Exception')
            )
            
            billable_amount = sum(trip.billable_qty * task.unit_price for trip in valid_trips)
            equipment_amount = sum(trip.equipment_qty * task.additional_rate for trip in valid_trips)
            return billable_amount + equipment_amount

        elif task.branch_for == 'hro':
            excluded_uoms = ['month', 'months', 'lumpsum', 'week', 'weeks', 'day', 'days']
            uom = (task.task_uom.name or '').lower()
            
            if uom not in excluded_uoms:
                # Regular hours calculation
                regular_timesheets = task.timesheet_ids.filtered(
                    lambda t: 
                        t.date and
                        date_from <= fields.Datetime.to_datetime(t.date).date() <= date_to and
                        fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and 
                        (not t.ref or t.ref != 'Exception')
                )
                regular_amount = sum(t.unit_amount * task.unit_price for t in regular_timesheets)

                # OT NORMAL
                normal_ot = task.overtime_lines_ids.filtered(
                    lambda o: 
                        o.ot_date and
                        date_from <= fields.Datetime.to_datetime(o.ot_date).date() <= date_to and
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                )
                normal_ot_amount = sum(o.ot_hour * task.new_overtime for o in normal_ot)

                # OT SPECIAL
                special_ot = task.overtime_lines_ids.filtered(
                    lambda o: 
                        o.ot_date and
                        date_from <= fields.Datetime.to_datetime(o.ot_date).date() <= date_to and
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                )
                special_ot_amount = sum(o.ot_hour * task.spe_overtime for o in special_ot)

                return regular_amount + normal_ot_amount + special_ot_amount
            
            elif task.task_uom and task.task_uom.name.lower() in ['week', 'weeks']:
                # Weekly calculation
                valid_timesheets = task.timesheet_ids.filtered(
                    lambda t: 
                        t.date and
                        date_from <= fields.Datetime.to_datetime(t.date).date() <= date_to and
                        fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and 
                        (not t.ref or t.ref != 'Exception')
                )
                
                if not valid_timesheets:
                    return 0.0

                # Calculate weeks between date_from and date_to
                max_date = max(valid_timesheets.mapped('date'))
                max_date = fields.Datetime.to_datetime(max_date).date()

                # Weekly calculation
                days_diff = (max_date - task.last_invoice_date).days
                week_diff = days_diff / 7
                
                unbilled_period_amount = week_diff * task.unit_price

                # Agency fee calculation
                agency_fee_amount = 0.0
                if task.agency_fee == 'fix' and task.amount:
                    agency_fee_amount = task.amount * week_diff
                elif task.agency_fee == 'percentage' and task.amount:
                    agency_fee_amount = (task.unit_price * task.amount / 100) * week_diff

                # OT calculation
                normal_ot = task.overtime_lines_ids.filtered(
                    lambda o: 
                        o.ot_date and
                        date_from <= fields.Datetime.to_datetime(o.ot_date).date() <= date_to and
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                )
                special_ot = task.overtime_lines_ids.filtered(
                    lambda o: 
                        o.ot_date and
                        date_from <= fields.Datetime.to_datetime(o.ot_date).date() <= date_to and
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                )

                normal_ot_amount = sum(o.ot_hour * task.new_overtime for o in normal_ot)
                special_ot_amount = sum(o.ot_hour * task.spe_overtime for o in special_ot)

                return unbilled_period_amount + agency_fee_amount + normal_ot_amount + special_ot_amount
            
            elif task.task_uom and task.task_uom.name.lower() in ['day', 'days']:
                valid_days = task.timesheet_ids.filtered(
                    lambda t: t.date and 
                    date_from <= fields.Datetime.to_datetime(t.date).date() <= date_to and
                    fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
                    t.unit_amount > 0 and
                    (not t.ref or t.ref != 'Exception')
                ).mapped('date')
                
                # Count distinct days
                day_count = len(set(valid_days))
                regular_hrs_amount = day_count * task.unit_price

                normal_ot_records = task.overtime_lines_ids.filtered(
                    lambda o: o.ot_date and 
                    date_from <= fields.Datetime.to_datetime(o.ot_date).date() <= date_to and
                    fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                    o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                )
                normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

                special_ot_records = task.overtime_lines_ids.filtered(
                    lambda o: o.ot_date and 
                    date_from <= fields.Datetime.to_datetime(o.ot_date).date() <= date_to and
                    fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                    o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                )
                special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)

                return regular_hrs_amount + normal_ot_amount + special_ot_amount

            else:
                valid_timesheets = task.timesheet_ids.filtered(
                    lambda t: t.date and 
                    date_from <= fields.Datetime.to_datetime(t.date).date() <= date_to and
                    fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and 
                    (not t.ref or t.ref != 'Exception')
                )
                
                if not valid_timesheets:
                    return 0.0
                    
                max_date = max(valid_timesheets.mapped('date'))
                max_date = fields.Datetime.to_datetime(max_date).date()

                month_diff = (max_date.year - task.last_invoice_date.year) * 12 + (max_date.month - task.last_invoice_date.month)
                
                unbilled_month_amount = month_diff * task.unit_price
                
                # Calculate Agency Fee
                agency_fee_amount = 0.0
                if task.agency_fee == 'fix' and task.amount:
                    agency_fee_amount = task.amount * month_diff
                elif task.agency_fee == 'percentage' and task.amount:
                    agency_fee_amount = (task.unit_price * task.amount / 100) * month_diff
                
                # Calculate OT amounts
                normal_ot_records = task.overtime_lines_ids.filtered(
                    lambda o: o.ot_date and 
                    date_from <= fields.Datetime.to_datetime(o.ot_date).date() <= date_to and
                    fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                    o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                )
                normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

                special_ot_records = task.overtime_lines_ids.filtered(
                    lambda o: o.ot_date and 
                    date_from <= fields.Datetime.to_datetime(o.ot_date).date() <= date_to and
                    fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                    o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                )
                special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)
                
                # Final calculation
                return unbilled_month_amount + agency_fee_amount + normal_ot_amount + special_ot_amount
        else:
            return (task.delivered - task.invoiced) * task.unit_price if task.delivered > task.invoiced else 0.0

            
    def generate_xlsx_report(self, workbook, data, wizard):
        """
        Generate the Excel report
        """
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        branch_ids = data.get('branch_ids', [])

        if not branch_ids:
            branch_ids = self.env['res.branch'].search([]).ids

        sheet = workbook.add_worksheet("Unbilled Revenue")

        # Define formats
        bold = workbook.add_format({'bold': True})
        left = workbook.add_format({'align': 'left'})
        right_amt = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})

        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#002060',
            'font_color': 'white',
            'border': 1
        })

        header_red = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#FF0000',
            'font_color': 'white',
            'border': 1
        })

        # Report Title
        sheet.merge_range("A1:I1", "UNBILLED REVENUE REPORT", bold)

        # Report Parameters
        sheet.write("A3", "Date From", bold)
        sheet.write("B3", str(date_from))
        sheet.write("A4", "Date To", bold)
        sheet.write("B4", str(date_to))

        branches = self.env['res.branch'].browse(branch_ids)
        sheet.write("A5", "Branches", bold)
        sheet.write("B5", ", ".join(branches.mapped('name')) or 'All')

        # Column Headers
        headers = [
            'Branch Code', 'Customer Code', 'Customer Name',
            'Sale Order', 'Task No', 'Task Name',
            'Supervisor', 'Task Location', 'Unbilled Value'
        ]

        row = 7
        for col, title in enumerate(headers):
            if col == 8:  # Unbilled Value column in red
                sheet.write(row, col, title, header_red)
            else:
                sheet.write(row, col, title, header_format)
        row += 1

        # Search for tasks that have trips within the date range
        tasks = self.env['project.task'].search([
            ('sale_order_id.branch_id', 'in', branch_ids),
            ('trip_sheet_ids', '!=', False),
        ])

        total_unbilled = 0
        records_found = 0

        for task in tasks:
            # Calculate unbilled value - CORRECTED: Remove branch_ids parameter
            unbilled_value = self._get_unbilled_value(task, date_from, date_to)

            # Skip if no unbilled value
            if unbilled_value <= 0:
                continue

            sale = task.sale_order_id
            customer = sale.partner_id

            # Write data row
            sheet.write(row, 0, sale.branch_id.code or '', left)
            sheet.write(row, 1, customer.ref or '', left)
            sheet.write(row, 2, customer.name or '', left)
            sheet.write(row, 3, sale.name, left)
            sheet.write(row, 4, task.seq_code or '', left)
            sheet.write(row, 5, task.name or '', left)
            sheet.write(row, 6, task.emp_id.name or '', left)
            sheet.write(row, 7, task.partner_location_id.name or '', left)
            sheet.write(row, 8, unbilled_value, right_amt)

            total_unbilled += unbilled_value
            records_found += 1
            row += 1

        # Total Row
        sheet.write(row + 1, 7, "TOTAL", header_format)
        sheet.write(row + 1, 8, total_unbilled, right_amt)

        # Set column widths for better readability
        sheet.set_column('A:A', 12)  # Branch Code
        sheet.set_column('B:B', 15)  # Customer Code
        sheet.set_column('C:C', 25)  # Customer Name
        sheet.set_column('D:D', 15)  # Sale Order
        sheet.set_column('E:E', 12)  # Task No
        sheet.set_column('F:F', 25)  # Task Name
        sheet.set_column('G:G', 20)  # Supervisor
        sheet.set_column('H:H', 25)  # Task Location
        sheet.set_column('I:I', 15)  # Unbilled Value

        return workbook