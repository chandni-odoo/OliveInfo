from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class EmployeeTransfer(models.Model):
    _name = 'employee.transfer'
    _description = 'Employee Accommodation Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Transfer Reference", copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('employee.transfer'))
    employee_id = fields.Many2one(
        'hr.employee', 
        string="Employee", 
        required=True
    )
    checkin_id = fields.Many2one('accommodation.check.in', string="Check-in Record", readonly=True)
    current_camp_id = fields.Many2one('accommodation.camp', string="Current Camp", readonly=True, domain=[('status', '=', 'active')])
    current_floor_id = fields.Many2one('accommodation.floor', string="Current Floor", readonly=True)
    current_room_id = fields.Many2one('accommodation.room', string="Current Room", readonly=True)
    current_bed_id = fields.Many2one('accommodation.bed', string="Current Bed", readonly=True)
    current_facilities = fields.Many2many(
        'accommodation.facility', 
        'accommodation_transfer_current_facility_rel',  
        'transfer_id', 'facility_id', 
        string="Current Facilities", readonly=True
    )
    new_camp_id = fields.Many2one('accommodation.camp', string="New Camp", required=True, domain=[('status', '=', 'active')])
    new_floor_id = fields.Many2one('accommodation.floor', string="New Floor")
    new_room_id = fields.Many2one('accommodation.room', string="New Room")
    new_bed_id = fields.Many2one('accommodation.bed', string="New Bed")
    use_existing_facilities = fields.Boolean(string="Use Existing Facilities")
    facilities = fields.Many2many(
        'accommodation.facility', 
        'accommodation_transfer_new_facility_rel',  
        'transfer_id', 'facility_id', domain="[('state', '=', 'available')]",
        string="New Facilities"
    )
    previous_camp_id = fields.Many2one('accommodation.camp', string="Previous Camp", readonly=True, domain=[('status', '=', 'active')])
    previous_floor_id = fields.Many2one('accommodation.floor', string="Previous Floor", readonly=True)
    previous_room_id = fields.Many2one('accommodation.room', string="Previous Room", readonly=True)
    previous_bed_id = fields.Many2one('accommodation.bed', string="Previous Bed", readonly=True)
    previous_facilities = fields.Many2many(
        'accommodation.facility', 
        'accommodation_transfer_previous_facility_rel',  
        'transfer_id', 'facility_id', 
        string="Previous Facilities", readonly=True
    )
    transfer_date = fields.Datetime(string="Transfer Date", default=fields.Datetime.now, required=True)
    reason = fields.Text(string="Transfer Reason")
    customer_id = fields.Many2one('res.partner', string="Customer", domain=[('customer_rank', '>', 0)])

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string="Status", default='draft', tracking=True)
    
    @api.model
    def _get_checked_in_employees(self):
        return self.env['accommodation.check.in'].search([('status', '=', 'checked_in')]).mapped('employee_id.id')
    
    @api.onchange('employee_id')
    def _update_employee_domain(self):
        checked_in_employee_ids = self._get_checked_in_employees()
        return {'domain': {'employee_id': [('id', 'in', checked_in_employee_ids)]}}
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            checkin_record = self.env['accommodation.check.in'].search([
                ('employee_id', '=', self.employee_id.id),
                ('status', '=', 'checked_in')
            ], limit=1)

            if checkin_record:
                self.checkin_id = checkin_record.id
                self.current_camp_id = checkin_record.camp_id.id
                self.current_floor_id = checkin_record.floor_id.id
                self.current_room_id = checkin_record.room_id.id
                self.current_bed_id = checkin_record.bed_id.id
                self.current_facilities = checkin_record.facilities.ids
            else:
                self.checkin_id = False
                self.current_camp_id = False
                self.current_floor_id = False
                self.current_room_id = False
                self.current_bed_id = False
                self.current_facilities = [(5, 0, 0)]  

                return {
                    'warning': {
                        'title': _("No Check-in Found"),
                        'message': _("This employee does not have an active check-in record."),
                    }
                }
                
    @api.onchange('use_existing_facilities')
    def _onchange_use_existing_facilities(self):
        if self.use_existing_facilities:
            self.facilities = self.current_facilities
        else:
            self.facilities = [(5, 0, 0)]  

    @api.onchange('new_camp_id')
    def _onchange_new_camp(self):
        self.new_floor_id = False
        self.new_room_id = False
        self.new_bed_id = False

        return {'domain': {
            'new_floor_id': [('camp_id', '=', self.new_camp_id.id)],
        }}

    @api.onchange('new_floor_id')
    def _onchange_new_floor(self):
        self.new_room_id = False
        self.new_bed_id = False

        return {'domain': {
            'new_room_id': [('floor_id', '=', self.new_floor_id.id)],
        }}

    @api.onchange('new_room_id')
    def _onchange_new_room(self):
        self.new_bed_id = False
        if self.new_room_id:
            available_beds = self.env['accommodation.bed'].search([
                ('room_id', '=', self.new_room_id.id),
                ('status', '=', 'available')
            ])

            if not available_beds:
                return {
                    'warning': {
                        'title': _("No Available Beds"),
                        'message': _("There are no available beds in the selected room."),
                    }
                }

        return {'domain': {
            'new_bed_id': [('room_id', '=', self.new_room_id.id), ('status', '=', 'available')],
        }}
     
        
    def action_approve(self):
        self.state = 'approved'
        
    def action_done(self):
        self.ensure_one()

        checkin_record = self.env['accommodation.check.in'].search([
            ('employee_id', '=', self.employee_id.id),
            ('status', '=', 'checked_in')
        ], limit=1)

        if not checkin_record:
            raise ValidationError(_("No active check-in record found in the system."))

        self.write({
            'previous_camp_id': checkin_record.camp_id.id,
            'previous_floor_id': checkin_record.floor_id.id,
            'previous_room_id': checkin_record.room_id.id,
            'previous_bed_id': checkin_record.bed_id.id,
            'previous_facilities': [(6, 0, checkin_record.facilities.ids)],
        })

        if checkin_record.bed_id:
            checkin_record.bed_id.write({
                'status': 'available',
                'occupied_employee_id': False,
                'check_in_time': False
            })

        checkin_record.write({
            'camp_id': self.new_camp_id.id,
            'floor_id': self.new_floor_id.id,
            'room_id': self.new_room_id.id,
            'bed_id': self.new_bed_id.id,
            'facilities': [(6, 0, self.facilities.ids)],
        })

        if self.new_bed_id:
            self.new_bed_id.write({
                'status': 'occupied',
                'occupied_employee_id': self.employee_id.id,
                'check_in_time': self.transfer_date,
            })

        if self.facilities:
            self.facilities.filtered(lambda f: f.usage == 'employee').write({
                    'state': 'in_use',
                    'employee_id': self.employee_id.id,
                    'check_in_time': self.transfer_date,
                    'check_in_id': self.id,  
                })

        self.state = 'done'
        
    def action_cancel(self):
        self.state = 'cancel'

    


    