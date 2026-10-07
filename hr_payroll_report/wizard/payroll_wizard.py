from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta

class PayslipReportWizard(models.TransientModel):
    _name = 'payslip.report.wizard'
    _description = 'Payroll Report Wizard'

    payslip_batch_id = fields.Many2one('hr.payslip.run', string="Payroll Batch", required=True)
    date_to = fields.Date(
        string="Payroll Date", 
        readonly=True,
        compute='_compute_batch_data'
    )
    state = fields.Selection([
        ('draft', 'New'),
        ('verify', 'Confirmed'),
        ('close', 'Done'),
        ('paid', 'Paid'),
    ], 
    string='Status',
    readonly=True,
    compute='_compute_batch_data'
    )

    @api.depends('payslip_batch_id')
    def _compute_batch_data(self):
        for wizard in self:
            if wizard.payslip_batch_id:
                wizard.date_to = wizard.payslip_batch_id.date_end
                wizard.state = wizard.payslip_batch_id.state
            else:
                wizard.date_to = False
                wizard.state = False

    def action_generate_report(self):
        self.ensure_one()
        data = {
            'payslip_batch_id': self.payslip_batch_id.id,
            'payslip_batch_name': self.payslip_batch_id.name,
        }
        return self.env.ref('hr_payroll_report.action_employee_payroll_report').report_action(self, data=data)
    
# class PayslipReportWizard(models.TransientModel):
#     _name = 'payslip.report.wizard'
#     _description = 'Payroll Report Wizard'

#     date_to = fields.Date("Payroll Date", required=True)
#     payslip_batch_id = fields.Many2one('hr.payslip.run', string="Payroll Batch")
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('verify', 'Waiting'),
#         ('done', 'Done'),
#         ('paid', 'Paid'),
#         ('cancel', 'Rejected')],
#         string='Status',
#         default='done')

#     def action_generate_report(self):
#         data = {
#             'date_to': self.date_to.strftime('%Y-%m-%d') if self.date_to else False,
#             'payslip_batch_id': self.payslip_batch_id.id if self.payslip_batch_id else False,
#             'payslip_batch_name': self.payslip_batch_id.name if self.payslip_batch_id else False,
#             'state': self.state,
#         }
#         return self.env.ref('hr_payroll_report.action_employee_payroll_report').report_action(self, data=data)

