# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountAsset(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super(AccountAsset, self).action_post()
        for move in self:
            for line in move.line_ids:
                if line.task_id:
                    for trip_sheet in line.task_id.trip_sheet_ids:
                        trip_sheets = self.env['custom.trip.sheet'].search([
                            ('req_seq', '=', trip_sheet.req_seq)
                        ])
                        for trip in trip_sheets:
                            trip.invoice_no = move.name
        return res
    

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    non_deductible_tax_value = fields.Monetary(
        string="Non-Deductible Tax Value",
        currency_field='currency_id',
        default=0.0,
        help="Non-deductible portion of tax included in this line"
    )
