# -*- coding: utf-8 -*-
from odoo import api, fields, models,_
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    log_fuel_id = fields.Many2one('fleet.vehicle.log.fuel', string="Log Fuel")


class FleetVehicleFuelLog(models.Model):    
    _name = 'fleet.vehicle.log.fuel'
    _rec_name = 'date'

    @api.onchange('vehicle_id')
    def on_change_vehicle_id(self):
        for i in self:
            if i.vehicle_id:
                i.driver_id = i.vehicle_id.driver_id.id

    @api.model
    def _get_default_location_id(self):
        stock_location = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
        try:
            stock_location.check_access_rule('read')
            return stock_location.id
        except (AttributeError, AccessError):
            return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).lot_stock_id.id

    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    location_id = fields.Many2one('stock.location', 'Location', default=_get_default_location_id)
    driver_id = fields.Many2one('res.partner', string="Driver")
    date = fields.Date ('Date')
    ini_km_reading = fields.Float('Initial Reading KM')
    end_km_reading = fields.Float('End Reading KM')
    total_km = fields.Float('Total KM' , compute='_compute_total_km')
    expected_fuel_req = fields.Float('Expected Fuel Requisition')
    fuel_amount = fields.Float('Fuel Purchased (Ltr)')
    amount = fields.Float('Amount')
    doc1 = fields.Binary('Bill upload')
    file_name = fields.Char("File Name")
    fuel_purchase_ids = fields.One2many('fuel.purchase.history', 'fuel_log_id', string="Fuel Purchase History")
    state = fields.Selection([('open', 'Open'), ('lock', 'Lock')], string="State", default='open', tracking=True)
    user_id = fields.Many2one('res.users', string='Created By', store= True, default=lambda self: self.env.user)
    refueling_ids = fields.One2many('refueling.details.line', 'log_fuel_id', string="Lines")
    invoice_count = fields.Integer(string="#Invoice Count", compute="_tota_invoice_count")
    picking_count = fields.Integer(string="#Delivery Count", compute="_tota_picking_count")


    def _tota_picking_count(self):
        for rec in self:
            picking_ids = self.env['stock.picking'].search([('log_fuel_id', '=', rec.id)])
            rec.picking_count = len(picking_ids.ids)

    def _tota_invoice_count(self):
        for rec in self:
            move_ids = self.env['account.move'].search([('log_fuel_id', '=', rec.id)])
            rec.invoice_count = len(move_ids.ids)

    def view_invoice(self):
        move_ids = self.env['account.move'].search([('log_fuel_id', '=', self.id)])
        return {
            'name': _('Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids.ids)]
        }

    def view_picking(self):
        picking_ids = self.env['stock.picking'].search([('log_fuel_id', '=', self.id)])
        return {
            'name': _('Picking'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', picking_ids.ids)]
        }

    @api.depends('end_km_reading', 'ini_km_reading')
    def _compute_total_km(self):
        for rec in self:
            rec.total_km = rec.end_km_reading - rec.ini_km_reading

    def _prepare_invoice_lines(self, line):
        return {
            'product_id' : line.product_id.id,
            'name': line.product_id.name,
            'quantity': line.quantity,
            'price_unit': line.price_unit,
            'tax_ids': [(6, 0, [])],
        }

    def _create_invoice(self):
        partner_id = False
        if self.vehicle_id and self.vehicle_id.log_contracts:
            partner_id = self.vehicle_id.log_contracts[0].insurer_id
        lines = [(0,0, self._prepare_invoice_lines(line)) for line in self.refueling_ids]
        vals = {'move_type': 'out_invoice', 
                'partner_id': partner_id.id if partner_id else False, 
                'date': self.date,
                'log_fuel_id' : self.id,
                'invoice_line_ids' : lines,}
        invoice_ids = self.env['account.move'].create(vals)
        return True

    def _prepare_procurement_id(self):
        name = "{}_{}".format(self.vehicle_id.model_id.name, str(self.id))
        group_id =  self.env['procurement.group'].search([('name', '=', name)], limit=1)
        if not group_id:
            group_id = self.env["procurement.group"].create({'name' : name})
        return group_id

    def _prepare_move_outgoing(self, line):
        log_contract_id = False
        if self.vehicle_id and self.vehicle_id.log_contracts:
            log_contract_id = self.vehicle_id and self.vehicle_id.log_contracts[0]
        partner_id = log_contract_id.insurer_id if log_contract_id else False
        if not partner_id:
            raise UserError(_("Partner not found"))
        company_id = self.env.company
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1)
        procurement_id = self._prepare_procurement_id()
        origin = "{}-{}".format(self.vehicle_id.model_id.name, self.vehicle_id.license_plate)
        return {
            'name' : line.product_id.name,
            'product_id': line.product_id.id,
            'product_uom': line.product_id.uom_id.id,
            'location_id':8,
            'location_dest_id':partner_id.property_stock_customer.id if partner_id.property_stock_customer else False,
            'company_id': company_id.id,
            'product_uom_qty': line.quantity,
            'origin': origin,
            'group_id' : procurement_id.id,
            'picking_type_id': picking_type_id.id,
        }

    def _create_picking(self):
        move_lines = [self._prepare_move_outgoing(line) for line in self.refueling_ids]
        move_ids = self.env['stock.move'].create(move_lines)
        # qty = move_ids._set_quantities_to_reservation()
        stock_move = move_ids._action_confirm()
        if stock_move.picking_id:
            stock_move.picking_id.write({'log_fuel_id' : self.id,})

    def action_lock(self):
        self.state = 'lock'
        self.env['fleet.vehicle.odometer'].create(
            {'value': self.end_km_reading, 'date': fields.date.today(), 'vehicle_id': self.vehicle_id.id,
             'driver_id': self.driver_id.id})
        total_fuel_purchase = 0
        for rec in self.fuel_purchase_ids:
            total_fuel_purchase = total_fuel_purchase + rec.fuel_purchase
        self.fuel_amount = total_fuel_purchase
        self.vehicle_id.average_mileage = (self.total_km / total_fuel_purchase) if total_fuel_purchase else 0
        #self._create_invoice()
        self._create_picking()

class FleetVehicleFuelLog(models.Model):
    _name = 'fuel.purchase.history'

    fuel_log_id = fields.Many2one('fleet.vehicle.log.fuel', string='Fuel Log')
    fuel_purchase = fields.Float('Fuel Purchase(litre)')
    fuel_type = fields.Selection([('gasoline', 'Petrol'),('lpg', 'CNG'),('diesel', 'Diesel'),('octane','Octane')], string="Fuel Type")
    amount = fields.Float('Amount')
    doc = fields.Binary('Bill upload')
    file_name = fields.Char("File Name")
    purchase_date = fields.Date("Purchase Date")

class RefuelingDetails(models.Model):
    _name = "refueling.details.line"

    @api.depends('price_unit', 'quantity')
    def _compute_amount(self):
        for line in self:
            line.sub_total = line.price_unit * line.quantity

    product_id = fields.Many2one('product.product', string="Product")
    location_id = fields.Many2one('stock.location', string="Location")
    quantity = fields.Float('Quantity')
    avelabal_quantity = fields.Float(string="Available Quantity")
    price_unit = fields.Float(string="Price Unit")
    sub_total = fields.Float('Sub Total', compute="_compute_amount")
    log_fuel_id = fields.Many2one('fleet.vehicle.log.fuel', string="Log Fuel")
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
        default=lambda self: self.env.company)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.standard_price or 0.0
