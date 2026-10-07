# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PendingDetailsWizard(models.TransientModel):
    _name = 'pending.details.wizard'
    _description = 'pending.details.wizard'

    approval_ids = fields.One2many('pending.details.line.wizard', 'wizard_id', readonly="True")

    @api.model
    def default_get(self, fields_list):
        lines = []
        res = super(PendingDetailsWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        res_model = self.env.context.get('active_model')
        approval = self.env['record.approval'].sudo().search([('model_id.model', '=', res_model)])
        if approval:
            for app in approval.approver_ids.sorted(lambda x: x.sequence):
                rec_id = self.env['record.approved'].search([('res_model', '=', res_model), ('res_id', '=', active_id), ('user_id', '=', app.user_id.id)])
                status = 'pending'
                if rec_id.state == 'approved':
                    status = 'done'
                if rec_id.state == 'rejected':
                    status = 'rejected'
                lines.append((0, 0, {
                    'user_id': app.user_id.id,
                    'sequence': app.sequence,
                    'status': status
                }))
            res['approval_ids'] = lines
        return res

class PendingDetailsLineWizard(models.TransientModel):
    _name = 'pending.details.line.wizard'
    _description = 'pending.details.line.wizard'

    wizard_id = fields.Many2one('pending.details.wizard')
    user_id = fields.Many2one('res.users', string='Approver')
    sequence = fields.Integer(index=True, help="Gives the sequence order when displaying a list of bank statement lines.", default=1)
    status = fields.Selection([('pending', 'Pending'), ('done', 'Approved'), ('rejected', 'Rejected')], string="Status")
