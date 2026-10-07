# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def create_stock_move(self):
        move_ref = self.env['stock.move']
        form_view_id = self.env.ref('stock.view_picking_form').id
        line_ids = self.invoice_line_ids.filtered(lambda a: a.product_id.detailed_type != 'service')
        stock_move_ids = []
        for line in line_ids:
            val = {
                'product_id' : line.partner_id.id,
                'product_uom_qty' : line.quantity,
                'product_uom' : line.product_uom_id.id,
            }
            move_id = move_ref.create(move_ref)
            print("________move_id",move_id)
            stock_move_ids.append(move_id.id)
        print("________stock_move_ids",stock_move_ids)
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'view_id': form_view_id,
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'move_ids_without_package': stock_move_ids,
            },
        }