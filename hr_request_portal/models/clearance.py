from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from datetime import datetime


class ClearanceRequest(models.Model):
    _name = "clearance.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee Clearance Request"
    _table = 'clearance_request'
    _rec_name = 'name'
    
    name = fields.Char(default='New', readonly=True, copy=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Manager Approval'),  
        ('manager_approve', 'Manager Approved'),  
        ('approve', 'Approved'),
        ('submit', 'Submitted'),
        ('reject', 'Rejected')
    ], default='draft', tracking=True)
        
    employee_id = fields.Many2one('hr.employee', required=True)
    branch_id = fields.Many2one('res.branch', string="Branch", readonly=False)
    job_id = fields.Many2one('hr.job', readonly=False)
    request_date = fields.Date(default=fields.Date.today)
    manager_id = fields.Many2one('hr.employee', string="Manager", compute='_compute_manager', store=True)
    
    description = fields.Text()
    requirements = fields.Html()
    attachments = fields.Binary()
    attachments_filename = fields.Char()
    final_document = fields.Binary(attachment=True)
    final_document_filename = fields.Char()
    document_exists = fields.Boolean(compute='_compute_document_exists')
    
    approval_history_ids = fields.One2many(
        'clearance.approval.history',
        'clearance_id',
        string="Approval History"
    )
    resignation_id = fields.Many2one(
        'hr.resignation',
        string='Related Resignation',
        readonly=True
    )
    is_current_user_manager = fields.Boolean(
    string="Is Current User Manager",
    compute='_compute_is_current_user_manager',
    )
    relieving_date = fields.Date(string="Last Working Date", compute="_compute_relieving_date", store=True, readonly=False)

    # Department Concerned Booleans
    vehicle_keys = fields.Boolean(string="Vehicle / Keys", default=False)
    uniforms_shoes = fields.Boolean(string="Uniforms / Shoes", default=False)
    drawer_keys = fields.Boolean(string="Drawer Keys", default=False)
    petrol_card = fields.Boolean(string="Petrol Card", default=False)
    traffic_violation = fields.Boolean(string="Traffic Violation", default=False)
    warehouse_keys = fields.Boolean(string="Warehouse Keys", default=False)
    tools_hardware = fields.Boolean(string="Tools / Hardware", default=False)
    business_cards = fields.Boolean(string="Business Cards", default=False)
    job_files_handover = fields.Boolean(string="Jobs / Files Handover", default=False)
    gate_pass = fields.Boolean(string="Gate Pass", default=False)
    remarks_department = fields.Text(string="Remarks (Department)", default=False)

    # 5. Finance & Admin
    petty_cash = fields.Boolean("Petty Cash", default=False)
    wages_cash = fields.Boolean("Wages Cash", default=False)
    salary_advance = fields.Boolean("Salary Advance", default=False)
    bank_loan = fields.Boolean("Bank Loan", default=False)
    phone_bills = fields.Boolean("Phone bills", default=False)
    company_loan = fields.Boolean("Company Loan", default=False)
    house_furnishing = fields.Boolean("House Furnishing / Keys", default=False)
    accommodation_keys = fields.Boolean("Accommodation Keys", default=False)
    office_keys = fields.Boolean("office Keys", default=False)
    remarks_finance = fields.Text(string="Remarks (Finance)", default=False)

    # 6. IT
    computer_accessories = fields.Boolean("Computer / Accessories", default=False)
    user_name_block = fields.Boolean("User Name Block", default=False)
    biometric_access_block = fields.Boolean("Biometric Access Block", default=False)
    books_manuals_it = fields.Boolean("Books / Manuals", default=False)
    password_block = fields.Boolean("Password Block", default=False)
    mobile_sim_card = fields.Boolean(string="Mobile / Sim Card", default=False)
    remarks_it = fields.Text(string="Remarks (IT)", default=False)

    # 7. HR
    labour_card = fields.Boolean("Labour Card", default=False)
    driving_license = fields.Boolean("Traffic Violation", default=False)
    library_books_hr = fields.Boolean("Library Books", default=False)
    insurance_card = fields.Boolean("Medical Card", default=False)
    bank_notification = fields.Boolean("Bank Notification", default=False)
    remarks_hr = fields.Text(string="Remarks (HR)", default=False)

    # Fields to track user access
    is_finance_user = fields.Boolean(compute='_compute_user_access')
    is_it_user = fields.Boolean(compute='_compute_user_access')
    is_hr_user = fields.Boolean(compute='_compute_user_access')

    finance_approved = fields.Boolean(string="Finance Approved", default=False)
    it_approved = fields.Boolean(string="IT Approved", default=False)
    hr_approved = fields.Boolean(string="HR Approved", default=False)

     # Track which department rejected
    rejected_by_department = fields.Selection([
        ('finance', 'Finance & Admin'),
        ('it', 'Information Technology'),
        ('hr', 'Human Resources')
    ], string="Rejected By Department")
    
    @api.depends_context('uid')
    def _compute_user_access(self):
        """Compute user access based on groups"""
        for record in self:
            user = self.env.user
            record.is_finance_user = user.has_group('clearance.group_finance_admin')
            record.is_it_user = user.has_group('clearance.group_it_admin')
            record.is_hr_user = user.has_group('clearance.group_hr_admin')


    @api.depends('manager_id')
    def _compute_is_current_user_manager(self):
        for record in self:
            employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            record.is_current_user_manager = employee and employee.id == record.manager_id.id

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.branch_id = self.employee_id.branch_id
            self.job_id = self.employee_id.job_id
            # Ensure fields are updated even after state change
            self._compute_manager()
            self._compute_relieving_date()

    @api.depends('employee_id')
    def _compute_manager(self):
        for record in self:
            if record.employee_id and record.employee_id.parent_id:
                record.manager_id = record.employee_id.parent_id.id
            else:
                record.manager_id = False

    @api.depends('employee_id')
    def _compute_relieving_date(self):
        for record in self:
            resignation = self.env['hr.resignation'].search([
                ('employee_id', '=', record.employee_id.id),
                ('state', 'in', ['confirm', 'approved'])
            ], limit=1, order='create_date desc')
            
            if resignation:
                record.relieving_date = resignation.expected_revealing_date
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('clearance.request') or 'New'
        records = super().create(vals_list)
        return records
    
    @api.depends('final_document')
    def _compute_document_exists(self):
        for record in self:
            record.document_exists = bool(record.final_document)



    def _is_manager(self):
        """Check if current user is the manager of this request"""
        self.ensure_one()
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee and employee.id == self.manager_id.id
    
    def action_submit(self):
        for rec in self:
            if rec.state == 'draft':
                rec.write({
                    'state': 'pending',  # Now means "Pending Manager Approval"
                })
                # Create activity for manager
                rec._create_manager_notification()
        return True
    
    def _create_manager_notification(self):
        if not self.manager_id or not self.manager_id.user_id:
            return
            
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'clearance.request')], limit=1)
        activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Manager Clearance Approval')], limit=1)
        if not activity_type_id:
            activity_type_id = self.env['mail.activity.type'].sudo().create({
                'name': 'Manager Clearance Approval',
            })
        
        activity_vals = {
            'res_model_id': model_id.id,
            'res_model': 'clearance.request',
            'res_id': self.id,
            'res_name': 'Clearance Request For Manager Approval',
            'user_id': self.manager_id.user_id.id,
            'activity_type_id': activity_type_id.id,
            'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')
        }
        self.env['mail.activity'].sudo().create(activity_vals)


    def action_manager_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("The record must be in 'Pending Manager Approval' state to be approved by manager."))
        
        # Check if current user is the manager
        if not self._is_manager() and not self.env.user.has_group('hr.group_hr_manager'):
            raise AccessError(_("Only the employee's manager can approve this request."))
        
        self.write({'state': 'manager_approve'})
        self.message_post(body=_("Clearance Request approved by manager %s.") % self.env.user.name)
        
        # Clear manager activity
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'clearance.request'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.uid),
            ('activity_type_id.name', '=', 'Manager Clearance Approval')
        ])
        if activity:
            activity.action_done()
        
        # Create approval history records for department groups
        approval_history_values = []
        
        # Get users from all department groups
        finance_group = self.env.ref('hr_request_portal.group_finance_admin', raise_if_not_found=False)
        it_group = self.env.ref('hr_request_portal.group_it_admin', raise_if_not_found=False)
        hr_group = self.env.ref('hr_request_portal.group_hr_admin', raise_if_not_found=False)
        
        # Add finance users
        if finance_group and finance_group.users:
            for user in finance_group.users:
                approval_history_values.append((0, 0, {
                    'user_id': user.id,
                    'department': 'finance'
                }))
        
        # Add IT users
        if it_group and it_group.users:
            for user in it_group.users:
                approval_history_values.append((0, 0, {
                    'user_id': user.id,
                    'department': 'it'
                }))
        
        # Add HR users
        if hr_group and hr_group.users:
            for user in hr_group.users:
                approval_history_values.append((0, 0, {
                    'user_id': user.id,
                    'department': 'hr'
                }))
        
        self.write({
            'approval_history_ids': approval_history_values
        })
        
        # Create notifications for department users
        self._create_department_notifications()
        
        return True
    
    def _create_department_notifications(self):
        """Create activities for department users"""
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'clearance.request')], limit=1)
        activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Department Clearance Approval')], limit=1)
        if not activity_type_id:
            activity_type_id = self.env['mail.activity.type'].create({
                'name': 'Department Clearance Approval',
            })
        
        # Create activities for all users in approval history
        for approval in self.approval_history_ids:
            activity_vals = {
                'res_model_id': model_id.id,
                'res_model': 'clearance.request',
                'res_id': self.id,
                'res_name': 'Clearance Request - Department Approval Required',
                'user_id': approval.user_id.id,
                'activity_type_id': activity_type_id.id,
                'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M'),
                'note': _('Please review and approve the clearance request for department: %s') % approval.department.upper()
            }
            self.env['mail.activity'].sudo().create(activity_vals)

    def action_department_approve(self):
        """Approve from department perspective"""
        self.ensure_one()
        if self.state != 'manager_approve':
            raise UserError(_("Manager must approve the request first."))
            
        # Check if user belongs to any department group
        user = self.env.user
        is_finance_user = user.has_group('hr_request_portal.group_finance_admin')
        is_it_user = user.has_group('hr_request_portal.group_it_admin')
        is_hr_user = user.has_group('hr_request_portal.group_hr_admin')
        
        if not (is_finance_user or is_it_user or is_hr_user):
            raise AccessError(_("You do not have the necessary department permissions to approve this record."))
        
        # Update approval history for current user
        for approval_history in self.approval_history_ids:
            if approval_history.user_id.id == self.env.uid:
                approval_history.write({
                    'status': 'approve', 
                    'date_done': datetime.now()
                })
                
                # Clear the activity for this user
                activity = self.env['mail.activity'].search([
                    ('res_model', '=', 'clearance.request'),
                    ('res_id', '=', self.id),
                    ('user_id', '=', self.env.uid),
                    ('activity_type_id.name', '=', 'Department Clearance Approval')
                ])
                
                if activity:
                    activity.action_done()
        
        # Check if all departments have approved
        self._check_all_departments_approved()
        
        self.message_post(body=_("Clearance Request approved by %s.") % self.env.user.name)
        return True
    
    def action_department_reject(self):
        """Reject from department perspective"""
        self.ensure_one()
        if self.state != 'manager_approve':
            raise UserError(_("This action is only allowed in 'Pending Department Approval' state."))
            
        # Check if user belongs to any department group
        user = self.env.user
        is_finance_user = user.has_group('hr_request_portal.group_finance_admin')
        is_it_user = user.has_group('hr_request_portal.group_it_admin')
        is_hr_user = user.has_group('hr_request_portal.group_hr_admin')
        
        if not (is_finance_user or is_it_user or is_hr_user):
            raise AccessError(_("You do not have the necessary department permissions to reject this record."))
        
        # Determine which department is rejecting
        rejecting_department = None
        if is_finance_user:
            rejecting_department = 'finance'
        elif is_it_user:
            rejecting_department = 'it'
        elif is_hr_user:
            rejecting_department = 'hr'
        
        # Update approval history for current user
        for approval_history in self.approval_history_ids:
            if approval_history.user_id.id == self.env.uid:
                approval_history.write({
                    'status': 'reject', 
                    'date_done': datetime.now()
                })
                
                # Clear the activity for this user
                activity = self.env['mail.activity'].search([
                    ('res_model', '=', 'clearance.request'),
                    ('res_id', '=', self.id),
                    ('user_id', '=', self.env.uid),
                    ('activity_type_id.name', '=', 'Department Clearance Approval')
                ])
                
                if activity:
                    activity.action_done()
        
        # Clear all other department activities
        all_activities = self.env['mail.activity'].search([
            ('res_model', '=', 'clearance.request'),
            ('res_id', '=', self.id),
            ('activity_type_id.name', '=', 'Department Clearance Approval')
        ])
        if all_activities:
            all_activities.action_done()
        
        # Update the request state and track which department rejected
        self.write({
            'state': 'reject',
            'rejected_by_department': rejecting_department
        })
        
        self.message_post(body=_("Clearance Request rejected by %s department (%s).") % (
            rejecting_department.upper(), self.env.user.name))
        return True
    
    # def _check_all_departments_approved(self):
    #     """Check if all required departments have approved"""
    #     # Get approval status by department
    #     finance_approvals = self.approval_history_ids.filtered(lambda r: r.department == 'finance')
    #     it_approvals = self.approval_history_ids.filtered(lambda r: r.department == 'it')
    #     hr_approvals = self.approval_history_ids.filtered(lambda r: r.department == 'hr')
        
    #     # Check if at least one user from each department has approved
    #     finance_approved = any(approval.status == 'approve' for approval in finance_approvals) if finance_approvals else True
    #     it_approved = any(approval.status == 'approve' for approval in it_approvals) if it_approvals else True
    #     hr_approved = any(approval.status == 'approve' for approval in hr_approvals) if hr_approvals else True
        
    #     # Update department approval flags
    #     self.write({
    #         'finance_approved': finance_approved,
    #         'it_approved': it_approved,
    #         'hr_approved': hr_approved,
    #     })
        
    #     # If all departments have approved, mark as fully approved
    #     if finance_approved and it_approved and hr_approved:
    #         self.write({
    #             'state': 'approve',
    #         })
    #         self.message_post(body=_("Clearance Request fully approved by all departments."))

    def _check_all_departments_approved(self):
        """Check if all required departments have approved"""
        for rec in self:
            # Get approval status by department
            finance_approvals = rec.approval_history_ids.filtered(lambda r: r.department == 'finance')
            it_approvals = rec.approval_history_ids.filtered(lambda r: r.department == 'it')
            hr_approvals = rec.approval_history_ids.filtered(lambda r: r.department == 'hr')
            
            # Check if at least one user from each department has approved
            finance_approved = any(approval.status == 'approve' for approval in finance_approvals) if finance_approvals else True
            it_approved = any(approval.status == 'approve' for approval in it_approvals) if it_approvals else True
            hr_approved = any(approval.status == 'approve' for approval in hr_approvals) if hr_approvals else True
            
            # Update department approval flags
            rec.write({
                'finance_approved': finance_approved,
                'it_approved': it_approved,
                'hr_approved': hr_approved,
            })
            
            # If all departments have approved, mark as fully approved
            if finance_approved and it_approved and hr_approved:
                rec.write({'state': 'approve'})
                rec.message_post(body=_("✅ Clearance Request fully approved by all departments."))

                # ----------------------------------------
                # ✨ Notify manager and request creator
                # ----------------------------------------
                manager_partner = rec.manager_id.user_id.partner_id if rec.manager_id.user_id else False
                creator_partner = rec.create_uid.partner_id if rec.create_uid else False
                notify_partners = []

                if manager_partner:
                    notify_partners.append(manager_partner.id)
                if creator_partner and creator_partner.id not in notify_partners:
                    notify_partners.append(creator_partner.id)

                if notify_partners:
                    rec.message_post(
                        body=_("All departments have approved the Clearance Request.<br/>"
                            "Please Final submit the request to complete the process."),
                        partner_ids=notify_partners
                    )

                # Optional: Add activity to remind them
                activity_type = self.env.ref('mail.mail_activity_data_todo')
                deadline = fields.Date.today()
                for partner_id in notify_partners:
                    user = self.env['res.users'].search([('partner_id', '=', partner_id)], limit=1)
                    if user:
                        self.env['mail.activity'].create({
                            'res_model_id': self.env['ir.model']._get_id('clearance.request'),
                            'res_id': rec.id,
                            'user_id': user.id,
                            'activity_type_id': activity_type.id,
                            'summary': 'Final Submit Required',
                            'note': 'All departments approved. Please Final submit the request to complete the process.',
                            'date_deadline': deadline
                        })

    def action_reject(self):
        self.ensure_one()
        
        # Manager rejection (pending state)
        if self.state == 'pending':
            # Check if current user is the manager or has admin rights
            if not self._is_manager() and not self.env.user.has_group('hr.group_hr_manager'):
                raise AccessError(_("Only the employee's manager can reject this request at this stage."))
                
            self.write({'state': 'reject'})
            self.message_post(body=_("Clearance Request rejected by manager %s.") % self.env.user.name)
            
            # Clear manager activity
            activity = self.env['mail.activity'].search([
                ('res_model', '=', 'clearance.request'),
                ('res_id', '=', self.id),
                ('user_id', '=', self.env.uid),
                ('activity_type_id.name', '=', 'Manager Clearance Approval')
            ])
            if activity:
                activity.action_done()
            return True
        
        raise UserError(_("This action is not allowed in the current state."))

    
    
    # def action_manager_approve(self):
    #     self.ensure_one()
    #     if self.state != 'pending':
    #         raise UserError(_("The record must be in 'Pending Manager Approval' state to be approved by manager."))
        
    #     # Check if current user is the manager
    #     if not self._is_manager() and not self.env.user.has_group('hr.group_hr_manager'):
    #         raise AccessError(_("Only the employee's manager can approve this request."))
        
    #     self.write({'state': 'manager_approve'})
    #     self.message_post(body=_("Clearance Request approved by manager %s.") % self.env.user.name)
        
    #     # Clear manager activity
    #     activity = self.env['mail.activity'].search([
    #         ('res_model', '=', 'clearance.request'),
    #         ('res_id', '=', self.id),
    #         ('user_id', '=', self.env.uid),
    #         ('activity_type_id.name', '=', 'Manager Clearance Approval')
    #     ])
    #     if activity:
    #         activity.action_done()
        
    #     # Create approver activities and records only after manager approval
    #     approval_history_values = []
    #     clearance_approver_group = self.env.ref("hr_request_portal.group_clearance_approver", raise_if_not_found=False)
        
    #     if clearance_approver_group and clearance_approver_group.users:
    #         for user in clearance_approver_group.users:
    #             approval_history_values.append((0, 0, {
    #                 'user_id': user.id,
    #             }))
        
    #     self.write({
    #         'approval_history_ids': approval_history_values
    #     })
        
    #     self._create_approver_notifications()
        
    #     return True
    
    # def _create_approver_notifications(self):
    #     model_id = self.env['ir.model'].sudo().search([('model', '=', 'clearance.request')], limit=1)
    #     activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Clearance Request To Approve')], limit=1)
    #     if not activity_type_id:
    #         activity_type_id = self.env['mail.activity.type'].create({
    #             'name': 'Clearance Request To Approve',
    #         })
        
    #     clearance_approver_group = self.env.ref("hr_request_portal.group_clearance_approver", raise_if_not_found=False)
        
    #     if clearance_approver_group:
    #         for user in clearance_approver_group.users:
    #             activity_vals = {
    #                 'res_model_id': model_id.id,
    #                 'res_model': 'clearance.request',
    #                 'res_id': self.id,
    #                 'res_name': 'Clearance Request To Approve',
    #                 'user_id': user.id,
    #                 'activity_type_id': activity_type_id.id,
    #                 'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')
    #             }
    #             self.env['mail.activity'].sudo().create(activity_vals)

    # def action_approve(self):
    #     self.ensure_one()
    #     if self.state != 'manager_approve':
    #         raise UserError(_("Manager must approve the request first."))
            
    #     is_approver = False
    #     approver_group = self.env.ref("hr_request_portal.group_clearance_approver", raise_if_not_found=False)
    #     if approver_group and self.env.user in approver_group.users:
    #         is_approver = True
        
    #     if not is_approver:
    #         raise AccessError(_("You do not have the necessary permissions to approve this record."))
        
    #     for approval_history in self.approval_history_ids:
    #         if approval_history.user_id.id == self.env.uid:
    #             approval_history.write({
    #                 'status': 'approve', 
    #                 'date_done': datetime.now()
    #             })
                
    #             activity = self.env['mail.activity'].search([
    #                 ('res_model', '=', 'clearance.request'),
    #                 ('res_id', '=', self.id),
    #                 ('user_id', '=', self.env.uid),
    #                 ('activity_type_id.name', '=', 'Clearance Request To Approve')
    #             ])
                
    #             if activity:
    #                 activity.action_done()
        
    #     total_approvers = len(self.approval_history_ids)
    #     approved_count = len(self.approval_history_ids.filtered(lambda r: r.status == 'approve'))
        
    #     if approved_count == total_approvers:
    #         self.write({
    #             'state': 'approve',
    #         })
    #         self.message_post(body=_("Clearance Request fully approved."))
    #     else:
    #         self.message_post(body=_("Clearance Request approved by %s.") % self.env.user.name)
    

    # def action_reject(self):
    #     self.ensure_one()
        
    #     # Manager rejection (pending state)
    #     if self.state == 'pending':
    #         # Check if current user is the manager or has admin rights
    #         if not self._is_manager() and not self.env.user.has_group('hr.group_hr_manager'):
    #             raise AccessError(_("Only the employee's manager can reject this request at this stage."))
                
    #         self.write({'state': 'reject'})
    #         self.message_post(body=_("Clearance Request rejected by manager %s.") % self.env.user.name)
            
    #         # Clear manager activity
    #         activity = self.env['mail.activity'].search([
    #             ('res_model', '=', 'clearance.request'),
    #             ('res_id', '=', self.id),
    #             ('user_id', '=', self.env.uid),
    #             ('activity_type_id.name', '=', 'Manager Clearance Approval')
    #         ])
    #         if activity:
    #             activity.action_done()
    #         return True
        
    #     # Group approvers rejection (manager_approve state)
    #     if self.state == 'manager_approve':
    #         is_approver = False
    #         approver_group = self.env.ref("hr_request_portal.group_clearance_approver", raise_if_not_found=False)
    #         if approver_group and self.env.user in approver_group.users:
    #             is_approver = True
            
    #         if not is_approver:
    #             raise AccessError(_("You do not have the necessary permissions to reject this record."))
            
    #         for approval_history in self.approval_history_ids:
    #             if approval_history.user_id.id == self.env.uid:
    #                 approval_history.write({
    #                     'status': 'reject', 
    #                     'date_done': datetime.now()
    #                 })
                    
    #                 activity = self.env['mail.activity'].search([
    #                     ('res_model', '=', 'clearance.request'),
    #                     ('res_id', '=', self.id),
    #                     ('user_id', '=', self.env.uid),
    #                     ('activity_type_id.name', '=', 'Clearance Request To Approve')
    #                 ])
                    
    #                 if activity:
    #                     activity.action_done()
            
    #         self.write({
    #             'state': 'reject',
    #         })
    #         self.message_post(body=_("Clearance Request rejected by %s.") % self.env.user.name)
    #         return True
        
    #     raise UserError(_("This action is not allowed in the current state."))
        
    def action_final_submit(self):
        self.ensure_one()
        self.write({'state': 'submit'})
        return True

    def action_draft(self):
        self.ensure_one()
        self.write({
            'state': 'draft', 
            'approval_history_ids': [(5, 0, 0)],
            'finance_approved': False,
            'it_approved': False,
            'hr_approved': False,
            'rejected_by_department': False,
        })
        return True
    

class ClearanceApprovalHistory(models.Model):
    _name = 'clearance.approval.history'
    _description = 'Clearance Request Approval History'
    _order = 'date_done desc'
    
    clearance_id = fields.Many2one('clearance.request', string="Clearance Request")
    user_id = fields.Many2one('res.users', string="Approver")
    department = fields.Selection([
        ('finance', 'Finance & Admin'),
        ('it', 'Information Technology'),
        ('hr', 'Human Resources')
    ], string="Department")
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approve', 'Approved'),
        ('reject', 'Rejected')], 
        default='pending', 
        copy=False, 
        string="Approval Status"
    )
    date_done = fields.Datetime(string="Approval Date")

