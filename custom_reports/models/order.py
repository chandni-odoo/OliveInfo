# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression


class Saleorder(models.Model):
    _inherit = 'sale.order'

    get_pass = fields.Char(string='Gate Pass/Visa')
    notice_period = fields.Char(string="Notice Period")
    off_hire_notice_period = fields.Char(string="Off Hire Notice Period")
    term_condition = fields.Html(string="Miscellaneous Term Cond.")
    aft_type_by = fields.Selection([
                                ('dulsco', 'Dulsco'),
                                ('client', 'Client'), 
                                ('candidate', 'Candidate')], 
                                string="FAT By")    
