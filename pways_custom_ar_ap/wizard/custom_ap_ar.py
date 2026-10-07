from odoo import models, fields, api, _
import datetime
from datetime import timedelta, date


class CustomApAr(models.TransientModel):
    _name = 'custom.ap.ar'
    _description = "Customer AR AP"

    aged_state = fields.Selection([('ap', 'AP'), ('ar', 'AR')], default="ar", string='Aged State')
    as_on_date = fields.Date(string="As on Date", default=date.today())
    # based_on = fields.Selection([('invoice_date', 'Invoice Date'), ('due_date', 'Due Date')], defult="invoice_date", string='Based On')
    based_on = fields.Selection([
        ('invoice_date', 'Invoice/Bill Date'), 
        ('due_date', 'Due Date'),
        ('received_date', 'Received Date')
        ], default="invoice_date", string='Based On')
    due_range_ids = fields.Many2many('account.due.range', string="Due Ranges")
    customer_ids = fields.Many2many('res.partner', 'student_category_rel', string="Customer")
    vendors_ids = fields.Many2many('res.partner', string="Vendor")
    branch_ids = fields.Many2many('res.branch', string="Branch")

    def action_aged_xls_report(self):
        active_record = self
        data = {
            'active_record': active_record.id,
        }
        return self.env.ref('pways_custom_ar_ap.aged_xlsx').report_action(self, data=data)
