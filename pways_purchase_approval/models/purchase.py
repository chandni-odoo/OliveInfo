# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    no_approval = fields.Boolean(compute='_compute_no_approval')
    has_approval = fields.Boolean(compute='_compute_has_approval')
    purchase_history_ids = fields.One2many('approval.history', 'purchase_id', string="Purchase History", readonly=True)
    reject_reason = fields.Text(string="Reject Reason", copy=False)
    state = fields.Selection(selection_add=[('approved', 'Approved'), ('reject', 'Reject')])

    def _compute_no_approval(self):
        for order in self:
            if order.purchase_history_ids and order.state == 'to approve' and all([line.status == ('approve') for line in order.purchase_history_ids]):
                order.no_approval = False
                order.write({'state': 'approved'})
            elif not order.purchase_history_ids:
                order.no_approval = False
            else:
                order.no_approval = True

    def _compute_has_approval(self):
        for order in self:
            approval_id = order.purchase_history_ids.filtered(lambda x: x.user_id.id == self.env.user.id)
            is_rejected = any([status == 'reject' for status in order.purchase_history_ids.mapped('status')])
            if is_rejected:
                order.has_approval = False
                order.write({'state': 'reject'})
            elif not is_rejected and order.state == 'to approve' and approval_id and approval_id.status == 'pending':
                order.has_approval = True
            else:
                order.has_approval = False

    def _create_mail_activity(self, user_id):
        res_model_id = self.env.ref('purchase.model_purchase_order')
        activity_type_id = self.env.ref('pways_purchase_approval.purchase_approval_activity')
        vals = {
            'res_id': self.id,
            'res_model_id': res_model_id.id,
            'activity_type_id': activity_type_id.id,
            'date_deadline': (fields.Datetime.today() + relativedelta(days=5)).strftime('%Y-%m-%d %H:%M'),
            'create_uid': self.env.user.id,
            'user_id': user_id.id,
        }
        self.env['mail.activity'].sudo().create(vals)

    def _done_mail_activity(self):
        res_model_id = self.env.ref('purchase.model_purchase_order')
        activity_type_id = self.env.ref('pways_purchase_approval.purchase_approval_activity')
        self.env['mail.activity'].sudo().search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id.id),
            ('activity_type_id', '=', activity_type_id.id),
            ('user_id', '=', self.env.user.id),
        ]).action_done()

    def too_approve(self):
        data = [(5,0,0)]
        approval_lines = self.env['purchase.approval.lines'].search([
            ('approval_id.model', '=', 'purchase'),
            ('limit', '<=', self.amount_total),
            ('approval_id.branch_id', '=', self.branch_id.id),
            ('approval_id.purchase_type', '=', self.purchase_type.purchase_type)
        ])
        if approval_lines:
            for line in approval_lines:
                data.append((0, 0, {'user_id': line.user_id.id}))
                self.purchase_history_ids = data
                self._create_mail_activity(line.user_id)
            self.write({'state': 'to approve'})
        else:
            self.write({'state': 'approved'})

    def action_button_approve(self, force=False):
        user_approval = self.env['approval.history'].search([('purchase_id', '=', self.id), ('user_id', '=', self.env.user.id)])
        user_approval.write({'status': 'approve', 'date_done' : datetime.now()})
        self._done_mail_activity()

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent', 'approved']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True
