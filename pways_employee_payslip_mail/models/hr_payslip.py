# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _find_mail_template(self, force_confirmation_template=False):
        template_id = False
        template_id = self.env['ir.model.data']._xmlid_to_res_id('pways_employee_payslip_mail.email_template_edi_payslip', raise_if_not_found=False)
        return template_id

    def action_payslip_send(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        template_id = self._find_mail_template()
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'hr.payslip',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': False,
            'custom_layout': "mail.mail_notification_paynow",
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang),
            'employee_id': self.employee_id.id
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def action_payslip_sends(self):
        email = self.env.user.email
        template_id = self.env.ref('pways_employee_payslip_mail.email_template_payslip_send')
        for slip in self:
            email_to = slip.employee_id.work_email
            template_id.with_context(from_email=email, email_to=email_to).sudo().send_mail(slip.id, force_send=True)
