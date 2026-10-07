from odoo import models, fields, api, _
from odoo.exceptions import AccessError
from datetime import datetime
from dateutil.relativedelta import relativedelta
from math import ceil
from collections import defaultdict
from odoo.exceptions import UserError

class CreditRequest(models.Model):
    _name = 'credit.request'
    _description = 'Customer Credit Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'partner_id'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string="Status", default='draft', tracking=True)

    # 1. Customer Information
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    customer_code = fields.Char(related='partner_id.address_no', string="Customer Code", readonly=True)
    branch_id = fields.Many2one('res.branch', related='partner_id.branch_id', string="Branch", readonly=True)
    customer_type = fields.Selection([
        ('new', 'New Customer'),
        ('existing', 'Existing Customer')
    ], string="Customer Type", default='existing')
    branch_ids = fields.Many2many('res.branch', string="Type of Business with Dulsco")
    dealing_since = fields.Date(
        string="Dealing with Customer Since",
        compute='_compute_dealing_since',
        store=True,
        readonly=False)
    branch_region = fields.Char(string="Customer Branch / Region")
    salesperson_id = fields.Many2one('res.users', related='partner_id.user_id', string="Salesperson", readonly=True)
    collection_manager_id = fields.Many2one('hr.employee', related='partner_id.collection_manager', string="Account Manager", readonly=True)

    # 2. Business History & Performance
    total_business_amount = fields.Float(string="Total Business Till Date (QAR)", compute='_compute_avg_monthly_business',store=True,)
    avg_monthly_business = fields.Float(string="Average Monthly Business (QAR)",compute='_compute_avg_monthly_business',store=True,)
    last_payment_date = fields.Date(string="Last Payment Received Date", compute='_compute_last_payment_date',store=True)
    payment_term_id = fields.Many2one('account.payment.term', related='partner_id.property_payment_term_id', string="Current Payment Terms", readonly=False, store=True)
    grade_id = fields.Many2one('grade.type', related='partner_id.grade_id', string="Customer Rating", readonly=False, store=True)

    # 3. Credit Request Details
    requested_credit_limit = fields.Float(string="Requested Credit Limit (QAR)")
    current_credit_limit = fields.Float(related='partner_id.credit_limit', string="Current Credit Limit (QAR)", readonly=True)
    requested_payment_term_id = fields.Many2one('account.payment.term', string="Requested Payment Terms")
    reason = fields.Text(string="Reason for Credit Limit Request")
    attachment_ids = fields.Many2many('ir.attachment', string="Supporting Documents")
    requested_by = fields.Many2one('res.users', default=lambda self: self.env.user, string="Requested By", readonly=True)

    # 4. Internal Approval Workflow
    approved_credit_limit = fields.Float(string="Approved Credit Limit (QAR)", copy=False)
    approved_payment_term_id = fields.Many2one('account.payment.term', string="Approved Payment Terms", copy=False)
    approval_date = fields.Date(string="Approval Date", default=lambda self: fields.Date.today(), copy=False)
    approval_remarks = fields.Text(string="Remarks / Final Decision Notes")

    approval_history_ids = fields.One2many(
        'credit.approval.history', 
        'credit_request_id', 
        string="Approval History"
    )
    approval_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string="Approval Status", default='pending', tracking=True)


    current_approver_id = fields.Many2one(
        'res.users',
        string="Current Approver",
        compute='_compute_current_approver',
        store=True
    )

    
    @api.depends('approval_history_ids.status')
    def _compute_current_approver(self):
        for request in self:
            if request.state != 'under_review':
                request.current_approver_id = False
                continue
                
            pending_approval = request.approval_history_ids.filtered(
                lambda h: h.status == 'pending'
            ).sorted(key=lambda h: h.sequence)
            
            if pending_approval:
                request.current_approver_id = pending_approval[0].user_id
            else:
                request.current_approver_id = False

    @api.depends('partner_id')
    def _compute_dealing_since(self):
        for record in self:
            if record.partner_id:
                first_so = self.env['sale.order'].search(
                    [('partner_id', '=', record.partner_id.id)],
                    order='date_order asc',
                    limit=1
                )
                record.dealing_since = first_so.date_order.date() if first_so and first_so.date_order else False
            else:
                record.dealing_since = False

    @api.depends('partner_id', 'total_business_amount')
    def _compute_avg_monthly_business(self):
        for record in self:
            if not record.partner_id:
                record.avg_monthly_business = 0.0
                continue

            if not record.total_business_amount:
                invoices = self.env['account.move'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted')
                ])
                record.total_business_amount = sum(invoices.mapped('amount_total'))

            if record.total_business_amount <= 0:
                record.avg_monthly_business = 0.0
                continue

            invoices = self.env['account.move'].search([
                ('partner_id', '=', record.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted')
            ], order="invoice_date asc")

            if not invoices:
                record.avg_monthly_business = 0.0
                continue

            first_invoice = invoices[0]
            last_invoice = invoices[-1]
            
            first_date = first_invoice.invoice_date or first_invoice.create_date.date()
            last_date = last_invoice.invoice_date or last_invoice.create_date.date()

            delta = relativedelta(last_date, first_date)
            month_diff = delta.years * 12 + delta.months
            # If there are any extra days, add 1 more month (ceiling effect)
            if delta.days > 0 or (delta.years == 0 and delta.months == 0):
                month_diff += 1
            month_diff = max(month_diff, 1)

            
            # delta = relativedelta(last_date, first_date)
            # month_diff = delta.years * 12 + delta.months
            # month_diff = max(month_diff, 1)

            record.avg_monthly_business = record.total_business_amount / month_diff


    @api.depends('partner_id')
    def _compute_last_payment_date(self):
        for record in self:
            if not record.partner_id:
                record.last_payment_date = False
                continue
            
            last_payment = self.env['account.payment'].search([
                ('partner_id', '=', record.partner_id.id),
                ('state', '=', 'posted'),
                ('payment_type', '=', 'inbound')  
            ], order='receipt_date desc', limit=1)
            
            record.last_payment_date = last_payment.receipt_date if last_payment else False


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'requested_credit_limit' in vals and 'approved_credit_limit' not in vals:
                vals['approved_credit_limit'] = vals['requested_credit_limit']
            if 'requested_payment_term_id' in vals and 'approved_payment_term_id' not in vals:
                vals['approved_payment_term_id'] = vals['requested_payment_term_id']
        return super().create(vals_list)

    @api.onchange('requested_credit_limit')
    def _onchange_requested_credit_limit(self):
        if not self.approved_credit_limit: 
            self.approved_credit_limit = self.requested_credit_limit

    @api.onchange('requested_payment_term_id')
    def _onchange_requested_payment_term(self):
        if not self.approved_payment_term_id: 
            self.approved_payment_term_id = self.requested_payment_term_id


    def action_submit(self):
        for rec in self:
            if rec.state == 'draft':
                branch_approvers = self.env['credit.branch.approvers'].search([
                    ('branch_id', '=', rec.branch_id.id)
                ], limit=1)
                
                approval_users = []
                if branch_approvers and branch_approvers.approver_line_ids:
                    # Get users in the specified order
                    approval_users = branch_approvers.approver_line_ids.sorted('sequence').mapped('user_id')
                else:
                    approved_group = self.env.ref("credit_control.credit_request_approved_group", raise_if_not_found=False)
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
                    'state': 'under_review',
                    'approval_status': 'pending',
                    'approval_history_ids': approval_history_values
                })
                
                if approval_history_values:
                    self._notify_current_approver(rec)
        return True

    
    def _notify_current_approver(self, request):
        """Notify only the current approver based on sequence"""
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'credit.request')], limit=1)
        activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Credit Request To Approve')], limit=1)
        if not activity_type_id:
            activity_type_id = self.env['mail.activity.type'].create({
                'name': 'Credit Request To Approve',
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
            'res_model': 'credit.request',
            'res_id': request.id,
            'summary': 'Credit Request To Approve',
            'note': f'Please review and approve the credit request for {request.partner_id.name}',
            'user_id': current_approval.user_id.id,
            'activity_type_id': activity_type_id.id,
            'date_deadline': fields.Date.today()
        }
        self.env['mail.activity'].sudo().create(activity_vals)

    

    # def action_approve(self):
    #     self.ensure_one()
    #     current_approval = self.approval_history_ids.filtered(
    #         lambda h: h.user_id == self.env.user and h.status == 'pending'
    #     )
        
    #     if not current_approval:
    #         raise AccessError(_("You are not authorized to approve this request at this time."))
            
    #     current_approval = current_approval[0]
    #     current_approval.write({
    #         'status': 'approved',
    #         'date_done': datetime.now()
    #     })
    #     activity = self.env['mail.activity'].search([
    #         ('res_model', '=', 'credit.request'),
    #         ('res_id', '=', self.id),
    #         ('user_id', '=', self.env.uid),
    #         ('activity_type_id.name', '=', 'Credit Request To Approve')
    #     ])
    #     if activity:
    #         activity.action_done()
        
    #     next_approval = self.approval_history_ids.filtered(
    #         lambda h: h.status == 'waiting'
    #     ).sorted(key=lambda h: h.sequence)
        
    #     if next_approval:
    #         self._notify_current_approver(self)
    #         self.message_post(body=f"Credit Request approved by {self.env.user.name}. Sent to next approver.")
    #     else:
    #         self.write({
    #             'state': 'approved',
    #             'approval_status': 'approved',
    #             'approval_date': fields.Date.today()
    #         })
    #         self.partner_id.write({
    #             'credit_limit': self.approved_credit_limit,
    #             'property_payment_term_id': self.approved_payment_term_id.id
    #         })
    #         self.message_post(body=f"Credit Request fully approved by {self.env.user.name}.")

    def action_approve(self):
        self.ensure_one()
        current_approval = self.approval_history_ids.filtered(
            lambda h: h.user_id == self.env.user and h.status in ('pending', 'approved')
        )
        
        if not current_approval:
            raise AccessError(_("You are not authorized to approve this request at this time."))
            
        # Check if already approved by this user
        if current_approval[0].status == 'approved':
            raise UserError(_("You have already approved this request."))
            
        current_approval = current_approval[0]
        current_approval.write({
            'status': 'approved',
            'date_done': datetime.now()
        })
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'credit.request'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.uid),
            ('activity_type_id.name', '=', 'Credit Request To Approve')
        ])
        if activity:
            activity.action_done()
        
        next_approval = self.approval_history_ids.filtered(
            lambda h: h.status == 'waiting'
        ).sorted(key=lambda h: h.sequence)
        
        if next_approval:
            self._notify_current_approver(self)
            self.message_post(body=f"Credit Request approved by {self.env.user.name}. Sent to next approver.")
        else:
            self.write({
                'state': 'approved',
                'approval_status': 'approved',
                'approval_date': fields.Date.today()
            })
            self.partner_id.write({
                'credit_limit': self.approved_credit_limit,
                'property_payment_term_id': self.approved_payment_term_id.id
            })
            self.message_post(body=f"Credit Request fully approved by {self.env.user.name}.")



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
            ('res_model', '=', 'credit.request'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.uid),
            ('activity_type_id.name', '=', 'Credit Request To Approve')
        ])
        if activity:
            activity.action_done()
        
        self.write({
            'state': 'rejected',
            'approval_status': 'rejected'
        })
        self.message_post(body=f"Credit Request rejected by {self.env.user.name}.")




class ManpowerApprovalHistory(models.Model):
    _name = 'credit.approval.history'
    _description = 'Credit Approval History'
    _order = 'sequence asc, date_done desc'
    
    credit_request_id = fields.Many2one('credit.request', string="Credit Request")
    user_id = fields.Many2one('res.users', string="Approver")
    sequence = fields.Integer(string="Approval Sequence", default=1)
    status = fields.Selection([
        ('waiting', 'Waiting'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')], 
        string="Approval Status", required=True, default='waiting')
    date_done = fields.Datetime(string="Approval Date")
    notes = fields.Text(string="Notes")


class CreditBranchApprovers(models.Model):
    _name = 'credit.branch.approvers'
    _description = 'Credit Branch Approvers'
    # _order = 'sequence, id'
    
    branch_id = fields.Many2one('res.branch', string='Branch', required=True)
    # user_ids = fields.Many2many('res.users', string='Approvers')
    approver_line_ids = fields.One2many(
        'credit.branch.approver.line', 
        'branch_approver_id', 
        string='Approvers'
    )

class CreditBranchApproverLine(models.Model):
    _name = 'credit.branch.approver.line'
    _description = 'Branch Approver Line'
    _order = 'sequence, id'
    
    branch_approver_id = fields.Many2one('credit.branch.approvers')
    user_id = fields.Many2one('res.users', string='Approver', required=True)
    sequence = fields.Integer(string='Sequence')


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def check(self, mode, values=None):
        try:
            return super(IrAttachment, self).check(mode, values=values)
        except AccessError:
            if self.env.is_superuser():
                return True
                
            if not (self.env.is_admin() or self.env.user.has_group('base.group_user')):
                raise AccessError(_("Sorry, you are not allowed to access this document."))
                
            if self:
                self._cr.execute('''
                    SELECT a.id, r.current_approver_id, r.requested_by
                    FROM ir_attachment a
                    JOIN credit_request r ON a.res_model = 'credit.request' AND a.res_id = r.id
                    WHERE a.id IN %s
                ''', [tuple(self.ids)])
                
                for att_id, approver_id, requested_by in self._cr.fetchall():
                    if self.env.uid == approver_id or self.env.uid == requested_by:
                        continue
                    raise AccessError(_("Sorry, you are not allowed to access this document."))
                    
            return True


