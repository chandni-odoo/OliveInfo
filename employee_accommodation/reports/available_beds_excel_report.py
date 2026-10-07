from odoo import models
import io
import xlsxwriter
import base64
from datetime import date

class AvailableBedsExcelReport(models.AbstractModel):
    _name = 'report.employee_accommodation.available_beds_excel_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Available Beds Excel Report'

    def generate_xlsx_report(self, workbook, data, wizard):
        
        domain = [('status', '=', 'active')]  
        if data.get('camp_ids'):
            domain.append(('id', 'in', data['camp_ids'])) 
        all_camps = self.env['accommodation.camp'].search(domain)
        
        worksheet = workbook.add_worksheet('Available Beds')
        
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#3498db',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })
        total_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'bg_color': '#ecf0f1',
            'border': 1
        })
        
        row = 0
        for camp in all_camps:
            worksheet.merge_range(row, 0, row, 3, f"Available Beds for Camp: {camp.name}", header_format)
            row += 1
            
            worksheet.write(row, 0, "Bed Number", header_format)
            worksheet.write(row, 1, "Room", header_format)
            worksheet.write(row, 2, "Floor", header_format)
            worksheet.write(row, 3, "Status", header_format)
            row += 1
            
            available_beds = self.env['accommodation.bed'].search([
                ('status', '=', 'available'),
                ('camp_id', '=', camp.id),
            ], order='floor_id, room_id, name')
            
            total_beds = 0
            for bed in available_beds:
                worksheet.write(row, 0, bed.name, cell_format)
                worksheet.write(row, 1, bed.room_id.name or '', cell_format)
                worksheet.write(row, 2, bed.floor_id.name or '', cell_format)
                worksheet.write(row, 3, bed.status, cell_format)
                row += 1
                total_beds += 1
            
            worksheet.write(row, 0, "Total Beds Available", total_format)
            worksheet.merge_range(row, 1, row, 2, "", total_format)
            worksheet.write(row, 3, total_beds, total_format)
            row += 2  
        
        worksheet.set_column(0, 0, 15)
        worksheet.set_column(1, 1, 20)
        worksheet.set_column(2, 2, 15)
        worksheet.set_column(3, 3, 15)