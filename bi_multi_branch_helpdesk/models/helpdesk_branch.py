# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    branch_id = fields.Many2one('res.branch', string='Branch') 
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
