# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class HrLoan(models.Model):
    _inherit = 'hr.loan'

    settlement_id = fields.Many2one('leave.settlement', copy=False)
    unpaid_days = fields.Float('Unpaid Days')
    date_from = fields.Date(string = "Date", default=fields.date.today())
    date_to = fields.Date(string = "Date To", readonly=True)
    

    def action_loan_validate(self):
        for record in self:
            record.write({'state': 'approve'})