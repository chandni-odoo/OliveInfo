from odoo import api, models, fields, modules, _
from odoo.models import BaseModel
import datetime
from pytz import timezone, UTC
import json
from dateutil.relativedelta import relativedelta


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    # approval_status = fields.Selection([('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', string='Approval Status', compute='_compute_approval_status')
    approval_ids = fields.Many2many('record.approved', compute="_compute_approval_ids")
    my_approval = fields.Boolean(compute='_compute_my_approval', search='_search_my_approval', string='My Approval')
    is_sent_to_approval = fields.Boolean(default=False, compute='_compute_is_sent_to_approval')

    def _compute_is_sent_to_approval(self):
        for rec in self:
            rec.is_sent_to_approval = True
            if not self.env['record.approved'].search([('state', '=', 'pending'), ('user_id', '=', self.env.user.id), ('res_id', '=', rec.id), ('res_model', '=', rec._name)]):
                rec.is_sent_to_approval = False

    def _compute_my_approval(self):
        for rec in self:
            approval = self.env['record.approver'].search([('approval_id.model_name', '=', rec._name), ('user_id', '=', self.env.user.id)])
            if approval and self.env['record.approved'].search([('res_model', '=', rec._name), ('res_id', '=', rec.id), ('user_id', '=', self.env.user.id)]):
                rec.my_approval = False
            else:
                rec.my_approval = True

    def _search_my_approval(self, operator, value):
        approval = self.env['record.approver'].search([('approval_id.model_name', '=', self._name), ('user_id', '=', self.env.user.id)])
        if approval:
            to_be_approved = []
            all_recs = self.search(eval(approval.approval_id.filter_domain))
            reject_approved_ids = self.env['record.approved'].search([('res_id', 'in', [str(rec_id) for rec_id in all_recs.ids]), ('res_model', '=', self._name), '|', ('user_id', '=', self.env.user.id), ('state', '=', 'rejected')])
            for rec in all_recs:
                if str(rec.id) not in reject_approved_ids.mapped('res_id'):
                    # if hasattr(self, 'message_ids'):
                    #     self._create_mail_activity(all_recs)
                    to_be_approved.append(rec.id)
            return [('id', 'in', to_be_approved)]
        return [('id', 'in', [])]

    def _create_mail_activity(self, approval):
        activity_type_id = self.env.ref('pways_record_approval.pways_approval_activity')
        model = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
        activity = self.env['mail.activity'].sudo().search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', model.id),
            ('activity_type_id', '=', activity_type_id.id),
            ('user_id', '=', approval.user_id.id),
        ])
        if not activity:
            vals = {
                'res_id': self.id,
                'res_model_id': model.id,
                'activity_type_id': activity_type_id.id,
                'date_deadline': (fields.Datetime.today() + relativedelta(days=5)).strftime('%Y-%m-%d %H:%M'),
                'create_uid': self.env.user.id,
                'user_id': approval.user_id.id,
            }
            activity = self.env['mail.activity'].sudo().create(vals)
            return  activity
        return True

    def _done_mail_activity(self):
        model = self._name
        activity_type_id = self.env.ref('pways_record_approval.pways_approval_activity')
        model = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
        self.env['mail.activity'].sudo().search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', model.id),
            ('activity_type_id', '=', activity_type_id.id),
            ('user_id', '=', self.env.user.id),
        ]).action_done()


    def _compute_approval_ids(self):
        for rec in self:
            rec.approval_ids = self.env['record.approved'].search([('res_id', '=', rec.id), ('res_model', '=', rec._name)]).ids

    def pways_action_approve(self):
        rec = self.env['record.approved'].search([('state', '=', 'approved'), ('user_id', '=', self.env.user.id), ('res_id', '=', self.id), ('res_model', '=', self._name)])
        if not rec:
            approved_id = self.env['record.approved'].search([('state', '=', 'pending'), ('user_id', '=', self.env.user.id), ('res_id', '=', self.id), ('res_model', '=', self._name)])
            approved_id.write({'state': 'approved'})
            if hasattr(self, 'message_ids'):
                self.message_post(body="Approved by %s" % self.env.user.name)
                self._done_mail_activity()

    def pways_action_reject(self):
        view_id = self.env.ref('pways_record_approval.reject_reason_wizard_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Reason'),
            'view_mode': 'form',
            'res_model': 'reject.reason.wizard',
            'target': 'new',
            'views': [[view_id, 'form']],
        }

    def pways_action_pending(self):
        view_id = self.env.ref('pways_record_approval.pending_details_wizard_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approval Pending Details'),
            'view_mode': 'form',
            'res_model': 'pending.details.wizard',
            'target': 'new',
            'views': [[view_id, 'form']],
        }

    def pways_action_send_approval(self):
        approval = self.env['record.approval'].search([('model_name', '=', self._name)], limit=1)
        if approval:
            filter_domain = eval(approval.filter_domain) if approval and approval.filter_domain else []
            all_recs = self.search(filter_domain)
            if self.id in all_recs.ids:
                for app in approval.approver_ids:
                    approval_record = self.env['record.approved'].search([('res_id', '=', self.id), ('res_model', '=', app.approval_id.model_name), ('user_id', '=', app.user_id.id)])
                    if not approval_record:
                        self.env['record.approved'].create({
                            'res_model': self._name,
                            'res_id': self.id,
                            'user_id': app.user_id.id,
                            'date': fields.Datetime.now(),
                            'state': 'pending',
                        })
                        self._create_mail_activity(app)
        return True

class Users(models.Model):
    _inherit = 'res.users'

    @api.model
    def systray_get_activities(self):
        res = super(Users, self).systray_get_activities()
        activity_type_id = self.env.ref('pways_record_approval.pways_approval_activity')
        for model_data in res:
            model_id = self.env['ir.model'].sudo().search([('model', '=', model_data.get('model'))], limit=1)
            active_count = self.env['mail.activity'].search_count([('user_id', '=', self.env.user.id), ('res_model_id', '=', model_id.id), ('activity_type_id', '=', activity_type_id.id)])
            model_data['approval_count'] = active_count
            model_data['activity_domain'] = json.dumps([['activity_type_id', '=', activity_type_id.id]])
        return res
