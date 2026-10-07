# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta, datetime
import json
import calendar

from odoo.tools import float_is_zero, html_keep_url, is_html_empty
from odoo.tools.safe_eval import safe_eval


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def domain_tasks(self):
        if self._context.get('active_model') == 'sale.order' and self._context.get('active_id', False):
            sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
            tasks = sale_order.mapped('order_line').mapped('task_id')
            return [('id', 'in', tasks.ids)]

    task_ids = fields.Many2many('project.task', string='Task', domain=domain_tasks)

    @api.onchange('inv_date')
    def onchange_inv_date(self):
        if self.inv_date:
            start = date(self.inv_date.year, self.inv_date.month, 1)
            end = None
            if int(self.inv_date.month) in [1, 3, 5, 7, 8, 10, 12]:
                end = date(self.inv_date.year, self.inv_date.month, 31)
            elif int(self.inv_date.month) in [4, 6, 9, 11]:
                end = date(self.inv_date.year, self.inv_date.month, 30)
            elif int(self.inv_date.month) in [2]:
                end = date(self.inv_date.year, self.inv_date.month, 28)

            self.date_start_invoice_timesheet = start
            self.date_end_invoice_timesheet = end
            self.date = self.inv_date
