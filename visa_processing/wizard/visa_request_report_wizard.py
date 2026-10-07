from odoo import models, fields, api

class VisaRequestReportWizard(models.TransientModel):
    _name = 'visa.request.report.wizard'
    _description = 'Visa Request Report Wizard'
    
    visa_process_type = fields.Selection([
        ('qvc', 'QVC'),
        ('non_qvc', 'NON-QVC'),
        ('change_employer', 'Change of Employer'),
        ('work_permit', 'Work Permit'),
        ('secondment', 'Secondment')], 
        string='Visa Process Type')
    
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")

    def action_print_report(self):
        domain = []
        if self.visa_process_type:
            domain.append(('visa_process_type', '=', self.visa_process_type))
        if self.from_date:
            domain.append(('request_date', '>=', self.from_date))
        if self.to_date:
            domain.append(('request_date', '<=', self.to_date))
            
        visa_requests = self.env['visa.request.application'].search(domain)
        
        if not visa_requests:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Records Found',
                    'message': 'No visa requests match your criteria.',
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        data = {
            'ids': visa_requests.ids,
            'model': 'visa.request.application',
            'form': {
                'visa_process_type': self.visa_process_type,
                'from_date': self.from_date and self.from_date.strftime('%Y-%m-%d') or False,
                'to_date': self.to_date and self.to_date.strftime('%Y-%m-%d') or False,
            }
        }
        return self.env.ref('visa_processing.action_visa_request_report').report_action(self, data=data)
