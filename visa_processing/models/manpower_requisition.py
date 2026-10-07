from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError
from odoo.exceptions import ValidationError
from datetime import datetime

class ManpowerRequisition(models.Model):
    _name = 'manpower.requisition'
    _description = 'Manpower Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'requisition_number desc'
    _rec_name = 'requisition_number'
    
    requisition_number = fields.Char(
        string='Requisition Number',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('manpower.requisition') or 'New'
    )
    request_date = fields.Date(string='Requisition Date', default=fields.Date.today)  
    description = fields.Char(string='Description') 
    branch_id = fields.Many2one('res.branch',string='Department/Business Unit')
    requisition_line_ids = fields.One2many(
        'manpower.requisition.line',
        'requisition_id',
        string='Position Requirements'
    )
    applicant_ids = fields.One2many(
        'hr.applicant', 
        'requisition_id', 
        string='Job Applications'
    )
    reject_reason = fields.Text(string="Reject Reason", readonly=True)
    state = fields.Selection([
        ('new', 'New'), 
        ('pending', 'Pending'), 
        ('approved', 'Approved'), 
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'), 
        ('reject', 'Rejected')
    ], string='State', default='new', track_visibility='onchange')
    is_approved = fields.Boolean(string="Is Approved", default=False)
    users_count = fields.Integer(string="Users Count", compute="_compute_users_count")
    
    approval_history_ids = fields.One2many(
        'manpower.approval.history',
        'requisition_id',
        string="Approval History"
    )

    current_approver_id = fields.Many2one(
        'res.users',
        string="Current Approver",
        compute='_compute_current_approver',
        store=True
    )

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.requisition_number} {rec.description or ''}".strip()
            result.append((rec.id, name))
        return result


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('requisition_number', 'New') == 'New':
                vals['requisition_number'] = self.env['ir.sequence'].next_by_code('manpower.requisition') or 'New'
                
        records = super().create(vals_list)    
        return records
    
    @api.depends('state')
    def _compute_users_count(self):
        for record in self:
            if record.message_partner_ids:
                count = len(record.message_partner_ids.ids)
                record.users_count = count
            else:
                record.users_count = 0
    

    @api.depends('approval_history_ids.status')
    def _compute_current_approver(self):
        for request in self:
            if request.state != 'pending':
                request.current_approver_id = False
                continue
                
            pending_approval = request.approval_history_ids.filtered(
                lambda h: h.status == 'pending'
            ).sorted(key=lambda h: h.sequence)
            
            if pending_approval:
                request.current_approver_id = pending_approval[0].user_id
            else:
                request.current_approver_id = False
    

    def action_submit(self):
        for rec in self:
            if rec.state == 'new':
                branch_approvers = self.env['branch.approvers'].search([
                    ('branch_id', '=', rec.branch_id.id)
                ], limit=1)
                
                approval_users = []
                if branch_approvers and branch_approvers.approver_line_ids:
                    approval_users = branch_approvers.approver_line_ids.sorted('sequence').mapped('user_id')
                else:
                    approved_group = self.env.ref("visa_processing.manpower_requisition_approved_group", raise_if_not_found=False)
                    if approved_group:
                        approval_users = approved_group.users
                
                approval_history_values = []
                for sequence, user in enumerate(approval_users, start=1):
                    approval_history_values.append((0, 0, {
                        'user_id': user.id,
                        'status': 'pending' if sequence == 1 else 'waiting',
                        'sequence': sequence,
                    }))
                
                rec.write({
                    'state': 'pending',
                    'approval_history_ids': approval_history_values
                })
                
                if approval_history_values:
                    self._notify_current_approver(rec)
        return True
    
    def _notify_current_approver(self, request):
        """Notify only the current approver based on sequence"""
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'manpower.requisition')], limit=1)
        activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Manpower Requisition To Approve')], limit=1)
        if not activity_type_id:
            activity_type_id = self.env['mail.activity.type'].create({
                'name': 'Manpower Requisition To Approve',
            })

        current_approval = request.approval_history_ids.filtered(
            lambda h: h.status in ('pending', 'waiting')
        ).sorted(key=lambda h: h.sequence)
        
        if not current_approval:
            return
            
        current_approval = current_approval[0]
        current_approval.status = 'pending'
        
        activity_vals = {
            'res_model_id': model_id.id,
            'res_model': 'manpower.requisition',
            'res_id': request.id,
            'summary': 'Manpower Requisition To Approve',
            'note': f'Please review and approve the manpower requisition {request.requisition_number}',
            'user_id': current_approval.user_id.id,
            'activity_type_id': activity_type_id.id,
            'date_deadline': fields.Date.today()
        }
        self.env['mail.activity'].sudo().create(activity_vals)

    
    def action_approve(self):
        self.ensure_one()
        current_approval = self.approval_history_ids.filtered(
            lambda h: h.user_id == self.env.user and h.status in ('pending', 'approved')
        )
        
        if not current_approval:
            raise AccessError(_("You are not authorized to approve this request at this time."))
            
        if current_approval[0].status == 'approved':
            raise UserError(_("You have already approved this request."))
            
        current_approval = current_approval[0]
        current_approval.write({
            'status': 'approved',
            'date_done': datetime.now()
        })
        
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'manpower.requisition'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.uid),
            ('activity_type_id.name', '=', 'Manpower Requisition To Approve')
        ])
        if activity:
            activity.action_done()
        
        next_approval = self.approval_history_ids.filtered(
            lambda h: h.status == 'waiting'
        ).sorted(key=lambda h: h.sequence)
        
        if next_approval:
            self._notify_current_approver(self)
            self.message_post(body=f"Manpower Requisition approved by {self.env.user.name}. Sent to next approver.")
        else:
            self.write({
                'state': 'approved',
                'is_approved': True
            })
            self.message_post(body=f"Manpower Requisition fully approved by {self.env.user.name}.")

    def action_reject(self):
        self.ensure_one()
        current_approval = self.approval_history_ids.filtered(
            lambda h: h.user_id == self.env.user and h.status == 'pending'
        )
        
        if not current_approval:
            raise AccessError(_("You are not authorized to reject this request at this time."))
            
        current_approval = current_approval[0]
        current_approval.write({
            'status': 'rejected',
            'date_done': datetime.now()
        })
        
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'manpower.requisition'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.uid),
            ('activity_type_id.name', '=', 'Manpower Requisition To Approve')
        ])
        if activity:
            activity.action_done()
        
        self.write({
            'state': 'reject',
            'is_approved': False
        })
        self.message_post(body=f"Manpower Requisition rejected by {self.env.user.name}.")

    def action_open_reject_wizard(self):
        self.ensure_one()
        
        current_approval = self.approval_history_ids.filtered(
            lambda h: h.user_id == self.env.user and h.status == 'pending'
        )
        
        if not current_approval:
            raise AccessError(_("You are not authorized to reject this request at this time."))
        
        return {
            'name': _('Reject Manpower Requisition'),
            'type': 'ir.actions.act_window',
            'res_model': 'manpower.requisition.reject',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'manpower.requisition',
                'default_reject_reason': self.reject_reason or '',
            }
        }
            
    
    def action_in_progress(self):
        for rec in self:
            rec.state = 'in_progress'
            
    def action_completed(self):
        for rec in self:
            rec.state = 'completed'


    
class ManpowerRequisitionLine(models.Model):
    _name = 'manpower.requisition.line'
    _description = 'Manpower Requisition Details'
    _rec_name = 'job_id'
    
    requisition_id = fields.Many2one('manpower.requisition', string='Requisition', ondelete='cascade')
    job_id = fields.Many2one('hr.job', string='Position/Category', required=True)
    specification = fields.Text(string='Specification')
    quantity = fields.Integer(string="Quantity")
    required_date = fields.Date(string='Required By Date')
    remark = fields.Text(string="Remarks")
    requisition_closed_date = fields.Date(string='Requisition Closed Date')
    hr_remarks = fields.Text(string="HR Remarks")
    applicant_ids = fields.One2many(
        'hr.applicant',
        'requisition_line_id',
        string='Job Applications'
    )
    hired_count = fields.Integer(
        string='Hired Count',
        compute='_compute_hired_count',
        store=True,
        help='Number of hired applicants for this position'
    )

    remaining_count = fields.Integer(
        string='Remaining',
        compute='_compute_remaining_count',
        store=True,
        help='Remaining positions to fill'
    )

    @api.depends('requisition_id', 'job_id')
    def _compute_hired_count(self):
        for line in self:
            line.hired_count = self.env['hr.applicant'].search_count([
                ('requisition_number', '=', line.requisition_id.id),
                ('job_id', '=', line.job_id.id),
                ('application_status', '=', 'hired')
            ])

    @api.depends('quantity', 'hired_count')
    def _compute_remaining_count(self):
        for line in self:
            line.remaining_count = line.quantity - line.hired_count


    def create_manager_notification(self, res):
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'manpower.requisition')], limit=1)
        activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Manpower Requisition To Approve')], limit=1)
        if not activity_type_id:
            activity_type_id = self.env['mail.activity.type'].create({
                'name': 'Manpower Requisition To Approve',
            })

        branch_approvers = self.env['branch.approvers'].sudo().search([
            ('branch_id', '=', res.branch_id.id)
        ], limit=1)
        
        users_to_notify = []
        if branch_approvers and branch_approvers.user_ids:
            users_to_notify = branch_approvers.user_ids
        else:
            approver_group = self.env.ref("visa_processing.manpower_requisition_approved_group", raise_if_not_found=False)
            if approver_group:
                users_to_notify = approver_group.users
        
        for user in users_to_notify:
            activity_vals = {
                'res_model_id': model_id.id,
                'res_model': 'manpower.requisition',
                'res_id': res.id,
                'res_name': 'Manpower Requisition To Approve',
                'user_id': user.id,
                'activity_type_id': activity_type_id.id,
                'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')
            }
            self.env['mail.activity'].sudo().create(activity_vals)

        
class HrApplicant(models.Model):
    _inherit = 'hr.applicant'
    
    requisition_id = fields.Many2one(
        'manpower.requisition',
        string='Manpower Requisition',
        tracking=True
    )
    requisition_line_id = fields.Many2one(
        'manpower.requisition.line',
        string='Requisition Position',
        tracking=True
    )
    requisition_number = fields.Many2one(
        'manpower.requisition',
        string='Requisition Number',
        domain=lambda self: [('state', '=', 'in_progress')])
    
    birth_date = fields.Date(string='Date of Birth', tracking=True)
    salary_line_ids = fields.One2many(
        'hr.applicant.salary.line', 
        'applicant_id', 
        string='Salary Components'
    )
    application_status = fields.Selection([('ic', 'Intial Contact'),('approved','Approved'),('hired','Hired')], default='ic',string="Application Status", store=True)

    has_visa_request = fields.Boolean(
        string='Has Visa Request',
        compute='_compute_has_visa_request',
        store=False,  
        help="Technical field to determine if a visa request already exists"
    )

    def _compute_has_visa_request(self):
        visa_requests = self.env['visa.request.application'].search([
            ('recruitment_app_number', 'in', self.ids),
            ('state', 'not in', ['reject', 'cancel'])
        ])
        applicant_visa_map = {visa.recruitment_app_number.id: visa for visa in visa_requests}
        for applicant in self:
            applicant.has_visa_request = applicant.id in applicant_visa_map

    @api.onchange('requisition_number')
    def _onchange_requisition_number(self):
        if self.requisition_number:
            self.requisition_id = self.requisition_number
            self.branch_id = self.requisition_number.branch_id

            return {'domain': {
                'job_id': [('id', 'in', self.requisition_number.requisition_line_ids.job_id.ids)],
                'requisition_line_id': [('requisition_id', '=', self.requisition_number.id)]
            }}
        else:
            self.requisition_id = False
            self.branch_id = False
            self.job_id = False
            self.requisition_line_id = False

    
    @api.onchange('job_id')
    def _onchange_job_id(self):
        if self.requisition_number and self.job_id:
            line = self.env['manpower.requisition.line'].search([
                ('requisition_id', '=', self.requisition_number.id),
                ('job_id', '=', self.job_id.id)
            ], limit=1)
            self.requisition_line_id = line


    def _update_requisition_hired_count(self):
        for applicant in self:
            if applicant.requisition_line_id:
                applicant.requisition_line_id._compute_hired_count()
            elif applicant.requisition_number and applicant.job_id:
                lines = self.env['manpower.requisition.line'].search([
                    ('requisition_id', '=', applicant.requisition_number.id),
                    ('job_id', '=', applicant.job_id.id)
                ])
                lines._compute_hired_count()


    def write(self, vals):
        if 'stage_id' in vals:
            new_stage = self.env['hr.recruitment.stage'].browse(vals['stage_id'])
            for applicant in self:
                current_stage = applicant.stage_id
                if current_stage and current_stage.sequence > new_stage.sequence:
                    raise ValidationError("You cannot move the stage backward!")
        
        res = super(HrApplicant, self).write(vals)
        
        if 'application_status' in vals:
            self._update_requisition_hired_count()
        elif any(field in vals for field in ['requisition_number', 'job_id', 'requisition_line_id']):
            self._update_requisition_hired_count()
    
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_requisition_hired_count()
        return records

        
    def action_open_requisition(self):
        self.ensure_one()
        if not self.requisition_number:
            return
            
        return {
            'name': _('Manpower Requisition'),
            'type': 'ir.actions.act_window',
            'res_model': 'manpower.requisition',
            'res_id': self.requisition_number.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def name_get(self):
        if self._context.get('show_applicant_no'):
            result = []
            for applicant in self:
                name = f"{applicant.applicant_no or ''} - {applicant.name or ''}"
                result.append((applicant.id, name))
            return result
        return super(HrApplicant, self).name_get()
    

    def action_create_visa_request(self):
        self.ensure_one()
        visa_request = self.env['visa.request.application'].search([
            ('recruitment_app_number', '=', self.id),
            ('state', 'not in', ['reject', 'cancel'])
        ], limit=1)
        
        if visa_request:
            return {
                'name': 'Visa Request',
                'type': 'ir.actions.act_window',
                'res_model': 'visa.request.application',
                'view_mode': 'form',
                'res_id': visa_request.id,
                'target': 'current',
            }
        
        return {
            'name': 'Create Visa Request',
            'type': 'ir.actions.act_window',
            'res_model': 'visa.request.application',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_recruitment_app_number': self.id,
                'default_applicant_id': self.id,
                'default_applicant_name': self.partner_name,
                'default_job_position': self.job_id.id if self.job_id else False,
                'default_department_id': self.department_id.id if self.department_id else False,
                'default_company_id': self.company_id.id if self.company_id else False,
                'default_nationality': self.country_id.id if self.country_id else False,
                'default_gender': self.gender if self.gender else False,
            }
        }
    
    @api.onchange('name')
    def _onchange_name_upper(self):
        if self.name:
            self.name = self.name.upper()

    @api.onchange('partner_name')
    def _onchange_partner_name_upper(self):
        if self.partner_name:
            self.partner_name = self.partner_name.upper()


    def create_employee_from_applicant(self):
        action = super(HrApplicant, self).create_employee_from_applicant()

        for applicant in self:
            if action.get('context'):
                ctx = dict(action['context'])
                ctx.pop('default_work_email', None)
                ctx.update({
                    'default_work_email': applicant.email_from,
                    'default_gender': applicant.gender,
                    'default_birthday': applicant.birth_date,
                })

                action['context'] = ctx

        return action
    
    
class HRApplicantSalaryLine(models.Model):
    _name = 'hr.applicant.salary.line'
    _description = 'Applicant Salary Component'
    
    applicant_id = fields.Many2one('hr.applicant', string='Applicant')
    salary_component_id = fields.Many2one('salary.component', string='Salary Component')
    amount = fields.Float(string='Amount')
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                default=lambda self: self.env.company.currency_id)
    notes = fields.Text(string='Notes')

class HRSalaryComponent(models.Model):
    _name = 'salary.component'
    _description = 'Salary Component'
    
    name = fields.Char(string='Name', required=True)
    category = fields.Selection([
        ('basic', 'Basic Salary'),
        ('allowance', 'Allowance'),
        ('bonus', 'Bonus'),
        ('deduction', 'Deduction')], 
        string='Category')
    
class ManpowerApprovalHistory(models.Model):
    _name = 'manpower.approval.history'
    _description = 'Manpower Requisition Approval History'
    _order = 'sequence asc, date_done desc'
    
    requisition_id = fields.Many2one('manpower.requisition', string="Manpower Requisition")
    user_id = fields.Many2one('res.users', string="Approver")
    sequence = fields.Integer(string="Approval Sequence", default=1)
    status = fields.Selection([
        ('waiting', 'Waiting'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')], default='waiting', copy=False, string="Approval Status")
    date_done = fields.Datetime(string="Approval Date")

class BranchApprovers(models.Model):
    _name = 'branch.approvers'
    _description = 'Branch Approvers'
    
    branch_id = fields.Many2one('res.branch', string='Branch', required=True)
    # user_ids = fields.Many2many('res.users', string='Approvers')
    approver_line_ids = fields.One2many(
        'manpower.branch.approver.line', 
        'branch_approver_id', 
        string='Approvers'
    )

class ManpowerBranchApproverLine(models.Model):
    _name = 'manpower.branch.approver.line'
    _description = 'Branch Approver Line'
    _order = 'sequence, id'
    
    branch_approver_id = fields.Many2one('branch.approvers')
    user_id = fields.Many2one('res.users', string='Approver', required=True)
    sequence = fields.Integer(string='Sequence')

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    emp_status = fields.Selection(
        tracking=True,
    )

    joining_date = fields.Date(
        tracking=True,
    )
    

