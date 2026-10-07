from odoo import models, fields, api

class CustomerChecklist(models.Model):
    _name = 'customer.checklist'
    _description = 'Customer Checklist'
    _rec_name = 'reference'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    reference = fields.Char(string="Reference Number", readonly=True, 
                            default=lambda self: self.env['ir.sequence'].next_by_code('customer.checklist'))
    create_date = fields.Datetime(string="Created Date", default=fields.Datetime.now, readonly=True)
    created_by = fields.Many2one('res.users', string="Created By", 
                                 default=lambda self: self.env.user, readonly=True)

    customer_id = fields.Many2one('res.partner', string="Customer", required=True,
                                  domain=lambda self: self._get_customer_domain())
    check_in_id = fields.Many2one('customer.checkin', string="Check-In Reference", required=True,
                                  domain="[('customer_id', '=', customer_id), ('status', '=', 'checked_in')]")

    employee_name = fields.Char(string="Employee Name")
    camp_id = fields.Many2one('accommodation.camp', string="Camp", domain=[('status', '=', 'active')])
    floor_id = fields.Many2one('accommodation.floor', string="Floor")
    room_id = fields.Many2one('accommodation.room', string="Room")
    bed_id = fields.Many2one('accommodation.bed', string="Bed")
    check_out_date = fields.Datetime(string="Check-Out Date", default=fields.Datetime.now)

    facilities = fields.Many2many("accommodation.facility", string="Assigned Items")
    facility_items = fields.One2many('facility.checklist.item', 'customer_checklist_id', string="Facility Items Checklist")

    @api.model
    def _get_customer_domain(self):
        return [('id', 'in', self.env['customer.checkin'].search([('status', '=', 'checked_in')]).mapped('customer_id.id'))]
    
    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        if self.customer_id:
            checkin_record = self.env['customer.checkin'].search([
                ('customer_id', '=', self.customer_id.id), ('status', '=', 'checked_in')
            ], limit=1)

            if checkin_record:
                self.check_in_id = checkin_record.id
                self._update_checkin_details()

    @api.onchange('check_in_id')
    def _onchange_check_in_id(self):
        if self.check_in_id:
            self._update_checkin_details()

    def _update_checkin_details(self):
        if self.check_in_id:
            self.employee_name = self.check_in_id.employee_name
            self.camp_id = self.check_in_id.camp_id.id
            self.floor_id = self.check_in_id.floor_id.id
            self.room_id = self.check_in_id.room_id.id
            self.bed_id = self.check_in_id.bed_id.id
            self.facilities = [(6, 0, self.check_in_id.facilities.ids)]
            self.facility_items = [(5, 0, 0)]
            facility_items = []
            for facility in self.check_in_id.facilities:
                facility_items.append((0, 0, {
                    'facility_id': facility.id,
                    'status': 'ok',  
                    'remark': '',    
                }))
            self.facility_items = facility_items

    