import base64
from io import BytesIO
from datetime import datetime
from odoo import models

class VisaRequestExcelReport(models.AbstractModel):
    _name = 'report.visa_processing.visa_request_excel_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Visa Request Excel Report'

    def generate_xlsx_report(self, workbook, data, partners):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        visa_process_type = data.get('visa_process_type')
        state = data.get('state')
        domain = data.get('domain', [])

        applications = self.env['visa.request.application'].search(domain)
        
        report_name = 'Visa Request Report'
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
        
        date_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10,
            'border': 1,
            'num_format': 'dd/mm/yyyy'
        })
        
        sheet.merge_range('A1:M1', 'Visa Request Report', header_format)
        sheet.merge_range('A2:M2', f'Report Generated on: {datetime.now().strftime("%d/%m/%Y")}', sub_header_format)
        
        row = 3  
        
        date_range = ''
        if date_from and date_to:
            date_from_str = datetime.strptime(date_from, "%Y-%m-%d").strftime("%d/%m/%Y") if isinstance(date_from, str) else date_from.strftime("%d/%m/%Y")
            date_to_str = datetime.strptime(date_to, "%Y-%m-%d").strftime("%d/%m/%Y") if isinstance(date_to, str) else date_to.strftime("%d/%m/%Y")
            date_range = f'Period: {date_from_str} to {date_to_str}'
        sheet.merge_range(f'A{row}:M{row}', date_range, sub_header_format)
        row += 1
        
        if visa_process_type:
            process_type_label = "All Process Types" if not visa_process_type else visa_process_type
            visa_model = self.env['visa.request.application']
            selection_dict = dict(visa_model._fields['visa_process_type'].selection)
            process_type_label = selection_dict.get(visa_process_type, visa_process_type)
            
            sheet.merge_range(f'A{row}:M{row}', f'Visa Process Type: {process_type_label}', sub_header_format)
            row += 1
        
        
        if state:
            state_label = "All States" if not state else state
            sheet.merge_range(f'A{row}:M{row}', f'State: {state_label}', sub_header_format)
            row += 1
        
        data_start_row = row + 1
        
        headers = [
            'Reference', 'Request Date', 'Status', 'Applicant', 'Employee Name',
            'Job Position', 'Business Unit', 'Nationality', 'Visa Process Type',
            'VP Number', 'VISA Profession', 'VISA Number'
        ]
        
        
        if visa_process_type == 'qvc':
            headers.extend([
                'QVC Country', 'QVC Center', 'VISA Application Date', 
                'QVC Payment Date', 'QVC Appointment Date', 'VISA Payment Date',
                'VISA Issue Date', 'Qatar First Entry Date', 'QID Apply Date'
            ])
        elif visa_process_type == 'non_qvc':
            headers.extend([
                'VISA Application Date', 'VISA Payment Date', 'VISA Issue Date',
                'Qatar First Entry Date', 'Medical Application Date',
                'Medical Appointment Date', 'Fingerprint Application Date',
                'Fingerprint Appointment Date', 'Employment Contract',
                'QID Payment Date', 'Days Left'
            ])
        elif visa_process_type in ['change_employer', 'secondment']:
            headers.extend([
                'NOC', 'Company Documents', 'Application Date',
                'Application No', 'Application Status', 'Employee Contract',
                'Transfer Payment Date'
            ])
        elif visa_process_type == 'work_permit':
            headers.extend([
                'Photo', 'QID', 'Sponsor ID', 'Education Certificate Arabic',
                'Application No', 'Application Date', 'PCC', 'Employee Contract',
                'Payment Date', 'Validity From', 'Expiry Date'
            ])
        
        
        for col, header in enumerate(headers):
            sheet.write(4, col, header, sub_header_format)
        
        
        sheet.set_column('A:A', 15)  # Reference
        sheet.set_column('B:B', 12)  # Request Date
        sheet.set_column('C:C', 12)  # Status
        sheet.set_column('D:D', 20)  # Applicant
        sheet.set_column('E:E', 20)  # Employee Name
        sheet.set_column('F:F', 20)  # Job Position
        sheet.set_column('G:G', 15)  # Business Unit
        sheet.set_column('H:H', 15)  # Nationality
        sheet.set_column('I:I', 15)  # Visa Process Type
        sheet.set_column('J:J', 12)  # VP Number
        sheet.set_column('K:K', 20)  # VISA Profession
        sheet.set_column('L:L', 15)  # VISA Number
        
        # Write data rows
        row = 5
        for app in applications:

            sheet.write(row, 0, app.name or '', cell_format)
            sheet.write(row, 1, app.request_date, date_format)
            sheet.write(row, 2, dict(app._fields['state'].selection).get(app.state, ''), cell_format)
            sheet.write(row, 3, app.recruitment_app_number.display_name or '', cell_format)
            sheet.write(row, 4, app.employee_name or '', cell_format)
            sheet.write(row, 5, app.job_position.name or '', cell_format)
            sheet.write(row, 6, app.business_unit.name or '', cell_format)
            sheet.write(row, 7, app.nationality.name or '', cell_format)
            sheet.write(row, 8, dict(app._fields['visa_process_type'].selection).get(app.visa_process_type, ''), cell_format)
            sheet.write(row, 9, app.vp_number_id.display_name or '', cell_format)
            sheet.write(row, 10, app.visa_profession_id.display_name or '', cell_format)
            sheet.write(row, 11, app.visa_number or '', cell_format)
            
            col = 12  
            
            # QVC specific fields
            if visa_process_type == 'qvc':
                sheet.write(row, col, app.qvc_country_id.name or '', cell_format)
                sheet.write(row, col+1, app.qvc_center_id.name or '', cell_format)
                sheet.write(row, col+2, app.qvc_visa_application_date and app.qvc_visa_application_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+3, app.qvc_payment_date and app.qvc_payment_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+4, app.qvc_appointment_date and app.qvc_appointment_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+5, app.qvc_visa_payment_date and app.qvc_visa_payment_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+6, app.qvc_visa_issue_date and app.qvc_visa_issue_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+7, app.qvc_qatar_first_entry_date and app.qvc_qatar_first_entry_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+8, app.qvc_qid_apply_date and app.qvc_qid_apply_date.strftime('%d/%m/%Y') or '', cell_format)
                col += 9
                
            # Non-QVC specific fields
            elif visa_process_type == 'non_qvc':
                sheet.write(row, col, app.non_qvc_visa_application_date and app.non_qvc_visa_application_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+1, app.non_qvc_visa_payment_date and app.non_qvc_visa_payment_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+2, app.non_qvc_visa_issue_date and app.non_qvc_visa_issue_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+3, app.non_qvc_qatar_first_entry_date and app.non_qvc_qatar_first_entry_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+4, app.non_qvc_medical_application_date and app.non_qvc_medical_application_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+5, app.non_qvc_medical_appointment_date and app.non_qvc_medical_appointment_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+6, app.non_qvc_fingerprint_application_date and app.non_qvc_fingerprint_application_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+7, app.non_qvc_fingerprint_appointment_date and app.non_qvc_fingerprint_appointment_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+8, 'Yes' if app.non_qvc_employment_contract else 'No', cell_format)
                sheet.write(row, col+9, app.non_qvc_qid_payment_date and app.non_qvc_qid_payment_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+10, app.days_left or '', cell_format)
                col += 11
                
            # Change of Employer/Secondment specific fields
            elif visa_process_type in ['change_employer', 'secondment']:
                sheet.write(row, col, 'Yes' if app.change_employer_noc else 'No', cell_format)
                sheet.write(row, col+1, 'Yes' if app.change_employer_company_documents else 'No', cell_format)
                sheet.write(row, col+2, app.change_employer_application_date and app.change_employer_application_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+3, app.change_employer_application_no or '', cell_format)
                sheet.write(row, col+4, dict(app._fields['change_employer_application_status'].selection).get(app.change_employer_application_status, ''), cell_format)
                sheet.write(row, col+5, 'Yes' if app.change_employer_employee_contract else 'No', cell_format)
                sheet.write(row, col+6, app.change_employer_transfer_payment_date and app.change_employer_transfer_payment_date.strftime('%d/%m/%Y') or '', cell_format)
                col += 7
                
            # Work Permit specific fields
            elif visa_process_type == 'work_permit':
                sheet.write(row, col, 'Yes' if app.work_permit_photo else 'No', cell_format)
                sheet.write(row, col+1, 'Yes' if app.work_permit_qid else 'No', cell_format)
                sheet.write(row, col+2, 'Yes' if app.work_permit_sponsor_id else 'No', cell_format)
                sheet.write(row, col+3, 'Yes' if app.work_permit_education_certificate_arabic else 'No', cell_format)
                sheet.write(row, col+4, app.work_permit_application_no or '', cell_format)
                sheet.write(row, col+5, app.work_permit_application_date and app.work_permit_application_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+6, 'Yes' if app.work_permit_pcc else 'No', cell_format)
                sheet.write(row, col+7, 'Yes' if app.work_permit_employee_contract else 'No', cell_format)
                sheet.write(row, col+8, app.work_permit_payment_date and app.work_permit_payment_date.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+9, app.work_permit_validity_from and app.work_permit_validity_from.strftime('%d/%m/%Y') or '', cell_format)
                sheet.write(row, col+10, app.work_permit_expiry_date and app.work_permit_expiry_date.strftime('%d/%m/%Y') or '', cell_format)
                col += 11

            row += 1