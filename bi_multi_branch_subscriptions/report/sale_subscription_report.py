# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo import SUPERUSER_ID, tools


class SaleSubscriptionReport(models.Model):
    _inherit = "sale.subscription.report"
    
    branch_id = fields.Many2one('res.branch', string='Branch') 
    
    def _select(self):
        return super(SaleSubscriptionReport, self)._select() + ", sub.branch_id as branch_id"

    def _group_by(self):
        return super(SaleSubscriptionReport, self)._group_by() + ", sub.branch_id"
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
