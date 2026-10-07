from odoo import models, fields, api, _
from datetime import date


class LpoControl(models.Model):
    _inherit = 'lpo.control'
    
    total_invoice_posted = fields.Float(
        string="Total Invoice Posted",
        compute="_compute_invoice_amounts",
        store=True
    )
    total_invoice_unposted = fields.Float(
        string="Total Invoice Unposted",
        compute="_compute_invoice_amounts",
        store=True
    )
    total_unbilled = fields.Float(
        string="Total Unbilled",
        compute="_compute_unbilled_amount",
        store=True
    )
    total_amount_used = fields.Float(
        string="Total Amount Used",
        compute="_compute_total_amount_used",
        store=True
    )
    total_po_value = fields.Float(
        string="Total PO Value",
        compute="_compute_total_po_value",
        store=True
    )
    total_available_balance = fields.Float(
        string="Total Available Balance",
        compute="_compute_available_balance",
        store=True
    )
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    
    @api.depends('sale_id', 'sale_id.invoice_ids', 'sale_id.invoice_ids.state', 'sale_id.invoice_ids.amount_total')
    def _compute_invoice_amounts(self):
        for record in self:
            posted_amount = 0.0
            unposted_amount = 0.0
            
            if record.sale_id:
                invoices = self.env['account.move'].search([
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('invoice_origin', '=', record.sale_id.name)
                ])
                
                for invoice in invoices:
                    if invoice.state == 'posted':
                        if invoice.move_type == 'out_invoice':
                            posted_amount += invoice.amount_total
                        else:  
                            posted_amount -= invoice.amount_total
                    elif invoice.state != 'cancel':
                        if invoice.move_type == 'out_invoice':
                            unposted_amount += invoice.amount_total
                        else:  
                            unposted_amount -= invoice.amount_total
            
            record.total_invoice_posted = posted_amount
            record.total_invoice_unposted = unposted_amount


    @api.depends('sale_id', 'sale_id.order_line', 'sale_id.order_line.product_id', 'sale_id.order_line.task_id')
    def _compute_unbilled_amount(self):
        for record in self:
            total_unbilled = 0.0
            
            if record.sale_id:
                for order_line in record.sale_id.order_line:
                    if order_line.product_id.code in ['SOC', 'NOC']:
                        continue
                        
                    if order_line.task_id:
                        total_unbilled += order_line.task_id.unbilled_value
                    else:
                        unbilled_qty = order_line.qty_delivered - order_line.qty_invoiced
                        if unbilled_qty > 0:
                            total_unbilled += unbilled_qty * order_line.price_unit
            
            record.total_unbilled = total_unbilled
    
    
    @api.depends('total_invoice_posted', 'total_invoice_unposted', 'total_unbilled')
    def _compute_total_amount_used(self):
        for record in self:
            record.total_amount_used = record.total_invoice_posted + record.total_invoice_unposted + record.total_unbilled
    
    @api.depends('sale_id.lpo_control_ids.lpo_control_line_ids.amount')
    def _compute_total_po_value(self):
        for record in self:
            if record.sale_id:
                total_po_value = sum(
                    line.amount 
                    for lpo_control in record.sale_id.lpo_control_ids 
                    for line in lpo_control.lpo_control_line_ids
                )
                record.total_po_value = total_po_value
            else:
                record.total_po_value = 0.0
    
    @api.depends('total_po_value', 'total_amount_used')
    def _compute_available_balance(self):
        for record in self:
            record.total_available_balance = record.total_po_value - record.total_amount_used


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    lpo_control_ids = fields.One2many(
        'lpo.control', 
        'sale_id', 
        string='LPO Controls'
    )