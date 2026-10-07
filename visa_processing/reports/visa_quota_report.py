from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError

class VisaQuotaReportXlsx(models.AbstractModel):
    _name = 'report.visa_processing.visa_quota_availability_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Visa Quota Availability Excel Report'

    def generate_xlsx_report(self, workbook, data, partners):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        visa_type_ids = data.get('visa_type_ids', [])
        nationality_ids = data.get('nationality_ids', [])
        domain = data.get('domain', [])

        quotas = self.env['visa.quota'].search(domain)
        
        report_name = 'Visa Quota Availability'
        sheet = workbook.add_worksheet(report_name)
        
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14,
            'bg_color': '#4F81BD',
            'color': 'white',
            'border': 1
        })
        
        sub_header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'bg_color': '#D9D9D9',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
            'border': 1
        })
        
        number_format = workbook.add_format({
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 10,
            'border': 1
        })
        
        date_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10,
            'border': 1,
            'num_format': 'dd/mm/yyyy'
        })
        
        sheet.merge_range('A1:L1', 'Visa Quota Availability Report', header_format)
        sheet.merge_range('A2:L2', f'Report Generated on: {datetime.now().strftime("%d/%m/%Y")}', sub_header_format)
        
        if date_from or date_to:
            period_text = 'Period: '
            period_text += date_from if date_from else "N/A"
            period_text += ' to '
            period_text += date_to if date_to else "N/A"
        else:
            period_text = 'Period: All Dates'
            
        sheet.merge_range('A3:L3', period_text, sub_header_format)
        
        headers = [
            'Batch Number', 'VP Number', 'Visa Type', 'Validity From', 'Validity To',
            'Associated To', 'Nationality', 'Profession', 'Gender', 'Approved Count',
            'Used Count', 'Remaining Count'
        ]
        
        for col, header in enumerate(headers):
            sheet.write(4, col, header, sub_header_format)
        
        sheet.set_column('A:A', 15)  # Batch Number
        sheet.set_column('B:B', 12)  # VP Number
        sheet.set_column('C:C', 15)  # Visa Type
        sheet.set_column('D:E', 12)  # Validity dates
        sheet.set_column('F:F', 20)  # Associated To
        sheet.set_column('G:G', 15)  # Nationality
        sheet.set_column('H:H', 20)  # Profession
        sheet.set_column('I:I', 10)  # Gender
        sheet.set_column('J:L', 12)  # Counts
        
        row = 5
        for quota in quotas:
            quota_lines = quota.quota_line_ids
            if nationality_ids:
                quota_lines = quota_lines.filtered(lambda l: l.nationality_id.id in nationality_ids)
                
            quota_lines = quota_lines.filtered(lambda l: l.remaining_count > 0)
                
            if not quota_lines:
                continue
                
            for line in quota_lines:
                sheet.write(row, 0, quota.batch_number, cell_format)
                sheet.write(row, 1, quota.vp_number, cell_format)
                sheet.write(row, 2, quota.visa_type_id.name, cell_format)
                sheet.write(row, 3, quota.validity_from_date, date_format)
                sheet.write(row, 4, quota.validity_to_date, date_format)
                sheet.write(row, 5, quota.associated_to.name or '', cell_format)
                sheet.write(row, 6, line.nationality_id.name, cell_format)
                sheet.write(row, 7, line.profession or '', cell_format)
                sheet.write(row, 8, dict(line._fields['gender'].selection).get(line.gender) if line.gender else '', cell_format)
                sheet.write(row, 9, line.approved_count, number_format)
                sheet.write(row, 10, line.used_count, number_format)
                sheet.write(row, 11, line.remaining_count, number_format)
                row += 1