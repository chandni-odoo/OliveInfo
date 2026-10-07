from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CrossoveredBudgetLines(models.Model):
    _inherit = 'crossovered.budget.lines'
    
    remark = fields.Text(string='Remark')
    working_details = fields.Text(string='Working Details')
    

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    
    branch_id = fields.Many2one('res.branch', string='Branch')


class AccountBudgetPost(models.Model):
    _inherit = "account.budget.post"

    
    main_group_id = fields.Many2one(
        'budget.main.group', 
        string='Main Group',
        ondelete='restrict'
    )
    sub_group_id = fields.Many2one(
        'budget.sub.group', 
        string='Sub Group',
        ondelete='restrict'
    )

    sequence = fields.Integer(string='Sequence')


class BudgetMainGroup(models.Model):
    _name = 'budget.main.group'
    _description = 'Budget Main Group'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    budget_type = fields.Selection(
        [('revenue', 'Revenue'), ('expense', 'Expense')],
        string='Type',
        default='revenue',
        required=True
    )

class BudgetSubGroup(models.Model):
    _name = 'budget.sub.group'
    _description = 'Budget Sub Group'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')