from odoo import models, fields, api

class Camp(models.Model):
    _name = "accommodation.camp"
    _description = "Camp Management"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    camp_seq = fields.Char(string="Camp ID", required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('accommodation.camp'))
    name = fields.Char("Camp Name", required=True)
    location_id = fields.Many2one('contact.location', string='Location')
    capacity = fields.Integer("Capacity (Pax)")
    total_floors = fields.Integer("Total Floors")
    total_rooms = fields.Integer("Total Rooms")
    size = fields.Float("Size (Sqm)")
    type = fields.Selection([
        ('owned', 'Owned'),
        ('rented', 'Rented')
    ], string="Camp Type", required=True)
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], string="Status", default='active')
    owner_id = fields.Many2one("res.partner", string="Owner")
    rental_start_date = fields.Date("Rental Start Date")
    rental_end_date = fields.Date("Rental End Date")
    camp_boss = fields.Many2one("res.users", string="Camp Boss")
    facilities = fields.Many2many("accommodation.facility", string="Facilities")
    floor_ids = fields.One2many("accommodation.floor", "camp_id", string="Floors")
    room_ids = fields.One2many("accommodation.room", "camp_id", string="Rooms") 
