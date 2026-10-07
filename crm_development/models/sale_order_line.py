from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    incoterm_ids = fields.Many2many(
        'account.incoterms',
        'sale_line_incoterm_rel',
        'sale_line_id',
        'incoterm_id',
        string='Incoterms'
    )

    landing_cost_id = fields.Many2one(
        'landing.cost',
        string='Landing Cost',
        copy=False
    )

    margin_type = fields.Selection(
        [
            ('percentage', 'Percentage'),
            ('fixed', 'Fixed Amount'),
            ('target_margin', 'Target Margin')
        ],
        string='Margin Type',
    )

    margin_unit = fields.Float(string='Margin Unit')
    margin = fields.Float(
        string='Margin',
        compute='_compute_margin_values',
        store=True
    )
    landed_cost = fields.Float(
        string='Landed Cost'
    )
    sales_price = fields.Float(
        string='Sales Price',
        compute='_compute_margin_values',
        store=True
    )

    gross_margin = fields.Float(
        string='Gross Margin (%)',
        compute='_compute_margin_values',
        store=True
    )

    profit = fields.Float(
        string='Profit',
        compute='_compute_margin_values',
        store=True
    )

    total_price = fields.Float(
        string="Total Price",
        compute="_compute_total_price",
        store=True
    )

    delivery_time = fields.Char(
        string="Delivery Time"
    )

    @api.depends('product_uom_qty', 'sales_price')
    def _compute_total_price(self):
        for line in self:
            line.total_price = line.product_uom_qty * line.sales_price

    @api.depends('price_unit','landed_cost','margin_type','margin_unit')
    def _compute_margin_values(self):
        for line in self:
            unit_price = line.price_unit or 0.0
            landed_cost = line.landed_cost or 0.0
            margin_value = 0.0

            # 1️⃣ Margin calculation
            if line.margin_type == 'fixed':
                margin_value = line.margin_unit

            elif line.margin_type == 'percentage':
                margin_value = (unit_price + landed_cost) * (line.margin_unit / 100.0)

            elif line.margin_type == 'target_margin':
                # Optional logic (can be customized later)
                margin_value = line.margin_unit

            # 2️⃣ Sales Price
            sales_price = unit_price + landed_cost + margin_value

            # 3️⃣ Profit
            profit = sales_price - unit_price - landed_cost

            # 4️⃣ Gross Margin %
            gross_margin = 0.0
            if sales_price:
                gross_margin = ((sales_price - landed_cost) / sales_price) * 100.0

            # Assign values
            line.margin = margin_value
            line.sales_price = sales_price
            line.profit = profit
            line.gross_margin = gross_margin

    def action_open_landing_cost(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Landing Cost',
            'res_model': 'landing.cost',
            'view_mode': 'form',
            'target': 'new',  
            'context': {
                'default_sale_line_id': self.id,
                'default_landing_cost_id': self.landing_cost_id.id,
            }
        }
    
    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)

        if self.order_id.branch_for == 'mro':
            res['price_unit'] = self.sales_price
            qty = self.qty_delivered - self.qty_invoiced
            if qty < 0:
                qty = 0

            res['quantity'] = qty

        return res
    

class SaleOrder(models.Model):
    _inherit = "sale.order"

    tender_count = fields.Integer(
        string="Tender Count",
        compute="_compute_tender_count"
    )

    indent_count = fields.Integer(
        string="RFQ Count",
        compute="_compute_indent_count"
    )

    # -------------------------------------
    # Compute Tender Count
    # -------------------------------------
    def _compute_tender_count(self):
        for order in self:
            count = 0
            if order.opportunity_id:
                indents = self.env['indent.request'].search([
                    ('crm_id', '=', order.opportunity_id.id)
                ])
                tenders = indents.mapped('request_lines_ids.tender_id')
                count = len(tenders)
            order.tender_count = count

    # -------------------------------------
    # Open Related Tender
    # -------------------------------------
    def action_view_tender_from_sale(self):
        self.ensure_one()

        if not self.opportunity_id:
            return {'type': 'ir.actions.act_window_close'}

        indents = self.env['indent.request'].search([
            ('crm_id', '=', self.opportunity_id.id)
        ])

        tender_ids = indents.mapped('request_lines_ids.tender_id')

        if not tender_ids:
            return {'type': 'ir.actions.act_window_close'}

        action = self.env.ref(
            'purchase_requisition.action_purchase_requisition'
        ).read()[0]

        if len(tender_ids) > 1:
            action['domain'] = [('id', 'in', tender_ids.ids)]
        else:
            form_view = self.env.ref(
                'purchase_requisition.view_purchase_requisition_form'
            )
            action['views'] = [(form_view.id, 'form')]
            action['res_id'] = tender_ids.id

        return action


    def _compute_indent_count(self):
        for order in self:
            if order.opportunity_id:
                order.indent_count = self.env['indent.request'].search_count([
                    ('crm_id', '=', order.opportunity_id.id)
                ])
            else:
                order.indent_count = 0

    def action_view_indent_request_from_sale(self):
        self.ensure_one()

        if not self.opportunity_id:
            return {'type': 'ir.actions.act_window_close'}

        indent_requests = self.env['indent.request'].search([
            ('crm_id', '=', self.opportunity_id.id)
        ])

        if not indent_requests:
            return {'type': 'ir.actions.act_window_close'}

        if len(indent_requests) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Indent Request',
                'view_mode': 'form',
                'res_model': 'indent.request',
                'res_id': indent_requests.id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Indent Requests',
                'view_mode': 'tree,form',
                'res_model': 'indent.request',
                'domain': [('id', 'in', indent_requests.ids)],
            }