# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import random

class OtherEarnings(models.Model):
    _name = "other.earnings"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Other Earnings"
    
    name = fields.Char(default="New", readonly=True, copy=False)
    start_date = fields.Date(default=fields.Date.today(), string="Date")
    end_date = fields.Date(default=fields.Date.today())
    amount = fields.Float("Amount")
    payslip_input_type_id = fields.Many2one('hr.payslip.input.type', string='Other Input Types')
    type = fields.Selection([('allowance', 'Allowance'),('deduction', 'Deduction')], string="Type", default='')
    applied_to = fields.Selection([
        ('company', 'Company'),
        ('branch', 'Branch'),
        ('department', 'Department'),
        ('emplopyee', 'Employee'),
        ('project', 'Project'),
        ('task', 'Task'),
    ], string="Applied To")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('under_approval', 'Under Approval'),
        ('approve', 'Approved'),
        ('confirm', 'Confirm'),
        ('paid', 'Paid'),
        ('cancel', 'Cancel'),
    ], string="State", default='draft')
    company_ids = fields.Many2many('res.company')
    branch_ids = fields.Many2many('res.branch')
    department_ids = fields.Many2many('hr.department')
    employee_ids = fields.Many2many('hr.employee')
    project_ids = fields.Many2many('project.project')
    task_ids = fields.Many2many('project.task')
    earnings_ids = fields.One2many('other.earnings.line', 'earnings_line_id')
    name = fields.Char(default="New", readonly=True, copy=False)
    start_date = fields.Date(default=fields.Date.today(), string="Date")
    end_date = fields.Date(default=fields.Date.today())

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('other.earning.seq') or ('New')
        return super(OtherEarnings, self).create(vals)

    @api.onchange('applied_to')
    def onchange_applied(self):
        self.employee_ids = self.branch_ids = self.department_ids = self.company_ids = self.project_ids = self.task_ids = self.earnings_ids = [(5, 0, 0)]

    @api.onchange('payslip_input_type_id')
    def onchange_payslip_input_type_id(self):
        if self.payslip_input_type_id :
            if not self.payslip_input_type_id.struct_ids:
                raise ValidationError (_("Please select structure in selected other input type")) 
            self.type = self.payslip_input_type_id.type
            for line in self.earnings_ids:
                line.payslip_input_type_id = self.payslip_input_type_id.id
                line.type = self.payslip_input_type_id.type
                line.date = fields.Date.today()

    def update_earning_ids(self, employee_ids):
        earnings_lines = [(5, 0, 0)]
        for emp in employee_ids:
            earnings_lines.append((0, 0, {
                'employee_id': emp.id,
                'payslip_input_type_id': self.payslip_input_type_id.id if self.payslip_input_type_id else False,
                'type': self.payslip_input_type_id.type if self.payslip_input_type_id else False,
                'date': fields.Date.today()
            }))
        self.earnings_ids = earnings_lines

    @api.onchange('company_ids')
    def onchange_company_ids(self):
        emp_ids = self.env['hr.employee'].search([('company_id', '=', self.company_ids.ids)])
        self.update_earning_ids(emp_ids)

    @api.onchange('department_ids')
    def onchange_department_ids(self):
        emp_ids = self.env['hr.employee'].search([('department_id', '=', self.department_ids.ids)])
        self.update_earning_ids(emp_ids)

    @api.onchange('employee_ids')
    def onchange_employee_ids(self):
        emp_ids = self.env['hr.employee'].search([('id', '=', self.employee_ids.ids)])
        self.update_earning_ids(emp_ids)

    @api.onchange('branch_ids')
    def onchange_branch_ids(self):
        emp_ids = self.env['hr.employee'].search([('branch_id', '=', self.branch_ids.ids)])
        self.update_earning_ids(emp_ids)

    @api.onchange('project_ids')
    def onchange_project_ids(self):
        emp_ids = self.env['project.task'].search([('project_id', 'in', self.project_ids.ids)])
        self.update_earning_ids(emp_ids.filtered(lambda x: x.engineer))

    @api.onchange('task_ids')
    def onchange_task_ids(self):
        emp_ids = self.env['project.task'].search([('id', 'in', self.task_ids.ids)])
        self.update_earning_ids(emp_ids.filtered(lambda x: x.engineer))

    def action_under_approval(self):
        if not self.earnings_ids:
            raise ValidationError(_("Please select some employees"))
        self.write({'state': 'under_approval'})

    def action_approve(self):
        self.write({'state': 'approve'})

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def compute_amount(self):
        for rec in self.earnings_ids:
            if not rec.amount:
                rec.amount = self.amount
            if not rec.date:
                rec.date = fields.Date.today()
            if not rec.payslip_input_type_id:
                rec.payslip_input_type_id = self.payslip_input_type_id
            if not rec.type:
                rec.type = rec.payslip_input_type_id.type

    def action_paid(self):
        for struct in self.payslip_input_type_id.struct_ids:
            payslip_ids = self.env['hr.payslip'].search([('date_from', '<=', self.start_date), ('date_to', '>=', self.start_date), ('struct_id', '=', struct.id)])
            for rec in payslip_ids:
                if rec.state != 'paid':
                    raise ValidationError(_('Payslip %s-for-%s is not in paid state. Please make it paid', rec.number, rec.employee_id.name))
            rule_ids = struct.rule_ids.filtered(lambda m: m.code == self.payslip_input_type_id.code)
            if rule_ids:
                rule_ids.write({'active': False})
        self.write({'state': 'paid'})

    def action_cancel(self):
        salary_rule_id = self.env['hr.salary.rule'].search([('code', '=', self.payslip_input_type_id.code)], limit=1)
        if salary_rule_id:
            salary_rule_id.write({'active': False})
        self.write({'state': 'cancel'})

    # @api.onchange('payslip_input_type_id')
    # def onchange_type(self):
    #     self.type = self.payslip_input_type_id.type
    #     for line in self.earnings_ids:
    #         line.payslip_input_type_id = self.payslip_input_type_id and self.payslip_input_type_id.id

    # @api.constrains('date_from','payslip_input_type_id')
    # def check_validation(self):
    #     for rec in self:
    #         match_earnings = self.env['other.earnings'].search([
    #             ('id', '!=', rec.id),
    #             ('payslip_input_type_id', '=', rec.payslip_input_type_id.id),
    #             ('start_date', '=', rec.start_date),
    #         ])
    #         if match_earnings:
    #             raise ValidationError(_('You can not create same date and same other input type for earnings'))

    def create_salary_rule(self):
        hr_rule = self.env['hr.salary.rule']
        category_id = self.env['hr.salary.rule.category']
        amount = 0.0
        if self.type == 'allowance':
            category_id = self.env['hr.salary.rule.category'].search([('code', '=', 'ALW')], limit=1)
            amount = self.amount
        else:
            category_id = self.env['hr.salary.rule.category'].search([('code', '=', 'DED')], limit=1) 
            amount = self.amount * -1
        if not category_id:
            raise ValidationError(_("Please create allowance or deduction category"))
        for struct in self.payslip_input_type_id.struct_ids:
            salary_rule = hr_rule.search([('code', '=', self.payslip_input_type_id.code), ('struct_id', '=', struct.id)], limit=1)
            if salary_rule:
                raise ValidationError(_("Salary rule for code %s is already exist" %salary_rule.code))            
            vals = {
                'name': self.payslip_input_type_id.name,
                'category_id': category_id.id,
                'code': self.payslip_input_type_id.code,
                'struct_id': struct.id,
                'sequence': int(random.randint(500, 9999)),
                'amount_fix': 0.0,
                'account_debit' : self.payslip_input_type_id.account_debit,
                'account_credit' : self.payslip_input_type_id.account_credit,
                'analytic_account_id' : self.payslip_input_type_id.analytic_account_id,
                'not_computed_in_net' : self.payslip_input_type_id.not_computed_in_net,

            }
            hr_rule.create(vals)

class OtherEarningsLine(models.Model):
    _name = "other.earnings.line"
    _description = 'Other Earnings Lines'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    amount = fields.Float(string='Amount')
    date = fields.Date(string='Date')
    earnings_line_id = fields.Many2one('other.earnings',ondelete='cascade')
    payslip_input_type_id = fields.Many2one('hr.payslip.input.type', string='Other Input Types')
    type = fields.Selection([('allowance', 'Allowance'),('deduction', 'Deduction')], string="Type")
    is_payslip_created = fields.Boolean(string="Payslip Created")

    @api.onchange('payslip_input_type_id')
    def onchange_payslip_input_type(self):
        if self.payslip_input_type_id:
            if not self.payslip_input_type_id.struct_ids:
                raise ValidationError (_("Please select structure in selected other input type")) 
            self.type = self.payslip_input_type_id.type

class HrPayslipInputType(models.Model):
    _inherit = 'hr.payslip.input.type'

    type = fields.Selection([('allowance', 'Allowance'),('deduction', 'Deduction')], string="Type", default='allowance', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', company_dependent=True)
    account_debit = fields.Many2one('account.account', 'Debit Account', company_dependent=True, domain=[('deprecated', '=', False)])
    account_credit = fields.Many2one('account.account', 'Credit Account', company_dependent=True, domain=[('deprecated', '=', False)])
    not_computed_in_net = fields.Boolean(string="Not computed in net accountably", default=False, help='This field allows you to delete the value of this rule in the "Net Salary" rule at the accounting level to explicitly display the value of this rule in the accounting. For example, if you want to display the value of your representation fees, you can check this field.')

class PayslipOtherEarnings(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        for rec in self:
            map_earning_line_ids = self.env['other.earnings.line']
            earning_line_ids = self.env['other.earnings.line'].search([('employee_id', '=', rec.employee_id.id), ('date', '>=', rec.date_from), ('date', '<=', rec.date_to), ('earnings_line_id.state', '=', 'confirm'), ('is_payslip_created', '=', False)])
            map_earning_line_ids |= earning_line_ids
            before_earning_line_ids = self.env['other.earnings.line'].search([('employee_id', '=', rec.employee_id.id), ('date', '<=', rec.date_from), ('date', '<=', rec.date_to), ('earnings_line_id.state', '=', 'confirm'), ('is_payslip_created', '=', False)])
            map_earning_line_ids |= before_earning_line_ids
            if map_earning_line_ids:
                map_earning_line_ids.write({'is_payslip_created': True})
        return super(PayslipOtherEarnings, self).action_payslip_done()

    def action_payslip_cancel(self):
        rec = super(PayslipOtherEarnings, self).action_payslip_cancel()
        for rec in self:
            map_earning_line_ids = self.env['other.earnings.line']
            earning_line_ids = self.env['other.earnings.line'].search([('employee_id', '=', rec.employee_id.id),('earnings_line_id.state', '=', 'confirm'), ('is_payslip_created', '=', True)])
            map_earning_line_ids |= earning_line_ids
            line_ids = rec.input_line_ids.filtered(lambda x: x.is_other_earning)
            record_ids = map_earning_line_ids.filtered(lambda x: x.earnings_line_id.id in list(map(int, line_ids.mapped('ref'))))
            if record_ids:
                record_ids.write({'is_payslip_created': False})
        return rec

class HrContract(models.Model):
    _inherit = 'mail.mail'
    