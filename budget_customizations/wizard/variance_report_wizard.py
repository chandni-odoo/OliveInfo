from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class VarianceReportWizard(models.TransientModel):
    _name = 'budget.variance.report.wizard'
    _description = 'Budget Variance Report Wizard'
    
    company_ids = fields.Many2many(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    branch_ids = fields.Many2many('res.branch', string='Branches')
    budget_ids = fields.Many2many('crossovered.budget', string='Budgets')
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    report_level = fields.Selection([
        ('level1', 'Level 1'),
        ('level2', 'Level 2'),
        ('level3', 'Level 3 (Detailed)'),
    ], string='Report Level', required=True)
    

    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        if self.company_ids:
            company_domain = [('company_id', 'in', self.company_ids.ids)]
            return {
                'domain': {
                    'branch_id': company_domain,
                    'budget_id': company_domain
                }
            }
        else:
            return {'domain': {'branch_id': [], 'budget_id': []}}
    
    def action_generate_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("Date From cannot be greater than Date To"))
        
        data = {
            'company_ids': self.company_ids.ids,
            'branch_ids': self.branch_ids.ids,
            'budget_ids': self.budget_ids.ids,
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
            'report_level': self.report_level,
        }
        
        return self.env.ref('budget_customizations.action_report_budget_variance_report_xlsx').report_action(self, data=data)