from odoo import models, fields, api
from odoo.tools import format_date

class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    reporting_account_id = fields.Many2one('account.account',string='Reporting Account')

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    
    @api.depends('name', 'date_end')
    def name_get(self):
        result = []
        for run in self:
            name = run.name
            if run.date_end:
                formatted_date = format_date(self.env, run.date_end, date_format='dd/MM/yyyy')
                name = f"{run.name} [{formatted_date}]"
            result.append((run.id, name))
        return result
    

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    exclude_from_leave_pay = fields.Boolean(
        string="Exclude from Leave Pay",
        help="If enabled, this rule will be excluded from leave salary calculation."
    )


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_release_date = fields.Date(
        string="Payment Release Date",
        tracking=True,
    )

