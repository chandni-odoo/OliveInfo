from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date

class CustomerCheckIn(models.Model):
    _name = 'customer.checkin'
    _description = 'Customer Check-In'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Check-In Sequence", required=True, copy=False, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('customer.checkin'))
    customer_id = fields.Many2one('res.partner', string="Customer", required=True)
    employee_name = fields.Char(string="Employee Name")
    employee_ref = fields.Char(string="Employee Reference")
    qid = fields.Char(string="QID No.", required=True)
    passport = fields.Char(string="Passport No.")
    camp_id = fields.Many2one('accommodation.camp', string="Camp", required=True, domain=[('status', '=', 'active')])
    floor_id = fields.Many2one('accommodation.floor', string="Floor", domain="[('camp_id', '=', camp_id)]", required=True)
    room_id = fields.Many2one('accommodation.room', string="Room", domain="[('floor_id', '=', floor_id)]", required=True)
    bed_id = fields.Many2one('accommodation.bed', string="Bed", domain="[('room_id', '=', room_id), ('status', '=', 'available')]", required=True)
    check_in_date = fields.Datetime(string="Check-In Date", default=fields.Datetime.now, required=True)
    status = fields.Selection([
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out')
    ], string="Status", default="checked_in")
    facilities = fields.Many2many("accommodation.facility", string="Assigned Items", domain="[('state', '=', 'available')]")
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} - {record.employee_name}"  
            result.append((record.id, name))
        return result

    @api.onchange('camp_id')
    def _onchange_camp(self):
        self.floor_id = False
        self.room_id = False
        self.bed_id = False

    @api.onchange('floor_id')
    def _onchange_floor(self):
        self.room_id = False
        self.bed_id = False

    @api.onchange('room_id')
    def _onchange_room(self):
        self.bed_id = False
        if self.room_id:
            available_bed = self.env['accommodation.bed'].search([
                ('room_id', '=', self.room_id.id),
                ('status', '=', 'available')
            ], limit=1)
            if available_bed:
                self.bed_id = available_bed.id
            else:
                return {
                    'warning': {
                        'title': _("No Available Beds"),
                        'message': _("There are no available beds in the selected room."),
                    }
                }
    
    @api.model
    def create(self, vals):
        record = super(CustomerCheckIn, self).create(vals)
        customer_id = str(record.customer_id.id) if record.customer_id else "Unknown"
        customer_name = record.customer_id.name or "Unknown"
        employee_name = record.employee_name or "Unknown"
        occupied_customer = f"{customer_id} - {customer_name} ({employee_name})"
        if record.facilities:
            for facility in record.facilities.filtered(lambda f: f.usage == 'customer'):
                facility.write({
                    'state': 'in_use',
                    'customer_id': record.customer_id.id,
                    'employee_name': record.employee_name,
                    'check_in_time': record.check_in_date,
                    'customer_check_in_id': record.id,  
                })

        if vals.get('bed_id'):
            bed = self.env['accommodation.bed'].browse(vals['bed_id'])
            if bed.status == 'occupied':
                raise ValidationError(_("The selected bed is already occupied. Please choose another bed."))
            bed.write({
                'status': 'occupied',
                'occupied_customer': occupied_customer,
                'check_in_time': record.check_in_date,
            })

        elif vals.get('room_id'):
            available_bed = self.env['accommodation.bed'].search([
                ('room_id', '=', vals['room_id']),
                ('status', '=', 'available')
            ], limit=1)

            if available_bed:
                record.bed_id = available_bed.id
                available_bed.write({
                    'status': 'occupied',
                    'occupied_customer': occupied_customer,
                    'check_in_time': record.check_in_date,
                })
            else:
                raise ValidationError(_("No available beds in the selected room. Please choose another room."))

        return record

    