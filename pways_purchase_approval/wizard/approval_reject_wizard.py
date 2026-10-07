# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime


class RejectReasonWizard(models.TransientModel):
    _name = "reject.reason.wizard"
    _description = "Reject Reason Wizard"

    reject_reason = fields.Text(string="Reject Reason")

    def action_reject(self):
        active_model = self.env.context.get('active_model')
        active_id = self.env[active_model].browse(self.env.context.get('active_id'))
        history_ids = self.env['approval.history']
        if active_model == 'indent.request':
            history_ids = self.env['approval.history'].search([('indent_id', '=', active_id.id), ('user_id', '=', self.env.user.id)])
        if active_model == 'purchase.order':
            history_ids = self.env['approval.history'].search([('purchase_id', '=', active_id.id), ('user_id', '=', self.env.user.id)])
        history_ids.write({'status': 'reject', 'date_done': datetime.now()})
        active_id.write({'reject_reason': self.reject_reason})
