# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class Vehicle(models.Model):
    _inherit = 'fleet.vehicle'
    
    _sql_constraints = [
        ('license_unique',
         'unique(license_plate)',
         'The vehicle plate number Should be unique number !')
      ]

    def open_vehicle_fuel_logs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fuel Issue',
            'view_mode': 'tree,form',
            'res_model': 'fleet.vehicle.log.fuel',
            'domain': [('vehicle_id', '=', self.id)],
        }
    
    def get_fuel_log_count(self):
        count = self.env['fleet.vehicle.log.fuel'].search_count([('vehicle_id', '=', self.id)])
        self.fuel_log_count = count

    def open_vehicle_tyres(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tyres',
            'view_mode': 'tree,form',
            'res_model': 'vehicle.tyre.detail',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id}  
            
        }

    def get_tyres_count(self):
        count = self.env['vehicle.tyre.detail'].search_count([('vehicle_id', '=', self.id)])
        self.tyres_count = count
    
    # mobility_card = fields.Char('Mobility Card')

    # vehicle_type = fields.Selection(selection_add=[('car', 'Car'), ('bike', 'Bike')], default='car', required=True)
    tyres_count = fields.Integer(string='Tyres', compute='get_tyres_count')
    ntsa_start_date = fields.Date('NTSA Start Date')
    ntsa_end_date = fields.Date('NTSA End Date')
    speed_governor_start_date = fields.Date('Speed Governor Start Date')
    speed_governor_end_date = fields.Date('Speed Governor End Date')
    end_date = fields.Date('End Date')
    start_date = fields.Date('Start Date')
    insurance_no = fields.Char('Insurance No.')
    insurance_company = fields.Char('Insurance Company')
    vehicle_handover_count= fields.Integer(string='Handover', compute='get_vehicle_handover_count')
    vehicle_maintance_count= fields.Integer(string='Maintance', compute='get_vehicle_maintance_count')
    fuel_log_count = fields.Integer(string='Fuel Logs', compute='get_fuel_log_count')
    average_mileage = fields.Float('Average Mileage')
    on_services = fields.Selection([('self', 'Self'), ('contract', 'Contract')], default='self', string="On Services")
    ownership = fields.Selection([('self', 'Self'), ('3rd_part', '3rd party')], default='self', string="Ownership")
    # pro_category_ids = fields.Many2many('product.product', string="Product Category Group")

    def open_vehicle_handover(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicle Handover',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'vehicle.handover',
            'view_id': False,
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id}
        }

    def get_vehicle_handover_count(self):
        count = self.env['vehicle.handover'].search_count([('vehicle_id', '=', self.id)])
        self.vehicle_handover_count = count

    def open_vehicle_maintance(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicle Repair',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'repair.order',
            'view_id': False,
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id}
        }

    def get_vehicle_maintance_count(self):
        count = self.env['repair.order'].search_count([('vehicle_id', '=', self.id)])
        self.vehicle_maintance_count = count


class Contract(models.Model):
    _inherit = 'fleet.vehicle.log.contract'

    insurer_mobile = fields.Char('Mobile No.')
    purchaser_mobile = fields.Char('Mobile No.')
    transport_rate = fields.Float(string="Transport Rate")

    @api.onchange('insurer_id')
    def on_change_insurer(self):
        for i in self:
            if i.insurer_id:
                i.insurer_mobile = i.insurer_id.mobile

    @api.onchange('purchaser_id')
    def on_change_purchaser(self):
        for i in self:
            if i.purchaser_id:
                i.purchaser_mobile = i.purchaser_id.mobile
