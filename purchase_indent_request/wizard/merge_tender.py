# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models,fields,api, _
from odoo.exceptions import UserError


class IndentRequestTendar(models.TransientModel):
    _name = 'indent.request.tender.wizard'
    _description = "Indent Request Tender wizard"

    partner_id = fields.Many2one('res.partner', string="Partner")
    tender_date = fields.Date(string="Tender Date")

    def _prepare_tender_lines(self,line):
        remaining_qty = abs((line.quantity + line.extra_qty) - line.available_qty)
        return{
            'product_id' : line.product_id.id or False,
            'product_uom_id' : line.product_uom.id or False,
            'product_qty' : remaining_qty,
            'price_unit' : line.price_unit,
            'schedule_date' : self.tender_date,
            'move_dest_id' : line.move_ids.mapped('move_dest_ids') and line.move_ids.mapped('move_dest_ids')[0].id or False,
        }

    def _prepaire_tender(self, request_ids):
        lines = [(0,0, self._prepare_tender_lines(line)) for line in request_ids.mapped('request_lines_ids').filtered(lambda x:(x.quantity + x.extra_qty) > x.available_qty)]
        origin = ', '.join(request_ids.mapped('name')) or ''
        return {
            'user_id' : request_ids.mapped('user_id').id or False,
            'vendor_id' : self.partner_id.id or False,
            'seller_type' : self.partner_id.olila_seller_type,
            'indent_request_ids' : request_ids.ids or False,
            'ordering_date' : self.tender_date,
            'origin' : origin,
            'line_ids' : lines

        }

    def merge_tender(self):
        active_ids = self.env.context.get('active_ids', [])
        indent_request_ids = self.env['indent.request'].browse(active_ids)
        user_id = indent_request_ids.mapped('user_id')
        if len(user_id) > 1:
            raise UserError(_('Please select same User.'))
        for line in indent_request_ids:
            line.check_availability()
        if not all([rec.state == 'waiting' for rec in indent_request_ids]):
            raise UserError(_('Indent request must be in waiting state.'))
        vals = self._prepaire_tender(indent_request_ids)
        tender_id = self.env['purchase.requisition'].create(vals)
        indent_request_ids.request_lines_ids.write({'tender_id' : tender_id.id})
        return True
