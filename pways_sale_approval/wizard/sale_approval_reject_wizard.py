# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime


class SaleRejectReasonWizard(models.TransientModel):
    _name = "sale.reject.reason.wizard"
    _description = "Reject Reason Wizard"

    reject_reason = fields.Text(string="Reject Reason")

    def action_reject(self):
        print('self.context++++++++++++', self._context)
        if self._context.get('active_model') != 'cost.plus':
            active_model = self.env.context.get('active_model')
            active_id = self.env[active_model].browse(self.env.context.get('active_id'))
            history_ids = self.env['sale.approval.history'].search([('status', '=', 'pending'), ('sale_id', '=', active_id.id), ('user_id', '=', self.env.user.id)])
            history_ids.write({'status': 'reject', 'date_done': datetime.now()})
            active_id.write({'reject_reason': self.reject_reason, 'state': 'to_reject'})

            for act in active_id.activity_ids.filtered(lambda u: u.user_id.id == self.env.user.id):
                act.action_done()

            model_id = self.env['ir.model'].sudo().search([('model', '=', 'sale.order')], limit=1)
            activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Sale Approval Update')],
                                                                            limit=1)
            if not activity_type_id:
                activity_type_id = self.env['mail.activity.type'].create({
                    'name': 'Sale Approval Update',
                    'res_model': 'sale.order',
                })
            activity_vals = {'res_model_id': model_id.id,
                             'res_model': 'sale.order',
                             'res_id': active_id.id,
                             'res_name': 'Sale Order Approval Update',
                             'user_id': active_id.user_id.id,
                             'activity_type_id': activity_type_id.id,
                             'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')
                             }
            print("activity_vals+_+_+_+", activity_vals)
            activity_id = self.env['mail.activity'].sudo().create(activity_vals)

        if self._context.get('active_model') == 'cost.plus':
            cost_plus = self.env['cost.plus'].browse(self._context.get('active_id'))
            cost_plus.write({'reject_reason': self.reject_reason, 'state': 'reject'})
            cost_plus.message_post(body=_('Rejected: %s ') % (self.reject_reason,))

