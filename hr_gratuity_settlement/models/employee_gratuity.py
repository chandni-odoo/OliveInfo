# -*- coding: utf-8 -*-
from odoo import fields, models, api, exceptions, _
from odoo.exceptions import ValidationError, UserError
import datetime
from datetime import timedelta




class EmployeeGratuity(models.Model):
    _name = 'hr.gratuity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee Gratuity"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('validate', 'Validated'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled')],
        default='draft', track_visibility='onchange')
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_name = fields.Many2one('hr.resignation', string='Employee', required=True, domain="[('state', '=', 'approved')]")
    revealing_date = fields.Date(related='employee_name.expected_revealing_date')
    joined_date = fields.Date(string="Joined Date", readonly=True)
    worked_years = fields.Integer(string="Total Work Years", readonly=True)
    last_month_salary = fields.Integer(string="Last Basic Salary", default=0)
    allowance = fields.Char(string="Dearness Allowance", default=0)
    gratuity_amount = fields.Integer(string="Gratuity Payable", required=True, default=0,readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', 'Company',  default=lambda self: self.env.user.company_id)
    unproductive_days = fields.Float(default=0)
    total_days = fields.Integer('Service Days', default=0)
    eligible_days = fields.Integer('Eligible Days', default=0)
    absentees_count = fields.Float(string="Absent Days")
    sum_unproductive_days = fields.Float(string="Total Unproductive Days")

    # assigning the sequence for the record
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.gratuity')
        return super(EmployeeGratuity, self).create(vals)

    # Check whether any Gratuity request already exists
    @api.onchange('employee_name')
    @api.depends('employee_name')
    def check_request_existence(self):
        for rec in self.filtered(lambda x:x.employee_name):
            gratuity_request = self.env['hr.gratuity'].search([('employee_name', '=', rec.employee_name.id), ('state', 'in', ['draft', 'validate', 'approve'])])
            if gratuity_request:
                raise ValidationError(_('Gratuity request is already processed for this employee'))

    def _get_date_list(self):
        gratuity_date = self.env.company.gratuity_date
        if self.employee_id and self.employee_id.original_hire_date > self.env.company.gratuity_date:
            gratuity_date = self.employee_id.original_hire_date

        if not gratuity_date:
            raise ValidationError(_("Please set gratuity date in company."))
        if  gratuity_date and self.revealing_date:
            delta_date = self.revealing_date - gratuity_date
            all_days = [gratuity_date + timedelta(days=i) for i in range(delta_date.days + 1)]
            return all_days

    # def get_unproductive_days(self):
    #     unpaid_leave_days = 0.0
    #     for date in self._get_date_list():
    #         leave_domain = [
    #             ('state', '=', 'validate'),
    #             ('employee_id', '=', self.employee_name.employee_id.id),
    #             ('holiday_status_id.is_paid', '=', False), 
    #             ('holiday_status_id.work_entry_type_id.is_paid', '=', False),
    #             ('request_date_from', '<=', date),
    #             ('request_date_to', '>=', date),
    #         ]
    #         unpaid_leave_ids = self.env['hr.leave'].search(leave_domain)
    #         for rec in unpaid_leave_ids:
    #             unpaid_leave_days += 1
    #         attendance_ids = self.employee_name.employee_id.attendance_ids.filtered(lambda x: x.check_in.date() >= date and x.check_out.date() <= date)
    #         week_off_ids = self.employee_name.employee_id.dayofweek_ids.filtered(lambda x : x.date == date)
    #         public_holiday_ids = self.env['resource.calendar.leaves'].search([('date_from', '<=', date), ('date_to', '>=', date), ('resource_id', '=', False)])
    #         if not attendance_ids and not week_off_ids and not public_holiday_ids and not unpaid_leave_ids:
    #             unpaid_leave_days += 1
    #     return unpaid_leave_days

    def get_unproductive_days(self):
        # Compute Absentees Count
        absents = self.env['hr.absentee'].search_count([
            ('employee_id', '=', self.employee_name.employee_id.id)  # Fixed: use employee_id.id
        ])
        self.absentees_count = absents
        
        # Compute Unproductive Days
        emp = self.employee_name.employee_id  # Fixed: access the actual employee record
        gratuity_unproductive_days = emp.gratuity_unproductive_days or 0.0
        
        unpaid_leave_types = self.env['hr.leave.type'].search([
            ('name', '=ilike', 'Unpaid%')
        ])
        
        unpaid_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', emp.id),  # Fixed: use emp.id
            ('state', '=', 'validate'),
            ('holiday_status_id', 'in', unpaid_leave_types.ids)
        ])
        
        all_validated_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', emp.id),  # Fixed: use emp.id
            ('state', '=', 'validate')
        ])
        
        unpaid_leave_days = sum(unpaid_leaves.mapped('number_of_days'))
        unpaid_days_field_sum = sum(leave.unpaid_days for leave in all_validated_leaves if leave.unpaid_days)
        
        total_unproductive_days = gratuity_unproductive_days + unpaid_leave_days + unpaid_days_field_sum
        self.unproductive_days = total_unproductive_days
        self.sum_unproductive_days = self.absentees_count + self.unproductive_days
        
        return total_unproductive_days

    def validate_function(self):
        # calculating the years of work by the employee
        amount = 0.0
        # gratuity_unproductive_days = self.employee_name.employee_id.gratuity_unproductive_days
        unproductive_days = self.get_unproductive_days()
        worked_years = int(self.revealing_date.year) - int(self.joined_date.year)
        self.worked_years = worked_years
        # self.unproductive_days = unproductive_days + gratuity_unproductive_days
        self.total_days = ((self.revealing_date - self.joined_date).days)
        self.eligible_days = self.total_days - self.sum_unproductive_days

        employee_contract = self.env['hr.contract'].search([('employee_id', '=', self.employee_name.employee_id.id), ('state', '=', 'open')], limit=1)
        last_month_salary = employee_contract.wage
        allowance_amount = abs(sum(employee_contract.allowance_ids.mapped('amount')))

        if self.eligible_days < 365:
            self.last_month_salary = last_month_salary
            self.allowance = allowance_amount
            amount = 0

        if self.eligible_days >= 365 and self.eligible_days <= 1825:
            self.last_month_salary = last_month_salary
            self.allowance = allowance_amount
            amount = (self.last_month_salary * (12/365)) * ((21/365) * self.eligible_days) 

        if self.eligible_days > 1825:
            self.last_month_salary = last_month_salary
            self.allowance = allowance_amount
            more_then_five = worked_years - 5
            eligible_days = self.eligible_days - 1825
            less_five_amount = ((self.last_month_salary * (12/365)) * ((21/365 * 1825)))
            more_five_amount = ((self.last_month_salary * (12/365)) * (30/365 * eligible_days))
            amount = less_five_amount + more_five_amount

        self.gratuity_amount = round(amount)
        self.write({'state': 'validate'})

    def approve_function(self):
        self.write({'state': 'approve'})

    def cancel_function(self):
        self.write({'state': 'cancel'})

    def draft_function(self):
        self.write({'state': 'draft'})

    # assigning the join date of the selected employee
    @api.onchange('employee_name')
    def _on_change_employee_name(self):
        rec = self.env['hr.resignation'].search([['id', '=', self.employee_name.id]])
        if rec:
            self.joined_date = rec.joined_date

class Company(models.Model):
    _inherit = "res.company"

    gratuity_date = fields.Date(string="Gratuity Date")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gratuity_date = fields.Date(related="company_id.gratuity_date", string="Gratuity Date", readonly=False)

class HrResignation(models.Model):
    _inherit = 'hr.resignation'

    def action_create_emp_gratuity(self):
        employee_id = self.employee_id.id
        joined_date = self.joined_date
        return {
                'name': "Create Employee Gratuity",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'hr.gratuity',
                'view_id': self.env.ref('hr_gratuity_settlement.employee_gratuity_form').id,
                'context': {
                    'default_employee_name': self.id,
                    'default_reason': 'resign',
                    'default_joined_date': joined_date,
                },
        }