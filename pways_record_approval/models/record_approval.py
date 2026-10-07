# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class RecordApproval(models.Model):
    _name = 'record.approval'
    _description = 'Record Approval'
    _rec_name = 'model_id'

    model_id = fields.Many2one('ir.model', string='Model', domain=[('is_mail_thread', '=', True)])
    type = fields.Selection([('one', 'Anyone'), ('all', 'All')], string='Approval', default='one', required=True)
    filter_domain = fields.Char(string='Apply on', help="If present, this condition must be satisfied before executing the action rule.")
    model_name = fields.Char(related='model_id.model', string='Model Name', readonly=True, store=True)
    approver_ids = fields.One2many('record.approver', 'approval_id')

    @api.onchange('model_id')
    def onchange_model_id(self):
        self.model_name = self.model_id.model


    @api.model
    def get_approval(self, res_model, res_id):
 
        approval = self.env['record.approval'].sudo().search([('model_id.model', '=', res_model)], limit=1)
        approval_bool = self.env[res_model].browse(res_id)
        filter_domain = eval(approval.filter_domain) if approval and approval.filter_domain else []
        if approval and  (res_id not in self.env[res_model].sudo().search(filter_domain).ids):
            return {'show_approval': False, 'show_all': True}
        rec_approved = False
        hide_approval = False
        user_ids = approval.approver_ids.mapped('user_id')
        approver_sequence = approval.approver_ids.filtered(lambda x: x.user_id.id == self.env.user.id).sequence
        top_approver = approval.approver_ids.filtered(lambda x: x.sequence < approver_sequence)
        top_approved = self.env['record.approved'].search([('state', '=', 'approved'), ('res_model', '=', res_model), ('res_id', '=', res_id), ('user_id', 'in', top_approver.mapped('user_id').ids)])

        if approval and approval.type == 'one':
            if self.env['record.approved'].search([('state', '=', 'approved'), ('res_model', '=', res_model), ('res_id', '=', res_id)]):
                rec_approved = True
        if approval and approval.type == 'all':
            rec_ids = self.env['record.approved'].search([('state', '=', 'approved'), ('user_id', 'in', user_ids.ids), ('res_model', '=', res_model), ('res_id', '=', res_id)])
            if len(rec_ids) == len(user_ids.ids):
                rec_approved = True
            if (self.env.user.id in rec_ids.mapped('user_id').ids) or (len(top_approver) > len(top_approved)):
                hide_approval = True

        status = {'show_approval': False, 'show_all': False, 'to_approve': False}
        rejected = self.env['record.approved'].search_count([('state', '=', 'rejected'), ('res_model', '=', res_model), ('res_id', '=', res_id)])
        if not rejected and approval and not rec_approved and (self.env.user.id in user_ids.ids) and not hide_approval and not approval_bool.is_sent_to_approval:
            status['to_approve'] = True
        if not rejected and approval and not rec_approved and (self.env.user.id in user_ids.ids) and not hide_approval and approval_bool.is_sent_to_approval:
            status['show_approval'] = True
        if not rejected and not approval or (approval and rec_approved):
            status['show_all'] = True
        return status

class RecordApprover(models.Model):
    _name = 'record.approver'
    _description = 'Record Approver'

    sequence = fields.Integer(index=True, help="Gives the sequence order when displaying a list of bank statement lines.", default=1)
    user_id = fields.Many2one('res.users', required=True)
    approval_id = fields.Many2one('record.approval')

class RecordApproved(models.Model):
    _name = 'record.approved'
    _description = 'Record Approved'
    _rec_name = 'res_model'

    res_model = fields.Char(string='Related Document Model')
    res_id = fields.Char(string='Related Document ID')
    user_id = fields.Many2one('res.users', string='Approved By')
    date = fields.Datetime('Approved Date')
    state = fields.Selection([('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')])
