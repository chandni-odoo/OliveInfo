import io
from datetime import datetime
from odoo import models, fields, api

class ManpowerRequisitionXLSXReport(models.AbstractModel):
    _name = 'report.visa_processing.manpower_requisition_xlsx_report'
    _description = 'Manpower Requisition XLSX Report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizards):
        wizard = wizards[0]
        
        # Create worksheet
        sheet = workbook.add_worksheet('Manpower Requisition Report')
        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})
        number_format = workbook.add_format({'num_format': '#,##0', 'border': 1})
        regular_format = workbook.add_format({'border': 1})
        text_format = workbook.add_format({'border': 1, 'text_wrap': True})
        center_format = workbook.add_format({'align': 'center', 'border': 1})

        # Report title
        sheet.merge_range(0, 0, 0, 9, 'MANPOWER REQUISITION REPORT', header_format)
        sheet.set_row(0, 25)
        
        # Report details
        row = 2
        sheet.write(row, 0, "Generated On:", bold)
        sheet.write(row, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        row += 1
        sheet.write(row, 0, "Date Range:", bold)
        sheet.write(row, 1, f"{wizard.date_from} to {wizard.date_to}")
        
        row += 1
        sheet.write(row, 0, "Branch Filter:", bold)
        sheet.write(row, 1, ', '.join(wizard.branch_ids.mapped('name')) if wizard.branch_ids else "All Branches")

        # Prepare domain for data
        domain = [
            ('request_date', '>=', wizard.date_from),
            ('request_date', '<=', wizard.date_to)
        ]
        
        if wizard.branch_ids:
            domain.append(('branch_id', 'in', wizard.branch_ids.ids))

        requisitions = self.env['manpower.requisition'].search(domain, order='request_date asc')

        # Headers
        headers = [
            'Req. Number',
            'Position/Category',
            'Requisition Date',
            'Required by date',
            'Quantity',
            'Hired Count',
            'Remaining Count',
            'Requisition Closed Date',
            'Completion Duration (Days)',
            'HR Remarks'
        ]
        
        # Write headers
        sheet.set_row(8, 20)
        for col, header in enumerate(headers):
            sheet.write(8, col, header, header_format)

        # Write data
        row = 9
        for req in requisitions:
            for line in req.requisition_line_ids:
                # Calculate completion duration
                duration = 0
                if line.requisition_closed_date and line.required_date:
                    delta = line.requisition_closed_date - line.required_date
                    duration = delta.days
                
                sheet.write(row, 0, req.requisition_number or '', regular_format)
                sheet.write(row, 1, line.job_id.name or '', regular_format)
                
                # Handle request_date
                if req.request_date:
                    sheet.write_datetime(row, 2, req.request_date, date_format)
                else:
                    sheet.write(row, 2, '', center_format)
                
                # Handle required_date
                if line.required_date:
                    sheet.write_datetime(row, 3, line.required_date, date_format)
                else:
                    sheet.write(row, 3, '', center_format)
                
                sheet.write_number(row, 4, line.quantity or 0, number_format)
                sheet.write_number(row, 5, line.hired_count or 0, number_format)
                sheet.write_number(row, 6, line.remaining_count or 0, number_format)
                
                # Handle requisition_closed_date
                if line.requisition_closed_date:
                    sheet.write_datetime(row, 7, line.requisition_closed_date, date_format)
                else:
                    sheet.write(row, 7, '', center_format)
                
                sheet.write_number(row, 8, duration, number_format)
                sheet.write(row, 9, line.hr_remarks or '', text_format)
                row += 1

        # Set column widths
        sheet.set_column(0, 0, 15)  # Req. Number
        sheet.set_column(1, 1, 25)  # Position/Category
        sheet.set_column(2, 2, 15)  # Requisition Date
        sheet.set_column(3, 3, 15)  # Required by date
        sheet.set_column(4, 4, 10)  # Quantity
        sheet.set_column(5, 5, 10)  # Hired Count
        sheet.set_column(6, 6, 12)  # Remaining Count
        sheet.set_column(7, 7, 20)  # Requisition Closed Date
        sheet.set_column(8, 8, 20)  # Completion Duration
        sheet.set_column(9, 9, 30)  # HR Remarks
        
        # Freeze headers
        sheet.freeze_panes(9, 0)
        
        # Add auto-filter
        sheet.autofilter(8, 0, row-1, 9)