import io
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
from datetime import datetime
from pytz import timezone, UTC



class CompactorReportXlsx(models.AbstractModel):
    _name = 'report.skip_compactor_report.compactor_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Compactor Vehicle Excel Report'

    def generate_xlsx_report(self, workbook, data, schedules):
        sheet = workbook.add_worksheet('Compactor Vehicle Time Sheet')
        
        # Define formats
        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': True, 
            'bg_color': '#2F5F8F', 
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        sub_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4A90E2',
            'font_color': 'white', 
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        info_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1F4E79',
            'font_color': 'white',
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })
        duty_info_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4A90E2',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        breakdown_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E74C3C',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
        border_format = workbook.add_format({'border': 1})
        time_format = workbook.add_format({'num_format': 'HH:MM:SS', 'border': 1})
        
        # Parse the scheduled_date from string to date object
        try:
            scheduled_date = fields.Date.from_string(data['scheduled_date'])
        except:
            scheduled_date = fields.Date.today()
        
        # Get vehicle and shift details
        vehicle = self.env['fleet.vehicle'].browse(data['vehicle_id'])
        shift = self.env['fleet.shift.type'].browse(data['shift_id'])
        vehicle_type = vehicle.vehicle_type_id if vehicle.vehicle_type_id else None
        
        # Set column widths
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 12)
        sheet.set_column('G:G', 12)
        sheet.set_column('H:H', 12)
        sheet.set_column('I:I', 12)
        sheet.set_column('J:J', 15)
        sheet.set_column('K:K', 15)
        sheet.set_column('L:L', 15)
        sheet.set_column('M:M', 15)
        sheet.set_column('N:N', 15)
        sheet.set_column('O:O', 15)  
        
        # Title
        sheet.merge_range('A1:O1', 'COMPACTOR VEHICLE - TIME SHEET', header_format)
        
        # Vehicle Information Section
        sheet.write('A3', 'Date :', info_header_format)
        sheet.write('B3', scheduled_date, date_format)
        sheet.write('A4', 'Vehicle No :', info_header_format)
        sheet.write('B4', vehicle.name or '', border_format)
        sheet.write('A5', 'Vehicle Type:', info_header_format)
        sheet.write('B5', vehicle_type.name if vehicle_type else '', border_format)
        sheet.write('A6', 'Shift :', info_header_format)
        sheet.write('B6', shift.name or '', border_format)
        
        # Get employee data from operation.schedule model
        operation_schedule_domain = [
            ('scheduled_date', '=', scheduled_date),
            ('vehicle_id', '=', data['vehicle_id']),
            ('shift_type', '=', data['shift_id']),
        ]
        operation_schedules = self.env['operation.schedule'].search(operation_schedule_domain)
        
        # Separate drivers and helpers
        drivers = operation_schedules.filtered(lambda s: s.employee_type == 'driver')
        helpers = operation_schedules.filtered(lambda s: s.employee_type == 'helper')
        
        # Employee Details
        current_row = 7
        
        # Driver Name
        if drivers:
            driver = drivers[0]
            emp = driver.employee_id
            emp_id = self._get_employee_id(emp)
            sheet.write('A7', 'Driver Name:', info_header_format)
            sheet.write('B7', f"{emp_id} {emp.name}" if emp else '', border_format)
        else:
            sheet.write('A7', 'Driver Name:', info_header_format)
            sheet.write('B7', '', border_format)
        
        # Helper Names
        helper_row = 8
        for i, helper in enumerate(helpers[:2]):  # Max 2 helpers
            emp = helper.employee_id
            emp_id = self._get_employee_id(emp)
            sheet.write(f'A{helper_row}', f'Helper Name :', info_header_format)
            sheet.write(f'B{helper_row}', f"{emp_id} {emp.name}" if emp else '', border_format)
            helper_row += 1
        
        # Fill empty helper rows if needed
        while helper_row <= 9:
            sheet.write(f'A{helper_row}', f'Helper Name :', info_header_format)
            sheet.write(f'B{helper_row}', '', border_format)
            helper_row += 1
        
        # Duty Information Section
        sheet.merge_range('H3:O3', 'Duty Information', duty_info_format)
        sheet.write('H4', 'Duty Start Time :', duty_info_format)
        sheet.write('I4', '', border_format)
        sheet.write('J4', 'Break Time :', duty_info_format)
        sheet.write('K4', '', border_format)
        sheet.write('L4', 'Duty Finish Time :', duty_info_format)
        sheet.write('M4', '', border_format)
        sheet.write('H5', 'Start KM :', duty_info_format)
        sheet.write('I5', '', border_format)
        sheet.write('L5', 'Finish KM :', duty_info_format)
        sheet.write('M5', '', border_format)
        
        # Breakdown Details Section
        sheet.merge_range('H7:O7', 'Brakedown Details:', breakdown_header_format)
        sheet.write('H8', 'Start Time', sub_header_format)
        sheet.write('I8', 'Breakdown reason', sub_header_format)
        sheet.write('J8', 'End Time', sub_header_format)
        
        for i in range(9, 12):
            sheet.write(f'H{i}', '', border_format)
            sheet.write(f'I{i}', '', border_format)
            sheet.write(f'J{i}', '', border_format)
        
        # Main Trip Data Table
        start_row = 13
        
        # Main table headers
        headers = [
            'Trip Seq',
            'Client\'s Name', 
            'Locations',
            'Task No',
            'Title / Type of waste',
            'Frequency',
            'Eqpt Size',
            'Quantity',
            'Collection',
            'Trip Sheet No',
            'Client In',
            'Client Out',
            'Scheduled Time',
            'Remarks'
        ]
        
        # Write headers
        for col, header in enumerate(headers):
            sheet.write(start_row, col, header, sub_header_format)
        
        # Get trip data using datetime range
        date_start = datetime.combine(scheduled_date, datetime.min.time())
        date_end = datetime.combine(scheduled_date, datetime.max.time())
        
        trip_domain = [
            ('schedule_date', '>=', date_start),
            ('schedule_date', '<=', date_end),
            ('vehicle_no_id', '=', data['vehicle_id']),
            ('shift_id', '=', data['shift_id']),
        ]
        trips = self.env['custom.trip.sheet'].search(trip_domain, order='sequence asc')
        
        # Write trip data
        data_row = start_row + 1
        for trip in trips:
            sheet.write(data_row, 0, trip.sequence or '', border_format)
            sheet.write(data_row, 1, trip.customer_id.name or '', border_format)
            sheet.write(data_row, 2, trip.site.name or '', border_format)
            sheet.write(data_row, 3, trip.task_seq_code or '', border_format)
            sheet.write(data_row, 4, trip.waste_type_id.name or '', border_format)
            
            frequency_mapping = {
                'daily': 'Daily',
                'weekly': 'Weekly',
                'monthly': 'Monthly',
                'on_call': 'Call Off'
            }
            frequency = frequency_mapping.get(trip.frequency_value, 'Daily')
            sheet.write(data_row, 5, frequency, border_format)
            
            main_name = trip.equipment_type_id.name if trip.equipment_type_id else ''
            alternate_names = ''
            if trip.task_id and trip.task_id.alternate_skip_types_ids:
                alt_names = trip.task_id.alternate_skip_types_ids.mapped('name')
                alternate_names = ' (' + ', '.join(alt_names) + ')'
            size = main_name + alternate_names if main_name else ''
            sheet.write(data_row, 6, size, border_format)
            
            sheet.write(data_row, 7, trip.quantity if hasattr(trip, 'quantity') else '', border_format)
            sheet.write(data_row, 8, trip.collection_status if hasattr(trip, 'collection_status') else '', border_format)
            sheet.write(data_row, 9, trip.name if hasattr(trip, 'name') else '', border_format)
            sheet.write(data_row, 10, trip.client_in_time if hasattr(trip, 'client_in_time') else '', border_format)
            sheet.write(data_row, 11, trip.client_out_time if hasattr(trip, 'client_out_time') else '', border_format)
            
            # Scheduled Time with timezone conversion
            if trip.schedule_date:
                # Get user timezone from context, default to UTC if not set
                user_tz_name = self.env.context.get('tz') or 'UTC'
                user_tz = timezone(user_tz_name)
                # Convert from UTC to user's timezone
                local_dt = trip.schedule_date.replace(tzinfo=UTC).astimezone(user_tz)
                
                # Format time as HH:MM:SS
                scheduled_time = local_dt.strftime('%H:%M:%S')
                sheet.write(data_row, 12, scheduled_time, time_format)
            else:
                sheet.write(data_row, 12, '', border_format)
            
            sheet.write(data_row, 13, trip.remarks if hasattr(trip, 'remarks') else '', border_format)
            
            data_row += 1
        
        # Add extra empty rows for manual entries
        for i in range(5):
            for col in range(14):  
                sheet.write(data_row, col, '', border_format)
            data_row += 1

    def _get_employee_id(self, emp):
        if not emp:
            return ''
        if hasattr(emp, 'emp_no') and emp.emp_no:
            return emp.emp_no
        return str(emp.id)
    
    # updated

