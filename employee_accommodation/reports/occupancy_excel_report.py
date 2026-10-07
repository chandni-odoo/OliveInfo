import io
import xlsxwriter
from odoo import models, fields
from odoo.tools import date_utils

class OccupancyReportXLSX(models.AbstractModel):
    _name = 'report.employee_accommodation.occupancy_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Occupancy Report XLSX'

    def generate_xlsx_report(self, workbook, data, wizard):
        to_date = data.get('to_date')
        camp_ids = data.get('camp_ids', [])
        floor_ids = data.get('floor_ids', [])
        room_ids = data.get('room_ids', [])
        
        if isinstance(to_date, str):
            to_date = fields.Date.from_string(to_date)
        
        formatted_date = to_date.strftime('%d-%m-%Y') if to_date else ''
        domain = [
            ('check_in_date', '<=', to_date),
            ('status', '=', 'checked_in'),
            ('camp_id.status', '=', 'active')
        ]
        if camp_ids:
            domain.append(('camp_id', 'in', camp_ids))
        if floor_ids:
            domain.append(('floor_id', 'in', floor_ids))
        if room_ids:
            domain.append(('room_id', 'in', room_ids))
        
        docs = self.env['accommodation.check.in'].search(domain)
        camps_data = {}
        for doc in docs:
            camp_id = doc.camp_id.id
            if camp_id not in camps_data:
                camps_data[camp_id] = {
                    'camp_name': doc.camp_id.name,
                    'docs': [],
                    'total_occupied_beds': 0,
                }
            camps_data[camp_id]['docs'].append(doc)
            camps_data[camp_id]['total_occupied_beds'] += 1
        
        sheet = workbook.add_worksheet('Occupancy Report')
        
        bold_format = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#007BFF',
            'font_color': 'white',
            'border': 1
        })
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16,
            'font_color': '#007BFF'
        })
        date_format = workbook.add_format({'num_format': 'dd-mm-yyyy'})
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#ecf0f1',
            'border': 1
        })
        
        sheet.set_column('A:A', 15)  # Allocation ID
        sheet.set_column('B:B', 25)  # Employee
        sheet.set_column('C:C', 15)  # Nationality
        sheet.set_column('D:D', 15)  # Phone
        sheet.set_column('E:E', 15)  # Branch
        sheet.set_column('F:F', 15)  # Religion
        sheet.set_column('G:G', 20)  # Designation
        sheet.set_column('H:H', 15)  # Date of Join
        sheet.set_column('I:I', 20)  # Company
        sheet.set_column('J:J', 20)  # Vendor
        sheet.set_column('K:K', 15)  # Floor
        sheet.set_column('L:L', 15)  # Room
        sheet.set_column('M:M', 10)  # Bed
        sheet.set_column('N:N', 15)  # Check-In Date
        sheet.set_column('O:O', 30)  # Facilities
        
        sheet.merge_range('A1:O1', 'Occupancy List - As On %s' % formatted_date, title_format)
        
        headers = [
            'Allocation ID', 'Employee', 'Nationality', 'Phone Number', 'Branch', 
            'Religion', 'Designation', 'Date of Join', 'Company', 'Vendor',
            'Floor', 'Room', 'Bed', 'Check-In Date', 'Facilities Assigned'
        ]
        
        row = 2
        for camp_id, camp_data in camps_data.items():
            sheet.merge_range(row, 0, row, 14, 'Camp: %s' % camp_data['camp_name'], bold_format)
            row += 1
            
            for col, header in enumerate(headers):
                sheet.write(row, col, header, header_format)
            row += 1
            
            for doc in camp_data['docs']:
                facilities = "\n".join([facility.name for facility in doc.facilities])
                
                sheet.write(row, 0, doc.allocation_id or '')
                sheet.write(row, 1, doc.employee_id.name or '')
                sheet.write(row, 2, doc.nationality.name if doc.nationality else '')
                sheet.write(row, 3, doc.contact or '')
                sheet.write(row, 4, doc.business_unit.name if doc.business_unit else '')
                sheet.write(row, 5, doc.religion.name if doc.religion else '')
                sheet.write(row, 6, doc.designation or '')
                sheet.write(row, 7, doc.date_of_join, date_format)
                sheet.write(row, 8, doc.company.name if doc.company else '')
                sheet.write(row, 9, doc.vendor_id.name if doc.vendor_id else '')
                sheet.write(row, 10, doc.floor_id.name if doc.floor_id else '')
                sheet.write(row, 11, doc.room_id.name if doc.room_id else '')
                sheet.write(row, 12, doc.bed_id.name if doc.bed_id else '')
                sheet.write(row, 13, doc.check_in_date, date_format)
                sheet.write(row, 14, facilities)
                row += 1
            
            sheet.merge_range(row, 0, row, 13, 'Total Occupied Beds:', total_format)
            sheet.write(row, 14, camp_data['total_occupied_beds'], total_format)
            row += 2