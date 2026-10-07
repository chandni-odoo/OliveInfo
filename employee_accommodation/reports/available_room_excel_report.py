import xlsxwriter
from odoo import models

class AvailableRoomExcelReport(models.AbstractModel):
    _name = 'report.employee_accommodation.available_room_excel_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Available Room Excel Report'
    
    def generate_xlsx_report(self, workbook, data, wizard):
        camp_ids = data.get('camp_ids', [])
        
        domain = [('status', '=', 'active')]
        if camp_ids:
            domain.append(('id', 'in', camp_ids))
        all_camps = self.env['accommodation.camp'].search(domain)
        
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#3498db',
            'font_color': 'white',
            'border': 1,
            'font_size': 14,
        })
        
        camp_header_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#2c3e50',
        })
        
        data_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 12,
        })
        
        total_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'fg_color': '#ecf0f1',
            'border': 1,
            'font_size': 12,
        })
        
        for camp in all_camps:
            sheet = workbook.add_worksheet(camp.name[:31])  
            
            sheet.merge_range('A1:F1', f'Room Availability for Camp: {camp.name}', camp_header_format)
            
            sheet.set_column('A:A', 15)  # Room Number
            sheet.set_column('B:B', 15)  # Floor
            sheet.set_column('C:C', 20)  # Room Type
            sheet.set_column('D:D', 10)  # Capacity
            sheet.set_column('E:E', 15)  # Allocated Beds
            sheet.set_column('F:F', 15)  # Available Beds
            
            sheet.write_row(2, 0, [  
                'Room Number', 
                'Floor', 
                'Room Type', 
                'Capacity', 
                'Allocated Beds', 
                'Available Beds'
            ], header_format)
            
            rooms = self.env['accommodation.room'].search([
                ('camp_id', '=', camp.id)
            ], order='floor_id, name')
            
            row = 3  
            total_capacity = 0
            total_allocated = 0
            total_available = 0
            
            for room in rooms:
                sheet.write(row, 0, room.name or 'N/A', data_format)
                sheet.write(row, 1, room.floor_id.name if room.floor_id else 'N/A', data_format)
                sheet.write(row, 2, room.type or 'N/A', data_format)
                sheet.write_number(row, 3, room.capacity or 0, data_format)
                sheet.write_number(row, 4, room.allocated_bed_count or 0, data_format)
                sheet.write_number(row, 5, room.available_bed_count or 0, data_format)
                
                total_capacity += room.capacity or 0
                total_allocated += room.allocated_bed_count or 0
                total_available += room.available_bed_count or 0
                
                row += 1
            
            sheet.write(row, 0, 'Total', total_format)
            sheet.write(row, 3, total_capacity, total_format)
            sheet.write(row, 4, total_allocated, total_format)
            sheet.write(row, 5, total_available, total_format)