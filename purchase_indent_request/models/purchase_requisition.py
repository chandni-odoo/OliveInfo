# -*- coding: utf-8 -*-

from odoo import models,fields,api, _
from odoo.exceptions import ValidationError


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    def _get_seller_type(self):
        res = [('local', 'Local'), ('import', 'Import')]
        return res

    indent_request_ids = fields.Many2many('indent.request', string='Indent')
    department_id = fields.Many2one('hr.department', string='Department')
    seller_type = fields.Selection(selection=_get_seller_type, string="Vendor Type")
    remark = fields.Text(string='Remark')

    @api.onchange('vendor_id')
    def onchange_vendor_type(self):
    	if self.vendor_id:
    		self.seller_type = self.vendor_id.olila_seller_type
              

class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    vendor_id = fields.Many2one('res.partner', string="Supplier")
    price_unit = fields.Float(string="Unit Price")
