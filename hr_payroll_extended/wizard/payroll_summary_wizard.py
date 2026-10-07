from odoo import api, fields, models, _
import datetime

class PayrollSummaryizard(models.TransientModel):
    _name = "payroll.summary.wizard"
    _description = "Payroll Summary Wizard"

    batch_id = fields.Many2one("payroll.batch", required=True)

    def action_report_print(self):
        data = {

            'batch_id' : self.batch_id.id,
        }
        return self.env.ref('hr_payroll_extended.action_report_payroll_summary').report_action(self, data=data)

class PaymentSummaryReport(models.AbstractModel):
    _name = 'report.hr_payroll_extended.report_payroll_summary_template'

    def _get_costs(self, lines):
        """ This method will return allowance lines """
        costs = sum(lines.filtered(lambda x: x.code in ('EarningSCR', 'TrafficDed', 'StaffDed', 'TelDed')).mapped('amount'))
        return costs

    def _get_loan(self, lines):
        loan = sum(lines.filtered(lambda x: x.code in ('Loan', 'Salary')).mapped('amount'))
        return loan

    def _get_deduction(self, lines):
        cost_lines = lines.filtered(lambda x: x.code in ('EarningSCR', 'TrafficDed', 'StaffDed', 'TelDed'))
        loan_lines = lines.filtered(lambda x: x.code in ('Loan', 'Salary'))
        deduction_lines = lines - (cost_lines | loan_lines)
        lines_deductions = deduction_lines.filtered(lambda x: x.category_id.code == 'DED')
        amount = sum(lines_deductions.mapped('amount'))
        return amount

    def _get_other_allowance(self, lines):
        other_allowance = self.env['hr.payslip.input.type'].search([('type', '=', 'allowance')])
        other_lines = lines.filtered(lambda x: x.code in other_allowance.mapped('code'))
        return round(sum(other_lines.mapped('amount')), 2)

    @api.model
    def _get_report_values(self, docids, data=None):
        batch_id = data.get('batch_id')
        batch = self.env['payroll.batch'].browse(batch_id)
        all_paylips = self.env['hr.payslip'].search([('payslip_run_id.payroll_batch_id', '=', batch.id)])
        lines = []
        data = {'lines': [], 'total_employee':0.0, 'total_with_branch':0.0, 'total_cost':0.0 , 'total_basic': 0.0, 'total_overtime': 0.0, 'total_allowance': 0.0, 'total_with_allowance' :0.0, 'total_with_deduction' :0.0 , 'total_deduction' :0.0, 'total_others': 0.0, 'total_loan': 0.0,}
        branches = all_paylips.mapped('branch_id')
        for branch in branches:
            branch_payslips = all_paylips.filtered(lambda x: x.branch_id == branch)
            lines = branch_payslips.mapped('line_ids')
            branch_employee = len(branch_payslips.mapped('employee_id'))
            basic  = sum(lines.filtered(lambda x: x.code == 'BASIC').mapped('amount'))
            hours , ovetime_amount = branch_payslips.get_overtime()
            allowance = sum(lines.filtered(lambda x: x.category_id.code == 'ALW').mapped('amount')) - self._get_other_allowance(lines) - ovetime_amount
            other_allowance = self._get_other_allowance(lines)
            total_with_allowance = basic + ovetime_amount + allowance + other_allowance
            cost = self._get_costs(lines)
            loan = self._get_loan(lines)
            deduction = self._get_deduction(lines)
            total_with_deduction = abs(cost + loan + deduction)
            total_with_branch = total_with_allowance - total_with_deduction
            data['total_employee'] += branch_employee
            data['total_basic'] += basic
            data['total_allowance'] += allowance
            data['total_overtime'] += ovetime_amount
            data['total_others'] += other_allowance
            data['total_with_allowance'] += total_with_allowance
            data['total_loan'] += loan
            data['total_cost'] += cost
            data['total_deduction'] += deduction
            data['total_with_deduction'] += total_with_deduction
            data['total_with_branch'] += total_with_branch
            data['batch_id'] = batch
            data['date'] = datetime.date.today()
            branch_data = {
                'branch_id': branch,
                'employee_id' : branch_employee,
                'basic': basic,
                'allowance': allowance,
                'overtime': ovetime_amount,
                'other' : other_allowance,
                'total_with_allowance': total_with_allowance,
                'loan' : loan,
                'cost' : cost,
                'deduction': deduction,
                'total_with_deduction': total_with_deduction,
                'branch_total': total_with_branch,
            }
            data['lines'].append(branch_data),
        return {
                'company': self.env.company,
                'data': [data],
                'lines':data['lines'],

            }
