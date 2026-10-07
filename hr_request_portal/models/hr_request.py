from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError
                    

class HrRequest(models.Model):
    _name = "request.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "HR Request"

    name = fields.Char(default='New', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'), 
        ('approve', 'Approve'),
        ('completed', 'Completed'),
        ('reject', 'Rejected')
    ], default='draft', store=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    branch_id = fields.Many2one('res.branch', string="Branch", related="employee_id.branch_id", required=True)
    job_id = fields.Many2one('hr.job')
    manager_id = fields.Many2one('hr.employee', string="Manager", compute='_compute_manager', store=True)
    approval_comment = fields.Text(string="Approval Comment", tracking=True)
    rejection_comment = fields.Text(string="Rejection Comment", tracking=True)
    request_date = fields.Date(string="Request Date")
    description = fields.Text(string="Description")
    type_id = fields.Many2one('hr.request.type', string="Request Type", required=True)
    is_resignation = fields.Boolean(string="Is Resignation", compute='_compute_is_resignation', store=True)
    is_termination = fields.Boolean(string="Is Termination", compute='_compute_is_termination', store=True)
    relieving_date = fields.Date(string="Relieving Date")
    languages = fields.Selection([
        ('english', 'English'),
        ('arabic', 'Arabic'),
        ('both', 'Both'),
        ('na', 'Not Applicable')
    ], string="Language", default='na', tracking=True, widget="radio")
    requirements = fields.Html(string="Requirements")
    attachments = fields.Binary(string="Attachments")
    attachments_filename = fields.Char(string="Attachment Filename")
    relieving_date_visible = fields.Boolean(compute='_compute_relieving_date_visible')
    language_field_visible = fields.Boolean(compute='_compute_language_field_visible')
    final_document = fields.Binary(string="Final Document", attachment=True, store=True, tracking=True) 
    final_document_filename = fields.Char(string="Final Document Filename", store=True, tracking=True)
    can_approve = fields.Boolean(compute='_compute_can_approve', string="Can Approve")
    document_exists = fields.Boolean(
        string="Document Available", 
        compute='_compute_document_exists', 
        store=False
    )
    reason_for_leaving_id = fields.Many2one(
        'hr.leaving.reason', 
        string="Reason For Leaving",
    ) 
    resignation_date = fields.Date(string="Resignation Date")
    notice_id = fields.Many2one('notice.period', string="Notice Period", related="employee_id.notice_id")

    @api.depends('final_document')
    def _compute_document_exists(self):
        for record in self:
            record.document_exists = bool(record.final_document)

    @api.depends('type_id')
    def _compute_is_resignation(self):
        for record in self:
            if record.type_id and record.type_id.name:
                record.is_resignation = record.type_id.name.lower() == 'resignation'
            else:
                record.is_resignation = False

    @api.depends('type_id')
    def _compute_is_termination(self):
        for record in self:
            if record.type_id and record.type_id.name:
                record.is_termination = record.type_id.name.lower() == 'termination'
            else:
                record.is_termination = False

    @api.depends('type_id', 'manager_id')
    def _compute_can_approve(self):
        current_user = self.env.user
        is_hr_manager = current_user.has_group('hr.group_hr_manager')
        
        for record in self:
            is_direct_manager = False
            if record.manager_id and record.manager_id.user_id:
                is_direct_manager = (current_user.id == record.manager_id.user_id.id)
            
            if record.is_resignation:
                record.can_approve = is_direct_manager
            else:
                record.can_approve = is_direct_manager or is_hr_manager

    @api.depends('employee_id')
    def _compute_manager(self):
        for record in self:
            if record.employee_id and record.employee_id.parent_id:
                record.manager_id = record.employee_id.parent_id.id
            else:
                record.manager_id = False

    @api.depends('type_id')
    def _compute_relieving_date_visible(self):
        for record in self:
            if record.type_id:
                record.relieving_date_visible = record.type_id.name.lower() in ['termination', 'resignation']
            else:
                record.relieving_date_visible = False
    
    @api.depends('type_id')
    def _compute_language_field_visible(self):
        for record in self:
            if record.type_id:
                record.language_field_visible = not record.type_id.name.lower() in ['resignation', 'final clearance']
            else:
                record.language_field_visible = True

    def button_confirm(self):
        for record in self:
            record.state = 'confirm'
            
            # Create an activity for the manager to approve
            if record.manager_id and record.manager_id.user_id:
                record.message_subscribe(partner_ids=[record.manager_id.user_id.partner_id.id])
                
                record.message_post(
                    body=_("A %s request has been submitted by %s and requires your approval.") % 
                          (record.type_id.name, record.employee_id.name),
                    partner_ids=[record.manager_id.user_id.partner_id.id],
                    message_type='notification',
                    subtype_id=self.env.ref('mail.mt_note').id
                )
                
                record.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_("Approve %s Request") % record.type_id.name,
                    note=_("Please review and approve the %s request of %s.") % 
                         (record.type_id.name, record.employee_id.name),
                    user_id=record.manager_id.user_id.id
                )


    def button_approve(self):
        for record in self:
            current_user = self.env.user
            
            if record.is_resignation:
                is_direct_manager = False
                if record.manager_id and record.manager_id.user_id:
                    is_direct_manager = (current_user.id == record.manager_id.user_id.id)
                
                if not is_direct_manager:
                    raise AccessError(_("Only the employee's direct manager can approve resignation requests."))
            
            elif not record.can_approve:
                raise AccessError(_("You do not have permission to approve this request."))
            
            # if (record.is_resignation or record.is_termination) and not record.approval_comment:
            #     raise UserError(_("Please provide an approval comment for this request."))
            
            record.state = 'approve'

            record.activity_ids.action_done()

            # HR Notification for specific request types
            hr_notification_types = ['document', 'noc', 'salary certificate', 'other', 'passport']
            if record.type_id and record.type_id.name.lower() in hr_notification_types:
                self._notify_hr_users(record)
            # upto this
            
            if record.is_resignation or record.is_termination:
                if not record.relieving_date:
                    raise UserError(_("Relieving Date is required for termination/resignation requests"))
                
                separation_type = 'terminate' if record.is_termination else 'resign'
                
                resignation_vals = {
                    'employee_id': record.employee_id.id,
                    'branch_id': record.branch_id.id,
                    'joined_date': record.employee_id.create_date.date() if record.employee_id.create_date else fields.Date.today(),
                    'expected_revealing_date': record.relieving_date,
                    'reason': record.description or "No reason provided",
                    'state': 'draft',
                    'sepration_type': separation_type,
                    'resign_confirm_date': fields.Date.today(),
                    'reason_for_leaving_id': record.reason_for_leaving_id.id,
                    'resignation_date':record.resignation_date,
                    'manager_comment':record.approval_comment,
                    'request_id': record.id,
                }
                
                if record.attachments:
                    attachment = self.env['ir.attachment'].create({
                        'name': record.attachments_filename or 'resignation_attachment',
                        'datas': record.attachments,
                        'res_model': 'hr.resignation',
                        'res_id': 0,
                    })
                    resignation_vals['attachment_ids'] = [(4, attachment.id)]
                
                try:
                    resignation = self.env['hr.resignation'].sudo().create(resignation_vals)
                    if record.attachments:
                        attachment.write({'res_id': resignation.id})
                    
                    if record.employee_id.user_id:
                        comment_text = ""
                        if record.approval_comment:
                            comment_text = _(" with comment: %s") % record.approval_comment
                            
                        record.message_post(
                            body=_("Your %s request has been approved%s") % 
                                  (record.type_id.name, comment_text),
                            partner_ids=[record.employee_id.user_id.partner_id.id],
                            message_type='notification',
                            subtype_id=self.env.ref('mail.mt_note').id
                        )
                        
                except Exception as e:
                    raise UserError(_('Failed to create resignation record: %s') % str(e))
                
    def _notify_hr_users(self, record):
        """Notify HR users when specific request types are approved"""
        hr_group = self.env.ref('hr_request_portal.group_hr_notification')
        hr_users = hr_group.users
        
        if hr_users:
            # Create activity for HR users
            note = _("""
                <p>The following request has been approved by %s and requires HR action:</p>
                <ul>
                    <li>Employee: %s</li>
                    <li>Request Type: %s</li>
                    <li>Description: %s</li>
                </ul>
            """) % (
                record.manager_id.name if record.manager_id else _("Unknown Manager"),
                record.employee_id.name,
                record.type_id.name,
                record.description or _("No description provided")
            )
            
            # Subscribe HR users to the record
            record.message_subscribe(partner_ids=hr_users.mapped('partner_id').ids)
            
            # Post a message in the chatter
            record.message_post(
                body=note,
                partner_ids=hr_users.mapped('partner_id').ids,
                message_type='notification',
                subtype_id=self.env.ref('mail.mt_note').id
            )
            
            # Create activities for each HR user
            for user in hr_users:
                record.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_("Employee Request Approved"),
                    note=note,
                    user_id=user.id
                )


    def button_reject(self):
        for record in self:
            current_user = self.env.user
            
            if record.is_resignation:
                is_direct_manager = False
                if record.manager_id and record.manager_id.user_id:
                    is_direct_manager = (current_user.id == record.manager_id.user_id.id)
                
                if not is_direct_manager:
                    raise AccessError(_("Only the employee's direct manager can reject resignation requests."))
            
            elif not record.can_approve:
                raise AccessError(_("You do not have permission to reject this request."))
            
            if not record.rejection_comment:
                raise UserError(_("Please provide a rejection comment."))
            
            # Move to rejected state instead of draft
            record.state = 'reject'
            record.activity_ids.action_done()
            
            # Notify employee
            if record.employee_id.user_id:
                record.message_post(
                    body=_("Your %s request has been rejected. Rejection Comment: %s") % 
                        (record.type_id.name, record.rejection_comment),
                    partner_ids=[record.employee_id.user_id.partner_id.id],
                    message_type='notification',
                    subtype_id=self.env.ref('mail.mt_note').id
                )

    def button_complete(self):
        self.write({'state': 'completed'})


    @api.onchange('employee_id')
    def _onChangeEmployee(self):
        if self.employee_id:
            self.branch_id = self.employee_id.branch_id and self.employee_id.branch_id.id   
            self.job_id = self.employee_id.job_id and self.employee_id.job_id.id
            if self.employee_id.parent_id:
                self.manager_id = self.employee_id.parent_id.id
            else:
                self.manager_id = False

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('request.request') or ('New')
        return super(HrRequest, self).create(vals)
    
    @api.onchange('type_id')
    def _onchange_type_id(self):
        for record in self:
            if record.type_id:
                record.relieving_date = False
                if record.type_id.name.lower() in ['termination', 'resignation']:
                    record.relieving_date_visible = True
                else:
                    record.relieving_date_visible = False
                    
                				
	

class RequestType(models.Model):
	_name = "hr.request.type"

	name = fields.Char()
	code = fields.Char()


class HrLeavingReason(models.Model):
    _name = 'hr.leaving.reason'
    _description = 'Reason for Leaving'
    
    name = fields.Char(string="Reason", required=True)
    notes = fields.Text(string="Description")
    






	


