from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta


class DeductionType(models.Model):
    _name = "hr.employee.deduction.type"
    _description = "Deduction Type (Loan, Traffic Fine, etc.)"

    name = fields.Char(required=True)
    code = fields.Char(required=True, help="Code used in payroll rules")
    debit_account_id = fields.Many2one('account.account', string="Debit Account", required=True)
    credit_account_id = fields.Many2one('account.account', string="Credit Account", required=True)
    journal_id = fields.Many2one('account.journal', string="Journal", required=True)


class EmployeeDeduction(models.Model):
    _name = "hr.employee.deduction"
    _description = "Employee Deduction (Loan, Traffic Fine, etc.)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default='New')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, tracking=True)
    deduction_type_id = fields.Many2one('hr.employee.deduction.type', string="Deduction Type", required=True, tracking=True)
    total_amount = fields.Float(string="Total Amount", required=True, tracking=True)
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True, tracking=True)
    state = fields.Selection([('draft','Draft'), ('approved','Approved'), ('cancel','Cancelled')], string="Status", default='draft', tracking=True)
    installment_ids = fields.One2many('hr.employee.deduction.installment', 'deduction_id', string="Installments")
    journal_entry_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    amount_paid = fields.Float(string="Amount Paid", compute='_compute_amounts', store=True)
    amount_balance = fields.Float(string="Balance Amount", compute='_compute_amounts', store=True)
    no_of_installments = fields.Integer(
                    string="Number of Installments",
                    required=True,
                    tracking=True,
                )

    @api.depends('installment_ids.state', 'installment_ids.amount')
    def _compute_amounts(self):
        for rec in self:
            paid_installments = rec.installment_ids.filtered(lambda l: l.state == 'paid')
            rec.amount_paid = sum(paid_installments.mapped('amount'))
            draft_installments = rec.installment_ids.filtered(lambda l: l.state == 'draft')
            rec.amount_balance = sum(draft_installments.mapped('amount'))

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.employee.deduction') or 'New'
        return super(EmployeeDeduction, self).create(vals)
    
    def compute_installments(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft deductions can compute installments."))
        if not self.no_of_installments or self.no_of_installments <= 0:
            raise UserError(_("Please set a valid number of installments (must be greater than 0)."))
        if self.installment_ids:
            self.installment_ids.unlink()
        
        amount_per_installment = self.total_amount / self.no_of_installments
        installments = []
        start_date = self.date or fields.Date.context_today(self)
        
        for i in range(self.no_of_installments):
            due = start_date + relativedelta(months=i)  
            installments.append((0, 0, {
                'due_date': due,
                'amount': amount_per_installment,
                'state': 'draft'
            }))
        
        self.installment_ids = installments

    # def compute_installments(self):
    #     self.ensure_one()
    #     if self.state != 'draft':
    #         raise UserError(_("Only draft deductions can compute installments."))
    #     if self.installment_ids:
    #         self.installment_ids.unlink()
    #     # Simple equal installments in 3 months (can be changed)
    #     months = 3
    #     amount_per_installment = self.total_amount / months
    #     installments = []
    #     start_date = self.date or fields.Date.context_today(self)
    #     for i in range(months):
    #         due = start_date + relativedelta(months=i)
    #         installments.append((0, 0, {
    #             'due_date': due,
    #             'amount': amount_per_installment,
    #             'state': 'draft'
    #         }))
    #     self.installment_ids = installments

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_set_to_draft(self):
        self.write({'state': 'draft'})

    def action_create_journal_entry(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_("Only approved deductions can create journal entry."))
        if self.journal_entry_id:
            raise UserError(_("Journal entry already created."))

        journal = self.deduction_type_id.journal_id
        if not journal:
            raise UserError(_("Please configure Journal on Deduction Type."))
        debit_account = self.deduction_type_id.debit_account_id
        credit_account = self.deduction_type_id.credit_account_id
        if not debit_account or not credit_account:
            raise UserError(_("Please configure Debit and Credit accounts on Deduction Type."))

        move_vals = {
            'journal_id': journal.id,
            'date': self.date,
            'ref': self.name,
            'line_ids': [
                (0, 0, {
                    'account_id': debit_account.id,
                    'partner_id': self.employee_id.address_home_id.id,
                    'debit': self.total_amount,
                    'credit': 0.0,
                    'name': self.name,
                }),
                (0, 0, {
                    'account_id': credit_account.id,
                    'partner_id': self.employee_id.address_home_id.id,
                    'debit': 0.0,
                    'credit': self.total_amount,
                    'name': self.name,
                }),
            ]
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.journal_entry_id = move.id

    def action_open_journal_entry(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.journal_entry_id.id,
            'target': 'current',
        }
    

    def get_deduction_for_payslip(self, payslip):
        """Returns the deduction amount to be applied in the payslip"""
        self.ensure_one()
        due_installments = self.installment_ids.filtered(
            lambda i: i.state == 'draft' and 
                     i.due_date <= payslip.date_to and
                     i.due_date >= payslip.date_from
        )
        return sum(due_installments.mapped('amount'))




class EmployeeDeductionInstallment(models.Model):
    _name = "hr.employee.deduction.installment"
    _description = "Deduction Installment"

    deduction_id = fields.Many2one('hr.employee.deduction', string="Deduction", required=True, ondelete='cascade')
    due_date = fields.Date(string="Due Date", required=True)
    amount = fields.Float(string="Amount", required=True)
    state = fields.Selection([('draft', 'Draft'), ('paid', 'Paid')], string="Status", default='draft')
    payslip_id = fields.Many2one('hr.payslip', string="Payslip")

    def mark_as_paid(self, payslip_id):
        """Mark installment as paid and link to payslip"""
        self.write({
            'state': 'paid',
            'payslip_id': payslip_id
        })