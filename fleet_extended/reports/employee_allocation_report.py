from odoo import models, fields
from odoo.exceptions import UserError
import base64
import io
import json
from datetime import date, datetime

class EmployeeAllocationXlsx(models.AbstractModel):
    _name = 'report.fleet_extended.employee_allocation_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Employee Allocation Excel Report'

    def generate_xlsx_report(self, workbook, data, allocations):
        report_data = self.env['employee.allocation.report'].get_report_data(data)
        
        sheet = workbook.add_worksheet('Employee Allocations')
        bold = workbook.add_format({'bold': True})
        title_format = workbook.add_format({
            'bold': True, 
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#5B9BD5',
            'color': '#FFFFFF',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        report_date = fields.Date.from_string(data['report_date']).strftime('%d/%m/%Y')
        
        # Write main title and date
        sheet.merge_range('A1:L1', 'VEHICLE WISE EMPLOYEE ALLOCATION LIST', title_format)
        sheet.merge_range('A2:L2', f"Report Date: {report_date}", title_format)
        sheet.write('A3', '')  # Empty row for spacing
        
        headers = [
            'Vehicle', 'License Plate', 'Employee', 'Customer', 
            'Sale Order', 'Task', 'Location', 'Start Date', 
            'End Date', 'Demobilize Date', 'Pickup Time', 'Drop Time'
        ]

        # Write headers starting from row 4 (after title and date)
        for col, header in enumerate(headers):
            sheet.write(3, col, header, header_format)
            
        row = 4  # Start data from row 5 (0-based index 4)
        
        # Group data by vehicle for better organization
        vehicle_groups = {}
        for alloc in report_data:
            vehicle = alloc['vehicle']
            if vehicle not in vehicle_groups:
                vehicle_groups[vehicle] = []
            vehicle_groups[vehicle].append(alloc)
        
        # Write grouped data
        for vehicle, allocations in vehicle_groups.items():
            # Add vehicle header
            vehicle_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D6E1F0',
                'border': 1
            })
            sheet.merge_range(row, 0, row, len(headers)-1, f"Vehicle: {vehicle}", vehicle_format)
            row += 1
            
            # Write allocations for this vehicle
            for alloc in allocations:
                # Format dates to dd/mm/yyyy before writing
                start_date = fields.Date.from_string(alloc['start_date']).strftime('%d/%m/%Y') if alloc['start_date'] else ''
                end_date = fields.Date.from_string(alloc['end_date']).strftime('%d/%m/%Y') if alloc['end_date'] and alloc['end_date'] != 'Ongoing' else alloc['end_date']
                demobilize_date = fields.Date.from_string(alloc['demobilize_date']).strftime('%d/%m/%Y') if alloc['demobilize_date'] else ''
                
                sheet.write(row, 0, alloc['vehicle'])
                sheet.write(row, 1, alloc['license_plate'])
                sheet.write(row, 2, alloc['employee'])
                sheet.write(row, 3, alloc['customer'])
                sheet.write(row, 4, alloc['sale_order'])
                sheet.write(row, 5, alloc['task'])
                sheet.write(row, 6, alloc['location'])
                sheet.write(row, 7, start_date)
                sheet.write(row, 8, end_date)
                sheet.write(row, 9, demobilize_date)
                sheet.write(row, 10, alloc['pickup_time'])
                sheet.write(row, 11, alloc['drop_time'])
                row += 1
            
            # Add empty row between vehicle groups
            row += 1
        
        # Auto-fit columns
        for col in range(len(headers)):
            sheet.set_column(col, col, max(15, len(headers[col]) + 2))
        
        # for col, header in enumerate(headers):
        #     sheet.write(0, col, header, bold)
            
        # row = 1
        # for alloc in report_data:
        #     sheet.write(row, 0, alloc['vehicle'])
        #     sheet.write(row, 1, alloc['license_plate'])
        #     sheet.write(row, 2, alloc['employee'])
        #     sheet.write(row, 3, alloc['customer'])
        #     sheet.write(row, 4, alloc['sale_order'])
        #     sheet.write(row, 5, alloc['task'])
        #     sheet.write(row, 6, alloc['location'])
        #     sheet.write(row, 7, alloc['start_date'], date_format)
        #     sheet.write(row, 8, str(alloc['end_date']))
        #     sheet.write(row, 9, alloc['demobilize_date'], date_format)
        #     sheet.write(row, 10, alloc['pickup_time'])
        #     sheet.write(row, 11, alloc['drop_time'])
        #     row += 1
            
        # # Auto-fit columns
        # for col in range(len(headers)):
        #     sheet.set_column(col, col, max(15, len(headers[col]) + 2))