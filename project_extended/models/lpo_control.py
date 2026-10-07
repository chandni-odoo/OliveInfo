# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class LpoControl(models.Model):
    _name = 'lpo.control'
    _description = "LPO Control"

    name = fields.Char(required=True, string="Number")
    date = fields.Datetime(string="Date", default=fields.Datetime.now)
    attachment_id = fields.Binary(string="Attachment")
    lpo_control_line_ids = fields.One2many('lpo.control.line', 'lpo_control_id')
    sale_id = fields.Many2one('sale.order')
    total_qty = fields.Float(string="LPO Quantity", compute="_compute_lpo_total")
    total_amount = fields.Float(string="LPO Amount", compute="_compute_lpo_total")
    total_no_of_hour = fields.Float(string="Total Hours", compute="_compute_lpo_total")
    branch_id = fields.Many2one('res.branch', string="Branch")

    @api.depends('lpo_control_line_ids')
    def _compute_lpo_total(self):
        for rec in self:
            rec.total_qty = sum(rec.lpo_control_line_ids.mapped('quantity'))
            rec.total_amount = sum(rec.lpo_control_line_ids.mapped('amount'))
            rec.total_no_of_hour = sum(rec.lpo_control_line_ids.mapped('no_of_hour'))


class LpoControlLine(models.Model):
    _name = 'lpo.control.line'
    _description = "LPO Control Line"

    lpo_control_id = fields.Many2one('lpo.control', ondelete='cascade', )
    name = fields.Char(required=True)
    no_of_hour = fields.Float('No. of hours')
    quantity = fields.Float(string="Quantity")
    amount = fields.Float(string="Amount")
    sale_order_line_id = fields.Many2one('sale.order.line')

    stop_check = fields.Boolean('Stop')
    warning_check = fields.Boolean('Warning')

    @api.onchange('stop_check')
    def _onchange_stop_check(self):
        if self.stop_check:
            self.warning_check = False

    @api.onchange('warning_check')
    def _onchange_warning_check(self):
        if self.warning_check:
            self.stop_check = False
