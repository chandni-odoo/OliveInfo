from odoo import models, fields
from odoo.exceptions import ValidationError


class LeavePayJournalWizard(models.TransientModel):
    _name = 'leave.pay.journal.wizard'
    _description = 'Leave Pay Journal Wizard'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company
    )
    branch_id = fields.Many2one(
        'res.branch',
        string="Branch",
        required=True
    )

    date_from = fields.Date(string="Period From", required=True)
    date_to = fields.Date(string="Period To", required=True)

    journal_id = fields.Many2one(
        'account.journal',
        string="Journal",
        required=True
    )
    debit_account_id = fields.Many2one(
        'account.account',
        string="Debit Account",
        required=True
    )

    def action_create_journal(self):

        if self.date_from > self.date_to:
            raise ValidationError("Invalid period!")

        period_days = (self.date_to - self.date_from).days + 1

        payslips = self.env['hr.payslip'].search([
            ('company_id', '=', self.company_id.id),
            ('branch_id', '=', self.branch_id.id),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('leave_day', '>', 0)
        ])

        if not payslips:
            raise ValidationError("No payslips found with leave days!")

        move_lines = []
        credit_summary = {}

        for slip in payslips:

            if not slip.contract_id:
                continue

            contract = slip.contract_id

            if not contract.gross_amount:
                continue

            # -------------------------
            # ✅ Subtract excluded rule amounts from gross
            # -------------------------
            excluded_amount = sum(
                line.total
                for line in slip.line_ids
                if line.salary_rule_id.exclude_from_leave_pay
            )

            adjusted_gross = contract.gross_amount - excluded_amount

            if adjusted_gross <= 0:
                continue

            leave_pay = (adjusted_gross / period_days) * slip.leave_day

            # leave_pay = (contract.gross_amount / period_days) * slip.leave_day

            if leave_pay <= 0:
                continue

            credit_account = False

            for rule in slip.struct_id.rule_ids:
                if rule.code == 'NET':
                    credit_account = rule.account_debit
                    break

            if not credit_account:
                raise ValidationError(
                    f"Credit account not found for NET Salary in payslip {slip.number}"
                )

            # Debit
            move_lines.append((0, 0, {
                'name': f"Leave Pay - {slip.employee_id.name}",
                'account_id': self.debit_account_id.id,
                'debit': leave_pay,
                'credit': 0.0,
                'partner_id': slip.employee_id.address_home_id.id,
                'employee_id': slip.employee_id.id,
            }))
            
            # -------------------------
            # ✅ Collect Credit Summary
            # -------------------------
            if credit_account.id not in credit_summary:
                credit_summary[credit_account.id] = {
                    'amount': 0.0,
                    'account': credit_account,
                }

            credit_summary[credit_account.id]['amount'] += leave_pay

        # -------------------------
        # ✅ Create Summarized Credit Lines
        # -------------------------
        for acc_id, data in credit_summary.items():
            move_lines.append((0, 0, {
                'name': f"Leave Pay ({self.date_from} - {self.date_to})",
                'account_id': acc_id,
                'debit': 0.0,
                'credit': data['amount'],
                'partner_id': False,   # No single partner
                'employee_id': False,  # Multiple employees
            }))
            
            # Credit
            # move_lines.append((0, 0, {
            #     'name': f"Leave Pay - {slip.employee_id.name}",
            #     'account_id': credit_account.id,
            #     'debit': 0.0,
            #     'credit': leave_pay,
            #     'partner_id': slip.employee_id.address_home_id.id,
            #     'employee_id': slip.employee_id.id,
            # }))

        move = self.env['account.move'].create({
            'journal_id': self.journal_id.id,
            'date': fields.Date.today(),
            'ref': f'Leave Pay ({self.date_from} - {self.date_to})',
            'branch_id': self.branch_id.id,
            'line_ids': move_lines
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entry',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
        }