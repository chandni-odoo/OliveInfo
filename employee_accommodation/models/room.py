from odoo import models, fields, api

class Room(models.Model):
    _name = "accommodation.room"
    _description = "Room Management"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Room Number", required=True)
    floor_id = fields.Many2one("accommodation.floor", string="Floor", domain="[('camp_id', '=', camp_id)]")
    camp_id = fields.Many2one('accommodation.camp', string="Camp", domain=[('status', '=', 'active')])
    type = fields.Selection([
        ('single', 'Single'),
        ('shared', 'Shared'),
        ('studio', 'Studio'),
        ('1bhk', '1BHK'),
        ('2bhk', '2BHK'),
        ('3bhk', '3BHK')
    ], string="Room Type", required=True)
    size = fields.Float("Size (Sqm)")
    capacity = fields.Integer("Capacity (No. of Beds)")
    facilities = fields.Many2many("accommodation.facility", string="Facilities")
    bed_ids = fields.One2many("accommodation.bed", "room_id", string="Beds")
    status = fields.Selection([
        ('available', 'Available'),
        ('full', 'Full')
    ], string="Status", default="available", compute="_compute_status")
    
    allocated_bed_count = fields.Integer(string="Allocated Beds", compute="_compute_bed_counts", store=True)
    available_bed_count = fields.Integer(string="Unallocated Beds", compute="_compute_bed_counts", store=True)
    
    @api.depends('bed_ids.status')
    def _compute_bed_counts(self):
        for room in self:
            allocated_beds = room.bed_ids.filtered(lambda b: b.status == 'occupied')
            room.allocated_bed_count = len(allocated_beds)
            room.available_bed_count = room.capacity - len(allocated_beds)

    @api.depends('allocated_bed_count')
    def _compute_status(self):
        for room in self:
            if room.allocated_bed_count >= room.capacity:
                room.status = 'full'
            else:
                room.status = 'available'

    @api.onchange('camp_id')
    def _onchange_camp_id(self):
        self.floor_id = False  
        return {'domain': {'floor_id': [('camp_id', '=', self.camp_id.id)]}}
    