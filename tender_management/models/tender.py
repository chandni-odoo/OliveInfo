from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.exceptions import ValidationError
from datetime import datetime

class TenderWorkingStatus(models.Model):
    _name = 'tender.working.status'
    _description = 'Tender Working Status'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)

class TenderBidApproverGroup(models.Model):
    _name = 'tender.bid.approver.group'
    _description = 'Tender Bid Approver Group'

    name = fields.Char(string='Name', required=True, default='Tender Bid Approver Group')
    approver_line_ids = fields.One2many(
        'tender.bid.approver.line',
        'group_id',
        string='Approvers'
    )


class TenderBidApproverLine(models.Model):
    _name = 'tender.bid.approver.line'
    _description = 'Tender Bid Approver Line'
    _order = 'sequence asc'

    group_id = fields.Many2one('tender.bid.approver.group', string='Group', ondelete='cascade')
    sequence = fields.Integer(string='Order', default=1)
    user_id = fields.Many2one('res.users', string='Approver', required=True)




class TenderManagement(models.Model):
    _name = 'tender.management'
    _description = 'Tender'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'sequence_no'

    sequence_no = fields.Char(
        string='Sequence Number',
        readonly=True,
        copy=False,
        default='New'
    )

    tender_no = fields.Char(string='Tender No',required=True)
    tender_name = fields.Char(string='Tender Name')
    project_location = fields.Char(string='Project Location')
    duration = fields.Char(string='Duration')
    annual_estimated_value_contract = fields.Char(
        string='Annual Estimated Value Of Contract'
    )
    total_contract_value = fields.Char(
        string='Total Contract Value'
    )

    sector_id = fields.Many2one(
        'customer.sector',
        string='Sector'
    )

    tender_bond_amount = fields.Char(
        string='Tender Bond Amount'
    )

    contract_start_date = fields.Date(
        string='Contract Start Date'
    )

    contract_end_date = fields.Date(
        string='Contract End Date'
    )
    
    tender_branch_id = fields.Many2one('res.branch', string='Tender Branch')

    client_id = fields.Many2one(
        'res.partner',
        string='Client'
    )

    tender_received_date = fields.Date(
        string='Tender Received Date'
    )

    tender_submission_date = fields.Date(
        string='Tender Submission Date'
    )

    contract_award_date = fields.Date(
        string='Contract Award Date'
    )

    mobilization_period = fields.Char(
        string='Mobilization Period'
    )

    tender_bond_expiry = fields.Date(
        string='Tender Bond Expiry'
    )

    tender_bond_validity_days = fields.Integer(
        string='Tender Bond Validity Days',
        compute='_compute_tender_bond_validity_days',
        store=True
    )

    partner_ids = fields.Many2many('res.partner', string='Associated Partners')
    branch_ids = fields.Many2many('res.branch', string='Associated Branch', domain="[('id', '!=', tender_branch_id)]")
    working_status_id = fields.Many2one(
        'tender.working.status',
        string='Working Status'
    )

    state = fields.Selection([
        ('tendering', 'Tendering'),
        ('bid_submitted', 'Bid Submitted'),
        ('technical', 'Technical'),
        ('commercial', 'Commercial'),
        ('negotiation', 'Negotiation'),
    ], string='Stage', default='tendering', tracking=True)

    result_state = fields.Selection([
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('cancelled', 'Cancelled'),
    ], string='Result Status', tracking=True)

    # Approval workflow state
    approval_state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),  
        ('rejected', 'No Bid'),    
    ], string='Approval State', default='draft', tracking=True)

    current_approver_id = fields.Many2one(
        'res.users',
        string='Current Approver',
        compute='_compute_current_approver',
        store=True
    )
    is_current_approver = fields.Boolean(
        string='Is Current Approver',
        compute='_compute_is_current_approver'
    )
    active = fields.Boolean(default=True)

    lead_count = fields.Integer(
        string='Lead Count',
        compute='_compute_lead_count'
    )



    # =====================================================
    # BRIEF PROJECT SUMMARY
    # =====================================================

    summary = fields.Text(
        string='Summary'
    )

    key_risks = fields.Text(
        string='Key risks & mitigation'
    )

    # =====================================================
    # ONE2MANY LINES
    # =====================================================

    tender_document_line_ids = fields.One2many(
        'tender.document.line',
        'tender_id',
        string='Tender Documents'
    )

    working_file_line_ids = fields.One2many(
        'working.file.line',
        'tender_id',
        string='Working Files'
    )

    tender_bulletin_line_ids = fields.One2many(
        'tender.bulletin.line',
        'tender_id',
        string='Tender Bulletin'
    )

    submitted_document_line_ids = fields.One2many(
        'submitted.document.line',
        'tender_id',
        string='Submitted Documents'
    )

    post_tender_line_ids = fields.One2many(
        'post.tender.line',
        'tender_id',
        string='Post Tender Clarification'
    )

    signed_contract_line_ids = fields.One2many(
        'signed.contract.line',
        'tender_id',
        string='Signed Contracts'
    )

    poc_line_ids = fields.One2many(
        'tender.poc.line',
        'tender_id',
        string='Point Of Contact'
    )

    approval_history_ids = fields.One2many(
        'tender.approval.history',
        'tender_id',
        string='Approval History'
    )

    @api.depends('approval_state', 'current_approver_id')
    def _compute_is_current_approver(self):
        for rec in self:
            rec.is_current_approver = (
                rec.approval_state == 'under_review'
                and rec.current_approver_id == self.env.user
            )

    @api.constrains('tender_branch_id', 'branch_ids')
    def _check_duplicate_branch(self):

        for rec in self:
            if rec.tender_branch_id and rec.tender_branch_id in rec.branch_ids:
                raise ValidationError(_(
                    "Tender Branch cannot be added "
                    "in Associated Branches."
                ))

    def _compute_lead_count(self):
        crm_obj = self.env['crm.lead']
        for rec in self:
            rec.lead_count = crm_obj.search_count([
                ('tender_id', '=', rec.id)
            ])

    @api.depends('tender_bond_expiry')
    def _compute_tender_bond_validity_days(self):
        today = fields.Date.today()

        for rec in self:
            if rec.tender_bond_expiry:
                rec.tender_bond_validity_days = (
                    rec.tender_bond_expiry - today
                ).days
            else:
                rec.tender_bond_validity_days = 0

    @api.model
    def create(self, vals):
        if vals.get('sequence_no', 'New') == 'New':
            vals['sequence_no'] = self.env['ir.sequence'].next_by_code(
                'tender.management.seq'
            ) or 'New'
        return super(TenderManagement, self).create(vals)
    
    def action_tendering(self):
        self.state = 'tendering'


    def action_bid_submitted(self):
        self.state = 'bid_submitted'


    def action_technical(self):
        self.state = 'technical'


    def action_commercial(self):
        self.state = 'commercial'


    def action_negotiation(self):
        self.state = 'negotiation'

    # =====================================================
    # SERVER ACTION METHODS
    # =====================================================

    def action_mark_won(self):
        for rec in self:
            rec.write({
                'result_state': 'won',
            })

    def action_mark_lost(self):
        for rec in self:
            rec.write({
                'result_state': 'lost'
            })

    def action_mark_cancelled(self):
        for rec in self:
            rec.write({
                'result_state': 'cancelled'
            })

    @api.depends('approval_history_ids.status')
    def _compute_current_approver(self):
        for rec in self:
            if rec.approval_state != 'under_review':
                rec.current_approver_id = False
                continue
            pending = rec.approval_history_ids.filtered(
                lambda h: h.status == 'pending'
            ).sorted('sequence')
            rec.current_approver_id = pending[0].user_id if pending else False

    def _is_current_approver(self):
        self.ensure_one()
        return (
            self.approval_state == 'under_review'
            and self.current_approver_id == self.env.user
        )

    # =====================================================
    # SERVER ACTION: SEND FOR APPROVAL
    # =====================================================

    def action_send_for_approval(self):
        """
        Server action: Send tender for bid approval.
        """

        for rec in self:

            # Allow only Tendering stage
            if rec.state != 'tendering':
                raise UserError(_(
                    "Send For Approval is allowed only in Tendering stage."
                ))

            # Prevent resend
            if rec.approval_state != 'draft':
                raise UserError(_(
                    "This tender has already been sent for approval."
                ))

            approver_group = self.env['tender.bid.approver.group'].search([], limit=1)

            if not approver_group or not approver_group.approver_line_ids:
                raise UserError(_(
                    "No approver group configured. "
                    "Please configure Tender Bid Approver Group."
                ))

            approval_users = approver_group.approver_line_ids.sorted('sequence')

            rec.approval_history_ids.unlink()

            approval_history_values = []

            for idx, line in enumerate(approval_users, start=1):
                approval_history_values.append((0, 0, {
                    'user_id': line.user_id.id,
                    'sequence': idx,
                    'status': 'pending' if idx == 1 else 'waiting',
                }))

            rec.write({
                'approval_state': 'under_review',
                'approval_history_ids': approval_history_values,
            })

            # Notify first approver
            rec._notify_current_approver()

        return True


    # =====================================================
    # NOTIFY CURRENT APPROVER
    # =====================================================

    def _notify_current_approver(self):
        self.ensure_one()
        pending = self.approval_history_ids.filtered(
            lambda h: h.status == 'pending'
        ).sorted('sequence')
        if not pending:
            return
        current = pending[0]

        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', 'tender.management')], limit=1
        )
        activity_type = self.env['mail.activity.type'].sudo().search(
            [('name', '=', 'Tender Bid Approval')], limit=1
        )
        if not activity_type:
            activity_type = self.env['mail.activity.type'].sudo().create({
                'name': 'Tender Bid Approval',
            })

        self.env['mail.activity'].sudo().create({
            'res_model_id': model_id.id,
            'res_model': 'tender.management',
            'res_id': self.id,
            'summary': 'Tender Bid Approval Required',
            'note': f'Please review and select Bid or No Bid for tender: {self.tender_name or self.tender_no}',
            'user_id': current.user_id.id,
            'activity_type_id': activity_type.id,
            'date_deadline': fields.Date.today(),
        })

        self.message_post(
            body=_(f"Tender sent for approval. Awaiting decision from <b>{current.user_id.name}</b>."),
            subtype_xmlid='mail.mt_note',
        )

    def _notify_tender_creator(self, decision):
        """
        Notify tender creator after final approval/rejection.
        """

        self.ensure_one()

        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', 'tender.management')],
            limit=1
        )

        activity_type = self.env['mail.activity.type'].sudo().search(
            [('name', '=', 'Tender Final Decision')],
            limit=1
        )

        if not activity_type:
            activity_type = self.env['mail.activity.type'].sudo().create({
                'name': 'Tender Final Decision',
            })

        if decision == 'bid':
            note = _(
                "All approvers selected Bid "
                "for this tender."
            )
        else:
            note = _(
                "An approver selected No Bid "
                "for this tender."
            )

        self.env['mail.activity'].sudo().create({
            'res_model_id': model_id.id,
            'res_model': 'tender.management',
            'res_id': self.id,
            'summary': 'Tender Final Decision',
            'note': note,
            'user_id': self.create_uid.id,
            'activity_type_id': activity_type.id,
            'date_deadline': fields.Date.today(),
        })

        self.message_post(
            body=_(
                f"Final decision notification sent to "
                f"<b>{self.create_uid.name}</b>."
            ),
            subtype_xmlid='mail.mt_note',
        )

    # =====================================================
    # BID DECISION METHODS
    # =====================================================

    def action_bid(self):
        """
        Current approver selects 'Bid' — moves to next approver in sequence.
        If last approver, marks tender as fully approved (Bid).
        """
        self.ensure_one()
        if not self._is_current_approver():
            raise AccessError(_("You are not the current approver for this tender."))

        current = self.approval_history_ids.filtered(
            lambda h: h.user_id == self.env.user and h.status == 'pending'
        )
        if not current:
            raise AccessError(_("No pending approval found for your user."))

        current = current[0]
        current.write({
            'status': 'bid',
            'date_done': datetime.now(),
            'notes': current.notes,
        })

        # Mark activity done
        self._mark_activity_done()

        # Check for next approver
        next_approver = self.approval_history_ids.filtered(
            lambda h: h.status == 'waiting'
        ).sorted('sequence')

        if next_approver:
            next_approver[0].write({'status': 'pending'})
            self._notify_current_approver()
            self.message_post(
                body=_(f"<b>Bid</b> selected by {self.env.user.name}. Sent to next approver <b>{next_approver[0].user_id.name}</b>."),
                subtype_xmlid='mail.mt_note',
            )
        else:
            # All approved
            self.write({
                'approval_state': 'approved'
            })

            # Notify tender creator
            self._notify_tender_creator('bid')

            self.message_post(
                body=_(
                    "All approvers selected <b>Bid</b>. "
                    "Tender is fully approved for bidding."
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_no_bid(self):
        """
        Current approver selects 'No Bid' — stops the workflow immediately.
        """
        self.ensure_one()
        if not self._is_current_approver():
            raise AccessError(_("You are not the current approver for this tender."))

        current = self.approval_history_ids.filtered(
            lambda h: h.user_id == self.env.user and h.status == 'pending'
        )
        if not current:
            raise AccessError(_("No pending approval found for your user."))

        current = current[0]
        current.write({
            'status': 'no_bid',
            'date_done': datetime.now(),
            'notes': current.notes,
        })

        # Set remaining waiting lines as skipped
        waiting = self.approval_history_ids.filtered(lambda h: h.status == 'waiting')
        waiting.write({'status': 'skipped'})

        # Mark activity done
        self._mark_activity_done()

        self.write({
            'approval_state': 'rejected'
        })

        # Notify tender creator
        self._notify_tender_creator('no_bid')

        self.message_post(
            body=_(
                f"<b>No Bid</b> selected by "
                f"{self.env.user.name}. "
                "Tender approval completed."
            ),
            subtype_xmlid='mail.mt_note',
        )

    def _mark_activity_done(self):
        self.ensure_one()
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'tender.management'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.uid),
            ('activity_type_id.name', '=', 'Tender Bid Approval'),
        ], limit=1)
        if activity:
            activity.action_done()

    def action_generate_lead(self):

        self.ensure_one()

        if self.result_state != 'won':
            raise UserError(_(
                "Lead can be generated only "
                "when result status is Won."
            ))

        crm_obj = self.env['crm.lead']

        # First POC Line
        first_poc = self.poc_line_ids[:1]

        contact_name = first_poc.contact_name if first_poc else False
        mobile = first_poc.contact_number if first_poc else False
        email = first_poc.contact_email if first_poc else False


        created_branches = []

        # Main Tender Branch Lead
        if self.tender_branch_id:

            existing = crm_obj.search([
                ('tender_id', '=', self.id),
                ('branch_id', '=', self.tender_branch_id.id)
            ], limit=1)

            if not existing:

                crm_obj.create({
                    'name': '%s / %s' % (
                        self.tender_name or '',
                        self.tender_no or ''
                    ),
                    'partner_id': self.client_id.id,
                    'branch_id': self.tender_branch_id.id,
                    'tender_id': self.id,
                    'expected_revenue': self.total_contract_value,
                    'description': self.summary,
                    'contact_name': contact_name,
                    'mobile': mobile,
                    'email_from': email,
                })

                created_branches.append(self.tender_branch_id.name)

        # Associated Branch Leads
        for branch in self.branch_ids:

            existing = crm_obj.search([
                ('tender_id', '=', self.id),
                ('branch_id', '=', branch.id)
            ], limit=1)

            if not existing:

                crm_obj.create({
                    'name': '%s / %s' % (
                        self.tender_name or '',
                        self.tender_no or ''
                    ),
                    'partner_id': self.client_id.id,
                    'branch_id': branch.id,
                    'tender_id': self.id,
                    'expected_revenue': self.total_contract_value,
                    'description': self.summary,
                    'contact_name': contact_name,
                    'mobile': mobile,
                    'email_from': email,
                })

                created_branches.append(branch.name)

        if created_branches:
            self.message_post(
                body=_(
                    "Lead(s) generated for branches: %s"
                ) % (', '.join(created_branches))
            )
        else:
            raise UserError(_("Leads already generated for all branches."))
        
    def action_view_leads(self):

        self.ensure_one()

        leads = self.env['crm.lead'].search([
            ('tender_id', '=', self.id)
        ])

        action = self.env.ref('crm.crm_lead_all_leads').read()[0]

        if len(leads) == 1:
            action['views'] = [(self.env.ref('crm.crm_case_form_view_leads').id, 'form')]
            action['res_id'] = leads.id
        else:
            action['domain'] = [('id', 'in', leads.ids)]

        return action


# =====================================================
# TENDER DOCUMENT
# =====================================================

class TenderDocumentLine(models.Model):
    _name = 'tender.document.line'
    _description = 'Tender Document Line'

    tender_id = fields.Many2one('tender.management')

    file_name = fields.Char(string='File Name')
    remarks = fields.Char(string='Remarks')
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')


# =====================================================
# WORKING FILES
# =====================================================

class WorkingFileLine(models.Model):
    _name = 'working.file.line'
    _description = 'Working File Line'

    tender_id = fields.Many2one('tender.management')

    file_name = fields.Char(string='File Name')
    remarks = fields.Char(string='Remarks')
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')


# =====================================================
# TENDER BULLETIN
# =====================================================

class TenderBulletinLine(models.Model):
    _name = 'tender.bulletin.line'
    _description = 'Tender Bulletin Line'

    tender_id = fields.Many2one('tender.management')

    file_name = fields.Char(string='File Name')
    remarks = fields.Char(string='Remarks')
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')


# =====================================================
# SUBMITTED DOCUMENTS
# =====================================================

class SubmittedDocumentLine(models.Model):
    _name = 'submitted.document.line'
    _description = 'Submitted Document Line'

    tender_id = fields.Many2one('tender.management')

    file_name = fields.Char(string='File Name')
    remarks = fields.Char(string='Remarks')
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')


# =====================================================
# POST TENDER
# =====================================================

class PostTenderLine(models.Model):
    _name = 'post.tender.line'
    _description = 'Post Tender Line'

    tender_id = fields.Many2one('tender.management')

    file_name = fields.Char(string='File Name')
    remarks = fields.Char(string='Remarks')
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')


# =====================================================
# SIGNED CONTRACT
# =====================================================

class SignedContractLine(models.Model):
    _name = 'signed.contract.line'
    _description = 'Signed Contract Line'

    tender_id = fields.Many2one('tender.management')

    file_name = fields.Char(string='File Name')
    remarks = fields.Char(string='Remarks')
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')


# =====================================================
# POINT OF CONTACT
# =====================================================

class TenderPOCLine(models.Model):
    _name = 'tender.poc.line'
    _description = 'Tender Point Of Contact'

    tender_id = fields.Many2one('tender.management')

    contact_name = fields.Char(string='Contact Name')
    contact_number = fields.Char(string='Contact Number')
    contact_email = fields.Char(string='Email')

# =====================================================
# TENDER APPROVAL HISTORY
# =====================================================

class TenderApprovalHistory(models.Model):
    _name = 'tender.approval.history'
    _description = 'Tender Approval History'
    _order = 'sequence asc'

    tender_id = fields.Many2one('tender.management', string='Tender', ondelete='cascade')
    sequence = fields.Integer(string='Order', default=1)
    user_id = fields.Many2one('res.users', string='Approver')
    status = fields.Selection([
        ('waiting', 'Waiting'),
        ('pending', 'Pending'),
        ('bid', 'Bid'),
        ('no_bid', 'No Bid'),
        ('skipped', 'Skipped'),
    ], string='Approval Status', default='waiting', required=True)
    date_done = fields.Datetime(string='Approval Date')
    notes = fields.Text(string='Notes')