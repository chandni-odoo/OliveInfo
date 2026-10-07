from odoo import models, fields, api

class CustomerLeaseReport(models.AbstractModel):
    _name = 'report.employee_accommodation.customer_lease_report' 
    _description = 'Customer Lease Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['client.accommodation'].browse(docids)  

        return {
            'docs': docs,  
        }