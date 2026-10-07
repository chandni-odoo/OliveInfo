# -*- coding: utf-8 -*-
import calendar
import datetime
from datetime import  timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError,UserError
from dateutil.relativedelta import relativedelta
date_format = "%Y-%m-%d"

class AccountMove(models.Model):
    _inherit = 'account.move'

    other_settlement_id = fields.Many2one('other.settlements',string='Employee Settlement')

class HrLoan(models.Model):
    _inherit = 'hr.loan'

    emp_settlement_id = fields.Many2one('other.settlements', string='Employee Settlement')

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_salary_wages = fields.Boolean(string="Salaries and wages")

class EmployeeGratuity(models.Model):
    _inherit = 'hr.gratuity'

    employee_id = fields.Many2one('hr.employee', string='Employee')

    def action_open_settelement(self):
        return {
            'name': _('Settlements'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'other.settlements',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('gratuity_id', '=', self.id)],
        }

    def action_create_emp_settement(self):
        employee_id = self.employee_name.employee_id
        joined_date = employee_id.date_started
        notice_id = employee_id.notice_id
        settlement_id = self.env['other.settlements'].search([('gratuity_id', '=', self.id)], limit=1)
        if settlement_id:
            raise ValidationError(_('Employee settelement is already created'))
        journal_id = self.env['account.journal'].search([('is_salary_wages','=', True)], limit=1)
        end_date = fields.Date.today()
        if joined_date and notice_id:
            end_date = fields.Datetime.from_string(joined_date) + timedelta(days=notice_id.days)
        return {
                'name': "Create Employee Settlement",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'other.settlements',
                'view_id': self.env.ref('hr_resignation_settlement.other_settlements_form').id,
                'context': {
                    'default_from_gratuity': True,
                    'default_gratuity_id': self.id,
                    'default_employee_name': employee_id and employee_id.id, 
                    'default_reason': 'resign',
                    'default_notice_id' : notice_id and notice_id.id,
                    'default_joined_date': joined_date,
                    'default_last_date': end_date,
                    'default_journal_id': journal_id.id if journal_id else False
                },
        }

class HrLeaveBalance(models.Model):
    _name = 'hr.leave.balance'
    _description = "Hr Leave Balance"

    other_leave_id = fields.Many2one('other.settlements')
    other_input_type = fields.Many2one('hr.payslip.input.type')
    quantity = fields.Float(string="Quantity",default=1)
    description = fields.Char(string="Description")
    remarks = fields.Char(string="Remarks")
    amount = fields.Float(string="Amount")
    total = fields.Float(string="Total", compute="_compute_total")

    @api.depends('quantity','amount')
    def _compute_total(self):
        for record in self:
            record.total= record.quantity * record.amount

    def report_leave_data(self):
        if self.other_input_type:
            hr_leave_type = self.env['hr.leave.type'].search([('other_input_type', '=', self.other_input_type.id)])
            allocation_id =  self.env['hr.leave.allocation'].search([('holiday_status_id', 'in', hr_leave_type.ids), ('employee_id', '=', self.other_leave_id.employee_name.id)], limit=1)
        return allocation_id

class HrOtherGratuity(models.Model):
    _name = 'hr.other.gratuity'
    _description = "Other Settlements"

    description = fields.Char(string="Description")
    remarks = fields.Char(string="Remarks")
    other_input_type = fields.Many2one('hr.payslip.input.type')
    quantity = fields.Float(string="Quantity",default=1)
    amount = fields.Float(string="Amount")
    total = fields.Float(string="Total", compute="_compute_total")
    other_settlement_id = fields.Many2one('other.settlements')

    @api.depends('quantity','amount')
    def _compute_total(self):
        for record in self:
            record.total= record.quantity * record.amount

class HrOthersattlement(models.Model):
    _name = 'hr.other.statement'
    _description = "Hr Other Settlements"

    description = fields.Char(string="Description")
    remarks = fields.Char(string="Remarks")
    other_input_type = fields.Many2one('hr.payslip.input.type')
    quantity = fields.Float(string="Quantity",default=1)
    amount = fields.Float(string="Amount")
    total = fields.Float(string="Total", compute="_compute_total")
    other_settlement_id = fields.Many2one('other.settlements')

    @api.depends('quantity','amount')
    def _compute_total(self):
        for record in self:
            record.total= record.quantity * record.amount

class OtherSettlements(models.Model):
    _name = 'other.settlements'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Settlements"

    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validated'), ('approve', 'Approved'), ('cancel', 'Cancelled'), ('done', 'Done')], default='draft', track_visibility='onchange')
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_name = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_ids = fields.Many2many('hr.employee', compute="_compute_employee_ids")
    employee_dept = fields.Many2one('hr.department', string='Department')
    employee_job_id = fields.Many2one('hr.job', string='Job Tittle')
    gratuity_ids = fields.One2many('hr.other.gratuity', 'other_settlement_id')
    leave_ids = fields.One2many('hr.leave.balance', 'other_leave_id')
    other_sattlement_ids = fields.One2many('hr.other.statement', 'other_settlement_id')
    joined_date = fields.Date(string="Joined Date")
    last_date = fields.Date(string="Last Working Date")
    worked_years = fields.Integer(string="Service Duration")
    notice_id = fields.Many2one('notice.period', string="Notice Period")
    leave_balance = fields.Float(string="Leave Balance")
    notice_period_amount = fields.Float(string="Notice Period Amount")
    allowance = fields.Char(string="Dearness Allowance", default=0)
    total_payable_amount = fields.Float(string="Total Payable Amount", compute="_total_payable_amount")
    basic_salary = fields.Float(string="Basic Salary", required=True, default=0)
    net_amount = fields.Float(string="Net Amount", required=True, default=0)
    gross_amount = fields.Float(string="Gross Amount", required=True, default=0)
    last_month_salary = fields.Integer(string="Last Salary", required=True, default=0)
    gratuity_amount = fields.Integer(string="Gratuity Payable", required=True, default=0, readonly=True, help=("Gratuity is calculated based on the equation Last salary * Number of years of service * 15 / 26 "))
    type_of_contract = fields.Selection([('limited', 'Limited'), ('unlimited', 'Unlimited')], default='unlimited')
    reason = fields.Selection([('resign', 'Resignation'), ('terminate', 'Terminate'), ('retirement', 'Retirement')], default="retirement", string="Type of Sepration", required="True")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    request_date = fields.Date('Request Date', default=fields.date.today())
    journal_id = fields.Many2one('account.journal', string="Journal", required=True, domain="[('is_salary_wages', '=', True)]")
    gratuity_id = fields.Many2one('hr.gratuity', default=lambda self: self.env['hr.gratuity'].search([('employee_name.employee_id', '=', self.employee_name.id)], limit=1))
    remarks = fields.Text()
    branch_id = fields.Many2one('res.branch', related='employee_name.branch_id')
    leave_pay = fields.Float(string="Leave Pay")
    service_days = fields.Float(string="Service Days")
    unpaid_days = fields.Float('Unpaid Days', readonly=True)
    unpaid_days_amount = fields.Float('Unpaid Salary',readonly=True)
    revealing_date = fields.Date(string="Revealing Date")
    gross_salary = fields.Float(string="Gross Salary")
    payslip_ids = fields.Many2many('hr.payslip', string="Payslip")
    total_advance_salary = fields.Integer(string="Advance Salary", compute="_compute_total_advance_salary")
    absentees_count = fields.Float(string="Absent Days")
    unproductive_days = fields.Float(string="Unproductive Days")
    sum_unproductive_days = fields.Float(string="Total Unproductive Days")
    pending_salary = fields.Float(string="Previous Month Salary", readonly=True)
    payslip_count = fields.Integer(string="Payslip Count", readonly=True)
    hr_payslip_info = fields.Text(string="Payslip Info", readonly=True)
    advance_salary_ids = fields.One2many(
        'hr.loan', 
        'emp_settlement_id', 
        string='Advance Salary Entries',
        domain=[('types', '=', 'salary_advance')]
    )

    # def _compute_total_advance_salary(self):
    #     for vals in self:
    #         advance_entry_ids = self.env['hr.loan'].search([('emp_settlement_id', '=', self.id)])
    #         vals.total_advance_salary = len(advance_entry_ids)

    # def action_advance_salary(self):
    #     return {
    #         'name': _('Advance Payment'),
    #         'view_type': 'form',
    #         'view_mode': 'tree,form',
    #         'res_model': 'hr.loan',
    #         'view_id': False,
    #         'type': 'ir.actions.act_window',
    #         'domain': [('emp_settlement_id', '=', self.id)],
    #         'context': {'default_emp_settlement_id': self.id}
    #     }

    # def create_advance_entries(self):
    #     advance_entry_id = self.env['hr.loan'].search([('emp_settlement_id', '=', self.id)], limit=1)
    #     if not advance_entry_id:
    #         for payslip in self.payslip_ids:
    #             values = {
    #                 'emp_settlement_id': self.id,
    #                 'employee_id': payslip.employee_id.id,
    #                 'types': 'salary_advance',
    #                 'loan_amount': payslip.net_wage,
    #                 'date': payslip.date_to,
    #                 'payment_date': payslip.date_to
    #             }
    #             loan_id = self.env['hr.loan'].create(values)
    #             if loan_id:
    #                 loan_id.compute_installment()
    #     return advance_entry_id

    # def get_unpaid_emp_settlements(self):
    #     unpaid_days = 0.0
    #     unpaid_days_amount = 0.0
    #     if self.last_date:
    #         contract_id = self.env['hr.contract'].search([('employee_id', '=', self.employee_name.id), ('state', '=', 'open')], limit=1)
    #         if not contract_id:
    #             raise UserError(_('Employee does not have running contract'))
    #         if contract_id.net_amount <= 0:
    #             raise UserError(_('Contract net salary is zero'))
    #         date_from = fields.Date.from_string(self.last_date)
    #         total_month_days = calendar.monthrange(self.last_date.year, self.last_date.month)
    #         first_day_date = date_from.replace(day=1)
    #         if date_from and first_day_date:
    #             unpaid_days = abs((date_from - first_day_date).days)
    #         # self.unpaid_days = unpaid_days
    #         if unpaid_days > 0 and total_month_days:
    #             month_days = total_month_days[1]
    #             if month_days > 0:
    #                 unpaid_days_amount = (contract_id.net_amount / month_days) * unpaid_days
    #         # self.unpaid_days_amount =  unpaid_days_amount
    #     return unpaid_days, unpaid_days_amount

    # def get_unpaid_emp_settlements(self):
    #     """Calculate unpaid days and unpaid amount based on last working day of employee."""
    #     unpaid_days = 0.0
    #     unpaid_days_amount = 0.0

    #     if self.last_date:
    #         contract_id = self.env['hr.contract'].search([
    #             ('employee_id', '=', self.employee_name.id),
    #             ('state', '=', 'open')
    #         ], limit=1)

    #         if not contract_id:
    #             raise UserError(_('Employee does not have a running contract'))

    #         if contract_id.net_amount <= 0:
    #             raise UserError(_('Contract net salary is zero'))

    #         date_from = fields.Date.from_string(str(self.last_date))
    #         total_month_days = calendar.monthrange(self.last_date.year, self.last_date.month)
    #         first_day_date = date_from.replace(day=1)

    #         if date_from and first_day_date:
    #             unpaid_days = abs((date_from - first_day_date).days)

    #         if unpaid_days > 0 and total_month_days:
    #             month_days = total_month_days[1]
    #             if month_days > 0:
    #                 unpaid_days_amount = (contract_id.net_amount / month_days) * unpaid_days

    #     return unpaid_days, unpaid_days_amount

     # def create_advance_entries(self):
    #     """Create salary advance loan entry based on payslip amount."""
    #     advance_entry_id = self.env['hr.loan'].search([
    #         ('emp_settlement_id', '=', self.id)
    #     ], limit=1)

    #     if not advance_entry_id:
    #         for payslip in self.payslip_ids:
    #             values = {
    #                 'emp_settlement_id': self.id,
    #                 'employee_id': payslip.employee_id.id,
    #                 'types': 'salary_advance',
    #                 'loan_amount': payslip.net_wage,
    #                 'date': payslip.date_to,
    #                 'payment_date': payslip.date_to
    #             }
    #             loan_id = self.env['hr.loan'].create(values)
    #             if loan_id:
    #                 loan_id.compute_installment()
    #     return advance_entry_id

    def get_unpaid_emp_settlements(self):
        """Calculate unpaid days and unpaid amount based on last working day of employee."""
        self.ensure_one()
        unpaid_days = 0.0
        unpaid_days_amount = 0.0

        if self.last_date:
            contract_id = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_name.id),
                ('state', '=', 'open')
            ], limit=1)

            if not contract_id:
                raise UserError(_('Employee does not have a running contract'))

            if contract_id.net_amount <= 0:
                raise UserError(_('Contract net salary is zero'))

            # Calculate unpaid days from 1st of month to last_date
            date_from = fields.Date.from_string(str(self.last_date))
            first_day_date = date_from.replace(day=1)
            
            # Calculate days from 1st to last_date (inclusive)
            unpaid_days = (date_from - first_day_date).days + 1
            
            # Get total days in month
            month_days = calendar.monthrange(date_from.year, date_from.month)[1]
            
            if unpaid_days > 0 and month_days > 0:
                unpaid_days_amount = (contract_id.net_amount / month_days) * unpaid_days

        return unpaid_days, unpaid_days_amount
    
    def last_month_sal_cal(self):
        """Calculate previous month salary from paid/done payslips or use existing net_amount"""
        total_sal = 0.00
        psal_dic = {}
        
        for record in self:
            if record.last_date:
                # Calculate previous month dates
                previous_month_end = record.last_date.replace(day=1) - timedelta(days=1)
                previous_month_start = previous_month_end.replace(day=1)
                
                print("======Previous Month Calculation=======", previous_month_start, previous_month_end)
                
                # Find payslips for previous month that are in done/paid state
                hr_payslip_ids = self.env['hr.payslip'].search([
                    ('employee_id', '=', record.employee_name.id),
                    ('date_from', '>=', previous_month_start),
                    ('date_to', '<=', previous_month_end),
                    ('state', 'in', ('draft','verify'))
                ])
                
                print("============Found Payslips============", hr_payslip_ids)
                
                if hr_payslip_ids:
                    hr_ids = []
                    total_net_salary = 0.0
                    
                    for payslip in hr_payslip_ids:
                        hr_ids.append(payslip.id)
                        # Get NET salary from payslip lines
                        salary_line = payslip.line_ids.filtered(lambda x: x.salary_rule_id.code == 'NET')
                        if salary_line:
                            net_salary = salary_line.total
                            print("==========NET Salary from Payslip============", net_salary)
                            total_net_salary += net_salary
                            
                            # Store in dictionary for each payslip
                            psal_dic[payslip.id] = {
                                'pending_salary': net_salary,
                                'from_date': payslip.date_from.strftime("%d/%m/%Y"),
                                'to_date': payslip.date_to.strftime("%d/%m/%Y"),
                                'payslip_name': payslip.name,
                                'source': 'payslip'
                            }
                    
                    record.payslip_count = len(hr_payslip_ids)
                    record.hr_payslip_info = tuple(hr_ids)
                    total_sal = total_net_salary
                    
                else:
                    # No payslips found, use the existing net_amount field
                    total_sal = record.net_amount
                    print("==========Using Existing Net Amount============", total_sal)
                    
                    # Store contract info in dictionary
                    psal_dic[0] = {
                        'pending_salary': total_sal,
                        'from_date': previous_month_start.strftime("%d/%m/%Y"),
                        'to_date': previous_month_end.strftime("%d/%m/%Y"),
                        'payslip_name': 'Contract Net Amount',
                        'source': 'net_amount_field'
                    }
                    
                    record.payslip_count = 0
                    record.hr_payslip_info = tuple()
            
            record.pending_salary = total_sal
            print("==============Final Salary Details=============", psal_dic, total_sal)

        return psal_dic
    
    
    def create_current_month_advance(self):
        """Create advance salary for current month (month of last working date) using unpaid_days_amount or payslip net salary"""
        print('***create_current_month_advance***')
        
        for record in self:
            if record.last_date:
                # Get current month dates (month of last working date)
                current_month_start = record.last_date.replace(day=1)
                current_month_end = (current_month_start + relativedelta(months=1)) - timedelta(days=1)
                
                print('Current Month Period:', current_month_start, 'to', current_month_end)
                
                # Check if advance entry already exists for current month
                existing_advance = self.env['hr.loan'].search([
                    ('emp_settlement_id', '=', record.id),
                    ('date_from', '=', current_month_start),
                    ('date_to', '=', current_month_end)
                ])
                
                if existing_advance:
                    print("Current month advance entry already exists, skipping creation")
                    continue
                
                # Find payslips for current month
                current_month_payslip_ids = self.env['hr.payslip'].search([
                    ('employee_id', '=', record.employee_name.id),
                    ('date_from', '>=', current_month_start),
                    ('date_to', '<=', current_month_end),
                    ('state', 'in', ('draft', 'verify'))
                ])
                
                advance_amount = 0.0
                source_text = ""
                
                if current_month_payslip_ids:
                    # Use net salary from payslips
                    total_net_salary = 0.0
                    for payslip in current_month_payslip_ids:
                        salary_line = payslip.line_ids.filtered(lambda x: x.salary_rule_id.code == 'NET')
                        if salary_line:
                            total_net_salary += salary_line.total
                    
                    advance_amount = total_net_salary
                    source_text = "Payslips Net Salary"
                    print("==========Using Current Month Payslip Net Salary============", advance_amount)
                    
                else:
                    # Use unpaid_days_amount
                    unpaid_days, unpaid_days_amount = record.get_unpaid_emp_settlements()
                    advance_amount = unpaid_days_amount
                    source_text = f"Unpaid Days Amount ({unpaid_days} days)"
                    print("==========Using Unpaid Days Amount============", advance_amount)

                    # Automatically create missing payslip for current month
                    if advance_amount > 0:
                        try:
                            payslip_id = record.create_missing_payslip(
                                current_month_start, 
                                current_month_end, 
                                advance_amount
                            )
                            source_text += " (Payslip Created)"
                            print("============Auto-created Current Month Payslip============", payslip_id)
                        except Exception as e:
                            print(f"Failed to create current month payslip: {e}")
                
                # Create advance entry for current month
                if advance_amount > 0:
                    vals = {
                        'emp_settlement_id': record.id,
                        'employee_id': record.employee_name.id,
                        'types': 'salary_advance',
                        'loan_amount': advance_amount,
                        'date_from': current_month_start,
                        'date_to': current_month_end,
                        'date': record.last_date,
                        'name': f"Current Month Advance for {current_month_start.strftime('%B %Y')} ({source_text})"
                    }
                    advance_entry_id = self.env['hr.loan'].create(vals)
                    if advance_entry_id:
                        advance_entry_id.compute_installment()
                        print("============Current Month Advance Entry Created============", advance_entry_id)
        
        return True
    
    
    def create_advance_entries(self):
        """Create salary advance loan entries for both previous month and current month"""
        print('***create_advance_entries***')
        
        for record in self:
            # Check if any advance entry already exists
            existing_advance = self.env['hr.loan'].search([
                ('emp_settlement_id', '=', record.id)
            ])
            
            if existing_advance:
                print("Advance entries already exist, skipping creation")
                continue
                
            # Create advance for previous month (using existing logic)
            psal_dic = record.last_month_sal_cal()
            
            if record.last_date and record.pending_salary > 0:
                # Calculate previous month dates
                previous_month_end = record.last_date.replace(day=1) - timedelta(days=1)
                previous_month_start = previous_month_end.replace(day=1)
                
                print('Previous Month Period:', previous_month_start, 'to', previous_month_end)
                print('Pending Salary Amount:', record.pending_salary)
                
                # Create advance entry for the total previous month salary
                advance_entry_id = self.env['hr.loan'].search([
                    ('employee_id', '=', record.employee_name.id),
                    ('date_from', '=', previous_month_start),
                    ('date_to', '=', previous_month_end),
                    ('emp_settlement_id', '=', record.id)
                ], limit=1)
                
                print("============Existing Advance Entry============", advance_entry_id)
                
                if not advance_entry_id:
                    total_previous_salary = record.pending_salary
                    
                    if total_previous_salary > 0:
                        # Check if we used payslips or net_amount
                        used_net_amount = record.payslip_count == 0
                        source_text = "Contract Net Amount" if used_net_amount else "Payslips"
                        
                        vals = {
                            'emp_settlement_id': record.id,
                            'employee_id': record.employee_name.id,
                            'types': 'salary_advance',
                            'loan_amount': total_previous_salary,
                            'date_from': previous_month_start,
                            'date_to': previous_month_end,
                            'date': previous_month_end,
                            'name': f"Previous Month Advance for {previous_month_start.strftime('%B %Y')} ({source_text})"
                        }
                        advance_entry_id = self.env['hr.loan'].create(vals)
                        if advance_entry_id:
                            advance_entry_id.compute_installment()
                            print("============Previous Month Advance Entry Created============", advance_entry_id)
            
            # Create advance for current month (month of last working date)
            record.create_current_month_advance()
        
        return True
    
    def _compute_total_advance_salary(self):
        """Compute total advance salary for previous month payslips only"""
        for record in self:
            advance_entry_ids = self.env['hr.loan'].search([('emp_settlement_id', '=', record.id)])
            record.total_advance_salary = len(advance_entry_ids)

    def action_advance_salary(self):
        """Action to view advance salary entries"""
        return {
            'name': _('Advance Payment - Previous Month'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.loan',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('emp_settlement_id', '=', self.id)],
            'context': {'default_emp_settlement_id': self.id}
        }

    def action_open_payslip(self):
        """Action to view previous month payslips"""
        hr_ids = self.hr_payslip_info or ()
        return {
            'name': _('Previous Month Payslips'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.payslip',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('employee_id', '=', self.employee_name.id), 
                    ('state', 'in', ('draft','verify')), 
                    ('id', 'in', hr_ids)],
        }



    @api.model
    def default_get(self, field):
        result = super(OtherSettlements, self).default_get(field)
        result['employee_ids'] = self.env['hr.resignation'].search([('state', '=', 'approved')]).mapped('employee_id')
        return result

    def _compute_employee_ids(self):
        for rec in self:
            rec.employee_ids = self.env['hr.resignation'].search([('state', '=', 'approved')]).mapped('employee_id')

    @api.depends('gratuity_ids', 'leave_ids', 'notice_period_amount', 'other_sattlement_ids')
    def _total_payable_amount(self):
        for rec in self:
            gratual_amount = sum(rec.gratuity_ids.mapped('total'))
            leave_amount = sum(rec.leave_ids.mapped('total'))
            other_amount = sum(rec.other_sattlement_ids.mapped('total'))
            advance_salary_amount = sum(rec.payslip_ids.mapped('net_wage'))
            total = gratual_amount  + leave_amount + rec.notice_period_amount + other_amount + advance_salary_amount
            rec.total_payable_amount = total

    # assigning the sequence for the record
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('other.settlements')
        return super(OtherSettlements, self).create(vals)

    def fil_account_entries(self,line_ids):
        account_debit = {}
        account_credit = {}
        for rec in line_ids:
            debit_account = rec.other_input_type.account_debit
            credit_account = rec.other_input_type.account_credit
            if not debit_account or not credit_account:
                raise UserError(_('Please set credit and debit accounts for %s', rec.other_input_type.name))
            if debit_account:
                if debit_account.id not in account_debit:
                    account_debit[debit_account.id] = rec
                else:
                    account_debit[debit_account.id] |= rec

            if credit_account:
                if credit_account.id not in account_credit:
                    account_credit[credit_account.id] = rec
                else:
                    account_credit[credit_account.id] |= rec
        return account_credit,account_debit

    def create_extra_journal_entries(self):
        line_ids = []
        move_id = self.env['account.move'].search([('other_settlement_id', '=', self.id)], limit=1)
        if move_id:
            return True

        move_obj = self.env['account.move']
        amount = self.total_payable_amount
        employee_id = self.employee_name
        partner_id = employee_id.user_id.partner_id
        journal_id = self.journal_id
        timenow = fields.Date.today()
        company_id = self.env.user.company_id
        advance_credit_account_id = company_id.advance_credit_account_id
        advance_debit_account_id = company_id.advance_debit_account_id

        # main move
        move = {
            'ref': "%s - %s"%(employee_id.name, "Final Settlement"),
            'journal_id': journal_id and journal_id.id,
            'date': timenow,
            'state': 'draft',
            'other_settlement_id': self.id,
            'amount_total': amount,
            'move_type': 'entry',
            'branch_id': employee_id.branch_id.id,
        }

        # gratuty settelement
        gratuity_debit, gratuity_credit = self.fil_account_entries(self.gratuity_ids)
        for key, debit in gratuity_debit.items():
            total = sum(debit.mapped('total'))
            line_ids.append((0, 0, {
                'name': "%s - %s"%(employee_id.name, "Gratuity Settlement"),
                'partner_id': partner_id and partner_id.id,
                'employee_id': employee_id and employee_id.id,
                'account_id': key,
                'journal_id': journal_id.id,
                'date': timenow,
                'branch_id': employee_id.branch_id.id,
                'debit': total > 0.0 and total or 0.0,
                'credit': total < 0.0 and -total or 0.0,
            }))

        for key, credit in gratuity_credit.items():
            total = sum(credit.mapped('total'))
            line_ids.append((0, 0, {
                'name': "%s - %s"%(employee_id.name, "Gratuity Settlement"),
                'partner_id': partner_id and partner_id.id,
                'employee_id': employee_id and employee_id.id,
                'account_id': key,
                'journal_id': journal_id and journal_id.id,
                'date': timenow,
                'branch_id': employee_id.branch_id.id,
                'debit': total < 0.0 and -total or 0.0,
                'credit': total > 0.0 and total or 0.0,
            }))

        # leave settelement
        leaves_debit,leaves_credit = self.fil_account_entries(self.leave_ids)
        for key, debit in leaves_debit.items():
            total = sum(debit.mapped('total'))
            line_ids.append((0, 0, {
                'name': "%s - %s"%(employee_id.name, "Leave Settlement"),
                'partner_id': partner_id and partner_id.id,
                'employee_id': employee_id and employee_id.id,
                'account_id': key,
                'journal_id': journal_id.id,
                'date': timenow,
                'branch_id': employee_id.branch_id.id,
                'debit': total > 0.0 and total or 0.0,
                'credit': total < 0.0 and -total or 0.0,
            }))

        for key, credit in leaves_credit.items():
            total = sum(credit.mapped('total'))
            line_ids.append((0, 0, {
                'name': "%s - %s"%(employee_id.name, "Leave Settlement"),
                'partner_id': partner_id and partner_id.id,
                'employee_id': employee_id and employee_id.id,
                'account_id': key,
                'journal_id': journal_id and journal_id.id,
                'date': timenow,
                'branch_id': employee_id.branch_id.id,
                'debit': total < 0.0 and -total or 0.0,
                'credit': total > 0.0 and total or 0.0,
            }))

        # other settelement
        other_debit,other_credit = self.fil_account_entries(self.other_sattlement_ids)
        for key, debit in other_debit.items():
            total = sum(debit.mapped('total'))
            line_ids.append((0, 0, {
                'name': "%s - %s"%(employee_id.name, "Other Settlement"),
                'partner_id': partner_id and partner_id.id,
                'employee_id': employee_id and employee_id.id,
                'account_id': key,
                'journal_id': journal_id.id,
                'date': timenow,
                'branch_id': employee_id.branch_id.id,
                'debit': total > 0.0 and total or 0.0,
                'credit': total < 0.0 and -total or 0.0,
            }))
        for key, credit in other_credit.items():
            total = sum(credit.mapped('total'))
            line_ids.append((0, 0, {
                'name': "%s - %s"%(employee_id.name, "Other Settlement"),
                'partner_id': partner_id and partner_id.id,
                'employee_id': employee_id and employee_id.id,
                'account_id': key,
                'journal_id': journal_id and journal_id.id,
                'date': timenow,
                'branch_id': employee_id.branch_id.id,
                'debit': total < 0.0 and -total or 0.0,
                'credit': total > 0.0 and total or 0.0,
            }))
        move.update({'line_ids': line_ids})
        move_id = move_obj.create(move)
        self.write({'state': 'done'})

        #Payslip Journal Entry Create
        for payslip in self.payslip_ids:
            move_line_ids = []
            payslip_move = {
            'ref': "%s - %s"%(payslip.employee_id.name, "Payslip"),
            'journal_id': journal_id and journal_id.id,
            'date': timenow,
            'state': 'draft',
            'other_settlement_id': self.id,
            'move_type': 'entry',
            'branch_id': payslip.employee_id.branch_id.id,
            }

            # debit move lines
            move_line_ids.append((0, 0, {
                'name': "%s - %s"%(payslip.employee_id.name, "Payslip"),
                'partner_id': partner_id and partner_id.id,
                'employee_id': payslip.employee_id and payslip.employee_id.id,
                'account_id': advance_debit_account_id.id,
                'journal_id': journal_id.id,
                'date': timenow,
                'branch_id': payslip.employee_id.branch_id.id,
                'debit': payslip.net_wage > 0.0 and payslip.net_wage or 0.0,
                'credit': payslip.net_wage < 0.0 and -payslip.net_wage or 0.0,
            }))
            # credit move lines
            move_line_ids.append((0, 0, {
                'name': "%s - %s"%(payslip.employee_id.name, "Payslip"),
                'partner_id': partner_id and partner_id.id,
                'employee_id': payslip.employee_id and payslip.employee_id.id,
                'account_id': advance_credit_account_id.id,
                'journal_id': journal_id.id,
                'date': timenow,
                'branch_id': payslip.employee_id.branch_id.id,
                'debit': payslip.net_wage < 0.0 and -payslip.net_wage or 0.0,
                'credit': payslip.net_wage > 0.0 and payslip.net_wage or 0.0,
            }))
            payslip_move.update({'line_ids': move_line_ids})
            payslip_move_id = move_obj.create(payslip_move)
        return move_id

    def action_journal_entries(self):
        journal_ids = self.env['account.move'].search([('other_settlement_id', '=', self.id)])
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', journal_ids.ids)],
        }

    def validate_function(self):
        # calculating the years of work by the employee
        if self.employee_name:
            if not self.employee_name.active:
                raise ValidationError("Employee is already seprated from your organisation")
            self.write({'state': 'validate'})

    def approve_function(self):
        if not self.allowance.isdigit() :
            raise ValidationError(_('Allowance value should be numeric !!'))
        self.write({'state': 'approve'})
        amount = ((self.last_month_salary + int(self.allowance)) * int(self.worked_years) * 15) / 26
        self.gratuity_amount = round(amount) if self.state == 'approve' else 0
        self.employee_name.active = False

    def cancel_function(self):
        self.write({'state': 'cancel'})

    def draft_function(self):
        self.write({'state': 'draft'})

    def employee_based_on(self, employee):
        per_based_on = employee.per_based_on
        amount = 0.0
        if per_based_on == 'basic':
            amount = (self.basic_salary / 30) if self.basic_salary > 0 else 0
        if per_based_on == 'net':
            amount = (self.net_amount / 30) if self.net_amount > 0 else 0
        if per_based_on == 'gross':
             amount = (self.gross_amount / 30) if self.gross_amount > 0 else 0
        return amount

    # def compute_function(self):
    #     self.get_unpaid_emp_settlements()
    #     # self.create_advance_entries()
    #     if not self.env['hr.payslip.input.type'].search([('code', '=', 'gratuity')], limit=1):
    #         raise ValidationError(_('Please create other input type with code gratuity !!'))
    #     if not self.env['hr.payslip.input.type'].search([('code', '=', 'leave')], limit=1):
    #         raise ValidationError(_('Please create leave other input type with code leave !!'))
    #     # gratuity lines
    #     gratuity_data = [(5,0,0)]
    #     employee_gratuity = self.env['hr.gratuity'].search([('employee_name.employee_id', '=', self.employee_name.id), ('state', '=', 'approve')])
    #     for gratuity in employee_gratuity:
    #         gratuity_code = self.env['hr.payslip.input.type'].search([('code', '=', 'gratuity')], limit=1).id
    #         gratuity_data.append((0, 0, {
    #             'description': "Grauity for %s Days" %self.gratuity_id.eligible_days,
    #             'other_input_type': gratuity_code,
    #             'amount': gratuity.gratuity_amount,
    #         }))
    #     self.gratuity_ids = gratuity_data
    #     # leave settelement line
    #     leave_data = [(5,0,0)]
    #     # self.payslip_ids = [(5,0,0)]
    #     allocation_ids = self.env['hr.leave.allocation'].search([('employee_id', '=', self.employee_name.id), ('state', '=', 'validate')])
    #     time_off_ids = self.env['hr.leave'].search([('employee_id', '=', self.employee_name.id), ('state', '=', 'validate')])
    #     leave_type_ids = allocation_ids.mapped('holiday_status_id')
    #     per_based_on = self.employee_name.per_based_on
    #     amount = self.employee_based_on(self.employee_name)
    #     for leave_type in leave_type_ids:
    #         time_off_days = sum(time_off_ids.filtered(lambda x: x.holiday_status_id == leave_type).mapped('number_of_days'))
    #         total_allocation_days = sum(allocation_ids.filtered(lambda x: x.holiday_status_id == leave_type).mapped('number_of_days_display'))
    #         total_qty  = abs(total_allocation_days - time_off_days)
    #         leave_code = self.env['hr.payslip.input.type'].search([('code', '=', 'leave')], limit=1).id
    #         if total_qty > 0 and self.leave_pay > 0:
    #             leave_data.append((0, 0, {
    #                 'description': leave_type.name,
    #                 'other_input_type': leave_code,
    #                 'quantity': total_qty,
    #                 'amount': amount,
    #             }))
    #         self.leave_ids = leave_data
    #     amount = self.employee_based_on(self.employee_name)
    #     leave_balance = sum(self.leave_ids.mapped('quantity'))
    #     self.write({'leave_balance': leave_balance,})
    #     if self.service_days >= 365:
    #         leave_pay = leave_balance * amount
    #         self.write({'leave_pay': leave_pay})
    #     self.create_advance_entries()

    def compute_function(self):
        # self.get_unpaid_emp_settlements()
        for record in self:
        # Calculate unpaid days and amount
            unpaid_days, unpaid_amount = record.get_unpaid_emp_settlements()
            record.write({
                'unpaid_days': unpaid_days,
                'unpaid_days_amount': unpaid_amount
            })
            if not self.env['hr.payslip.input.type'].search([('code', '=', 'gratuity')], limit=1):
                raise ValidationError(_('Please create other input type with code gratuity !!'))

            if not self.env['hr.payslip.input.type'].search([('code', '=', 'leave')], limit=1):
                raise ValidationError(_('Please create leave other input type with code leave !!'))
            # Compute Absentees Count
            absents = self.env['hr.absentee'].search_count([
                ('employee_id', '=', self.employee_name.id)
            ])
            self.absentees_count = absents
            # 2. Compute Unproductive Days
            emp = self.employee_name
            gratuity_unproductive_days = emp.gratuity_unproductive_days or 0.0
            unpaid_leave_types = self.env['hr.leave.type'].search([
                ('name', '=ilike', 'Unpaid%') 
            ])
            unpaid_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'validate'),
                ('holiday_status_id', 'in', unpaid_leave_types.ids)
            ])
            all_validated_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'validate')
            ])
            unpaid_leave_days = sum(unpaid_leaves.mapped('number_of_days'))
            unpaid_days_field_sum = sum(leave.unpaid_days for leave in all_validated_leaves if leave.unpaid_days)
            total_unproductive_days = gratuity_unproductive_days + unpaid_leave_days + unpaid_days_field_sum
            self.unproductive_days = total_unproductive_days
            self.sum_unproductive_days = self.absentees_count + self.unproductive_days
            # 🟡 Gratuity Calculation
            gratuity_data = [(5, 0, 0)]
            employee_gratuity = self.env['hr.gratuity'].search([
                ('employee_name.employee_id', '=', self.employee_name.id),
                ('state', '=', 'approve')
            ])

            gratuity_code = self.env['hr.payslip.input.type'].search([
                ('code', '=', 'gratuity')
            ], limit=1).id

            for gratuity in employee_gratuity:
                gratuity_data.append((0, 0, {
                    'description': "Gratuity for %s Days" % self.gratuity_id.eligible_days,
                    'other_input_type': gratuity_code,
                    'amount': gratuity.gratuity_amount,
                }))

            self.gratuity_ids = gratuity_data
            leave_data = [(5, 0, 0)]
            allocation_ids = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', self.employee_name.id),
                ('state', '=', 'validate')
            ])
            time_off_ids = self.env['hr.leave'].search([
                ('employee_id', '=', self.employee_name.id),
                ('state', '=', 'validate')
            ])

            leave_type_ids = allocation_ids.mapped('holiday_status_id')
            amount = self.employee_based_on(self.employee_name)
            leave_code = self.env['hr.payslip.input.type'].search([
                ('code', '=', 'leave')
            ], limit=1).id

            for leave_type in leave_type_ids:
                time_off_days = sum(time_off_ids.filtered(lambda x: x.holiday_status_id == leave_type).mapped('number_of_days'))
                total_allocation_days = sum(allocation_ids.filtered(lambda x: x.holiday_status_id == leave_type).mapped('number_of_days_display'))
                total_qty = abs(total_allocation_days - time_off_days)
                if total_qty > 0:
                    leave_data.append((0, 0, {
                        'description': leave_type.name,
                        'other_input_type': leave_code,
                        'quantity': total_qty,
                        'amount': amount,
                    }))
            self.leave_ids = leave_data
            leave_balance = sum(self.leave_ids.mapped('quantity'))
            self.write({'leave_balance': leave_balance})
            if self.service_days >= 365:
                leave_pay = leave_balance * amount
                self.write({'leave_pay': leave_pay})
            self.last_month_sal_cal()
            self.create_advance_entries()



    @api.onchange('employee_name')
    def onchange_employee(self):
        if self.employee_name:
            employee_contract = self.env['hr.contract'].search([('employee_id', '=', self.employee_name.id), ('state', '=', 'open')], limit=1)
            if not employee_contract:
                raise ValidationError(("Employee %s does not have any running contract.") % (self.employee_name.name))
            journal_id = self.env['account.journal'].search([('is_salary_wages', '=', True), ('company_id', '=', self.employee_name.company_id.id)], limit=1)
            employee_gratuity = self.env['hr.gratuity'].search([('employee_name.employee_id', '=', self.employee_name.id), ('state', '=', 'approve')],limit=1)
            employee_payslip = self.env['hr.payslip'].search([('employee_id', '=', self.employee_name.id), ('state', '=', 'done')], limit=1)
            #leave calculation
            # allocation = self.env['hr.leave.allocation'].search([('employee_id', '=', self.employee_name.id), ('state', '=', 'validate')])
            # fil_allocation_rec_ids = allocation.mapped('number_of_days_display')
            # time_off = self.env['hr.leave'].search([('employee_id', '=', self.employee_name.id), ('state', '=', 'validate')])
            # fil_timeoff_rec_ids = time_off.filtered(lambda x: x.holiday_status_id.work_entry_type_id.is_paid).mapped('number_of_days')
            # total_duration = sum(fil_allocation_rec_ids) - sum(fil_timeoff_rec_ids)
            employee_resignation = self.env['hr.resignation'].search([('employee_id', '=', self.employee_name.id), ('state', '=', 'approved')], limit=1)
            if employee_resignation:
                self.reason = 'resign'
            # Assgin values
            self.notice_id = employee_resignation.notice_id.id
            self.last_month_salary = employee_gratuity.last_month_salary
            self.worked_years = employee_gratuity.worked_years
            self.employee_dept = self.employee_name.department_id and self.employee_name.department_id.id 
            self.employee_job_id = self.employee_name.job_id and self.employee_name.job_id.id 
            self.joined_date = self.employee_name.date_started
            self.basic_salary = employee_contract.wage
            self.net_amount = employee_contract.net_amount
            self.gross_amount = employee_contract.gross_amount
            # self.leave_balance = abs(total_duration)
            self.gratuity_id = employee_gratuity and employee_gratuity.id
            self.journal_id = journal_id and journal_id.id
            self.branch_id = self.employee_name.branch_id.id or False
            # amount = self.employee_based_on(self.employee_name)
            # self.leave_pay = self.leave_balance * amount
            self.service_days = employee_gratuity.total_days
            self.revealing_date = self.gratuity_id and self.gratuity_id.revealing_date
            self.gross_salary = employee_contract.gross_amount
            self.last_date = self.revealing_date - timedelta(days=1) if self.revealing_date else False
            payslip_ids = self.env['hr.payslip'].search([('employee_id', '=', self.employee_name.id), ('state', 'not in', ['done', 'paid', 'cancel'])])
            self.payslip_ids = payslip_ids.ids
            if self.payslip_ids:
                self.unpaid_days = sum(payslip_ids.mapped('attendance_days'))
                self.unpaid_days_amount = sum(payslip_ids.mapped('net_wage'))
            else:
                self.unpaid_days = 0
                self.unpaid_days_amount = 0


class Company(models.Model):
    _inherit = "res.company"

    advance_credit_account_id = fields.Many2one('account.account', string="Credit Account")
    advance_debit_account_id = fields.Many2one('account.account', string="Debit Account")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    advance_credit_account_id = fields.Many2one('account.account', related="company_id.advance_credit_account_id", string="Credit Account", readonly=False)
    advance_debit_account_id = fields.Many2one('account.account', related="company_id.advance_debit_account_id", string="Debit Account", readonly=False)
