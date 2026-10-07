from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Floor(models.Model):
    _name = "accommodation.floor"
    _description = "Floor Management"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Floor", required=True)
    camp_id = fields.Many2one("accommodation.camp", string="Camp", required=True, domain=[('status', '=', 'active')])
    number_of_rooms = fields.Integer("Number of Rooms")
    size = fields.Float("Size (Sqm)")
    facilities = fields.Many2many("accommodation.facility", string="Facilities")
    room_ids = fields.One2many("accommodation.room", "floor_id", string="Rooms")
    
    @api.constrains('name', 'camp_id')
    def _check_duplicate_floor(self):
        for record in self:
            existing_floor = self.search([
                ('name', '=', record.name),
                ('camp_id', '=', record.camp_id.id),
                ('id', '!=', record.id)  
            ])
            if existing_floor:
                raise ValidationError("The floor name '%s' already exists in this camp!" % record.name)
    