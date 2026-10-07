# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models, modules, _
from pytz import timezone, UTC
import json

class Users(models.Model):
    _inherit = 'res.users'

    @api.model
    def systray_get_activities(self):
        res = super(Users, self).systray_get_activities()
        activity_type_id = self.env.ref('pways_purchase_approval.purchase_approval_activity')
        for model_data in res:
            model_id = self.env['ir.model'].sudo().search([('model', '=', model_data.get('model'))], limit=1)
            active_count = self.env['mail.activity'].search_count([('user_id', '=', self.env.user.id), ('res_model_id', '=', model_id.id), ('activity_type_id', '=', activity_type_id.id)])
            model_data['approval_count'] = active_count
            model_data['activity_domain'] = json.dumps([['activity_type_id', '=', activity_type_id.id]])
        return res
