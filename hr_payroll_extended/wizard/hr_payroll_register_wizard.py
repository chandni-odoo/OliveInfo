from odoo import models, fields, api, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

class EmployeePayrollWizard(models.TransientModel):
    _name = 'emplopyee.payroll.wizard'
    _description = "Emplopyee Payroll Wizard"

    employee_ids = fields.Many2many('hr.employee')
    branch_ids = fields.Many2many('res.branch', string='Branch')
    batch_ids = fields.Many2many("payroll.batch", string='Batch')
    based_on = fields.Selection([('employees', 'Emplopyee'),('branch', 'Branch'), ('batch', 'Batch')], default='employees', string="Based On")
    date_from = fields.Date(string="Date From", required=True, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string="Date To", required=True, default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))

    def button_generate_report(self):
        data = {
            'employee_ids': self.employee_ids.ids,
            'branch_ids': self.branch_ids.ids,
            'batch_ids': self.batch_ids.ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('hr_payroll_extended.action_report_payroll_employee').report_action(self, data=data)

    @api.onchange('based_on') 
    def onchange_based_on(self):
        if self.based_on != 'employees':
            self.employee_ids = [(5, 0, 0)]
        if self.based_on != 'branchbranch':
            self.branch_ids = [(5, 0, 0)]
        if self.based_on != 'batch':
            self.batch_ids = [(5, 0, 0)]

class EmployeeReportDetails(models.AbstractModel):
    _name = 'report.hr_payroll_extended.report_payroll_register_employee'


    def get_domain(self, data):
        domain = [('date_from', '>=', data.get('date_from')), ('date_to', '<=', data.get('date_to'))]
        if data.get('employee_ids'):
            domain += [('employee_id', 'in', data.get('employee_ids'))]
        if data.get('branch_ids'):
            domain += [('branch_id', 'in', data.get('branch_ids'))]
        if data.get('batch_ids'):
            domain += [('payroll_run_id.payroll_batch_id', 'in', data.get('batch_ids'))]
        return domain

    def _get_code_by_values(self, codes, slip_lines):
        lines_specific = []
        for code in codes:
            code_lines = slip_lines.filtered(lambda x: x.category_id.code == code)
            rule_ids = code_lines.mapped('salary_rule_id')
            for rule in rule_ids:
                rule_code_lines = code_lines.filtered(lambda x: x.salary_rule_id == rule)
                data = {
                    'name': rule_code_lines.mapped('name')[0],
                    'cur_amount': rule_code_lines.mapped('total')[0],
                    'yid_amount': sum(rule_code_lines.mapped('total'))
                }
                lines_specific.append(data)
        return lines_specific

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        domain = self.get_domain(data)
        data_lines = []
        payslips = self.env['hr.payslip'].search(domain)
        if payslips:    
            for employee in payslips.mapped('employee_id'):
                employee_payslips = payslips.filtered(lambda x: x.employee_id == employee)
                if employee_payslips:
                    payslip_id = employee_payslips[-1]
                line = payslip_id.mapped('line_ids').filtered(lambda x: x.total)
                lines = employee_payslips.mapped('line_ids').filtered(lambda x: x.total)
                batch_name = employee_payslips.mapped('payslip_run_id.name')
                branch_name = employee_payslips.mapped('branch_id.name')
                allowance_lines = lines.filtered(lambda x: x.category_id.code not in ('DED', 'GROSS', 'NET'))
                deduction_lines = lines.filtered(lambda x: x.category_id.code not in ('GROSS', 'NET')) - allowance_lines
                deduction_codes = deduction_lines.mapped('category_id.code')
                allowance_codes = allowance_lines.mapped('category_id.code')
                print(allowance_codes, deduction_codes)
                data_lines.append({
                    'employee_id': employee,
                    'payslips': employee_payslips,
                    'line_id': line,
                    'line_ids': lines,
                    'date_from': data.get('date_from'),
                    'date_to': data.get('date_to'),
                    'batch_name': batch_name,
                    'branch_name': branch_name,
                    'payslip_id': payslip_id,
                    'allowance_lines': self._get_code_by_values(allowance_codes, allowance_lines),
                    'deduction_lines': self._get_code_by_values(deduction_codes, deduction_lines)
                })
        return {
            'company': self.env.company,
            'lines':data_lines,
        }
