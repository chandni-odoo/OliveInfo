# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class MailCompose(models.Model):
    _inherit = "helpdesk.sla"

    sub_type_id = fields.Many2one('helpdesk.ticket.sub.type', string='Sub Type')
    employee_ids = fields.Many2one('hr.employee', string='Escalation Manager')

    @api.model
    def test_cron_mail(self):
        print('email=====================')
        print('date=====================', datetime.now().date())

        helpdesk_email = self.env['helpdesk.ticket'].search(
            [('sla_deadline', '>=', datetime.now().date()), ('is_validate', '!=', True)])
        print('helpdesk_______________', helpdesk_email)

        for rec in helpdesk_email:
            print('rec____________', rec)
            mail_temp = self.env.ref('gt_helpdesk_extended.email_template_escalation_opening_ticket')
            print("_+_+_+_+_+_+_", mail_temp.send_mail(self.id, force_send=True))
            mail_temp.send_mail(rec.id, force_send=True)

            model_id = self.env['ir.model'].sudo().search([('model', '=', 'helpdesk.ticket')], limit=1)
            activity_type_id = self.env['mail.activity.type'].sudo().search(
                [('name', '=', 'Urgent Action Required: SLA Failure Escalation')],
                limit=1)
            activity_vals = {'res_model_id': model_id.id,
                             'res_model': 'helpdesk.ticket',
                             'res_id': rec.id,
                             'res_name': 'Urgent Action Required: SLA Failure Escalation',
                             'user_id': rec.ticket_type_id.manager_id.id,
                             'activity_type_id': activity_type_id.id,
                             'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')
                             }
            print("activity_vals+_+_+_+", activity_vals)
            activity_id = self.env['mail.activity'].sudo().create(activity_vals)
            print("activity_id+_+_+_+_+_", activity_id)

            rec.write({'is_validate': True})
