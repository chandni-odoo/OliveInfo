from odoo import models,fields,api, _
from odoo.exceptions import ValidationError

class BulkOtRuleWizard(models.TransientModel):
    _name = 'ot.rule.wizard'
    _description = "Bulk OT Rule"

    employee_ids = fields.Many2many('hr.employee', string="Employees")
    ot_rule_line_ids = fields.One2many('ot.rule.line.wizard', 'wizard_id')
    
    @api.model
    def default_get(self, fields):
        vals = super(BulkOtRuleWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            employee_ids = self.env['hr.employee'].browse(active_ids)
            vals['employee_ids'] = employee_ids
        return vals

    def _prepare_ot_rule_line_values(self, contract_id):
        rule_lines = []
        for rec in self.ot_rule_line_ids.filtered(lambda x: x.ot_rule_id and x.ot_type):
            rule_lines.append({
                'ot_rule_id': rec.ot_rule_id.id,
                'ot_type': rec.ot_type,
                'fix_amount': rec.fix_amount,
                'per_amount': rec.per_amount,
                'per_based_on': rec.per_based_on,
                'contract_id': contract_id.id,
            })
        return rule_lines

    def action_bulk_ot_rule_line(self):
        for record in self.employee_ids:
            contract_id = self.env['hr.contract'].search([('employee_id', '=', record.id),('state', '=', 'open')], limit=1)
            if not contract_id:
                raise ValidationError(("Employee %s does not have any running contract . Please create on employee.") % (record.name))
            rule_lines = self._prepare_ot_rule_line_values(contract_id)
            rule_line_ids = self.env['hr.ot.rule.line'].search([('contract_id', '=', contract_id.id)])
            if rule_line_ids:
                rule_line_ids.unlink()
            for line in rule_lines:
                self.env['hr.ot.rule.line'].create(line)

class BulkOtRuleLine(models.TransientModel):
    _name = 'ot.rule.line.wizard'
    _description = "Bulk OT Rule Line"

    wizard_id = fields.Many2one('ot.rule.wizard', string="Rule Wizard")
    ot_rule_id = fields.Many2one('hr.ot.rule', string="Overtime Rule", required=True)
    ot_type_id = fields.Many2one(related='ot_rule_id.ot_type_id', string="Overtime Type")
    ot_type = fields.Selection([('fix', 'Fix'), ('percentage', 'Percentage')], string="Base On", default="fix", required=True)
    fix_amount = fields.Float(string="Fix Amount")
    per_amount = fields.Float(string="Percentage Amount")
    per_based_on = fields.Selection([('BASIC', 'BASIC'), ('GROSS', 'GROSS'), ('NET', 'NET')], string="Base On", default="BASIC")
