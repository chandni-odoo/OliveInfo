import xlsxwriter
from odoo import models
from datetime import datetime


class ContractSalaryReport(models.AbstractModel):
    _name = 'report.hr_payroll_report.contract_report_xlsx'
    _description = 'HR Contract Salary Report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizards):
        wizard = wizards[0]
        sheet = workbook.add_worksheet('Contract Salary Report')
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
        money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        regular_format = workbook.add_format({'border': 1})

        sheet.merge_range(0, 0, 0, 6, 'EMPLOYEE CONTRACT SALARY REPORT', bold)
        
        row = 2
        sheet.write(row, 0, "Generated On:", bold)
        sheet.write(row, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        row += 1
        sheet.write(row, 0, "Branch Filter:", bold)
        sheet.write(row, 1, ', '.join(wizard.branch_ids.mapped('name')) if wizard.branch_ids else "All Branches")
        
        row += 1
        sheet.write(row, 0, "Billable Only:", bold)
        sheet.write(row, 1, "Yes" if wizard.billable else "No")
        
        row += 1
        sheet.write(row, 0, "Employee Status:", bold)
        # sheet.write(row, 1, dict(wizard._fields['employee_status'].selection).get(wizard.employee_status, "All Statuses"))
        status_filters = []
        if wizard.active_status:
            status_filters.append("Active")
        if wizard.leave_status:
            status_filters.append("Leave")
        status_display = "All Statuses" if not status_filters else ", ".join(status_filters)
        sheet.write(row, 1, status_display)

        domain = [('state', '=', 'open')]
        
        if wizard.branch_ids:
            domain += [('employee_id.branch_id', 'in', wizard.branch_ids.ids)]
        if wizard.billable:
            domain += [('employee_id.billable', '=', True)]
        # if wizard.employee_status:
        #     domain += [('employee_id.emp_status', '=', wizard.employee_status)]
        # Handle status filter
        # Handle status filter
        status_domain = []
        if wizard.active_status:
            status_domain.append(('employee_id.emp_status', '=', 'active'))
        if wizard.leave_status:
            status_domain.append(('employee_id.emp_status', '=', 'leave'))
        
        # Apply status filter only if at least one checkbox is selected
        if status_domain:
            domain += ['|' if len(status_domain) > 1 else ''] * (len(status_domain) - 1) + status_domain

        contracts = self.env['hr.contract'].search(domain, order='employee_id')

        # Get all allowances for all contracts in one query
        allowance_records = self.env['hr.allowance.type'].search_read(
            [('contract_id', 'in', contracts.ids)],
            ['name', 'code', 'contract_id', 'amount']
        )
        
        # Organize allowances by contract and get unique allowance types
        contract_allowances = {}
        allowance_totals = {}  # To track which allowances have non-zero values
        
        for allowance in allowance_records:
            contract_id = allowance['contract_id'][0]
            code = allowance['code']
            amount = allowance['amount'] or 0.0
            
            if contract_id not in contract_allowances:
                contract_allowances[contract_id] = {}
            
            contract_allowances[contract_id][code] = amount
            
            # Track totals for each allowance type
            if code not in allowance_totals:
                allowance_totals[code] = {'name': allowance['name'], 'total': 0.0}
            allowance_totals[code]['total'] += amount

        # Filter out allowance types that have all zeros
        non_zero_allowances = {
            code: data['name'] 
            for code, data in allowance_totals.items() 
            if not wizard.hide_zero_records or data['total'] != 0.0
        }

        base_headers = [
            'Emp. No.',
            'Name',
            'Position',
            'Branch',
            'Start Date',
            'End Date',
            'Structure',
            'Status',
            'Basic',
            'Gross',
            'Net',
        ]
        
        headers = base_headers + list(non_zero_allowances.values())

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(8, col, header, header_format)

        row = 9
        for contract in contracts:
            emp = contract.employee_id

            branch = ''
            if emp.branch_id:
                branch_code = emp.branch_id.code or ''
                branch_name = emp.branch_id.name or ''
                if branch_code and branch_name:
                    branch = f"{branch_code} - {branch_name}"
                else:
                    branch = branch_code or branch_name
            
            # Get allowances for this contract from our pre-organized dictionary
            allowances = contract_allowances.get(contract.id, {})
            
            # Prepare row data
            row_data = [
                emp.emp_no or '',  # Employee Code
                emp.name or '',                        # Employee Name
                contract.job_id.name or '',           # Job Position
                branch,  # Branch
                contract.date_start,                   # Start Date
                contract.date_end or '',               # End Date
                contract.structure_id.name or '',      # Salary Structure
                dict(emp._fields['emp_status'].selection).get(emp.emp_status, ''),  # Status
                contract.wage,                        # Basic Wage
                contract.gross_amount,                 # Gross Salary
                contract.net_amount,                  # Net Salary
            ]
            
            # Add only non-zero allowance amounts in the same order as headers
            for allowance_code in non_zero_allowances.keys():
                row_data.append(allowances.get(allowance_code, 0.0))
            
            # Skip zero records if hide_zero_records is True
            if wizard.hide_zero_records:
                # Check if all money fields (basic wage, gross, net and allowances) are zero
                money_fields = row_data[8:11] + row_data[len(base_headers):]
                if all(float(v or 0) == 0.0 for v in money_fields):
                    continue
            
            for col, value in enumerate(row_data):
                if col in [4, 5]:  # Date columns (adjusted index after removing department)
                    sheet.write(row, col, value, date_format)
                elif col >= len(base_headers) or col in [8, 9, 10]:  # Allowance columns and money columns
                    sheet.write(row, col, value, money_format)
                else:
                    sheet.write(row, col, value, regular_format)
            
            row += 1

        # Set column widths
        sheet.set_column(0, 0, 12)  # Employee Code
        sheet.set_column(1, 1, 25)  # Employee Name
        sheet.set_column(2, 2, 20)  # Job Position
        sheet.set_column(3, 3, 20)  # Branch
        sheet.set_column(4, 5, 12)  # Dates
        sheet.set_column(6, 6, 20)  # Salary Structure
        sheet.set_column(7, 7, 15)  # Status
        sheet.set_column(8, len(headers)-1, 15)  # Money columns (basic wage, gross, net and allowances)

        # Freeze headers
        sheet.freeze_panes(9, 0)



