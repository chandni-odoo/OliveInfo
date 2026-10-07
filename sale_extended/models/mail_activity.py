from odoo import models, fields, api, _


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _action_done(self, feedback=False, attachment_ids=None):

        print('self++++++++++++++++', self)
        print('self++++++++++++++++', self._context)
        if self._context.get('default_res_id'):
            if self._context.get('default_res_model') == 'site.visit' or self._context.get(
                    'default_res_model') == 'sale.site.inspection':
                if self._context.get('default_res_model') == 'site.visit':
                    class_id = self.env['site.visit'].browse(self._context.get('default_res_id'))
                    mail_temp = self.env.ref('sale_extended.site_visit_mail_id')
                    mail_temp.send_mail(class_id.id, force_send=True)
                if self._context.get('default_res_model') == 'sale.site.inspection':
                    class_id = self.env['sale.site.inspection'].browse(self._context.get('default_res_id'))
                    mail_temp = self.env.ref('sale_extended.sale_site_inspection_mail_id')
                    mail_temp.send_mail(class_id.id, force_send=True)

        return super(MailActivity, self)._action_done(feedback, attachment_ids)
