from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PayrollBatchWizard(models.TransientModel):
    _name = "payroll.batch.wizard"
    _description = "Payroll Batch Wizard"

    payroll_batch_id = fields.Many2one("payroll.batch",readonly=True)
    batch_wizard_ids = fields.One2many('payroll.batch.wizard.lines', 'batch_wizard_id', string="warehouse")


    def default_get(self, fields):
        employees = []
        vals = super(PayrollBatchWizard, self).default_get(fields)
        active_model = self.env.context.get('active_model') # sale order line record set
        payroll_batch = self.env[active_model].browse(self.env.context.get('active_id'))
        vals['payroll_batch_id'] = payroll_batch.id
        employee_id =  self.env['hr.employee'].search([('payroll_batch_id', '=', payroll_batch.id)])
        for rec in employee_id:
            employees.append((0, 0, {'employee_id': rec.id}))
        vals['batch_wizard_ids'] = employees
        return vals

class PayrollBatchWizardLines(models.TransientModel):
    _name = "payroll.batch.wizard.lines"
    _description = "Sale Warehouse lines"

    employee_id = fields.Many2one('hr.employee')
    batch_wizard_id = fields.Many2one('payroll.batch.wizard')
