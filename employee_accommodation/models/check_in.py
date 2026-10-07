from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date

class AccommodationCheckIn(models.Model):
    _name = 'accommodation.check.in'
    _description = 'Employee Check-In'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    allocation_id = fields.Char("Allocation ID", required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('accommodation.check.in'))
    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True,
        domain=lambda self: self._get_employee_domain())
    is_vendor_employee = fields.Boolean(string="Is Vendor Employee?", 
                                        help="Check if the employee is a vendor staff.")
    vendor_id = fields.Many2one("res.partner", string="Vendor", 
                                domain="[('is_company', '=', True)]", 
                                help="Select the vendor company if the employee is a vendor staff.")
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
    nationality = fields.Many2one(related='employee_id.country_id', string="Nationality", store=True)
    contact = fields.Char(related='employee_id.mobile_phone', string="Phone Number", store=True)
    business_unit = fields.Many2one(related='employee_id.branch_id', string="Branch", store=True)
    religion = fields.Many2one(related='employee_id.ethinic_code_id', string="Religion", store=True)
    designation = fields.Char(related='employee_id.job_title', string="Designation", store=True)
    date_of_join = fields.Date(string="Date of Join", related="employee_id.joining_date", store=True)
    address_details = fields.Text(related='employee_id.camp_information', string="Address Details", store=True)
    company = fields.Many2one(related='employee_id.company_id', string="Company", store=True)
    
    @api.model
    def _get_employee_domain(self):
        checked_in_employees = self.env['accommodation.check.in'].search([
            ('status', '=', 'checked_in')
        ]).mapped('employee_id.id')
        return [('id', 'not in', checked_in_employees)]
        
    @api.onchange('facilities')
    def _onchange_facility_domain(self):
        return {
            'domain': {
                'facilities': [('state', '=', 'available')]
            }
        }

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.nationality = self.employee_id.country_id
            self.contact = self.employee_id.mobile_phone
            self.business_unit = self.employee_id.branch_id
            self.religion = self.employee_id.ethinic_code_id
            self.designation = self.employee_id.job_title
            self.date_of_join = self.employee_id.joining_date
            self.address_details = self.employee_id.camp_information
            self.company = self.employee_id.company_id
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            if self.employee_id.hr_employee_type == 'subcontractor':  
                self.is_vendor_employee = True
                self.vendor_id = self.employee_id.vendor_name 
            else:
                self.is_vendor_employee = False
                self.vendor_id = False
    
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
    def write(self, vals):
        res = super(AccommodationCheckIn, self).write(vals)
        for record in self:
            message = f"Employee {record.employee_id.name} moved to {record.camp_id.name} / Room No. {record.room_id.name} / Bed No. {record.bed_id.name}."
            record.employee_id.message_post(body=message, subtype_xmlid="mail.mt_note")
        return res            
    
    @api.model
    def create(self, vals):
        record = super(AccommodationCheckIn, self).create(vals)
        message = f"Employee {record.employee_id.name} checked into {record.camp_id.name} / Room No. {record.room_id.name} / Bed No. {record.bed_id.name}."
        record.employee_id.message_post(body=message, subtype_xmlid="mail.mt_note")
        
        if record.facilities:
            for facility in record.facilities.filtered(lambda f: f.usage == 'employee'):
                facility.write({
                    'state': 'in_use',
                    'employee_id': record.employee_id.id,
                    'check_in_time': record.check_in_date,
                    'check_in_id': record.id,  
                })

        if vals.get('bed_id'):
            bed = self.env['accommodation.bed'].browse(vals['bed_id'])
            if bed.status == 'occupied':
                raise ValidationError(_("The selected bed is already occupied. Please choose another bed."))
            
            bed.write({
                'status': 'occupied',
                'occupied_employee_id': vals.get('employee_id'),
                'check_in_time': vals.get('check_in_date'),
            })

        elif vals.get('room_id'):
            available_bed = self.env['accommodation.bed'].search([
                ('room_id', '=', vals['room_id']),
                ('status', '=', 'available')
            ], limit=1)

            if available_bed:
                vals['bed_id'] = available_bed.id
                available_bed.write({
                    'status': 'occupied',
                    'occupied_employee_id': vals.get('employee_id'),
                    'check_in_time': vals.get('check_in_date'),
                })
            else:
                raise ValidationError(_("No available beds in the selected room. Please choose another room."))
          
        if vals.get('is_vendor_employee'):
            model_id = self.env['ir.model'].sudo().search([('model', '=', 'accommodation.check.in')], limit=1)
            if not model_id:
                return record 

            activity_type = self.env['mail.activity.type'].sudo().search([('name', '=', 'New Check-In Notification')], limit=1)
            if not activity_type:
                activity_type = self.env['mail.activity.type'].sudo().create({
                    'name': 'New Check-In Notification',
                    'category': 'default'
                })

            user_group = self.env.ref('employee_accommodation.notification_alert').users
            for admin in user_group:
                activity_vals = {
                    'res_model_id': model_id.id,  
                    'res_model': 'accommodation.check.in',
                    'res_id': record.id,
                    'res_name': f'New Check-In: {record.employee_id.name}',
                    'user_id': admin.id,
                    'activity_type_id': activity_type.id,
                    'date_deadline': fields.Datetime.today(),
                }
                self.env['mail.activity'].sudo().create(activity_vals)

        return record

    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.allocation_id}" 
            result.append((record.id, name))
        return result
    

    
