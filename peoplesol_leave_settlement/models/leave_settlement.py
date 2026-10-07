from odoo import models, fields, api, _
from datetime import  timedelta, datetime,date
from odoo.exceptions import ValidationError, UserError
import calendar
import datetime
from ast import literal_eval as make_tuple
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class LeaveSettlement(models.Model):
    _name = "leave.settlement"
    _description = "Leave Settlement"
    _rec_name = "employee_id"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee')
    employee_ids = fields.Many2many('hr.employee', compute="_compute_employee_ids")
    job_title = fields.Char(required=True, related="employee_id.job_title")
    date = fields.Date(string = "Date", default=fields.date.today())
    date_to = fields.Date(string = "Date To", readonly=True)
    date_from = fields.Date(string = "Date From", readonly=True)
    leave_type_id = fields.Many2one('hr.leave.type')
    leave_type_ids = fields.Many2many('hr.leave.type', compute='_compute_leave_type_ids')
    per_based_on = fields.Selection([('basic', 'BASIC'), ('gross', 'GROSS'), ('net', 'NET')], string="Base On", default="basic")
    total_leaves = fields.Float('Total Leaves')
    accrued_leaves = fields.Float('Accrued Leaves', readonly=True)
    unpaid_days = fields.Float('Unpaid Days')
    unpaid_days_amount = fields.Float('Unpaid Salary')
    amount = fields.Float()
    branch_id = fields.Many2one('res.branch')
    settlement_ids = fields.One2many('leave.settlement.line','settlement_line_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string="State", default='draft')
    journal_count = fields.Integer('Journal Entries', compute="_get_leave_journal_count")
    journal_id = fields.Many2one('account.journal', domain="[('is_salary_wages', '=', True)]")
    loan_count = fields.Integer(compute='_compute_loan_count')
    extra_unpaid = fields.Float()
    basic_salary = fields.Float(string="Basic Salary", readonly=True)
    gross_salary = fields.Float(string="Gross Salary", readonly=True)
    net_salary = fields.Float(string="Net Salary", readonly=True)
    amount_total = fields.Float(string="Total Amount", compute="_compute_amount_total", store=True)
    remarks_of_leave = fields.Text()
    net_payable = fields.Float(string="Net Payable", compute="_compute_net_payable", store=True)
    advance_salary = fields.Float(string="Advance Salary")

    pending_salary = fields.Float(default=0)
    payslip_count = fields.Integer()
    hr_payslip_info = fields.Char()
    unpaid_month = fields.Float('Unpaid Month')
    unpaid_month_amount = fields.Float('Unpaid Month Salary')
    line_id_num = fields.Integer("settlement line id num")
    unpaid_prev_month_amount = fields.Float('Unpaid Salary')


    def fil_account_entries(self,line_ids):
        account_debit = {}
        account_credit = {}
        for rec in line_ids:
            debit_account = rec.payslip_inout_type_id.account_debit
            credit_account = rec.payslip_inout_type_id.account_credit
            if not debit_account or not credit_account:
                raise UserError(_('Please set credit and debit accounts for %s', rec.payslip_inout_type_id.name))
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
        move_obj = self.env['account.move']
        employee_id = self.employee_id
        partner_id = employee_id.user_id.partner_id
        journal_id = self.journal_id
        timenow = fields.Date.today()
        move = {
                'ref': "%s - %s"%(employee_id.name, "Settlement"),
                'journal_id': journal_id and journal_id.id,
                'date': timenow,
                'state': 'draft',
                'branch_id': employee_id.branch_id.id or False,
                'settlement_id': self.id,
            }
        leave_debit, leave_credit = self.fil_account_entries(self.settlement_ids)
        for key, debit in leave_debit.items():
            total = sum(debit.mapped('sub_total'))
            line_ids.append((0, 0, {
                'name': "%s - %s"%(employee_id.name, "Leave Settlement"),
                'partner_id': partner_id and partner_id.id,
                'employee_id': employee_id and employee_id.id,
                'account_id': key,
                'journal_id': journal_id.id,
                'date': timenow,
                'employee_id': self.employee_id.id,
                'debit': total > 0.0 and total or 0.0,
                'credit': total < 0.0 and -total or 0.0,
                'branch_id': employee_id.branch_id.id or False,

            }))
        for key, debit in leave_credit.items():
            total = sum(debit.mapped('sub_total'))
            line_ids.append((0, 0, {
                'name': "%s - %s"%(employee_id.name, "Leave Settlement"),
                'partner_id': partner_id and partner_id.id,
                'employee_id': employee_id and employee_id.id,
                'account_id': key,
                'journal_id': journal_id and journal_id.id,
                'date': timenow,
                'employee_id': self.employee_id.id,
                'debit': total < 0.0 and -total or 0.0,
                'credit': total > 0.0 and total or 0.0,
                'branch_id': employee_id.branch_id.id or False,
            }))
        move.update({'line_ids': line_ids})
        move_id = move_obj.create(move)
        return move_id

    @api.model
    def default_get(self, field):
        print('***default_get***')
        result = super(LeaveSettlement, self).default_get(field)
        print('result+_+_+_', result)
        # print('employee_ids+_+_+_', result['employee_ids'])
        print('data_from_leave+_+_+_', self.env['hr.leave'].search([('state', '=', 'validate')]).mapped('employee_id'))
        result['employee_ids'] = self.env['hr.leave'].search([('state', '=', 'validate')]).mapped('employee_id')
        return result

    def _compute_employee_ids(self):
        print('***_compute_employee_ids***')
        for rec in self:
            print('data_from_leave+_+_+_', self.env['hr.leave'].search([('state', '=', 'validate')]).mapped('employee_id'))
            rec.employee_ids = self.env['hr.leave'].search([('state', '=', 'validate')]).mapped('employee_id')

    def _compute_leave_type_ids(self):
        for rec in self:
            rec.leave_type_ids = self.env['hr.leave'].search([('employee_id', '=', rec.employee_id.id), ('holiday_status_id.is_paid', '=', True)]).mapped('holiday_status_id')

    @api.depends('settlement_ids.sub_total')
    def _compute_amount_total(self):
        for settlement in self:
            settlement.amount_total = sum(settlement.settlement_ids.mapped('sub_total'))

    @api.depends('amount_total', 'unpaid_days_amount')
    def _compute_net_payable(self):
        for settlement in self:
            print("============unpaid_prev_month_amount===============",settlement,settlement.unpaid_prev_month_amount)
            settlement.net_payable = settlement.amount_total + settlement.unpaid_days_amount + settlement.unpaid_prev_month_amount

    def _compute_loan_count(self):
        for settlement in self:
            settlement.loan_count = self.env['hr.loan'].search_count([('settlement_id', '=', settlement.id)])

    def _get_leave_journal_count(self):
        for rec in self:
            journal_ids = self.env['account.move'].search([('settlement_id', '=', rec.id)])
            rec.journal_count = len(journal_ids.ids)

    def leave_loan_amount(self):
        date_from = ''
        advance_start_date = ''
        advance_end_date = ''
        loan_dic = {}
        total_sal = 0.0
        leave_date = self.settlement_ids.filtered(lambda x: x.code == 'leave')
        if leave_date:
            for rec in leave_date:
                leave_date = rec.date_from
                get_leave_date = datetime.datetime.strptime(leave_date.strftime('%Y-%m-%d %H:%M:%S'), DEFAULT_SERVER_DATETIME_FORMAT)
                advance_start_date = get_leave_date.date().replace(day=1)
                advance_end_date = fields.Date.from_string(leave_date) + timedelta(days=-1)
                loan_ids = self.env['hr.loan'].search([('settlement_id', '=', self.id)])
                if loan_ids:
                    for loan in loan_ids:
                        loan_dic[loan] = {'loan_amount':loan.loan_amount,'qty':loan.unpaid_days,'date_from':loan.date_from,'date_to':loan.date_to,}
                if len(loan_dic)!=0:        
                    for index in loan_dic:
                        total_sal += loan_dic[index].get('loan_amount')
            self.pending_salary = total_sal
            print("==============pending_salary===============",self.pending_salary)
            return loan_dic

        else:
            return {'loan_amount': 0.0}

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('sequence.leave.sattlement')
        return super(LeaveSettlement, self).create(vals)

    def action_open_loan(self):
        return {
            'name': _('Advance Payment'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.loan',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('settlement_id', '=', self.id)],
        }

    def action_open_payslip(self):
        hr_ids = make_tuple(self.hr_payslip_info)
        return {
            'name': _('Pending Payment'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.payslip',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('employee_id', '=', self.employee_id.id),('state','in',('draft','verify')),('id','in',hr_ids)],
        }
    def action_journal_entries(self):
        journal_ids = self.env['account.move'].search([('settlement_id', '=', self.id)])
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', journal_ids.ids)],
        }

    def create_advance_entries(self):
        print('***create_advance_entries***')
        advance_entry_id = self.env['hr.loan']
        if self.unpaid_days_amount > 0:
            first_day = self.settlement_ids[0].date_from.replace(day=1)
            print('first_day+_+_+_', first_day)
            print('date_to+_+_+_', self.settlement_ids[0].date_from - timedelta(1))
            advance_entry_id = self.env['hr.loan'].search([('employee_id','=',self.employee_id.id),('date_from','=',first_day),('date_to','=',self.settlement_ids[0].date_from - timedelta(1))], limit=1)
            print("============settlement_id line============",self.settlement_ids[0],advance_entry_id,self.settlement_ids[0].date_from- timedelta(1))
            if not advance_entry_id:
                vals = {
                        'settlement_id': self.id,
                        'employee_id': self.employee_id.id,
                        'types': 'salary_advance',
                        'loan_amount': self.unpaid_days_amount,
                        'unpaid_days':self.unpaid_days,
                        'date_from':first_day,
                        'date_to':self.settlement_ids[0].date_from - timedelta(1),
                        'date':self.settlement_ids[0].date_from,
                        }
                advance_entry_id = self.env['hr.loan'].create(vals)
                if advance_entry_id:
                    advance_entry_id.compute_installment()
            return advance_entry_id

    def get_unpaid_settlement_leaves(self):
        print('***get_unpaid_settlement_leaves***')
        unpaid_days = 0.0
        unpaid_days_amount = 0.0
        pre_month_amount = 0.0
        settlement_ids = self.settlement_ids.filtered(lambda x: x.date_from)
        if settlement_ids:
            fil_date_from = min(settlement_ids.mapped('date_from'))
            contract_id = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('state', '=', 'open')], limit=1)
            if fil_date_from and contract_id:
                date_from = fields.Date.from_string(fil_date_from)
                total_month_days = calendar.monthrange(fil_date_from.year, fil_date_from.month)
                first_day = date_from.replace(day=1)
                month , year = (date_from.month-1,date_from.year) if date_from.month != 1 else (12,date_from.year-1)
                pre_month_date = date_from.replace(day=1,month = month,year = year)
                total_prev_days = calendar.monthrange(pre_month_date.year,pre_month_date.month)
                pay_month = date_from.month
                unpaid_month = 0
                last_day = pre_month_date.replace(day=total_prev_days[1])
                hr_payship_ids = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id)])
                print("============find============",hr_payship_ids,pay_month-1,contract_id,pre_month_date,total_prev_days,last_day)
                pending_payslip_id = hr_payship_ids.filtered(lambda x:x.date_from.month == pay_month-1 and x.date_from.year == date_from.year)
                print("===========pending_payslip_id================",pending_payslip_id)
                # erert
                if not pending_payslip_id:
                    unpaid_month = total_prev_days[1]
                    first_days = pre_month_date
                    # last_day = pre_month_date.replace(day=unpaid_month)
                    advance_entry_id = self.env['hr.loan'].search([('employee_id','=',self.employee_id.id),('date_from','=',first_days),('date_to','=',last_day)])

                    print("==========pending_payslip_id============",pending_payslip_id,unpaid_month,first_days,last_day,advance_entry_id,date_from)
                    if contract_id.net_amount > 0 and not advance_entry_id:
                        pre_unpaid_days_amount = contract_id.net_amount
                        pre_month_amount = contract_id.net_amount
                        self.unpaid_prev_month_amount = contract_id.net_amount
                        vals = {
                        'settlement_id': self.id,
                        'employee_id': self.employee_id.id,
                        'types': 'salary_advance',
                        'loan_amount': pre_unpaid_days_amount,
                        'date':last_day,
                        'date_from':first_days,
                        'date_to':last_day,
                        'unpaid_days':unpaid_month,
                        }
                        print("============vals=============",vals)
                        adv_entry_id = self.env['hr.loan'].create(vals)
                        if adv_entry_id:
                            adv_entry_id.compute_installment()
                if pending_payslip_id.state != 'done' and pending_payslip_id:
                    # advance_entry_count = 0
                    # print("=============len===========",len(advance_entry_id))
                    # if pending_payslip_id:
                    total_pre_month_days = calendar.monthrange(pending_payslip_id.date_from.year,pending_payslip_id.date_from.month)
                    self.unpaid_month = total_pre_month_days[1]
                    advance_entry_id = self.env['hr.loan'].search([('employee_id','=',self.employee_id.id),('date_from','=',pending_payslip_id.date_from),('date_to','=',pending_payslip_id.date_to)], limit=1)
                    # advance_entry_count = len(advance_entry_id)
                    if contract_id.net_amount > 0 and not advance_entry_id:
                        pre_unpaid_days_amount = contract_id.net_amount
                        pre_month_amount = contract_id.net_amount
                        self.unpaid_prev_month_amount = contract_id.net_amount

                        vals = {
                        'settlement_id': self.id,
                        'employee_id': self.employee_id.id,
                        'types': 'salary_advance',
                        'loan_amount': pre_unpaid_days_amount,
                        'date':last_day,
                        'date_from':pending_payslip_id.date_from ,
                        'date_to':pending_payslip_id.date_to,
                        'unpaid_days':self.unpaid_month,
                        }
                        print("============vals=============",vals)
                        adv_entry_id = self.env['hr.loan'].create(vals)
                        if adv_entry_id:
                            adv_entry_id.compute_installment()
                if date_from and first_day:
                    unpaid_days = abs((first_day - date_from).days)
                    self.unpaid_days = unpaid_days
                if contract_id.net_amount > 0 and unpaid_days > 0 and total_month_days:
                    month_days = total_month_days[1]
                    unpaid_days_amount = (contract_id.net_amount / month_days) * unpaid_days
                    self.write({'unpaid_days_amount': unpaid_days_amount, 'advance_salary': unpaid_days_amount + pre_month_amount})
        return unpaid_days, unpaid_days_amount

    def action_compute(self):
        print('***action_compute***')
        line_ids = []
        if self.employee_id:
            employee_id = self.employee_id
            partner_id = employee_id.user_id.partner_id
            journal_id = self.journal_id
            timenow = fields.Date.today()
            self.create_advance_entries()
            self.compute_leave_settelement()
            self.leave_sattlement_line()
            self.get_unpaid_settlement_leaves()
            if self.state == 'done':
                move_id = self.env['account.move'].search([('settlement_id', '=', self.id)], limit=1)
                if move_id:
                    move_id.line_ids = [(5,0,0)]
                    leave_compute_debit, leave_compute_credit = self.fil_account_entries(self.settlement_ids)
                    for key, debit in leave_compute_debit.items():
                        total = sum(debit.mapped('sub_total'))
                        line_ids.append((0, 0, {
                            'name': "%s - %s"%(employee_id.name, "Leave Settlement"),
                            'partner_id': partner_id and partner_id.id,
                            'employee_id': employee_id and employee_id.id,
                            'account_id': key,
                            'journal_id': journal_id.id,
                            'date': timenow,
                            'employee_id': self.employee_id.id,
                            'debit': total > 0.0 and total or 0.0,
                            'credit': total < 0.0 and -total or 0.0,

                        }))
                    for key, debit in leave_compute_credit.items():
                        total = sum(debit.mapped('sub_total'))
                        line_ids.append((0, 0, {
                            'name': "%s - %s"%(employee_id.name, "Leave Settlement"),
                            'partner_id': partner_id and partner_id.id,
                            'employee_id': employee_id and employee_id.id,
                            'account_id': key,
                            'journal_id': journal_id and journal_id.id,
                            'date': timenow,
                            'employee_id': self.employee_id.id,
                            'debit': total < 0.0 and -total or 0.0,
                            'credit': total > 0.0 and total or 0.0,
                        }))
                    move_id.write({'line_ids': line_ids})

    def total_amount(self):
        contract_id = self.employee_id.contract_id
        self.branch_id = self.employee_id.branch_id and self.employee_id.branch_id.id
        if self.per_based_on == 'basic':
            amount = (contract_id.wage)
        elif self.per_based_on == 'gross':
            amount = (contract_id.gross_amount)
        else:
            amount = (contract_id.net_amount)
        self.amount = amount / 30

    @api.onchange('per_based_on', 'employee_id')
    def onchange_leave_type_ids(self):
        amount = 0.0
        if self.per_based_on and self.employee_id:
            self.total_amount()

    #create sattlement line form leave
    def leave_sattlement_line(self):
        print('***leave_sattlement_line***')
        self.total_amount()
        total_leaves = 0.0
        unpaid_days = 0.0
        settlement_lines = [(5,0,0)]
        leave_ids = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id), ('state', "=", 'validate')])
        fil_leave_ids = leave_ids.filtered(lambda x: x.holiday_status_id.is_paid and x.leave_sattlement_done != True)
        encashment_leave_ids = fil_leave_ids.filtered(lambda x:x.holiday_status_id and x.is_leave_sattlement and x.encashment_days > 0)
        additional_leave_ids = leave_ids.filtered(lambda x:x.holiday_status_id and x.is_additional_leave and x.paid_days > 0)
        unpaid_leave_ids = leave_ids.filtered(lambda x:x.holiday_status_id and x.is_additional_leave and x.unpaid_days > 0)
        unpaid_days = sum(unpaid_leave_ids.mapped('unpaid_days'))
        if leave_ids:
            total_leaves = sum(leave_ids.mapped('number_of_days'))
        self.total_leaves = total_leaves
        for rec in fil_leave_ids:
            other_input_type = rec.holiday_status_id.other_input_type
            if not other_input_type:
                raise ValidationError(_('Other input for leave type %s not define')% rec.holiday_status_id.name)
            settlement_lines.append((0, 0, {
                'payslip_inout_type_id': other_input_type.id,
                'date_from': rec.date_from,
                'date_to': rec.date_to,
                'duration_qty': rec.number_of_days,
                'remarks': rec.holiday_status_id.name,
                'amount': self.amount,
                'is_compute': True,
                'leave_id': rec.id
            }))

        for encashment in encashment_leave_ids:
            other_input_type = encashment.holiday_status_id.other_input_type
            if not other_input_type:
                raise ValidationError(_('Other input for leave type %s not define')% encashment.holiday_status_id.name)
            settlement_lines.append((0, 0, {
                'payslip_inout_type_id': other_input_type.id,
                'date_from': encashment.request_date_from,
                'date_to': encashment.request_date_to,
                'duration_qty': encashment.encashment_days,
                'remarks': 'Encashment Days for %s days' % encashment.encashment_days,
                'amount': self.basic_salary/30 if self.basic_salary > 0 else 0.0,
                'is_compute': True,
                'is_encashment': True
            }))

        for additional in additional_leave_ids:
            other_input_type = additional.holiday_status_id.other_input_type
            if not other_input_type:
                raise ValidationError(_('Other input for leave type %s not define')% additional.holiday_status_id.name)
            settlement_lines.append((0, 0, {
                'payslip_inout_type_id': other_input_type.id,
                'date_from': additional.request_date_from,
                'date_to': additional.request_date_to,
                'duration_qty': additional.paid_days,
                'remarks': 'Additional Paid Days for %s days' % additional.paid_days,
                'amount': self.amount,
                'is_compute': True,
                'is_paid': True
            }))

        fil_settlement_line = self.settlement_ids.filtered(lambda x: not x.is_compute and x.payslip_inout_type_id)
        for rec in fil_settlement_line:
            other_input_type = rec.payslip_inout_type_id
            settlement_lines.append((0, 0, {
                'payslip_inout_type_id': other_input_type.id,
                'date_from': rec.date_from,
                'date_to': rec.date_to,
                'duration_qty': rec.duration_qty,
                'remarks': rec.payslip_inout_type_id.name,
                'amount': self.amount,
                # 'levae_type_id': rec.payslip_inout_type_id.id,
            }))
        self.write({'settlement_ids': settlement_lines, 'extra_unpaid': unpaid_days})

    def compute_leave_settelement(self):
        print('***compute_leave_settelement***')
        if self.employee_id:
            self.per_based_on = self.employee_id.per_based_on
            contract_id = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id),('state', '=', 'open')], limit=1)
            print('contract_id+_+_+_', contract_id)
            if not contract_id:
                raise ValidationError(_('contract not found in running state'))
            self.gross_salary = contract_id.gross_amount
            self.net_salary = contract_id.net_amount
            self.basic_salary = contract_id.wage

            print('gross_salary+_+_+_', contract_id.gross_amount)
            print('net_salary+_+_+_', contract_id.net_amount)
            print('basic_salary+_+_+_', contract_id.wage)

            allocation_ids = self.env['hr.leave.allocation'].search([('employee_id', '=', self.employee_id.id),('state', "=", 'validate')])
            fil_allocation_ids = allocation_ids.filtered(lambda x: x.holiday_status_id.is_paid)
            max_fil_allocation_ids = fil_allocation_ids.filtered(lambda x: x.date_to)
            min_fil_allocation_ids = fil_allocation_ids.filtered(lambda x: x.date_from)
            if fil_allocation_ids:
                self.accrued_leaves = sum(fil_allocation_ids.mapped('number_of_days_display'))
            print('min_fil_allocation_ids+_+_+_+_', min_fil_allocation_ids)
            if min_fil_allocation_ids:
                print('date_from+_+_+_+_', min_fil_allocation_ids.mapped('date_from'))
                self.date_from = min(min_fil_allocation_ids.mapped('date_from'))
            print('max_fil_allocation_ids+_+_+_+_', max_fil_allocation_ids)
            if max_fil_allocation_ids:
                print('date_to+_+_+_+_', max_fil_allocation_ids.mapped('date_to'))
                self.date_to = max(max_fil_allocation_ids.mapped('date_to'))

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        print('***_onchange_employee_id***')
        amount = 0.0
        self.journal_id = self.env['account.journal'].search([('is_salary_wages', '=', True), ('company_id', '=', self.employee_id.company_id.id)], limit=1)
        self.branch_id = self.employee_id.branch_id and self.employee_id.branch_id.id
        leave_type_ids = []
        self.leave_type_id = False
        if self.employee_id:
            leave_type_ids = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id), ('holiday_status_id.is_paid', '=', True)]).mapped('holiday_status_id').ids
        return {'domain': {'leave_type_id': [('id', 'in', leave_type_ids)]}}

    # @api.onchange('leave_type_id')
    # def _onchange_leave_type_id(self):
    #     if self.employee_id:
    #         self.leave_sattlement()


    def action_confirm(self):
        if not self.settlement_ids:
            raise UserError(_('There is no leave settlement to be submitted'))
        if not self.employee_id.contract_id.state == 'open':
            raise ValidationError(_('Please Select Employee Running Contracts.'))
        self.write({'state': 'confirm'})

    def action_done(self):
        if self.settlement_ids:
            for rec in self.settlement_ids:
                if rec.leave_id:
                    rec.leave_id.write({'leave_sattlement_done': True})
        journal_entry_id = self.env['account.move'].search([('settlement_id', '=', self.id)], limit=1)
        if not journal_entry_id:
            # self.create_extra_journal_entries()
            self.write({'state': 'done'})


    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        if self.settlement_ids:
            for rec in self.settlement_ids:
                if rec.leave_id:
                    rec.leave_id.write({'leave_sattlement_done': False})
        self.write({'state': 'draft'})

    # @api.constrains('employee_id' , 'date_from', 'date_to')
    # def check_leave_type_id(self):
    #     print('***check_leave_type_id***')
    #     print('self+_+_+_', self)
    #     for rec in self:
    #         print('employee_id+_+_+_+_', rec.employee_id)
    #         print('leave_type_id+_+_+_', rec.leave_type_id)
    #         print('date_from+_+_+_', rec.date_from)
    #         print('date_to+_+_+_+_', rec.date_to)
    #         record = self.env['leave.settlement'].search([('employee_id', '=', rec.employee_id.id),('date_from', '=', rec.date_from), ('date_to', '=', rec.date_to)])
    #         print('record+_+_+_+_', record)
    #         if len(record) > 1:
    #             raise ValidationError(_("You can not duplicate with same leave type and date records"))

    def last_month_sal_cal(self):
        total_sal = 0.00
        psal_dic = {}
        for rec in self.settlement_ids.filtered(lambda x:x.date_to and x.date_from.strftime("%d")=='01' and x.code == 'leave'):
            # if rec.date_from.strftime("%d")=="01":
            pay_month = rec.date_from.month
            print("======come============",type(rec.date_from.strftime("%d")),pay_month,rec)
            hr_payship_ids = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),('state','in',('verify','draft'))])
            print("============find============",hr_payship_ids,pay_month-1)
            # for hr_payship_id in hr_payship_ids:
            #     if hr_payship_id.date_from.month == pay_month-1:
            lst_mnth_sal = hr_payship_ids.filtered(lambda x:x.date_from.month == pay_month-1)
            print("=============lst_mnth_sal=========",len(lst_mnth_sal),lst_mnth_sal)
            if len(lst_mnth_sal) !=0:
                hr_ids = []
                # for ui in lst_mnth_sal:
                hr_ids.append(lst_mnth_sal.id)
                salary = lst_mnth_sal.line_ids.filtered(lambda x:x.salary_rule_id.code == 'NET')
                if salary:
                    print("==========salary============",salary,salary.total)
                    # lst_mnth_sal.action_payslip_done()
                    # lst_mnth_sal.action_payslip_paid()
                    print("==========salary============",salary,salary.total)
                # self.pending_salary = salary.total
                # self.pending_salary += salary.total

                self.payslip_count = len(lst_mnth_sal)
                self.hr_payslip_info = tuple(hr_ids)
                psal_dic[rec] = {'pending_salary':salary.total,'from_date':lst_mnth_sal.date_from.strftime("%d/%m/%Y"),'to_date':lst_mnth_sal.date_to.strftime("%d/%m/%Y"),'rec_name':rec}
        if len(psal_dic)!=0:        
            for index in psal_dic:
                print("===========sal=============",psal_dic[index].get('pending_salary'))
                total_sal += psal_dic[index].get('pending_salary')
            self.pending_salary = total_sal
            print("==============psal_dic=============",psal_dic,total_sal)

        return psal_dic


class LeaveSettlementLine(models.Model):
    _name = "leave.settlement.line"
    _description = "Leave Settlement Line"

    payslip_inout_type_id = fields.Many2one('hr.payslip.input.type', 'Description', required=True)
    code = fields.Char('Code', readonly=True, related="payslip_inout_type_id.code")
    date_from = fields.Datetime()
    date_to = fields.Datetime()
    remarks = fields.Char('Remarks')
    duration = fields.Char(string="Qty")
    qty = fields.Float(string="Qty", default=1.0)
    duration_qty = fields.Float(string="Duration", default=1.0)
    settlement_line_id = fields.Many2one('leave.settlement')
    amount = fields.Float()
    sub_total = fields.Float(compute="_compute_sub_total", store=True)
    is_compute = fields.Boolean()
    is_encashment = fields.Boolean()
    is_paid = fields.Boolean()
    leave_id = fields.Many2one('hr.leave')
    levae_type_id = fields.Many2one('hr.leave.type')
    eligibility_days = fields.Float('Eligibility Days', compute='_compute_leave_eligibility_days', store=True)


    @api.depends('date_from', 'date_to', 'code')
    def _compute_leave_eligibility_days(self):
        for rec in self.filtered(lambda x:x.date_to and x.date_from and x.code == 'leave'):
            start_date = datetime.datetime.strptime(rec.date_from.strftime('%Y-%m-%d %H:%M:%S'), DEFAULT_SERVER_DATETIME_FORMAT)
            end_date = datetime.datetime.strptime(rec.date_to.strftime('%Y-%m-%d %H:%M:%S'), DEFAULT_SERVER_DATETIME_FORMAT)
            difference = end_date - start_date
            if difference:
                number_of_days = abs(difference.days + 1)
                rec.eligibility_days = number_of_days



                    

    @api.depends('duration_qty', 'amount')
    def _compute_sub_total(self):
        for amnt in self:
            sub_total_amnt = 0.0
            sub_total_amnt =  float(amnt.duration_qty) * amnt.amount
            amnt.sub_total = sub_total_amnt

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    month_num = fields.Integer(string="Payslip Month")

#     def action_payslip_done(self):
#         print("=========my action_payslip_done call==============",self)
#         res = super(HrPayslip, self).action_payslip_done()
#         return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    settlement_id = fields.Many2one('leave.settlement')

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    is_leave_sattlement = fields.Boolean(related="holiday_status_id.is_paid", store=True)
    encashment_days = fields.Float(string="Encashment Days")
    is_additional_leave = fields.Boolean(related="holiday_status_id.is_additional_leave", store=True)
    paid_days = fields.Float(string="Paid Days")
    unpaid_days = fields.Float(string="Unpaid Days")
    leave_sattlement_done = fields.Boolean(string="Leave Sattlement Done")

    def action_refuse(self):
        res = super(HrLeave, self).action_refuse()
        encashment_line_ids = self.env['hr.leave.allocation.lines'].search([('leave_id', '=', self.id), ('holiday_status_id', '=', self.holiday_status_id.id)])
        for encashment_line in encashment_line_ids: 
            encashment_line.allocation_id.number_of_days += encashment_line.encashment_days
            encashment_line.unlink()
        return res
    
    def action_validate(self):
        if self.is_leave_sattlement:
            allocation_ids = self.env['hr.leave.allocation'].search([('employee_id', '=', self.employee_id.id), ('holiday_status_id', '=', self.holiday_status_id.id), ('state', '=', 'validate')])
            for allocation in allocation_ids:
                encash_taken_days = sum(allocation.mapped('enchasement_line_ids').mapped('encashment_days'))
                leaves_taken_days  = sum(allocation.mapped('leaves_taken'))
                left_days = allocation.number_of_days - (encash_taken_days + leaves_taken_days)
                encashment_days = self.encashment_days
                if encashment_days > 0 and left_days >= encashment_days:
                    allocation.number_of_days -= encashment_days
                allocation.enchasement_line_ids = [(0, 0, {
                    'allocation_id': allocation.id,
                    'leave_id': self.id,
                    'leave_days': self.number_of_days,
                    'user_id': self.env.user.id,
                    'holiday_status_id': self.holiday_status_id.id,
                    'date_from': self.date_from,
                    'date_to': self.date_to,
                    'description':self.name,
                    'encashment_days': encashment_days if left_days >= encashment_days else 0,
                })]
        return super(HrLeave, self).action_validate()

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_salary_wages = fields.Boolean(string="Salaries and wages")

class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'
    _description ="Leave Type"

    is_additional_leave = fields.Boolean(string="Additional Leave")

class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    enchasement_line_ids = fields.One2many('hr.leave.allocation.lines', 'allocation_id')

class HrLeaveAllocation(models.Model):
    _name = 'hr.leave.allocation.lines'
    _description = "Hr Leave Allocation Line"

    allocation_id = fields.Many2one('hr.leave.allocation')
    user_id = fields.Many2one('res.users', string='User')
    description = fields.Char(string='Description')
    leave_id = fields.Many2one('hr.leave', string="Leave")
    leave_days = fields.Float(string="Leave Days")
    holiday_status_id = fields.Many2one('hr.leave.type', string="Time Off Type")
    date = fields.Date(string="Create Date", default=fields.Date.today())
    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="From To")
    encashment_days = fields.Float(string="Encashment Days")
