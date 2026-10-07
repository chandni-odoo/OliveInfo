# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta, datetime
import json
import calendar

from odoo.tools import float_is_zero, html_keep_url, is_html_empty

from odoo.tools.safe_eval import safe_eval


class HRAttendance(models.Model):
    _inherit = 'hr.attendance'

    # @api.model
    # def create(self, vals):
    #     partner = self.env['res.partner'].browse(vals.get('partner_id'))
    #     if partner.partner_id.ava_credit_bal > partner.partner_id.credit_limit:
    #         raise UserError('The Customer Credit Limit is Over!!!')

    #     return super(HRAttendance, self).create(vals)

    @api.model
    def create(self, vals):
        partner = self.env['res.partner'].browse(vals.get('partner_id'))
        if partner.partner_id.ava_credit_bal <= 0:
            raise UserError('The Customer Credit Limit is Over!!!')

        return super(HRAttendance, self).create(vals)
