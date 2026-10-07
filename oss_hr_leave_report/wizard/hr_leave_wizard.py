# -*- coding: utf-8 -*-
from odoo import models, fields, api
import base64
import tempfile
import io
from datetime import datetime
from odoo.tools.misc import xlsxwriter

from odoo.exceptions import ValidationError


class HrLeaveWizard(models.TransientModel):
    _name = 'hr.leave.export.wizard'
    _description = 'HR Leave Export Wizard'

    employee_ids = fields.Many2many('hr.employee', string='Employees')
    branch_ids = fields.Many2many('res.branch', string='Branches', required=True)
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    file_data = fields.Binary('File', readonly=True)
    file_name = fields.Char('File Name', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(dates.date_from > dates.date_to for dates in self):
            raise ValidationError(_("Leave Export Wizard 'Date From' must be earlier 'Date To'."))

    def get_leave_data(self):
        domain = [('date_from', '<=', self.date_to),
            ('date_to', '>=', self.date_from) ]
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))
        # if self.branch_ids:
        #     domain.append(('employee_id.branch_id', 'in', self.branch_ids.ids))
        total_leave_days = 0
        leave_records = self.env['hr.leave'].search(domain)
        leave_data = []
        for leave in leave_records:
            # Initialize duty_resumption_date as empty by default
            duty_resumption_date = ''

            # Check if duty_resumption_leave is True, then search for the date in the duty.resumption model
            if leave.duty_resumption_leave:
                resumption_record = self.env['duty.resumption'].search([('leave_id', '=', leave.id)], limit=1)
                if resumption_record:
                    duty_resumption_date = resumption_record.reporting_date if resumption_record.reporting_date else ''

            leave_data.append({
                'employee_id': leave.employee_id.emp_no if leave.employee_id.emp_no else '',
                'employee_name': leave.employee_id.name,
                'branch': leave.employee_id.branch_id.name if leave.employee_id.branch_id else '',
                'leave_type': leave.holiday_status_id.name,
                'leave_start_date': leave.date_from,
                'leave_end_date': leave.date_to,
                'total_days': leave.number_of_days,
                'additional_unpaid_days': str(leave.unpaid_days),
                'additional_paid_days': str(leave.paid_days),
                'leave_settlement': 'Yes' if leave.leave_sattlement_done else 'No',
                'emergency_contact': leave.emergency_contact_number or 'N/A',
                'air_ticket': leave.air_ticket or 'N/A',
                'duty_resumption_date': duty_resumption_date,
                'reason': leave.name or 'N/A',
            })
        return leave_data

    def export_leave_data_to_excel(self):
        leave_data = self.get_leave_data()

        # Create an in-memory binary stream for the Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Leave Report')

        # Get company logo
        report_name = workbook.add_format({
            'font_size': 30,
            'align': 'left',
            'bold': True,
            'font_color': 'black',
        })
        format_logo = workbook.add_format({
            'font_size': 10,
            'align': 'center',
            'bold': True
        })
        company = self.env.user.company_id
        logo = base64.b64decode(company.logo) if company.logo else None
        worksheet.merge_range('D1:M1', 'Leave Report', report_name)

        if logo:
            temp_logo_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_logo_file.write(logo)
            temp_logo_file.close()
            logo_path = temp_logo_file.name
        else:
            logo_path = None

        # Insert company logo if available
        if logo_path:
            worksheet.insert_image('A1', logo_path, {'x_scale': 0.75, 'y_scale': 0.3})  # Adjust the scale as needed
            worksheet.merge_range('A1:C1', '', format_logo)  # Merge cells for the logo
        # Write the company name
        # worksheet.merge_range('A4:N4', company.name, format_logo)

        # formatting for header
        header_format = workbook.add_format({
            'font_size': 12,
            'align': 'center',
            'font_color': 'white',
            'bg_color': '#7030a0',
            'bold': True
        })
        lines_format = workbook.add_format({
            'font_size': 12,
            'align': 'center',
            'font_color': 'black',
        })
        start_end_date_format = workbook.add_format({
            'font_size': 14,
            'align': 'center',
            'font_color': 'white',
            'bg_color': '#black',
            'bold': True
        })

        # Merge and write date range
        date_range = f"Date From: {self.date_from.strftime('%d-%m-%Y')} - Date To: {self.date_to.strftime('%d-%m-%Y')}"
        worksheet.merge_range('A3:C3', date_range, start_end_date_format)

        # Write header row
        headers = [
            ('Employee ID', 12), ('Employee Name', 20), ('Branch', 15), ('Leave Type', 12),
            ('Leave Start Date', 18), ('Leave End Date', 18), ('Total Days', 10),
            ('Additional Unpaid Days', 25),('Additional Paid Days', 25), ('Leave Settlement', 15), ('Emergency Contact', 20),
            ('Air Ticket', 12), ('Duty Resumption Date', 20), ('Reason', 0)
        ]

        for col_num, (header, width) in enumerate(headers):
            worksheet.write(3, col_num, header, header_format)
            worksheet.set_column(col_num, col_num, max(width, len(header)))

        # Write data rows
        # Define a format for the data rows
        first_column_format = workbook.add_format({
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1  # Adds border around cells
        })
        data_format = workbook.add_format({
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1  # Adds border around cells
        })

        # Define the format for wrapping text in the "Reason" column
        wrap_format = workbook.add_format({
            'text_wrap': True,  # Enable text wrapping
            'valign': 'top',  # Align text to the top of the cell
            'font_size': 10 , # Adjust font size as needed
            'border': 1  # Adds border around cells
        })

        # Dictionary to track max width of each column
        column_widths = {i: 0 for i in range(14)}  # Assuming 13 columns

        # Write data rows
        for row_num, leave in enumerate(leave_data, start=4):
            # Employee ID
            worksheet.write(row_num, 0, leave['employee_id'], first_column_format)
            column_widths[0] = max(column_widths[0], len(leave['employee_id']))

            # Employee Name
            worksheet.write(row_num, 1, leave['employee_name'], first_column_format)
            column_widths[1] = max(column_widths[1], len(leave['employee_name']))

            # Branch
            worksheet.write(row_num, 2, leave['branch'], first_column_format)
            column_widths[2] = max(column_widths[2], len(leave['branch']))

            # Leave Type
            worksheet.write(row_num, 3, leave['leave_type'], first_column_format)
            column_widths[3] = max(column_widths[3], len(leave['leave_type']))

            # Leave Start Date
            start_date = leave['leave_start_date'].strftime('%d/%m/%Y') if leave['leave_start_date'] else ''
            worksheet.write(row_num, 4, start_date, data_format)
            column_widths[4] = max(column_widths[4], len(start_date))

            # Leave End Date
            end_date = leave['leave_end_date'].strftime('%d/%m/%Y') if leave['leave_end_date'] else ''
            worksheet.write(row_num, 5, end_date, data_format)
            column_widths[5] = max(column_widths[5], len(end_date))

            # Total Days
            worksheet.write(row_num, 6, leave['total_days'], data_format)
            column_widths[6] = max(column_widths[6], len(str(leave['total_days'])))

            # Additional Unpaid Days
            worksheet.write(row_num, 7, leave['additional_unpaid_days'], data_format)
            column_widths[7] = max(column_widths[7], len(leave['additional_unpaid_days']))

            # Additional Paid Days
            worksheet.write(row_num, 8, leave['additional_paid_days'], data_format)
            column_widths[8] = max(column_widths[8], len(leave['additional_paid_days']))

            # Leave Settlement
            worksheet.write(row_num, 9, leave['leave_settlement'], data_format)
            column_widths[9] = max(column_widths[9], len(leave['leave_settlement']))

            # Emergency Contact
            worksheet.write(row_num, 10, leave['emergency_contact'], data_format)
            column_widths[10] = max(column_widths[10], len(leave['emergency_contact']))

            # Air Ticket
            worksheet.write(row_num, 11, leave['air_ticket'], data_format)
            column_widths[11] = max(column_widths[11], len(leave['air_ticket']))

            # Duty Resumption Date
            duty_resumption = leave['duty_resumption_date'].strftime('%d/%m/%Y') if leave[
                'duty_resumption_date'] else ''
            worksheet.write(row_num, 12, duty_resumption, data_format)
            column_widths[12] = max(column_widths[12], len(duty_resumption))

            # Reason
            worksheet.write(row_num, 13, leave['reason'], wrap_format)
            column_widths[13] = max(column_widths[13], len(leave['reason']))

        # Auto-adjust column widths after writing all data
        for col_num, width in column_widths.items():
            worksheet.set_column(col_num, col_num, width + 2)  # Add some padding for better spacing

        workbook.close()
        output.seek(0)

        # Save the Excel file as a binary field
        self.file_data = base64.b64encode(output.read())
        self.file_name = 'HR_Leave_Report.xlsx'
        output.seek(0)

        # Return an action to download the file
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=hr.leave.export.wizard&id={self.id}&field=file_data&download=true&filename={self.file_name}',
            'target': 'self',
        }
