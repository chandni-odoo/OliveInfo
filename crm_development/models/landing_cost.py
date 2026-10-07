from odoo import models, fields, api

class LandingCost(models.Model):
    _name = 'landing.cost'
    _description = 'Landing Cost'
    _rec_name = 'sale_line_id'

    sale_line_id = fields.Many2one(
        'sale.order.line',
        required=True,
        readonly=True
    )

    line_ids = fields.One2many(
        'landing.cost.line',
        'landing_cost_id'
    )

    total_amount = fields.Float(
        compute='_compute_total',
        store=True
    )

    rate_per_qty = fields.Float(
        compute='_compute_rate_per_qty',
        store=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        sale_line = self.env['sale.order.line'].browse(
            self.env.context.get('default_sale_line_id')
        )

        if not sale_line:
            return res

        # Reopen existing landing cost
        if sale_line.landing_cost_id:
            res.update({
                'sale_line_id': sale_line.id,
                'line_ids': [(6, 0, sale_line.landing_cost_id.line_ids.ids)],
            })
            return res

        lines = []
        products = self.env['product.product'].search([
            ('incoterm_ids', 'in', sale_line.incoterm_ids.ids)
        ])

        for product in products:
            lines.append((0, 0, {
                'product_id': product.id,
                'amount': 0.0
            }))

        res.update({
            'sale_line_id': sale_line.id,
            'line_ids': lines
        })
        return res

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    @api.depends('total_amount', 'sale_line_id.product_uom_qty')
    def _compute_rate_per_qty(self):
        for rec in self:
            qty = rec.sale_line_id.product_uom_qty or 1
            rec.rate_per_qty = rec.total_amount / qty

    def action_apply(self):
        self.ensure_one()

        # Save link
        self.sale_line_id.landing_cost_id = self.id
        self.sale_line_id.landed_cost = self.rate_per_qty

        return {'type': 'ir.actions.act_window_close'}
    

class LandingCostLine(models.Model):
    _name = 'landing.cost.line'
    _description = 'Landing Cost Line'

    landing_cost_id = fields.Many2one(
        'landing.cost',
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        required=True
    )

    amount = fields.Float(required=True)
