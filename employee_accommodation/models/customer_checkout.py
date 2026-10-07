from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CustomerCheckOut(models.Model):
    _name = 'customer.checkout'
    _description = 'Customer Check-Out'
    _rec_name = 'check_out_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    check_out_id = fields.Char("Check-out ID", required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('customer.checkout'))
    customer_id = fields.Many2one('res.partner', string="Customer", required=True,
                                  domain=lambda self: self._get_customer_domain())
    check_in_id = fields.Many2one('customer.checkin', string="Check-In Reference", required=True,
                                  domain="[('customer_id', '=', customer_id), ('status', '=', 'checked_in')]")
    customer_checklist_id = fields.Many2one('customer.checklist', string="Clearence Form", readonly=True)
    employee_name = fields.Char(string="Employee Name")
    camp_id = fields.Many2one('accommodation.camp', string="Camp", domain=[('status', '=', 'active')])
    floor_id = fields.Many2one('accommodation.floor', string="Floor")
    room_id = fields.Many2one('accommodation.room', string="Room")
    bed_id = fields.Many2one('accommodation.bed', string="Bed")
    check_out_date = fields.Datetime(string="Check-Out Date", default=fields.Datetime.now)
    facilities = fields.Many2many("accommodation.facility", string="Assigned Items")
    
    
    @api.model
    def _get_customer_domain(self):
        checked_in_customers = self.env['customer.checkin'].search([
            ('status', '=', 'checked_in')
        ]).mapped('customer_id.id')
        return [('id', 'in', checked_in_customers)]
    
    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        self.check_in_id = False
        self.employee_name = False
        self.camp_id = False
        self.floor_id = False
        self.room_id = False
        self.bed_id = False
        self.facilities = False
        self.customer_checklist_id = False
        
    @api.onchange('check_in_id')
    def _onchange_check_in_id(self):
        if self.check_in_id:
            self.employee_name = self.check_in_id.employee_name
            self.camp_id = self.check_in_id.camp_id
            self.floor_id = self.check_in_id.floor_id
            self.room_id = self.check_in_id.room_id
            self.bed_id = self.check_in_id.bed_id
            self.facilities = self.check_in_id.facilities
            checklist = self.env['customer.checklist'].search([
                ('check_in_id', '=', self.check_in_id.id)
            ], limit=1)

            self.customer_checklist_id = checklist.id if checklist else False


    @api.model
    def create(self, vals):
        record = super(CustomerCheckOut, self).create(vals)

        for rec in record:
            checklist_record = self.env['customer.checklist'].search([
                ('customer_id', '=', rec.customer_id.id)
            ], order='create_date desc', limit=1)
            
            if checklist_record:
                faulty_items = checklist_record.facility_items.filtered(lambda item: item.status in ['damaged', 'missing', 'pending'])
                if faulty_items:
                    facility_names = ", ".join(faulty_items.mapped('facility_id.name'))
                    raise ValidationError(f"You cannot check out because the following facilities are not in OK status: {facility_names}.")

                for item in checklist_record.facility_items:
                    if item.facility_id:
                        if item.status == 'damaged':
                            item.facility_id.status = 'damaged'
                            item.facility_id.state = 'in_use'  
                        elif item.status == 'missing':
                            item.facility_id.status = 'missing'
                            item.facility_id.state = 'retired'  
                        elif item.facility_id.usage == 'customer':  
                            item.facility_id.state = 'available'

        if record.check_in_id:
            record.check_in_id.write({'status': 'checked_out'})

            if record.bed_id:
                record.bed_id.write({'status': 'available', 'occupied_customer': False, 'check_in_time': False})

            if record.facilities:
                record.facilities.filtered(lambda f: f.usage == 'customer').write({'state': 'available'})

        return record