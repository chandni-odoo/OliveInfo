import io
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
from datetime import datetime
from pytz import timezone, UTC


class TripReportXlsx(models.AbstractModel):
    _name = 'report.skip_compactor_report.trip_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Trip Sheet Excel Report'


    def generate_xlsx_report(self, workbook, data, schedules):
        sheet = workbook.add_worksheet('Operation Schedule Report')
        
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
            'align': 'center'
        })
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        time_format_24h = workbook.add_format({'num_format': 'hh:mm:ss'})
        border_format = workbook.add_format({'border': 1})
        
        # Get vehicle and shift details
        vehicle = self.env['fleet.vehicle'].browse(data['vehicle_id'])
        shift = self.env['fleet.shift.type'].browse(data['shift_id'])
        vehicle_type = vehicle.vehicle_type_id if vehicle.vehicle_type_id else None
        
        # Parse the scheduled_date from string to date object
        try:
            scheduled_date = fields.Date.from_string(data['scheduled_date'])
        except:
            scheduled_date = fields.Date.today()
        
        # Header section
        sheet.merge_range('A1:C1', 'Date :', bold)
        sheet.write('D1', scheduled_date, date_format)
        
        sheet.write('L1', 'Vehicle No. :', bold)
        sheet.write('M1', vehicle.name or '', border_format)
        
        sheet.write('A2', 'Start Time:', bold)
        sheet.write('L2', 'Vehicle Type:', bold)
        sheet.write('M2', vehicle_type.name if vehicle_type else '', border_format)
        
        sheet.write('A3', 'End Time:', bold)
        sheet.write('L3', 'Shift :', bold)
        sheet.write('M3', shift.name or '', border_format)
        
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
        
        # Driver Details section
        sheet.merge_range('A5:C5', 'Driver Details', header_format)
        sheet.write('A6', 'Emp ID', sub_header_format)
        sheet.write('B6', 'Name', sub_header_format)
        sheet.write('C6', 'Sign.', sub_header_format)
        
        driver_row = 7
        for driver in drivers:
            emp = driver.employee_id
            emp_id = ''
            if emp:
                if hasattr(emp, 'emp_no') and emp.emp_no:
                    emp_id = emp.emp_no
                else:
                    emp_id = str(emp.id)
            
            sheet.write(driver_row, 0, emp_id, border_format)
            sheet.write(driver_row, 1, emp.name if emp else '', border_format)
            sheet.write(driver_row, 2, '', border_format)  # Signature column
            driver_row += 1
        
        # Helper Details section
        sheet.merge_range('J5:L5', 'Helper Details', header_format)
        sheet.write('J6', 'Emp ID', sub_header_format)
        sheet.write('K6', 'Name', sub_header_format)
        sheet.write('L6', 'Sign.', sub_header_format)
        
        helper_row = 7
        for helper in helpers:
            emp = helper.employee_id
            emp_id = ''
            if emp:
                if hasattr(emp, 'emp_no') and emp.emp_no:
                    emp_id = emp.emp_no
                else:
                    emp_id = str(emp.id)
            
            sheet.write(helper_row, 9, emp_id, border_format)
            sheet.write(helper_row, 10, emp.name if emp else '', border_format)
            sheet.write(helper_row, 11, '', border_format)  # Signature column
            helper_row += 1
        
        # Calculate the next available row after employee details
        max_employee_row = max(driver_row, helper_row)
        
        # Skip number section - place it right after employee details
        skip_row = max_employee_row + 1
        sheet.write(skip_row, 0, 'Skip No. :', bold)
        
        # Main data table headers - place it right after skip number section
        start_row = skip_row + 2
        
        # Main data table headers
        main_headers = [
            'Trip Seq', 'Client\'s Name', 'Location', 'Task No', 'Waste / Type of waste', 'Frequency'
        ]
        
        delivery_headers = ['Skip No.', 'Size']
        collection_headers = ['Skip No.', 'Size'] 
        transport_headers = ['Transportation', 'Time', 'Time', 'K.M.', 'K.M.', 'Scheduled Time']  
        transport_sub_headers = ['Tripsheet', '(Start)', '(Finish)', '(Start)', '(Finish)', ''] 
        
        # Write main headers
        for col, header in enumerate(main_headers):
            sheet.write(start_row, col, header, header_format)
        
        # Delivery section
        sheet.merge_range(start_row, 6, start_row, 7, 'Delivery', header_format)
        for col, header in enumerate(delivery_headers):
            sheet.write(start_row + 1, 6 + col, header, sub_header_format)
        
        # Collection section  
        sheet.merge_range(start_row, 8, start_row, 9, 'Collection', header_format)
        for col, header in enumerate(collection_headers):
            sheet.write(start_row + 1, 8 + col, header, sub_header_format)
        
        # Transportation section
        for col, header in enumerate(transport_headers):
            sheet.write(start_row, 10 + col, header, header_format)
        for col, header in enumerate(transport_sub_headers):
            sheet.write(start_row + 1, 10 + col, header, sub_header_format)
        
        # Get trip data based on schedule - using same date conversion as in wizard
        date_start = datetime.combine(scheduled_date, datetime.min.time())
        date_end = datetime.combine(scheduled_date, datetime.max.time())
        
        trip_domain = [
            ('schedule_date', '>=', date_start),
            ('schedule_date', '<=', date_end),
            ('vehicle_no_id', '=', data['vehicle_id']),
            ('shift_id', '=', data['shift_id']),
        ]
        
        trips = self.env['custom.trip.sheet'].search(trip_domain, order='sequence asc')
        
        # Write trip data - start right after the sub-headers
        data_row = start_row + 2
        for trip in trips:
            sheet.write(data_row, 0, trip.sequence or '', border_format)
            sheet.write(data_row, 1, trip.customer_id.name or '', border_format)
            sheet.write(data_row, 2, trip.site.name or '', border_format)
            sheet.write(data_row, 3, trip.task_seq_code or '', border_format)
            sheet.write(data_row, 4, trip.waste_type_id.name or '', border_format)
            
            # Get frequency value from trip (which is related to task)
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
            
            sheet.write(data_row, 6, '', border_format)
            sheet.write(data_row, 7, size, border_format)

            # Collection
            sheet.write(data_row, 8, '', border_format)
            sheet.write(data_row, 9, size, border_format)
                                    
            # Transportation details
            sheet.write(data_row, 10, '', border_format)  # Transportation Tripsheet (manual)
            sheet.write(data_row, 11, '', border_format)  # Start Time (manual)
            sheet.write(data_row, 12, '', border_format)  # End Time (manual)
            sheet.write(data_row, 13, '', border_format)  # Start KM (manual)
            sheet.write(data_row, 14, '', border_format)  # End KM (manual)
               
            
            if trip.schedule_date:
                user_tz_name = self.env.context.get('tz') or 'UTC'
                user_tz = timezone(user_tz_name)
                
                # Convert from UTC to user's timezone
                local_dt = trip.schedule_date.replace(tzinfo=UTC).astimezone(user_tz)
                
                # Format time as HH:MM:SS
                scheduled_time = local_dt.strftime('%H:%M:%S')
                sheet.write(data_row, 15, scheduled_time, border_format)
            else:
                sheet.write(data_row, 15, '', border_format)

            data_row += 1
            
        # Set column widths
        sheet.set_column(0, 0, 12)   # Trip Seq
        sheet.set_column(1, 1, 20)   # Client Name
        sheet.set_column(2, 2, 25)   # Location
        sheet.set_column(3, 3, 15)   # Task No
        sheet.set_column(4, 4, 20)   # Waste Type
        sheet.set_column(5, 5, 12)   # Frequency
        sheet.set_column(6, 7, 10)   # Delivery columns
        sheet.set_column(8, 9, 10)   # Collection columns
        sheet.set_column(10, 15, 12) # Transportation columns 

    # updated

    