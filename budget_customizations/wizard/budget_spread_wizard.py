from odoo import api, fields, models, _
from odoo.exceptions import UserError
 
 
class BudgetSpreadReportWizard(models.TransientModel):
    _name = "budget.spread.report.wizard"
    _description = "Budget Spread Report Wizard"
 
    company_ids = fields.Many2many(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    branch_ids = fields.Many2many("res.branch", string="Branches")
    budget_ids = fields.Many2many("crossovered.budget", string="Budgets")
    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)
 
    @api.onchange("company_ids")
    def _onchange_company_ids(self):
        if self.company_ids:
            company_domain = [("company_id", "in", self.company_ids.ids)]
            return {
                "domain": {
                    "branch_ids": company_domain,
                    "budget_ids": company_domain,
                }
            }
        return {"domain": {"branch_ids": [], "budget_ids": []}}
 
    def action_generate_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("Date From cannot be greater than Date To."))
 
        data = {
            "company_ids": self.company_ids.ids,
            "branch_ids": self.branch_ids.ids,
            "budget_ids": self.budget_ids.ids,
            "date_from": str(self.date_from),
            "date_to": str(self.date_to),
        }
        return self.env.ref(
            "budget_customizations.action_report_budget_spread_report_xlsx"
        ).report_action(self, data=data)
 