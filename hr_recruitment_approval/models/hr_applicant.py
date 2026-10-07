from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from datetime import datetime

class HRApplicant(models.Model):
    _inherit = 'hr.applicant'
    
    offer_approval_line_ids = fields.One2many(
        'hr.applicant.offer.approval.line', 'applicant_id', string='Approval Lines')
    current_approver_id = fields.Many2one(
        'res.users', string='Current Approver', tracking=True)
    is_offer_approved = fields.Boolean(
        string='Offer Approved', default=False, tracking=True)
    is_offer_rejected = fields.Boolean(
        string='Offer Rejected', default=False, tracking=True)
    offer_approval_date = fields.Datetime(string='Approval Date')
    is_in_offer_approval = fields.Boolean(
        string='In Offer Approval', compute='_compute_is_in_offer_approval', store=True)
    can_current_user_approve = fields.Boolean(
        string='Can Current User Approve', compute='_compute_can_current_user_approve')
    is_contract_signed_stage = fields.Boolean(
        string='Is Contract Signed Stage',
        compute='_compute_is_contract_signed_stage'
    )

    @api.depends('stage_id')
    def _compute_is_contract_signed_stage(self):
        for applicant in self:
            applicant.is_contract_signed_stage = applicant.stage_id.name == 'Contract Signed' if applicant.stage_id else False
    
    @api.depends('stage_id', 'stage_id.is_offer_approval_stage')
    def _compute_is_in_offer_approval(self):
        for applicant in self:
            applicant.is_in_offer_approval = applicant.stage_id.is_offer_approval_stage if applicant.stage_id else False
    
    @api.depends('offer_approval_line_ids.status')
    def _compute_current_approver(self):
        for applicant in self:
            if not applicant.is_in_offer_approval:
                applicant.current_approver_id = False
                continue
                
            pending_approval = applicant.offer_approval_line_ids.filtered(
                lambda h: h.status == 'pending'
            ).sorted('sequence')
            
            if pending_approval:
                applicant.current_approver_id = pending_approval[0].user_id
            else:
                applicant.current_approver_id = False
    
    @api.depends('offer_approval_line_ids.status', 'offer_approval_line_ids.user_id', 'current_approver_id')
    def _compute_can_current_user_approve(self):
        for applicant in self:
            applicant.can_current_user_approve = applicant.current_approver_id == self.env.user
    
    def action_send_for_offer_approval(self):
        self.ensure_one()
        
        # Get the default approval group
        approval_group = self.env['offer.approval.group'].search([('active', '=', True)], limit=1)
        if not approval_group or not approval_group.approver_line_ids:
            raise UserError(_("Please configure Offer Approval Group with approvers first."))
            
        # Clear previous approval lines
        self.offer_approval_line_ids.unlink()
        
        # Create approval lines in sequence
        approval_history_values = []
        approvers = approval_group.approver_line_ids.sorted('sequence')
        
        for approver in approvers:
            approval_history_values.append((0, 0, {
                'user_id': approver.user_id.id,
                'status': 'pending' if approver.sequence == 1 else 'waiting',
                'sequence': approver.sequence,
            }))
            
        self.write({
            'offer_approval_line_ids': approval_history_values,
            'is_offer_approved': False,
            'is_offer_rejected': False,
        })
        
        # Rest of the method remains the same...
        # Change stage to Offer Approval
        offer_approval_stage = self.env['hr.recruitment.stage'].search([
            ('is_offer_approval_stage', '=', True)
        ], limit=1)
        if offer_approval_stage:
            self.stage_id = offer_approval_stage.id
        
        # Notify first approver
        self._notify_current_approver()
        
        return True
    
    def _notify_current_approver(self):
        """Notify only the current approver based on sequence"""
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'hr.applicant')], limit=1)
        activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Offer Approval Required')], limit=1)
        if not activity_type_id:
            activity_type_id = self.env['mail.activity.type'].create({
                'name': 'Offer Approval Required',
                'category': 'default',
            })

        current_approval = self.offer_approval_line_ids.filtered(
            lambda h: h.status in ('pending', 'waiting')
        ).sorted('sequence')
        
        if not current_approval:
            return
            
        current_approval = current_approval[0]
        current_approval.status = 'pending'
        self.current_approver_id = current_approval.user_id
        
        # Remove existing activities for this applicant
        existing_activities = self.env['mail.activity'].search([
            ('res_model', '=', 'hr.applicant'),
            ('res_id', '=', self.id),
            ('activity_type_id.name', '=', 'Offer Approval Required')
        ])
        existing_activities.unlink()
        
        activity_vals = {
            'res_model_id': model_id.id,
            'res_model': 'hr.applicant',
            'res_id': self.id,
            'summary': 'Offer Approval Required',
            'note': f'Please review and approve the offer for applicant {self.partner_name or self.name}',
            'user_id': current_approval.user_id.id,
            'activity_type_id': activity_type_id.id,
            'date_deadline': fields.Date.today()
        }
        self.env['mail.activity'].sudo().create(activity_vals)
    
    def action_approve_offer(self):
        self.ensure_one()
        
        # Check if user is in approval group
        approval_group = self.env.ref('hr_recruitment_approval.group_offer_approval', raise_if_not_found=False)
        if not approval_group or self.env.user not in approval_group.users:
            raise AccessError(_("You are not authorized to approve offers."))
        
        # Check if it's the current user's turn to approve
        current_approval = self.offer_approval_line_ids.filtered(
            lambda h: h.user_id == self.env.user and h.status in ('pending',)
        )
        
        if not current_approval:
            raise AccessError(_("You are not authorized to approve this offer at this time."))
            
        current_approval = current_approval[0]
        current_approval.write({
            'status': 'approved',
            'approval_date': datetime.now()
        })
        
        # Complete the activity
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'hr.applicant'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.uid),
            ('activity_type_id.name', '=', 'Offer Approval Required')
        ])
        if activity:
            activity.action_done()
        
        # Check for next approver
        next_approval = self.offer_approval_line_ids.filtered(
            lambda h: h.status == 'waiting'
        ).sorted('sequence')
        
        if next_approval:
            self._notify_current_approver()
            self.message_post(body=f"Offer approved by {self.env.user.name}. Sent to next approver.")
        else:
            # All approvals done
            self.write({
                'current_approver_id': False,
                'is_offer_approved': True,
                'offer_approval_date': datetime.now()
            })
            
            # Move to contract proposal stage
            contract_proposal_stage = self.env['hr.recruitment.stage'].search([
                ('name', 'ilike', 'contract proposal')
            ], limit=1)
            if contract_proposal_stage:
                self.stage_id = contract_proposal_stage.id
            self.message_post(body=f"Offer fully approved by all approvers.")
        
        return True
    
    
    def action_reject_offer(self):
        self.ensure_one()
        
        # Check if user is in approval group
        approval_group = self.env.ref('hr_recruitment_approval.group_offer_approval', raise_if_not_found=False)
        if not approval_group or self.env.user not in approval_group.users:
            raise AccessError(_("You are not authorized to reject offers."))
        
        # Check if it's the current user's turn to approve/reject
        current_approval = self.offer_approval_line_ids.filtered(
            lambda h: h.user_id == self.env.user and h.status == 'pending'
        )
        
        if not current_approval:
            raise AccessError(_("You are not authorized to reject this offer at this time."))
            
        current_approval = current_approval[0]
        current_approval.write({
            'status': 'rejected',
            'approval_date': datetime.now()
        })
        
        # Complete the activity
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'hr.applicant'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.uid),
            ('activity_type_id.name', '=', 'Offer Approval Required')
        ])
        if activity:
            activity.action_done()
        
        # Set rejected status and mark all remaining approvals as rejected
        remaining_approvals = self.offer_approval_line_ids.filtered(
            lambda h: h.status in ('waiting', 'pending')
        )
        remaining_approvals.write({'status': 'rejected'})
        
        self.write({
            'current_approver_id': False,
            'is_offer_rejected': True
        })
        
        # Return the refuse reason wizard action instead of moving to refuse stage immediately
        return {
            'type': 'ir.actions.act_window',
            'name': _('Refuse Reason'),
            'res_model': 'applicant.get.refuse.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_applicant_ids': self.ids, 
                'active_test': False,
                'from_offer_approval': True  # Optional: add context to identify this came from offer approval
            },
            'views': [[False, 'form']]
        }

    


class HRApplicantOfferApprovalLine(models.Model):
    _name = 'hr.applicant.offer.approval.line'
    _description = 'Applicant Offer Approval Line'
    _order = 'sequence asc, approval_date desc'
    
    applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Approver', required=True)
    sequence = fields.Integer(string='Sequence', required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('waiting', 'Waiting'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')], string='Status', default='pending')
    approval_date = fields.Datetime(string='Approval Date')


class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'
    
    is_offer_approval_stage = fields.Boolean(string='Is Offer Approval Stage', default=False)

class OfferApprovalGroup(models.Model):
    _name = 'offer.approval.group'
    _description = 'Offer Approval Group'
    
    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    approver_line_ids = fields.One2many(
        'offer.approver.line', 
        'approval_group_id', 
        string='Approvers'
    )

class OfferApproverLine(models.Model):
    _name = 'offer.approver.line'
    _description = 'Offer Approver Line'
    _order = 'sequence, id'
    
    approval_group_id = fields.Many2one('offer.approval.group')
    user_id = fields.Many2one('res.users', string='Approver', required=True)
    sequence = fields.Integer(string='Sequence', required=True, default=1)