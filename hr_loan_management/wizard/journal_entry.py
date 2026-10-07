from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class JournalEntryWizard(models.Model):
    _name = "journal.entry.wizard"

    journal_id = fields.Many2one('account.journal', string="Journal", required=True, domain="[('is_salary_wages', '=', True)]")
    credit_account_id = fields.Many2one('account.account')
    debit_account_id = fields.Many2one('account.account')
    employee_id = fields.Many2one('res.partner', string="Partner")
    emp_partner_id = fields.Many2one('hr.employee', string="Employee")

    @api.model
    def default_get(self,fields):
        res = super(JournalEntryWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        company_id = self.env.user.company_id
        if active_id:
            loan_id = self.env['hr.loan'].browse(active_id)
            journal_id = self.env['account.journal'].search([('is_salary_wages', '=', True), ('company_id', '=', loan_id.employee_id.company_id.id)], limit=1)
            res.update({
                'emp_partner_id': loan_id and loan_id.employee_id.id or False,
                'credit_account_id': company_id.credit_account_id.id or False,
                'debit_account_id': company_id.debit_account_id.id or False,
                'journal_id': loan_id.settlement_id.journal_id.id or False,
                })
        return res

    def create_extra_journal_entries(self):
        active_id = self.env.context.get('active_id')
        move_obj = self.env['account.move']
        line_ids = []
        if active_id:
            loan = self.env['hr.loan'].browse(active_id)
            total_amount = loan.total_amount
            for rec in self:
                line_ids = []
                partner_id = loan.employee_id.user_id.partner_id if loan.employee_id.user_id else False
                journal_id = self.journal_id
                timenow = loan.date
                move = {
                    'ref': "%s - %s"%(loan.employee_id.name, loan.name),
                    'journal_id': journal_id.id,
                    'date': timenow,
                    'state': 'draft',
                    'loan_id': loan.id,
                    'branch_id': loan.employee_id.branch_id.id,
                }
                if self.debit_account_id:
                    debit_line = (0, 0, {
                        'employee_id': loan.employee_id.id or False,
                        'partner_id': partner_id and partner_id.id,
                        'account_id': self.debit_account_id.id,
                        'journal_id': journal_id.id,
                        'date': timenow,
                        'branch_id': loan.employee_id.branch_id.id,
                        'debit': total_amount > 0.0 and total_amount or 0.0,
                        'credit': total_amount < 0.0 and -total_amount or 0.0,
                    })
                    line_ids.append(debit_line)

                if self.credit_account_id:
                    credit_line = (0, 0, {
                        'employee_id': loan.employee_id.id or False,
                        'partner_id': partner_id and partner_id.id,
                        'account_id': self.credit_account_id.id,
                        'journal_id': journal_id.id,
                        'date': timenow,
                        'branch_id': loan.employee_id.branch_id.id,
                        'debit': total_amount < 0.0 and -total_amount or 0.0,
                        'credit': total_amount > 0.0 and total_amount or 0.0,
                    })
                    line_ids.append(credit_line)
                move.update({'line_ids': line_ids})
            move_id = move_obj.create(move)
            return move_id
