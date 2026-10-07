from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Bed(models.Model):
    _name = "accommodation.bed"
    _description = "Bed Allocation"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Bed Number", required=True)
    room_id = fields.Many2one("accommodation.room", string="Room", required=True, domain="[('camp_id', '=', camp_id), ('floor_id', '=', floor_id)]")
    floor_id = fields.Many2one("accommodation.floor", string="Floor", domain="[('camp_id', '=', camp_id)]")
    status = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved')
    ], string="Status", default='available')
    camp_id = fields.Many2one('accommodation.camp', string="Camp", domain=[('status', '=', 'active')])
    occupied_employee_id = fields.Many2one("hr.employee", string="Occupied By", readonly=True)
    occupied_customer = fields.Char(string="Occupied Customer", readonly=True,)
    check_in_time = fields.Datetime(string="Check-In Time", readonly=True)
    reserved_from = fields.Date(string="Reserved From", readonly=True)
    reserved_to = fields.Date(string="Reserved To", readonly=True)
    reservation_reason = fields.Text(string="Reservation Reason", readonly=True)
    requested_by = fields.Many2one('res.users', string="Requested By", readonly=True)
    allocated_bed_numbers = fields.Char(string="Previously Allocated Beds", compute="_compute_allocated_bed_numbers")
    _sql_constraints = [
        ('unique_bed_number', 'unique(name, room_id)', "A bed with this number already exists in this room!")
    ]

    @api.depends('room_id', 'room_id.bed_ids.status')
    def _compute_allocated_bed_numbers(self):
        for bed in self:
            if not bed.room_id:
                bed.allocated_bed_numbers = ""
                continue  
            allocated_beds = bed.room_id.bed_ids.filtered(lambda b: b.status == 'occupied' and b.id != bed.id)

            if allocated_beds:
                bed.allocated_bed_numbers = ", ".join(allocated_beds.mapped('name'))
            else:
                bed.allocated_bed_numbers = "No allocated beds"

    @api.onchange('name', 'room_id')
    def _onchange_check_duplicate_bed_number(self):
        if self.name and self.room_id:
            if self.id and self.id != 0:
                existing_bed = self.env['accommodation.bed'].search([
                    ('name', '=', self.name),
                    ('room_id', '=', self.room_id.id),
                    ('id', '!=', self.id)  
                ])
            else:
                existing_bed = self.env['accommodation.bed'].search([
                    ('name', '=', self.name),
                    ('room_id', '=', self.room_id.id)
                ])

            if existing_bed:
                raise ValidationError(f"A bed with the number '{self.name}' already exists in this room!")

    @api.onchange('room_id')
    def _onchange_room_id(self):
        if self.room_id:
            self.floor_id = self.room_id.floor_id
            self.camp_id = self.room_id.camp_id
    
    @api.onchange('camp_id')
    def _onchange_camp_id(self):
        self.floor_id = False
        self.room_id = False
        return {
            'domain': {
                'floor_id': [('camp_id', '=', self.camp_id.id)],
                'room_id': [('camp_id', '=', self.camp_id.id)],
            }
        }

    @api.onchange('floor_id')
    def _onchange_floor_id(self):
        self.room_id = False
        return {
            'domain': {
                'room_id': [('camp_id', '=', self.camp_id.id), ('floor_id', '=', self.floor_id.id)]
            }
        }
        
        
    def _get_available_beds(self):
        return self.search([
            ('status', '=', 'available'),
            ('camp_id', '=', self.camp_id.id),
            ('floor_id', '=', self.floor_id.id),
            ('room_id.type', '=', self.room_id.type)
        ])
    
    @api.onchange('room_id')
    def _onchange_room(self):
        if self.room_id:
            self.floor_id = self.room_id.floor_id
            self.camp_id = self.room_id.camp_id

    @api.constrains('room_id')
    def _check_room_capacity(self):
        for bed in self:
            if bed.room_id:
                allocated_beds = self.search_count([
                    ('room_id', '=', bed.room_id.id)
                ])
                if allocated_beds > bed.room_id.capacity:
                    raise ValidationError(f"Room {bed.room_id.name} has reached its maximum capacity of {bed.room_id.capacity} beds.")