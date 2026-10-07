from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    
    is_hold = fields.Boolean(string="Is Hold", compute='_compute_hold_status', store=True)
    hold_reason = fields.Char(string="Hold Reason", compute='_compute_hold_status', store=True)
    
    @api.depends('partner_id.hold_option', 'partner_id.is_customer_black_list', 
                'partner_id.hold_reason', 'partner_id.blacklist_reason')
    def _compute_hold_status(self):
        for order in self:
            order.is_hold = False
            order.hold_reason = False
            
            if order.partner_id:
                partner = order.partner_id
                hold_reasons = []
            
                if partner.hold_option in ('credit_block', 'hold'):
                    order.is_hold = True
                    if partner.hold_reason:
                        hold_reasons.append(partner.hold_reason)
                
                if partner.is_customer_black_list:
                    order.is_hold = True
                    if partner.blacklist_reason:
                        hold_reasons.append(_("Blacklisted: ") + partner.blacklist_reason)
                
                if hold_reasons:
                    order.hold_reason = "\n".join(hold_reasons)
