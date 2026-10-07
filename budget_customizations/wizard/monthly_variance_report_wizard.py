from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date

class BudgetVarianceReportWizard(models.TransientModel):
    _name = 'budget.monthly.variance.report.wizard'
    _description = 'Budget Variance Report Wizard'

    company_ids = fields.Many2many(
        'res.company', 
        string='Company', 
        default=lambda self: self.env.company,
        required=True
    )
    branch_ids = fields.Many2many('res.branch', string='Branches')
    budget_ids = fields.Many2many('crossovered.budget', string='Budgets')
    report_date = fields.Date(
        string='Report Date', 
        required=True,
        default=fields.Date.context_today
    )

    show_consolidated = fields.Boolean(
        string='Include Consolidated Report',
        default=True,
        help="Include detailed consolidated operational results"
    )

    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        if self.company_ids:
            company_domain = [('company_id', 'in', self.company_ids.ids)]
            return {
                'domain': {
                    'branch_ids': company_domain,
                    'budget_ids': company_domain
                }
            }
        else:
            return {'domain': {'branch_id': [], 'budget_id': []}}
        
    @api.onchange('branch_ids')
    def _onchange_branch_ids(self):
        if self.branch_ids:
            return {
                'domain': {
                    'budget_ids': [
                        ('branch_id', 'in', self.branch_ids.ids)
                    ]
                }
            }
        else:
            return {
                'domain': {
                    'budget_ids': []
                }
            }

    def action_generate_report(self):
        self.ensure_one()
        
        if not self.report_date:
            raise UserError(_("Report Date is required"))
            
        data = {
            'company_ids': self.company_ids.ids,
            'branch_ids': self.branch_ids.ids,
            'budget_ids': self.budget_ids.ids,
            'report_date': str(self.report_date),
            'show_consolidated': self.show_consolidated,
        }
        return self.env.ref('budget_customizations.action_report_monthly_variance_report_xlsx').report_action(self, data=data)