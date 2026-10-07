# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class RejectReasonWizard(models.TransientModel):
    _name = 'reject.reason.wizard'
    _description = 'Reject Reason Wizard'

    reason = fields.Char('Reason')

    def action_reject(self):
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        rec = self.env['record.approved'].search([('state', '=', 'rejected'), ('user_id', '=', self.env.user.id), ('res_id', '=', active_id), ('res_model', '=', active_model)])
        if not rec and active_model and active_id:
            record = self.env[active_model].browse(active_id)
            approved_id = self.env['record.approved'].search([('state', '=', 'pending'), ('user_id', '=', self.env.user.id), ('res_id', '=', active_id), ('res_model', '=', active_model)])
            approved_id.write({'state': 'rejected'})
            record.message_post(body=self.reason)
            record._done_mail_activity()
