# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta, datetime
import json
import calendar

from odoo.tools import float_is_zero, html_keep_url, is_html_empty

from odoo.tools.safe_eval import safe_eval


class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    # @api.model
    # def create(self, vals):
    #     project = self.env['project.task'].browse(vals.get('task_resource_id'))
    #     if project.partner_id.ava_credit_bal > project.partner_id.credit_limit:
    #         raise UserError('The Customer Credit Limit is Over!!!')

    #     return super(PlanningSlot, self).create(vals)

    @api.model
    def create(self, vals):
        project = self.env['project.task'].browse(vals.get('task_resource_id'))
        if project.partner_id.ava_credit_bal <= 0:
            raise UserError('The Customer Credit Limit is Over!!!')

        return super(PlanningSlot, self).create(vals)
