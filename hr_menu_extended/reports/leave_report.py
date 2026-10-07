from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from datetime import datetime, timedelta
import io
import xlsxwriter

class LeaveAccrualXlsxReport(models.AbstractModel):
    _name = 'report.hr_menu_extended.leave_accrual_xlsx_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Leave Accrual XLSX Report'


    def _compute_future_accrual(self, employee, accrual_plan, as_on_date):
        
        today = fields.Date.today()
        if as_on_date <= today:
            return 0.0
            
        start_date = today + timedelta(days=1)
        
        accrual_levels = self.env['hr.leave.accrual.level'].search([
            ('accrual_plan_id', '=', accrual_plan.id)
        ], order='sequence')
        
        if not accrual_levels:
            return 0.0
            
        joining_date = employee.joining_date or employee.original_hire_date
        if not joining_date:
            return 0.0
            
        total_service_days = (today - joining_date).days
        
        future_accrual = 0.0
        current_date = start_date
        current_service_days = total_service_days
        
        level_thresholds = []
        level_rates = []
        
        for level in accrual_levels:
            threshold_days = level.start_count
            if level.start_type == 'year':
                threshold_days = level.start_count * 365
                
            level_thresholds.append(threshold_days)
            level_rates.append(level.added_value)
        
        while current_date <= as_on_date:
            current_service_days += 1  
            
            applied_rate = 0.0
            for i, threshold in enumerate(level_thresholds):
                if current_service_days >= threshold:
                    applied_rate = level_rates[i]
                else:
                    break
                    
            future_accrual += applied_rate
            
            current_date += timedelta(days=1)
        
        return round(future_accrual, 2)

    def generate_xlsx_report(self, workbook, data, wizard):
        as_on_date = data.get('as_on_date')
        employee_id = data.get('employee_id')
        employee_name = data.get('employee_name')
        
        domain = [('state', '=', 'validate')]
        
        if employee_id:
            domain.append(('employee_id', '=', employee_id))
        
        allocations = self.env['hr.leave.allocation'].search(domain)
        
        if not allocations:
            raise UserError(_("No leave allocations found for the selected criteria."))
        
        sheet = workbook.add_worksheet('Leave Accrual Report')
        
        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        
        date_obj = fields.Date.from_string(as_on_date)
        formatted_date = date_obj.strftime('%d/%m/%Y') 
        
        sheet.merge_range(0, 0, 0, 14, 
                         f'Leave Accrual Report - {formatted_date} (Employee: {employee_name})', 
                         workbook.add_format({
                             'bold': True, 
                             'align': 'center', 
                             'size': 16,
                             'num_format': '@'  
                         }))
        
        headers = [
            'Employee ID',
            'Employee',
            'Manager',
            'Job Title',
            'Branch',
            'Joining Date',
            'Accrual Status',
            'Employee Status',
            'Leave Type',
            'Allocation Type',
            'From Date',
            'To Date',
            'Total Accrued',
            'Future Accrual',  
            'Leaves Availed',
            'Total Accrued Balance'
        ]
        
        for col, header in enumerate(headers):
            sheet.write(2, col, header, header_format)
        
        # Set column widths
        sheet.set_column(0, 0, 15)  # Employee ID
        sheet.set_column(1, 1, 25)  # Employee
        sheet.set_column(2, 2, 25)  # Manager
        sheet.set_column(3, 3, 20)  # Job Title
        sheet.set_column(4, 4, 15)  # Branch
        sheet.set_column(5, 5, 15)  # Joining Date
        sheet.set_column(6, 6, 15)  # Status
        sheet.set_column(7, 7, 20)  # Employee Status
        sheet.set_column(8, 8, 20)  # Leave Type
        sheet.set_column(9, 9, 15)  # Allocation Type
        sheet.set_column(10, 11, 15) # From/To Dates
        sheet.set_column(12, 15, 15) # Numbers (Accrued, Future, Taken, Remaining)
        
        # Write data
        row = 3
        for alloc in allocations:
            employee = alloc.employee_id

            branch = ''
            if employee.branch_id:
                branch_code = employee.branch_id.code or ''
                branch_name = employee.branch_id.name or ''
                if branch_code and branch_name:
                    branch = f"{branch_code} - {branch_name}"
                else:
                    branch = branch_code or branch_name
            
            employee_status = ''
            if hasattr(employee, 'employee_status'):
                employee_status = employee.employee_status or ''
            else:
                employee_status = 'Active' if employee.active else 'Inactive'
            
            # branch = ''
            # if hasattr(employee, 'branch_id'):
            #     branch = employee.branch_id.name or ''
            
            # Calculate future accrual if there's an accrual plan
            future_accrual = 0.0
            if hasattr(alloc, 'accrual_plan_id') and alloc.accrual_plan_id:
                future_accrual = self._compute_future_accrual(
                    employee, 
                    alloc.accrual_plan_id, 
                    fields.Date.from_string(as_on_date)
                )

            
            sheet.write(row, 0, employee.emp_no or '')
            sheet.write(row, 1, employee.name or '')
            sheet.write(row, 2, employee.parent_id.name or '')  
            sheet.write(row, 3, employee.job_title or '')
            sheet.write(row, 4, branch)  
            sheet.write(row, 5, employee.joining_date or employee.original_hire_date or '', date_format)
            sheet.write(row, 6, employee_status) 
            # sheet.write(row, 8, employee.emp_status or '') 
            emp_status = employee.emp_status or ''
            if emp_status and 'emp_status' in employee._fields:
                # Get the selection options dictionary
                selection = employee._fields['emp_status'].selection
                # Convert the technical value to display value
                emp_status_display = dict(selection).get(emp_status, emp_status)
                sheet.write(row, 7, emp_status_display)
            else:
                sheet.write(row, 7, emp_status)
            sheet.write(row, 8, alloc.holiday_status_id.name or '')
            sheet.write(row, 9, alloc.allocation_type or '')
            sheet.write(row, 10, alloc.date_from or '', date_format)
            sheet.write(row, 11, alloc.date_to or '', date_format)
            sheet.write(row, 12, alloc.number_of_days or 0) 
            sheet.write(row, 13, future_accrual) 
            sheet.write(row, 14, alloc.leaves_taken or 0)  
            sheet.write(row, 15, (alloc.remaining_leaves or 0) + future_accrual)  
            row += 1

# class LeaveAccrualXlsxReport(models.AbstractModel):
#     _name = 'report.hr_menu_extended.leave_accrual_xlsx_report'
#     _inherit = 'report.report_xlsx.abstract'
#     _description = 'Leave Accrual XLSX Report'


#     def _compute_future_accrual(self, employee, accrual_plan, as_on_date):
        
#         today = fields.Date.today()
#         if as_on_date <= today:
#             return 0.0
            
#         start_date = today + timedelta(days=1)
        
#         accrual_levels = self.env['hr.leave.accrual.level'].search([
#             ('accrual_plan_id', '=', accrual_plan.id)
#         ], order='sequence')
        
#         if not accrual_levels:
#             return 0.0
            
#         joining_date = employee.joining_date or employee.original_hire_date
#         if not joining_date:
#             return 0.0
            
#         total_service_days = (today - joining_date).days
        
#         future_accrual = 0.0
#         current_date = start_date
#         current_service_days = total_service_days
        
#         level_thresholds = []
#         level_rates = []
        
#         for level in accrual_levels:
#             threshold_days = level.start_count
#             if level.start_type == 'year':
#                 threshold_days = level.start_count * 365
                
#             level_thresholds.append(threshold_days)
#             level_rates.append(level.added_value)
        
#         while current_date <= as_on_date:
#             current_service_days += 1  
            
#             applied_rate = 0.0
#             for i, threshold in enumerate(level_thresholds):
#                 if current_service_days >= threshold:
#                     applied_rate = level_rates[i]
#                 else:
#                     break
                    
#             future_accrual += applied_rate
            
#             current_date += timedelta(days=1)
        
#         return round(future_accrual, 2)

#     def generate_xlsx_report(self, workbook, data, wizard):
#         as_on_date = data.get('as_on_date')
#         employee_id = data.get('employee_id')
#         employee_name = data.get('employee_name')
        
#         domain = [('state', '=', 'validate')]
        
#         if employee_id:
#             domain.append(('employee_id', '=', employee_id))
        
#         allocations = self.env['hr.leave.allocation'].search(domain)
        
#         if not allocations:
#             raise UserError(_("No leave allocations found for the selected criteria."))
        
#         sheet = workbook.add_worksheet('Leave Accrual Report')
        
#         bold = workbook.add_format({'bold': True})
#         header_format = workbook.add_format({
#             'bold': True,
#             'align': 'center',
#             'valign': 'vcenter',
#             'bg_color': '#4472C4',
#             'font_color': 'white',
#             'border': 1
#         })
#         date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        
#         date_obj = fields.Date.from_string(as_on_date)
#         formatted_date = date_obj.strftime('%d/%m/%Y') 
        
#         sheet.merge_range(0, 0, 0, 14, 
#                          f'Leave Accrual Report - {formatted_date} (Employee: {employee_name})', 
#                          workbook.add_format({
#                              'bold': True, 
#                              'align': 'center', 
#                              'size': 16,
#                              'num_format': '@'  
#                          }))
        
#         headers = [
#             'Employee',
#             'Manager',
#             'Job Title',
#             'Branch',
#             'Department',
#             'Joining Date',
#             'Status',
#             'Leave Type',
#             'Allocation Type',
#             'From Date',
#             'To Date',
#             'Total Accrued',
#             'Future Accrual',  
#             'Leaves Availed',
#             'Total Accrued Balance'
#         ]
        
#         for col, header in enumerate(headers):
#             sheet.write(2, col, header, header_format)
        
#         # Set column widths
#         sheet.set_column(0, 0, 25)  # Employee
#         sheet.set_column(1, 1, 25)  # Manager
#         sheet.set_column(2, 2, 20)  # Job Title
#         sheet.set_column(3, 3, 15)  # Branch
#         sheet.set_column(4, 4, 20)  # Department
#         sheet.set_column(5, 5, 15)  # Joining Date
#         sheet.set_column(6, 6, 15)  # Status
#         sheet.set_column(7, 7, 20)  # Leave Type
#         sheet.set_column(8, 8, 15)  # Allocation Type
#         sheet.set_column(9, 10, 15) # From/To Dates
#         sheet.set_column(11, 14, 15) # Numbers (Accrued, Future, Taken, Remaining)
        
#         # Write data
#         row = 3
#         for alloc in allocations:
#             employee = alloc.employee_id
            
#             employee_status = ''
#             if hasattr(employee, 'employee_status'):
#                 employee_status = employee.employee_status or ''
#             else:
#                 employee_status = 'Active' if employee.active else 'Inactive'
            
#             branch = ''
#             if hasattr(employee, 'branch_id'):
#                 branch = employee.branch_id.name or ''
            
#             # Calculate future accrual if there's an accrual plan
#             future_accrual = 0.0
#             if hasattr(alloc, 'accrual_plan_id') and alloc.accrual_plan_id:
#                 future_accrual = self._compute_future_accrual(
#                     employee, 
#                     alloc.accrual_plan_id, 
#                     fields.Date.from_string(as_on_date)
#                 )
            
#             sheet.write(row, 0, employee.name or '')
#             sheet.write(row, 1, employee.parent_id.name or '')  
#             sheet.write(row, 2, employee.job_title or '')
#             sheet.write(row, 3, branch)  
#             sheet.write(row, 4, employee.department_id.name or '')
#             sheet.write(row, 5, employee.joining_date or employee.original_hire_date or '', date_format)
#             sheet.write(row, 6, employee_status)  
#             sheet.write(row, 7, alloc.holiday_status_id.name or '')
#             sheet.write(row, 8, alloc.allocation_type or '')
#             sheet.write(row, 9, alloc.date_from or '', date_format)
#             sheet.write(row, 10, alloc.date_to or '', date_format)
#             sheet.write(row, 11, alloc.number_of_days or 0) 
#             sheet.write(row, 12, future_accrual) 
#             sheet.write(row, 13, alloc.leaves_taken or 0)  
#             sheet.write(row, 14, (alloc.remaining_leaves or 0) + future_accrual)  
#             row += 1
        
        # Add totals row
        # sheet.write(row, 0, 'TOTAL', bold)
        # sheet.write_formula(row, 11, f'=SUM(L4:L{row})', bold)  # Total Accrued
        # sheet.write_formula(row, 12, f'=SUM(M4:M{row})', bold)  # Future Accrual
        # sheet.write_formula(row, 13, f'=SUM(N4:N{row})', bold)  # Leaves Taken
        # sheet.write_formula(row, 14, f'=SUM(O4:O{row})', bold)  # Remaining + Future Leaves


    # def _compute_future_accrual(self, employee, accrual_plan, as_on_date):
       
    #     today = fields.Date.today()
    #     if as_on_date <= today:
    #         return 0.0
            
    #     start_date = today + timedelta(days=1)
        
    #     rules = self.env['hr.leave.accrual.level'].search([
    #         ('accrual_plan_id', '=', accrual_plan.id)
    #     ], order='sequence')
        
    #     if not rules:
    #         return 0.0
            
    #     joining_date = employee.joining_date
    #     if not joining_date:
    #         return 0.0
            
    #     service_days_today = (today - joining_date).days
        
    #     future_accrual = 0.0
    #     current_date = start_date
    #     current_service_days = service_days_today
        
    #     while current_date <= as_on_date:
    #         current_service_days += 1
            
           
    #         applicable_rule = None
    #         for rule in rules:
    #             rule_days = rule.start_count if rule.start_type == 'day' else rule.start_count * 365
    #             if current_service_days >= rule_days:
    #                 applicable_rule = rule
    #             else:
    #                 break
                    
    #         if applicable_rule and applicable_rule.added_value > 0:
    #             future_accrual += applicable_rule.added_value
                
    #         current_date += timedelta(days=1)
            
    #     return round(future_accrual, 2)

    # def generate_xlsx_report(self, workbook, data, wizard):
    #     as_on_date = data.get('as_on_date')
    #     employee_id = data.get('employee_id')
    #     employee_name = data.get('employee_name')
        
    #     domain = [('state', '=', 'validate')]
        
    #     if employee_id:
    #         domain.append(('employee_id', '=', employee_id))
        
    #     allocations = self.env['hr.leave.allocation'].search(domain)
        
    #     if not allocations:
    #         raise UserError(_("No leave allocations found for the selected criteria."))
        
    #     sheet = workbook.add_worksheet('Leave Accrual Report')
        
    #     bold = workbook.add_format({'bold': True})
    #     header_format = workbook.add_format({
    #         'bold': True,
    #         'align': 'center',
    #         'valign': 'vcenter',
    #         'bg_color': '#4472C4',
    #         'font_color': 'white',
    #         'border': 1
    #     })
    #     date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    #     datetime_format = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm:ss'})
        
    #     date_obj = fields.Date.from_string(as_on_date)
    #     formatted_date = date_obj.strftime('%d/%m/%Y') 
        
    #     sheet.merge_range(0, 0, 0, 10, 
    #                      f'Leave Accrual Report - {formatted_date} (Employee: {employee_name})', 
    #                      workbook.add_format({
    #                          'bold': True, 
    #                          'align': 'center', 
    #                          'size': 16,
    #                          'num_format': '@'  
    #                      }))
        
    #     headers = [
    #         'Employee',
    #         'Manager',
    #         'Job Title',
    #         'Branch',
    #         'Department',
    #         'Joining Date',
    #         'Status',
    #         'Leave Type',
    #         'Allocation Type',
    #         'From Date',
    #         'To Date',
    #         'Total Accrued',
    #         'Future Accrual',  # New column
    #         'Leaves Taken',
    #         'Remaining Leaves'
    #     ]
        
    #     for col, header in enumerate(headers):
    #         sheet.write(2, col, header, header_format)
        
    #     # Set column widths
    #     sheet.set_column(0, 0, 25)  # Employee
    #     sheet.set_column(1, 1, 25)  # Manager
    #     sheet.set_column(2, 2, 20)  # Job Title
    #     sheet.set_column(3, 3, 15)  # Branch
    #     sheet.set_column(4, 4, 20)  # Department
    #     sheet.set_column(5, 5, 15)  # Joining Date
    #     sheet.set_column(6, 6, 15)  # Status
    #     sheet.set_column(7, 7, 20)  # Leave Type
    #     sheet.set_column(8, 8, 15)  # Allocation Type
    #     sheet.set_column(9, 10, 15) # From/To Dates
    #     sheet.set_column(11, 14, 15) # Numbers (Accrued, Future, Taken, Remaining)
        
    #     # Write data
    #     row = 3
    #     for alloc in allocations:
    #         employee = alloc.employee_id
            
    #         employee_status = ''
    #         if hasattr(employee, 'employee_status'):
    #             employee_status = employee.employee_status or ''
    #         else:
    #             employee_status = 'Active' if employee.active else 'Inactive'
            
    #         branch = ''
    #         if hasattr(employee, 'branch_id'):
    #             branch = employee.branch_id.name or ''
            
    #         # Calculate future accrual if there's an accrual plan
    #         future_accrual = 0.0
    #         if hasattr(alloc, 'accrual_plan_id') and alloc.accrual_plan_id:
    #             future_accrual = self._compute_future_accrual(
    #                 employee, 
    #                 alloc.accrual_plan_id, 
    #                 fields.Date.from_string(as_on_date)
    #             )
            
    #         sheet.write(row, 0, employee.name or '')
    #         sheet.write(row, 1, employee.parent_id.name or '')  # Manager
    #         sheet.write(row, 2, employee.job_title or '')
    #         sheet.write(row, 3, branch)  # Branch
    #         sheet.write(row, 4, employee.department_id.name or '')
    #         sheet.write(row, 5, employee.joining_date or '', date_format)
    #         sheet.write(row, 6, employee_status)  # Status
    #         sheet.write(row, 7, alloc.holiday_status_id.name or '')
    #         sheet.write(row, 8, alloc.allocation_type or '')
    #         sheet.write(row, 9, alloc.date_from or '', date_format)
    #         sheet.write(row, 10, alloc.date_to or '', date_format)
    #         sheet.write(row, 11, alloc.number_of_days or 0)  # Total Accrued
    #         sheet.write(row, 12, future_accrual)  # Future Accrual
    #         sheet.write(row, 13, alloc.leaves_taken or 0)  # Leaves Taken
    #         sheet.write(row, 14, (alloc.remaining_leaves or 0) + future_accrual)  # Remaining + Future
    #         row += 1
        
    #     # Add totals row
    #     sheet.write(row, 0, 'TOTAL', bold)
    #     sheet.write_formula(row, 11, f'=SUM(L4:L{row})', bold)  # Total Accrued
    #     sheet.write_formula(row, 12, f'=SUM(M4:M{row})', bold)  # Future Accrual
    #     sheet.write_formula(row, 13, f'=SUM(N4:N{row})', bold)  # Leaves Taken
    #     sheet.write_formula(row, 14, f'=SUM(O4:O{row})', bold)  # Remaining + Future Leaves


