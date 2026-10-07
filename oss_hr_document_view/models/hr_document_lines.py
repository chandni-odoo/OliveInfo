# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date

class HrDocumentLine(models.Model):
    _inherit = 'hr.document.line'



    emp_branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
        related='employee_id.branch_id',
        store=True,
        readonly=True
    )
    employee_job_title = fields.Char(related='employee_id.job_title', string='Job Title', readonly=True, store=True)
    employee_manager = fields.Many2one(related='employee_id.parent_id', string='Manager', readonly=True, store=True)
    employee_status = fields.Selection(related='employee_id.emp_status', string='Status', readonly=True)
    days_to_expire = fields.Integer(
        string='Days to Expire',
        compute='_compute_days_to_expire',
        store=True,
    )

    expiry_status = fields.Selection([
        ('expired', 'Expired'),
        ('soon', 'Expiring Soon (1-30 days)'),
        ('medium', 'Expiring in 31-90 Days'),
        ('valid', 'Valid (>90 days)'),
    ], string='Expiry Status', compute='_compute_days_to_expire', store=True)

    
    @api.depends('valid_to')
    def _compute_days_to_expire(self):
        today = date.today()
        for record in self:
            if record.valid_to:
                delta = record.valid_to - today
                record.days_to_expire = delta.days
                if delta.days < 0:
                    record.expiry_status = 'expired'
                elif delta.days <= 30:
                    record.expiry_status = 'soon'
                elif delta.days <= 90:
                    record.expiry_status = 'medium'
                else:
                    record.expiry_status = 'valid'
            else:
                record.days_to_expire = 0
                record.expiry_status = 'expired'
