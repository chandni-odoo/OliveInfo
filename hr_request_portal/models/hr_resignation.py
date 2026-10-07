from odoo import models, fields, api, _
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)

class HrResignation(models.Model):
    _inherit = 'hr.resignation'

    reason_for_leaving_id = fields.Many2one(
        'hr.leaving.reason', 
        string="Reason For Leaving",
    ) 
    resignation_date = fields.Date(string="Resignation Date")
    notice_id = fields.Many2one('notice.period', string="Notice Period", related="employee_id.notice_id")
    branch_id = fields.Many2one('res.branch', string="Branch", required=True, related="employee_id.branch_id")
    manager_comment = fields.Text(string="Manager Comment", tracking=True)
    request_id = fields.Many2one(
        'request.request',
        string="HR Request"
    )

    def action_open_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'HR Request',
            'res_model': 'request.request',
            'view_mode': 'form',
            'res_id': self.request_id.id,
            'target': 'current',
        }


    def approve_resignation(self):
        res = super(HrResignation, self).approve_resignation()

        for resignation in self:
            allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', resignation.employee_id.id),
                ('date_to', '=', False),
                ('state', '=', 'validate')  
            ])
            
            if allocations and resignation.expected_revealing_date:
                allocations.write({
                    'date_to': resignation.expected_revealing_date
                })
                
                resignation.message_post(
                    body=_("Updated %s leave allocations with end date %s") % 
                        (len(allocations), resignation.expected_revealing_date),
                    subtype_xmlid="mail.mt_note"
                )

        self._create_final_clearance_request()
        return res
    
    def check_upcoming_relieving_dates(self):
        today = fields.Date.today()
        target_date = today + timedelta(days=14)
        resignations = self.search([
            ('sepration_type', '!=', 'terminate'),
            ('state', '=', 'approved'),
            ('expected_revealing_date', '=', target_date),
        ])
        
        for resignation in resignations:
            existing_request = self.env['clearance.request'].search([
                ('employee_id', '=', resignation.employee_id.id),
                ('resignation_id', '=', resignation.id)  # Better way to link them
            ], limit=1)
            
            if not existing_request:
                resignation._create_final_clearance_request()
        
        return True
    

    def _create_final_clearance_request(self):
        self.ensure_one()
        
        existing_request = self.env['clearance.request'].search([
            ('employee_id', '=', self.employee_id.id),
            ('resignation_id', '=', self.id)  # Better way to check for existing requests
        ], limit=1)
        
        if existing_request:
            return existing_request
        
        clearance_vals = {
            'employee_id': self.employee_id.id,
            'branch_id': self.branch_id.id,
            'job_id': self.employee_id.job_id.id,
            'request_date': fields.Date.today(),
            'description': _("Automatic clearance request created for resignation %s of %s. Relieving date: %s") % (
                self.name,
                self.employee_id.name,
                self.expected_revealing_date
            ),
            'state': 'draft',
            'resignation_id': self.id,  # Add this link
        }
        
        clearance_request = self.env['clearance.request'].create(clearance_vals)
        clearance_request.action_submit()
        self.message_post(
            body=_("Clearance request %s has been automatically created.") % clearance_request.name,
            subtype_xmlid="mail.mt_note"
        )
        
        return clearance_request
    
    @api.model
    def auto_check_relieving_dates(self):
        # Log for debugging
        _logger.info("Cron job 'Check Resignation Relieving Dates' started at %s", fields.Datetime.now())
        result = self.check_upcoming_relieving_dates()
        _logger.info("Cron job completed with result: %s", result)
        return result
        

    # def check_upcoming_relieving_dates(self):
    #     today = fields.Date.today()
    #     target_date = today + timedelta(days=14)
    #     resignations = self.search([
    #         ('sepration_type', '!=', 'terminate'),
    #         ('state', '=', 'approved'),
    #         ('expected_revealing_date', '=', target_date),
    #     ])
        
    #     for resignation in resignations:
    #         existing_request = self.env['clearance.request'].search([
    #             ('employee_id', '=', resignation.employee_id.id),
    #             ('description', 'ilike', f'resignation {resignation.name}')
    #         ], limit=1)
            
    #         if not existing_request:
    #             resignation._create_final_clearance_request()
        
    #     return True
    
    # def _create_final_clearance_request(self):
    #     self.ensure_one()
        
    #     existing_request = self.env['clearance.request'].search([
    #         ('employee_id', '=', self.employee_id.id),
    #         ('description', 'ilike', f'resignation {self.name}')
    #     ], limit=1)
        
    #     if existing_request:
    #         return existing_request
            
    #     clearance_vals = {
    #         'employee_id': self.employee_id.id,
    #         'branch_id': self.branch_id.id,
    #         'job_id': self.employee_id.job_id.id,
    #         'request_date': fields.Date.today(),
    #         'description': _("Automatic clearance request created for resignation %s of %s. Relieving date: %s") % (
    #             self.name,
    #             self.employee_id.name,
    #             self.expected_revealing_date
    #         ),
    #         'state': 'draft',
    #     }
        
    #     clearance_request = self.env['clearance.request'].create(clearance_vals)
    #     clearance_request.action_submit()
    #     self.message_post(
    #         body=_("Clearance request %s has been automatically created.") % clearance_request.name,
    #         subtype_xmlid="mail.mt_note"
    #     )
        
    #     return clearance_request

    # @api.model
    # def auto_check_relieving_dates(self):
    #     self.check_upcoming_relieving_dates()