# -*- coding: utf-8 -*-
import time
import babel
from odoo import models, fields, api, tools, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError

class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    loan_line_id = fields.Many2one('hr.loan.line', string="Loan Installment", help="Loan installment")

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _prepare_hr_loan_data(self):
        loan_rule_id = self.env['hr.salary.rule'].search([('code', '=', 'Loan')], limit=1)
        payslip_lon = {}
        if not loan_rule_id:
            raise ValidationError(_("Please create loan rule with code 'Loan'"))
        input_type_input_type = self.env.ref('hr_loan_management.hr_payslip_loan_input')
        loan_line_ids = self.env['hr.loan.line'].search([('loan_id.employee_id', '=', self.employee_id.id), ('date', '>=', self.date_from), ('date', '<=', self.date_to), ('loan_id.state', '=', 'approve'), ('loan_id.types', '=', 'loan')])
        loan_lines = loan_line_ids.filtered(lambda x : not x.paid)
        for line in loan_lines:
            payslip_lon.update({
                'name': '%s-%s' %(line.loan_id.name, loan_rule_id.name),
                'code': loan_rule_id.code,
                'payslip_id' : self.id,
                'contract_id': self.contract_id.id if self.contract_id else False,
                'input_type_id' : input_type_input_type.id,
                'amount' : -line.amount,
                'loan_line_id' : line.id
            })
        paidloan_lines = loan_line_ids.filtered(lambda x : x.paid)
        for line in paidloan_lines:
            payslip_lon.update({
                'payslip_id' : self.id, 
                'loan_line_id' : line.id,
                 'input_type_id' : input_type_input_type.id,
            })
        return payslip_lon if payslip_lon else False

    def _prepare_hr_advance_salary_data(self):
        payslip_sal = {}
        salary_rule_id = self.env['hr.salary.rule'].search([('code', '=', 'Salary')], limit=1)
        if not salary_rule_id:
            raise ValidationError(_("Please create salary rule with code 'Salary'"))
        payslip_salary_input_type = self.env.ref('hr_loan_management.hr_payslip_salary_advance_input')
        loan_line_ids = self.env['hr.loan.line'].search([('loan_id.employee_id', '=', self.employee_id.id), ('date', '>=', self.date_from), ('date', '<=', self.date_to), ('loan_id.state', '=', 'approve'), ('loan_id.types', '=', 'salary_advance')])
        loan_lines = loan_line_ids.filtered(lambda x : not x.paid)
        for line in loan_lines:
            payslip_sal.update({
                'name': '%s-%s' %(line.loan_id.name, salary_rule_id.name),
                'code': salary_rule_id.code, 
                'payslip_id' : self.id, 
                'contract_id': self.contract_id.id if self.contract_id else False, 
                'input_type_id': payslip_salary_input_type.id,
                'amount' : -line.amount,
                'loan_line_id' : line.id,
                'ref': line.loan_id.id,
            })
        paid_loan_lines = loan_line_ids.filtered(lambda x : x.paid)
        for line in paid_loan_lines:
            payslip_sal.update({
                'payslip_id' : self.id, 
                'loan_line_id' : line.id,
                 'input_type_id' : payslip_salary_input_type.id,
            })
        return payslip_sal if payslip_sal else False

    def action_payslip_done(self):
        for line in self.input_line_ids.filtered(lambda x: x.loan_line_id):
            line.loan_line_id.paid = True
            line.loan_line_id.loan_id._compute_loan_amount()
        return super(HrPayslip, self).action_payslip_done()

    def action_payslip_cancel(self):
        for line in self.input_line_ids.filtered(lambda x: x.loan_line_id):
            line.loan_line_id.paid = False
            line.loan_line_id.loan_id._compute_loan_amount()
        return super(HrPayslip, self).action_payslip_cancel()
        