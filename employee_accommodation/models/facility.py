from odoo import models, fields, api

class Facility(models.Model):
    _name = "accommodation.facility"
    _description = "Facility Management"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    
    sequence_id = fields.Char("Sequence ID", required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('accommodation.facility'))
    name = fields.Char("Facility Name", required=True)
    facility_code = fields.Char("Facility Code", required=True)
    facility_type = fields.Selection([
        ('camp', 'Camp'),
        ('floor', 'Floor'),
        ('room', 'Room')
    ], string="Facility Type", required=True)
    camp_id = fields.Many2one("accommodation.camp", string="Camp", domain=[('status', '=', 'active')])
    floor_id = fields.Many2one("accommodation.floor", string="Floor", 
                               domain="[('camp_id', '=', camp_id)]")
    room_id = fields.Many2one("accommodation.room", string="Room", 
                              domain="[('floor_id', '=', floor_id)]")
    status = fields.Selection([
        ('good', 'Good'),
        ('damaged', 'Damaged'),
        ('missing', 'Missing')
    ], string="Status", required=True, default='good')
    usage = fields.Selection([
        ('common', 'Common'),
        ('shared', 'Shared'),
        ('employee', 'Employee'),
        ('customer', 'Customer')
    ], string="Usage", required=True, default='common')

    state = fields.Selection([
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('retired', 'Retired')
    ], string="State", required=True, default='available', tracking=True)
    remarks = fields.Html(string="Remarks")
    employee_id = fields.Many2one("hr.employee", string="Used By", readonly=True)
    check_in_time = fields.Datetime(string="Check-In Time", readonly=True)
    check_in_id = fields.Many2one("accommodation.check.in", string="Check-In Record", readonly=True)
    customer_id = fields.Many2one("res.partner", string="Used By (Customer)", readonly=True)
    employee_name = fields.Char(string="Employee Name", readonly=True)
    customer_check_in_id = fields.Many2one("customer.checkin", string="Check-In Record", readonly=True)


    def action_set_available(self):
        self.state = 'available'

    def action_set_in_use(self):
        self.state = 'in_use'

    def action_set_retired(self):
        self.state = 'retired'
    
    @api.onchange('facility_type')
    def _onchange_facility_type(self):
        if self.facility_type == 'camp':
            self.floor_id = False
            self.room_id = False
        elif self.facility_type == 'floor':
            self.room_id = False
        elif self.facility_type == 'room':
            pass  
    
    @api.onchange('camp_id')
    def _onchange_camp_id(self):
        self.floor_id = False
        self.room_id = False
    
    @api.onchange('floor_id')
    def _onchange_floor_id(self):
        self.room_id = False
    
    @api.model
    def create(self, vals):
        if vals.get('name') and vals.get('facility_code'):
            vals['name'] = f"{vals['name']} - {vals['facility_code']}"
        return super(Facility, self).create(vals)

    def write(self, vals):
        if 'name' in vals or 'facility_code' in vals:
            name = vals.get('name', self.name)
            facility_code = vals.get('facility_code', self.facility_code)
            vals['name'] = f"{name} - {facility_code}"
        return super(Facility, self).write(vals)
    