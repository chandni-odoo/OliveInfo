from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, date
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    unbilled_amount = fields.Monetary(
        string='Unbilled Value',
        compute='_compute_unbilled_amount',
        store=True,
        currency_field='currency_id'
    )
    
    current_outstanding = fields.Monetary(string='Current Outstanding',
                                        compute='_compute_current_outstanding',
                                        store=False,
                                        currency_field='currency_id')
    
    unposted_invoices = fields.Monetary(string='Unposted Invoices',
                                      compute='_compute_unposted_invoices',
                                      store=False,
                                      currency_field='currency_id')
    
    credit_control_exception = fields.Boolean(string='Credit Control Exception',
                                            default=False, tracking=True)
    
    is_customer_black_list = fields.Boolean(string='Customer Black List',
                                            default=False, tracking=True)
    
    blacklist_reason = fields.Text(
        string='Blacklist Reason',
        attrs={'invisible': [('is_customer_black_list', '=', False)]}
    )
    
    ava_credit_bal = fields.Float(
        string="Available Credit Balance", 
        compute="_compute_available_credit_balance",
        store=True
    )
    
    hold_option = fields.Selection([
        ('all', 'All'), 
        ('quote', 'Quote'), 
        ('bill', 'Bill'), 
        ('hold','Hold'),
        ('receipts', 'Receipts'),
        ('credit_block', 'Credit Block')
    ], default='quote', string="Hold", store=True, tracking=True)
    
    credit_block = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], 
        default='no', 
        string='Credit Block',
        compute='_compute_credit_block_status',
        store=True, tracking=True
    )
    hold_reason = fields.Text(string="Hold Reason", compute='_compute_credit_block_status',store=True)
    credit_bal_negative = fields.Boolean(
        string="Credit Balance Negative",
        compute="_compute_available_credit_balance",
        store=True
    )
    total_exposure = fields.Monetary(string='Exposure',
                               compute='_compute_total_exposure',
                               store=False,
                               currency_field='currency_id')
    
    approver_1 = fields.Many2one('res.users', string='First Approver', tracking=True)
    approver_2 = fields.Many2one('res.users', string='Second Approver', tracking=True)
    approver_3 = fields.Many2one('res.users', string='Third Approver', tracking=True)
    last_approver = fields.Many2one('res.users', string='Last Approver', readonly=True, tracking=True)
    release_until = fields.Date(string='Release Until', tracking=True)

    hold_position = fields.Selection([
        ('first_escalate', 'First Escalate'),
        ('released_by_1st', 'Released by 1st Approver'),
        ('released_by_2nd', 'Released by 2nd Approver'),
        ('released_by_3rd', 'Released by 3rd Approver')
    ], string='Hold Position', default='first_escalate', tracking=True)

    approver_comment = fields.Text(string='Approver Comment', tracking=True)

    credit_manager = fields.Many2one('hr.employee', string="Credit Manager")
    first_approval_request = fields.Boolean(string="First Approval Request", default=False, tracking=True)
    second_approval_request = fields.Boolean(string="Second Approval Request", default=False, tracking=True)
    third_approval_request = fields.Boolean(string="Third Approval Request", default=False, tracking=True)
    hold_date = fields.Date(
        string='Hold Date',
        readonly=True,
    )
    credit_limit = fields.Float(tracking=True)


    @api.depends('current_outstanding', 'unposted_invoices', 'unbilled_amount')
    def _compute_total_exposure(self):
        for partner in self:
            partner._compute_current_outstanding()
            partner._compute_unposted_invoices()
            
            partner.total_exposure = partner.current_outstanding + partner.unposted_invoices + partner.unbilled_amount

    @api.depends('credit_limit', 'total_exposure')
    def _compute_available_credit_balance(self):
        for partner in self:
            if partner.credit_limit == 0:
                partner.ava_credit_bal = 0.0
                partner.credit_bal_negative = False
                continue
            
            partner.ava_credit_bal = partner.credit_limit - partner.total_exposure
            partner.credit_bal_negative = partner.ava_credit_bal < 0

    @api.depends('total_due')
    def _compute_current_outstanding(self):
        for partner in self:
            partner.current_outstanding = partner.total_due if hasattr(partner, 'total_due') else 0.0

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.amount_total', 'invoice_ids.move_type')
    def _compute_unposted_invoices(self):
        for partner in self:
            domain = [
                ('partner_id', '=', partner.id),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'draft'),
            ]
            draft_invoices = self.env['account.move'].search(domain)
            total_amount = 0.0
            for invoice in draft_invoices:
                if invoice.move_type == 'out_invoice':
                    total_amount += invoice.amount_total
                elif invoice.move_type == 'out_refund':
                    total_amount -= invoice.amount_total
                    
            partner.unposted_invoices = total_amount


    @api.depends('task_ids.unbilled_value','task_ids.sale_line_id.order_id.advance_billing', 'task_ids.currency_id')
    def _compute_unbilled_amount(self):
        for partner in self:
            total_unbilled = sum(task.unbilled_value for task in partner.task_ids)
            partner.unbilled_amount = total_unbilled
            
            
    
    @api.depends('ava_credit_bal', 'credit_limit', 'total_due', 'invoice_ids', 'invoice_ids.state', 'invoice_ids.amount_total','credit_control_exception')
    def _compute_credit_block_status(self):
        for partner in self:
            if partner.credit_limit == 0:
                partner.credit_block = 'no'
                partner.hold_option = ""
                partner.hold_reason = False
                partner.hold_date = False
                continue

            if partner.credit_control_exception:
                partner.credit_block = 'no'
                partner.hold_option = ""
                partner.hold_reason = ""
                partner.hold_date = False
                continue

            # newcode
            # Check if there's an active temporary release
            if partner.release_until and partner.release_until >= fields.Date.today():
                # Keep the temporary release status
                partner.credit_block = 'no'
                if partner.hold_option == 'credit_block':
                    partner.hold_option = ""
                # Don't change hold_reason during temporary release
                partner.hold_date = False
                continue
            # upto this
            partner._compute_available_credit_balance()

            previous_credit_block = partner.credit_block
            
            if partner.ava_credit_bal <= 0:
                partner.hold_option = 'credit_block'
                partner.credit_block = 'yes'
                partner.hold_reason = f"Available credit limit is {partner.ava_credit_bal}"
                # Set hold date only if credit_block changed from 'no' to 'yes'
                if previous_credit_block != 'yes':
                    partner.hold_date = fields.Date.today()
            else:
                if partner.hold_option == 'credit_block':
                    partner.hold_option = ""
                partner.credit_block = 'no'
                partner.hold_date = False
                if partner.hold_reason and "Available credit limit is" in partner.hold_reason:
                    partner.hold_reason = ""

    @api.constrains('credit_block', 'credit_limit')
    def _check_credit_block_with_zero_limit(self):
        for partner in self:
            if partner.credit_limit == 0 and partner.credit_block == 'yes':
                raise ValidationError("Credit block cannot be 'Yes' when credit limit is 0")
    

    def write(self, vals):
        res = super().write(vals)
        
        if any(field in vals for field in ['hold_option', 'is_customer_black_list', 'hold_reason', 'blacklist_reason']):
            orders = self.env['sale.order'].search([
                ('partner_id', 'in', self.ids),
                ('state', 'in', ['draft', 'sent'])
            ])
            if orders:
                orders._compute_hold_status()
        return res
    

    def action_request_credit_release(self):
        """Open the credit release request form and notify specific approvers"""
        self.ensure_one()
        if not self.env.user.has_group('credit_control.group_credit_manager'):
            raise UserError(_("Only Credit Managers can request credit release."))
        
        # Determine which level we're requesting and get the appropriate approver
        approver = False
        action_ref = False
        if not self.first_approval_request and not self.second_approval_request and not self.third_approval_request:
            # First level approval
            if not self.approver_1:
                raise UserError(_("Please set a First Approver before requesting credit release."))
            self.write({
                'first_approval_request': True,
                'hold_position': 'first_escalate'
            })
            approver = self.approver_1
            message = _('Customer %s is waiting for your first level credit release approval') % self.name
            summary = _('First Level Credit Approval Required')
            action_ref = 'credit_control.action_credit_hold_first_escalate'
        elif self.first_approval_request and not self.second_approval_request and not self.third_approval_request:
            # Second level approval
            if not self.approver_2:
                raise UserError(_("Please set a Second Approver before requesting credit release."))
            self.write({
                'first_approval_request': False,
                'second_approval_request': True,
                'hold_position': 'released_by_1st'
            })
            approver = self.approver_2
            message = _('Customer %s has been escalated to your level for approval') % self.name
            summary = _('Second Level Credit Approval Required')
            action_ref = 'credit_control.action_credit_hold_second_escalate'
        elif self.second_approval_request and not self.third_approval_request:
            # Third level approval
            if not self.approver_3:
                raise UserError(_("Please set a Third Approver before requesting credit release."))
            self.write({
                'second_approval_request': False,
                'third_approval_request': True,
                'hold_position': 'released_by_2nd'
            })
            approver = self.approver_3
            message = _('Customer %s has been escalated to your level for final approval') % self.name
            summary = _('Final Credit Approval Required')
            action_ref = 'credit_control.action_credit_hold_third_escalate'
        else:
            raise UserError(_("This customer already has a pending approval request at the highest level."))
        
        # Create activity notification for the specific approver
        activity_type = self.env['mail.activity.type'].sudo().search(
            [('name', '=', 'Credit Hold Approval')], 
            limit=1
        )
        if not activity_type:
            activity_type = self.env['mail.activity.type'].sudo().create({
                'name': 'Credit Hold Approval',
                'category': 'approval'
            })
        
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', 'res.partner')], 
            limit=1
        )
        
        if approver and action_ref:
            # Get the action to generate the URL
            action = self.env.ref(action_ref)
            action_url = '/web#action=%s&model=res.partner&view_type=list&cids=1' % action.id
            
            # Add link to the appropriate list view in the message
            full_message = """
                <p>%s</p>
                <p><a href="%s" target="_blank" style="background-color: #875A7B; color: white; padding: 8px 16px; text-decoration: none; border-radius: 3px;">
                    View All Pending Approvals
                </a></p>
                <p>Customer: <strong>%s</strong></p>
                <p>Credit Limit: <strong>%s</strong></p>
                <p>Current Exposure: <strong>%s</strong></p>
                <p>Available Credit: <strong>%s</strong></p>
                <p>Hold Reason: <strong>%s</strong></p>
            """ % (
                message,
                action_url,
                self.name,
                self.credit_limit,
                self.total_exposure,
                self.ava_credit_bal,
                self.hold_reason or 'N/A'
            )
            
            existing_activity = self.env['mail.activity'].sudo().search([
                ('res_model_id', '=', model_id.id),
                ('user_id', '=', approver.id),
                ('activity_type_id', '=', activity_type.id),
                ('res_id', '=', self.id),
                ('state', '!=', 'done'),
            ], limit=1)
            
            if existing_activity:
                existing_activity.write({
                    'note': full_message,
                    'date_deadline': fields.Date.today(),
                })
            else:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': model_id.id,
                    'res_model': 'res.partner',
                    'res_id': self.id,
                    'user_id': approver.id,
                    'activity_type_id': activity_type.id,
                    'summary': summary,
                    'note': full_message,
                    'date_deadline': fields.Date.today(),
                })
        
        return {
            'name': _('Request Credit Release'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'current',
            'context': {
                'form_view_ref': 'credit_control.view_partner_credit_hold_form',
                'default_credit_request_status': 'requested',
            },
        }

    

    def release_credit_hold_action(self):
        """Action to release credit hold temporarily with a release until date"""
        for partner in self:
            # Check if partner is actually on credit block
            if partner.credit_block != 'yes' or partner.hold_option != 'credit_block':
                raise UserError(_('This partner is not currently under credit block hold.'))
                
            # Check if there's an existing release date in future
            if partner.release_until and partner.release_until > fields.Date.today():
                raise UserError(_('Credit hold is already temporarily released until %s') % partner.release_until)
                
        # Default release date (7 days from today)
        default_release_date = fields.Date.today() + timedelta(days=7)
        
        return {
            'name': _('Release Credit Hold'),
            'type': 'ir.actions.act_window',
            'res_model': 'release.credit.hold.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_ids': self.ids,
                'default_release_until': default_release_date,
            },
        }

    def _reinstate_expired_credit_hold(self):
        """Cron method to reinstate expired credit holds"""
        today = fields.Date.today()
        
        # Find partners with expired temporary releases that should be reinstated
        expired_partners = self.search([
            ('release_until', '!=', False),
            ('release_until', '<', today),
            ('credit_block', '=', 'no'),  # Currently not blocked
            ('hold_option', '!=', 'credit_block'),  # Currently not on credit block
            ('last_approver', '!=', False)  # Had been approved before
        ])
        
        for partner in expired_partners:
            # Recompute credit balance
            partner._compute_available_credit_balance()
            
            # Only reinstate if credit balance is negative
            if partner.credit_bal_negative:
                partner.write({
                    'hold_option': 'credit_block',
                    'credit_block': 'yes',
                    'hold_reason': f"Temporary release expired on {partner.release_until}. Available credit balance: {partner.ava_credit_bal}",
                })
                
                message = _("Credit hold has been automatically reinstated after temporary release period expired on %s. Available credit balance: %s") % (
                    partner.release_until, partner.ava_credit_bal)
                partner.message_post(body=message)
            else:
                # If credit balance is positive, just clear the release_until date
                partner.write({
                    'release_until': False,
                })
        
        return True
    

    