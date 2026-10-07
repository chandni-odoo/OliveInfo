from odoo import api, fields, models

class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    asset_id = fields.Many2one('account.asset', string="Assets")
    asset_sequence = fields.Char('Asset Number', related='asset_id.asset_sequence')
#     pro_category_ids = fields.Many2many('product.product', string="Product Category Group")
#     equ_type_id = fields.Many2one('equipment.type', string="Equipment Type")

# class EquipmentType(models.Model):
#     _name = 'equipment.type'
#     _description = "Equipment Type"

#     name = fields.Char(string="Equipment Type", required=True)
