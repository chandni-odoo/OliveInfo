from odoo import api, fields, models

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    asset_sequence = fields.Char(string="Asset Number", readonly=True, default="NEW")
    location_id = fields.Many2one('asset.location', string="Location")
    sub_location_id = fields.Many2one('asset.sub.location', string="Sub Location")
    classification_id = fields.Many2one('asset.classification', string="Classification")
    has_equipment = fields.Boolean(string="Has Equipment", compute="_compute_has_equipment_vehicle")
    has_vehicle = fields.Boolean(string="Has Equipment", compute="_compute_has_equipment_vehicle")
    vehicle_count = fields.Integer(string="Vehicles", compute='_compute_vehicle_count')
    equipment_count = fields.Integer(string="Vehicles", compute='_compute_equipment_count')
    asset_qty = fields.Float(string="Asset Quantity")
    asset_remarks = fields.Text(string="Remarks")

    def _compute_equipment_count(self):
        for asset in self:
            asset.equipment_count = self.env['maintenance.equipment'].search_count([('asset_id', '=', asset.id)])

    def _compute_vehicle_count(self):
        for asset in self:
            asset.vehicle_count = self.env['fleet.vehicle'].search_count([('asset_id', '=', asset.id)])

    def _compute_has_equipment_vehicle(self):
        for asset in self:
            asset.has_vehicle = bool(self.env['fleet.vehicle'].search([('asset_id', '=', asset.id)]))
            asset.has_equipment = bool(self.env['maintenance.equipment'].search([('asset_id', '=', asset.id)]))

    def action_open_equipment(self): 
        return {
            'type': 'ir.actions.act_window',
            'name': 'Equipment',
            'view_type': 'form',
            'res_model': 'maintenance.equipment',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': "{'create': False}",
            'domain' : [('asset_id', '=', self.id)],
        }

    def action_open_fleet_vehicle(self): 
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicles',
            'view_type': 'form',
            'res_model': 'fleet.vehicle',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': "{'create': False}",
            'domain' : [('asset_id', '=', self.id)],
        }

    def create_equipment(self):
        return {
            'name': "Maintance",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'maintenance.equipment',
            'view_id': self.env.ref('maintenance.hr_equipment_view_form').id,
            'context': {'default_asset_id': self.id, 'default_name': self.name, 'default_cost': self.original_value, 'default_effective_date': self.acquisition_date},
        }

    def create_fleet_vehicle(self):
        return {
            'name': "Fleet Vehicle",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'fleet.vehicle',
            'view_id': self.env.ref('fleet.fleet_vehicle_view_form').id,
            'context': {'default_asset_id': self.id},
        }

    def validate(self):
        asset_ids = self.filtered(lambda x: x.asset_sequence == 'NEW' or not x.asset_sequence)
        if asset_ids:
            seq_name =  self.env['ir.sequence'].next_by_code('account_asset_sequence')
            asset_ids.write({'asset_sequence': seq_name if seq_name else 'NEW'})
        super(AccountAsset, self).validate()


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    asset_id = fields.Many2one('account.asset', string="Assets")
    asset_sequence = fields.Char('Asset Number', related='asset_id.asset_sequence')
