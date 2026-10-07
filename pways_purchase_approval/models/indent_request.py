# -*- coding: utf-8 -*-
from odoo import models,fields,api


class IndentRequest(models.Model):
    _inherit = "indent.request"

    no_approval = fields.Boolean(compute='_compute_no_approval')
    has_approval = fields.Boolean(compute='_compute_has_approval')
    approval_history_ids = fields.One2many('approval.history', 'indent_id', string="History", readonly=True)
    reject_reason = fields.Text(string="Reject Reason", copy=False)

    def _compute_no_approval(self):
        for request in self:
            if not request.approval_history_ids or all([line.status == ('approve') for line in request.approval_history_ids]):
                request.no_approval = False
            else:
                request.no_approval = True

    def _compute_has_approval(self):
        for indent in self:
            approval_id = indent.approval_history_ids.filtered(lambda x: x.user_id.id == self.env.user.id)
            is_rejected = any([status == 'reject' for status in indent.approval_history_ids.mapped('status')])
            if not is_rejected and indent.state == 'approve' and approval_id and approval_id.status == 'pending':
                indent.has_approval = True
            else:
                indent.has_approval = False

    def action_approval(self):
        history_ids = self.env['approval.history'].search([('indent_id', '=', self.id), ('user_id', '=', self.env.user.id)])
        history_ids.write({'status': 'approve'})

    def button_approve_direct(self):
        data = []
        approval_lines = self.env['purchase.approval.lines'].search([
            ('approval_id.model', '=', 'indent'),
            # ('limit', '<', self.amount_total),
            ('approval_id.branch_id', '=', self.branch_id.id),
            ('approval_id.purchase_type', '=', self.type_purchase.purchase_type),
        ])
        for line in approval_lines:
            data.append((0, 0, {'user_id': line.user_id.id}))
        self.approval_history_ids = data
        super(IndentRequest, self).button_approve_direct()


class ApprovalHistory(models.Model):
    _name = "approval.history"
    _description = "Approval History"

    indent_id = fields.Many2one('indent.request', string="Indent Request")
    purchase_id = fields.Many2one('purchase.order', string="Indent Request")
    user_id = fields.Many2one('res.users', string="Approver")
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approve', 'Approved'),
        ('reject','Rejected')], default='pending', copy=False, string="Approval Status")
    date_done = fields.Datetime(string="Approval Date")

