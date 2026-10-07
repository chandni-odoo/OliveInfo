from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class HrResignation(models.Model):
    _inherit = 'hr.resignation'
    
    def approve_resignation(self):

        super(HrResignation, self).approve_resignation()
        
        for rec in self:
            if rec.sepration_type == 'terminate':
                self._create_clearance_request(rec)

    def _create_clearance_request(self, rec):
        existing_clearance = self.env['clearance.request'].search([
            ('employee_id', '=', rec.employee_id.id),
            ('resignation_id', '=', rec.id),  
            ('state', '!=', 'cancel')  
        ], limit=1)
        
        if existing_clearance:
            rec.message_post(
                body=_(f"Clearance request {existing_clearance.name} already exists for this termination.")
            )
            return existing_clearance
    
        clearance_obj = self.env['clearance.request']
        clearance_vals = {
            'employee_id': rec.employee_id.id,
            'branch_id': rec.branch_id.id,
            'job_id': rec.employee_id.job_id.id,
            'request_date': fields.Date.today(),
            'description': f"Automatic clearance request created for termination of {rec.employee_id.name}",
            'requirements': f"""
                <p><strong>Clearance required for employee termination</strong></p>
                <p>Employee: {rec.employee_id.name}</p>
                <p>Branch: {rec.branch_id.name or '-'}</p>
                <p>Termination Date: {rec.approved_revealing_date}</p>
                <p>Resignation Reference: {rec.name}</p>
            """,
            'state': 'draft', 
        }
        clearance_request = clearance_obj.create(clearance_vals)
        clearance_request.action_submit()
        
        rec.message_post(
            body=_(f"Clearance request {clearance_request.name} has been automatically created and submitted for this termination.")
        )
        
        clearance_request.message_post(
            body=_(f"This clearance request was automatically created from termination {rec.name}.")
        )
        
        return clearance_request