from odoo import api, fields, models, _
from odoo.exceptions import UserError

class VisaRequestExcelReportWizard(models.TransientModel):
    _name = 'visa.request.excel.report.wizard'
    _description = 'Visa Request Excel Report Wizard'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    visa_process_type = fields.Selection([
        ('qvc', 'QVC'),
        ('non_qvc', 'NON-QVC'),
        ('change_employer', 'Change of Employer'),
        ('work_permit', 'Work Permit'),
        ('secondment', 'Secondment')], 
        string='Visa Process Type')
    # state = fields.Selection([
    #     ('new', 'New'),
    #     ('submit', 'Submitted'),
    #     ('pending', 'Pending'),
    #     ('process', 'Processing'),
    #     ('complete', 'Completed'),
    #     ('reject', 'Rejected'),
    #     ('cancel', 'Cancelled')
    # ], string='Status')

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(_("Date From must be less than or equal to Date To"))

    def action_print_report(self):
        self.ensure_one()
        domain = []
        
        if self.date_from:
            domain.append(('request_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('request_date', '<=', self.date_to))
        if self.visa_process_type:
            domain.append(('visa_process_type', '=', self.visa_process_type))
        # if self.state:
        #     domain.append(('state', '=', self.state))
            
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'visa_process_type': self.visa_process_type,
            # 'state': self.state,
            'domain': domain,
        }
        
        return self.env.ref('visa_processing.action_visa_request_excel_report').report_action(self, data=data)