from odoo import models, fields, api

class VisaRequestReport(models.AbstractModel):
    _name = 'report.visa_processing.report_visa_request'
    _description = 'Visa Request Report'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        
        if data and data.get('ids'):
            applications = self.env['visa.request.application'].browse(data['ids'])
        else:
            applications = self.env['visa.request.application'].browse(docids)
        
        
        form_data = data.get('form', {})
        visa_process_type = form_data.get('visa_process_type')
        from_date = form_data.get('from_date')
        to_date = form_data.get('to_date')
        
       
        return {
            'doc_ids': applications.ids,
            'doc_model': 'visa.request.application',
            'docs': applications,
            'visa_process_type': visa_process_type,
            'visa_type': dict(self.env['visa.request.application']._fields['visa_process_type'].selection).get(visa_process_type, 'All'),
            'from_date': from_date,
            'to_date': to_date,
            'company': self.env.company,
        }