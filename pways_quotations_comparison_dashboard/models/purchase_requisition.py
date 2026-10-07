# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from calendar import monthrange
from datetime import date, timedelta
import datetime, calendar
import pytz

class PurchaseOrder(models.Model):
    _inherit = 'purchase.requisition'

    # @api.model
    # def get_purchase_line_data(self, option, reqisition_id=None):
    #     min_price_total = []
    #     min_delivery_date = []
        
    #     record = []
    #     total = []
    #     partner_ids = []

    #     min_total_vendor = 0
    #     min_delivery_vendor = 0
        
        
    #     tendor_id = self.env['purchase.requisition'].search([('id', '=', reqisition_id)], limit=1)
    #     purchase_ids = self.env['purchase.order'].search([('requisition_id', '=', tendor_id.id)]).filtered(lambda x: len(x.order_line.ids) > 0)
    #     product_ids = self.env['purchase.order.line'].search([('order_id', 'in', purchase_ids.ids)]).mapped('product_id')
        
    #     for purchase_id in purchase_ids:
    #         min_price_total.append(sum(purchase_id.order_line.mapped('price_unit')))
    #         min_delivery_date.append(min(purchase_id.order_line.mapped('date_planned')).date().strftime("%d/%m/%Y"))

    #     for order in purchase_ids:
    #         if min(min_price_total) == sum(order.order_line.mapped('price_unit')):
    #             min_total_vendor = order.partner_id
    #         if min(min_delivery_date) == min(order.order_line.mapped('date_planned')).date().strftime("%d/%m/%Y"):
    #             min_delivery_vendor = order.partner_id

    #     for order in purchase_ids:
    #         if option =='by_price' and min_total_vendor == order.partner_id:
    #             partner_ids.append({
    #                 'option': 'by_price',
    #                 'id': order.partner_id.id,
    #                 'name': order.partner_id.name,
    #             })
    #             total.append({
    #                 'state': order.state,
    #                 'option': 'by_price',
    #                 'id': order.id,
    #                 'partner_id':order.partner_id.id,
    #                 'total': order.amount_total,
    #                 'subtotal': sum(order.order_line.mapped('price_unit')),
    #                 'tax': order.amount_tax,
    #                 'delivery_date': min(order.order_line.mapped('date_planned')).date().strftime("%d/%m/%Y"),
    #             })
    #         elif option =='by_date' and min_delivery_vendor == order.partner_id:
    #             partner_ids.append({
    #                 'option': 'by_date',
    #                 'id': order.partner_id.id,
    #                 'name': order.partner_id.name,
    #             })
    #             total.append({
    #                 'state': order.state,
    #                 'option': 'by_date',
    #                 'id': order.id,
    #                 'partner_id':order.partner_id.id,
    #                 'total': order.amount_total,
    #                 'subtotal': sum(order.order_line.mapped('price_unit')),
    #                 'tax': order.amount_tax,
    #                 'delivery_date': min(order.order_line.mapped('date_planned')).date().strftime("%d/%m/%Y"),
    #             })
    #         else:
    #             partner_ids.append({
    #                 'option': '',
    #                 'id': order.partner_id.id,
    #                 'name': order.partner_id.name,
    #             })
    #             total.append({
    #                 'state': order.state,
    #                 'option': '',
    #                 'id': order.id,
    #                 'partner_id':order.partner_id.id,
    #                 'total': order.amount_total,
    #                 'subtotal': sum(order.order_line.mapped('price_unit')),
    #                 'tax': order.amount_tax,
    #                 'delivery_date': min(order.order_line.mapped('date_planned')).date().strftime("%d/%m/%Y"),
    #             })

    #     for product_id in product_ids:
    #         lines=[]
    #         min_prize = min(self.env['purchase.order.line'].search([
    #             ('order_id', 'in', purchase_ids.ids), 
    #             ('product_id', '=', product_id.id)]).mapped('price_unit'))
    #         min_prize_vendor = self.env['purchase.order'].search([
    #             ('order_line', '=', self.env['purchase.order.line'].search([
    #                 ('order_id', 'in', purchase_ids.ids), 
    #                 ('product_id', '=', product_id.id), 
    #                 ('price_unit', '=', min_prize)
    #                 ], limit=1).id)
    #             ]).partner_id
    #         min_date = min(self.env['purchase.order.line'].search([
    #             ('order_id', 'in', purchase_ids.ids), 
    #             ('product_id', '=', product_id.id)]).mapped('date_planned'))
    #         min_date_vendor = self.env['purchase.order'].search([
    #             ('order_line', '=', self.env['purchase.order.line'].search([
    #                 ('order_id', 'in', purchase_ids.ids), 
    #                 ('product_id', '=', product_id.id), 
    #                 ('date_planned', '=', min_date)
    #                 ], limit=1).id)
    #             ]).partner_id
    #         for vendor_id in purchase_ids:
    #             if product_id.id in vendor_id.order_line.mapped('product_id').ids:
    #                 for order_line in vendor_id.order_line:
    #                     if order_line.product_id.id == product_id.id:
    #                         if option =='by_price' and min_total_vendor == vendor_id.partner_id:
    #                             lines.append({
    #                                 'option': 'by_price',
    #                                 'message': ('Delivery Date :' + str(order_line.date_planned)),
    #                                 'vendor_id': vendor_id.partner_id.id,
    #                                 'line_id': order_line.id,
    #                                 'product_id': order_line.product_id.id,
    #                                 'vendor_name': vendor_id.partner_id.name,
    #                                 'unit_price': order_line.price_unit,
    #                                 'qty': order_line.product_qty,
    #                                 })
                            
    #                         elif option =='by_date' and min_delivery_vendor == vendor_id.partner_id:
    #                             lines.append({
    #                                 'option': 'by_date',
    #                                 'vendor_id': vendor_id.partner_id.id,
    #                                 'message': ('Delivery Date :' + str(order_line.date_planned)),
    #                                 'line_id': order_line.id,
    #                                 'product_id': order_line.product_id.id,
    #                                 'vendor_name': vendor_id.partner_id.name,
    #                                 'unit_price': order_line.price_unit,
    #                                 'qty': order_line.product_qty,
    #                                 })
    #                         else:
    #                             lines.append({
    #                                 'option': '',
    #                                 'vendor_id': vendor_id.partner_id.id,
    #                                 'message': ('Delivery Date :' + str(order_line.date_planned)),
    #                                 'line_id': order_line.id,
    #                                 'product_id': order_line.product_id.id,
    #                                 'vendor_name': vendor_id.partner_id.name,
    #                                 'unit_price': order_line.price_unit,
    #                                 'qty': order_line.product_qty,
    #                                 })
    #             else:
    #                 lines.append({
    #                     'option': '',
    #                     'vendor_id': 0,
    #                     'line_id': 0,
    #                     'product_id': product_id.id,
    #                     'vendor_name': 0,
    #                     'unit_price': 0,
    #                     'qty': 0,
    #                     })


    #         record.append({
    #             'min_date_vendor': min_date_vendor.name,
    #             'min_date': min_date.date().strftime("%d/%m/%Y"),
    #             'product_id': product_id.id,
    #             'product_name': product_id.name,
    #             'description': self.env['purchase.order.line'].search([('order_id', 'in', purchase_ids.ids), ('product_id', '=', product_id.id)], limit=1).name,
    #             'min_prize': min_prize,
    #             'min_prize_vendor': min_prize_vendor.name,
    #             'message': ("Vendor Name: " + min_prize_vendor.name + " ,Min Prize: " + str(min_prize)),
    #             'record_lines': lines,
    #             })

    #     return {
    #         'record_line_ids': record, 
    #         'partner_ids': partner_ids, 
    #         'total': total, 
    #         'length': len(purchase_ids.ids), 
    #         'option': option, 
    #         'min_total_vendor': min_total_vendor, 
    #         'min_delivery_vendor': min_delivery_vendor,
    #         'reqisition_name': tendor_id.name,
    #     }

    @api.model
    def get_purchase_line_data(self, option, requisition_id=None):
        min_price_total = []
        min_delivery_date = []
        record = []
        total = []
        partner_ids = []

        min_total_vendor = self.env['res.partner']
        min_delivery_vendor = self.env['res.partner']

        requisition = self.env['purchase.requisition'].browse(requisition_id)
        if not requisition:
            return {}

        purchase_ids = self.env['purchase.order'].search([
            ('requisition_id', '=', requisition.id)
        ]).filtered(lambda x: x.order_line)

        product_ids = self.env['purchase.order.line'].search([
            ('order_id', 'in', purchase_ids.ids)
        ]).mapped('product_id')

        # Calculate min price and delivery date per purchase
        for purchase in purchase_ids:
            subtotal = sum(purchase.order_line.mapped('price_unit'))
            min_price_total.append(subtotal)

            valid_dates = [d for d in purchase.order_line.mapped('date_planned') if d]
            if valid_dates:
                min_delivery_date.append(min(valid_dates).date())
            else:
                min_delivery_date.append(None)

        # Determine vendors for min price and min date
        if min_price_total:
            min_total_val = min(min_price_total)
            for purchase in purchase_ids:
                if sum(purchase.order_line.mapped('price_unit')) == min_total_val:
                    min_total_vendor = purchase.partner_id
                    break

        if min_delivery_date:
            min_delivery_val = min([d for d in min_delivery_date if d])
            for purchase in purchase_ids:
                valid_dates = [d for d in purchase.order_line.mapped('date_planned') if d]
                if valid_dates and min(valid_dates).date() == min_delivery_val:
                    min_delivery_vendor = purchase.partner_id
                    break

        # Prepare partner_ids and total summary
        for purchase in purchase_ids:
            valid_dates = [d for d in purchase.order_line.mapped('date_planned') if d]
            delivery_date = min(valid_dates).date().strftime("%d/%m/%Y") if valid_dates else "N/A"

            option_flag = ''
            if option == 'by_price' and min_total_vendor == purchase.partner_id:
                option_flag = 'by_price'
            elif option == 'by_date' and min_delivery_vendor == purchase.partner_id:
                option_flag = 'by_date'

            partner_ids.append({
                'option': option_flag,
                'id': purchase.partner_id.id,
                'name': purchase.partner_id.name,
            })

            total.append({
                'state': purchase.state,
                'option': option_flag,
                'id': purchase.id,
                'partner_id': purchase.partner_id.id,
                'total': purchase.amount_total,
                'subtotal': sum(purchase.order_line.mapped('price_unit')),
                'tax': purchase.amount_tax,
                'delivery_date': delivery_date,
            })

        # Prepare record_line_ids (per product)
        for product in product_ids:
            lines = []
            product_lines = self.env['purchase.order.line'].search([
                ('order_id', 'in', purchase_ids.ids),
                ('product_id', '=', product.id)
            ])

            if not product_lines:
                continue

            min_price = min(product_lines.mapped('price_unit'))
            min_price_line = product_lines.filtered(lambda x: x.price_unit == min_price)[:1]
            min_price_vendor = min_price_line.order_id.partner_id

            valid_product_dates = [d for d in product_lines.mapped('date_planned') if d]
            if valid_product_dates:
                min_date = min(valid_product_dates)
                min_date_line = product_lines.filtered(lambda x: x.date_planned == min_date)[:1]
                min_date_vendor = min_date_line.order_id.partner_id
            else:
                min_date = None
                min_date_vendor = self.env['res.partner']

            for line in product_lines:
                option_flag = ''
                if option == 'by_price' and min_total_vendor == line.order_id.partner_id:
                    option_flag = 'by_price'
                elif option == 'by_date' and min_delivery_vendor == line.order_id.partner_id:
                    option_flag = 'by_date'

                lines.append({
                    'option': option_flag,
                    'vendor_id': line.order_id.partner_id.id,
                    'line_id': line.id,
                    'product_id': line.product_id.id,
                    'vendor_name': line.order_id.partner_id.name,
                    'unit_price': line.price_unit,
                    'qty': line.product_qty,
                    'delivery_date': line.date_planned.strftime("%d/%m/%Y") if line.date_planned else "N/A"
                })

            record.append({
                'min_date_vendor': min_date_vendor.name if min_date_vendor else 'N/A',
                'min_date': min_date.strftime("%d/%m/%Y") if min_date else 'N/A',
                'product_id': product.id,
                'product_name': product.name,
                'description': product_lines[:1].name if product_lines else '',
                'min_price': min_price,
                'min_price_vendor': min_price_vendor.name,
                'record_lines': lines,
            })

        return {
            'record_line_ids': record,
            'partner_ids': partner_ids,
            'total': total,
            'length': len(purchase_ids),
            'option': option,
            'min_total_vendor': min_total_vendor.name if min_total_vendor else 'N/A',
            'min_delivery_vendor': min_delivery_vendor.name if min_delivery_vendor else 'N/A',
            'requisition_name': requisition.name,
        }


    def action_open_dashboard(self):
        active_id = self.env.context.get('active_id')
        return {
            'name': 'Dashboard',
            'type': 'ir.actions.client',
            'tag': 'compare_dashboard',
            'context': "{'reqisition_id': active_id}",
        }

    @api.model
    def remove_line_action(self, line_id=None, active_id=None):
        lines = self.env['purchase.order.line'].search([('id', '=', line_id)])
        if lines:
            lines.unlink()
        return True

    def confirm_order_action(self, purchase_id=None):
        purchase_orders = self.env['purchase.order'].search([('id', '=', self.id)])
        for order in purchase_orders:
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
            return True
        
    # @api.model
    # def update_tender_action(self, requisition_id=None):
    #     requisition = self.env['purchase.requisition'].browse(requisition_id)
    #     if not requisition:
    #         return False

    #     purchase_orders = self.env['purchase.order'].search([
    #         ('requisition_id', '=', requisition.id)
    #     ])

    #     # Update each line in the requisition
    #     for line in requisition.line_ids:
    #         # Get all RFQ lines for this product
    #         product_lines = self.env['purchase.order.line'].search([
    #             ('order_id', 'in', purchase_orders.ids),
    #             ('product_id', '=', line.product_id.id)
    #         ])
            
    #         if not product_lines:
    #             continue
            
    #         # Find the line with minimum price
    #         min_price = float('inf')
    #         best_line = None
            
    #         for poline in product_lines:
    #             if poline.price_unit < min_price:
    #                 min_price = poline.price_unit
    #                 best_line = poline
            
    #         if best_line:
    #             # Update requisition line with best price and vendor
    #             line.write({
    #                 'price_unit': best_line.price_unit,
    #                 'vendor_id': best_line.order_id.partner_id.id
    #             })
        
    #     return True

    @api.model
    def update_tender_action(self, requisition_id=None, purchase_id=None):
        requisition = self.env['purchase.requisition'].browse(requisition_id)
        if not requisition:
            return False
        
        if purchase_id:
            purchase_order = self.env['purchase.order'].browse(purchase_id)
            if not purchase_order or purchase_order.requisition_id != requisition:
                return False
            
            for requisition_line in requisition.line_ids:
                po_line = self.env['purchase.order.line'].search([
                    ('order_id', '=', purchase_order.id),
                    ('product_id', '=', requisition_line.product_id.id)
                ], limit=1)
                
                if po_line:
                    requisition_line.write({
                        'price_unit': po_line.price_unit,
                        'vendor_id': purchase_order.partner_id.id,
                    })
        else:
            purchase_orders = self.env['purchase.order'].search([
                ('requisition_id', '=', requisition.id)
            ])
            
            for line in requisition.line_ids:
                product_lines = self.env['purchase.order.line'].search([
                    ('order_id', 'in', purchase_orders.ids),
                    ('product_id', '=', line.product_id.id)
                ])
                
                if product_lines:
                    best_line = min(product_lines, key=lambda x: x.price_unit)
                    line.write({
                        'price_unit': best_line.price_unit,
                        'vendor_id': best_line.order_id.partner_id.id,
                    })
        
        return True