# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"


    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
    	res = super(PurchaseOrder, self)._onchange_requisition_id()
    	if self.requisition_id:
    		self.origin = self.requisition_id.origin
    		self.remark = self.requisition_id.remark
    		self.department_id = self.requisition_id.department_id and self.requisition_id.department_id.id
    	return res

    department_id = fields.Many2one('hr.department', string='Department')
    remark = fields.Text(string='Remark')
    lc_type = fields.Selection([('deferred', 'Deferred'), ('cash', 'Cash'),('at_sight','At Sight')], string='LC Type', default='cash')


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _prepare_account_move_line(self, move=False):
        result = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        result.update({
            'vehicle_id' : self.vehicle_id and self.vehicle_id.id or False,
            'employee_id' : self.employee_id and self.employee_id.id or False,
        })
        return result

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    detailed_type = fields.Selection(related='product_id.detailed_type', string="Product Type", store=True, readonly=True)
