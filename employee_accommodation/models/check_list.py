from odoo import models, fields, api

class AccommodationCheckList(models.Model):
    _name = 'accommodation.check.list'
    _description = 'Check-List for Accommodation'
    _rec_name = 'reference'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    reference = fields.Char(string="Reference Number", readonly=True, 
                            default=lambda self: self.env['ir.sequence'].next_by_code('accommodation.check.list'))
    create_date = fields.Datetime(string="Created Date", default=fields.Datetime.now, readonly=True)
    created_by = fields.Many2one('res.users', string="Created By", 
                                 default=lambda self: self.env.user, readonly=True)
    employee_id = fields.Many2one(
        'hr.employee', 
        string="Employee", 
        required=True
    )
    checkin_id = fields.Many2one('accommodation.check.in', string="Check-in Record")
    camp_id = fields.Many2one('accommodation.camp', string="Camp", related="checkin_id.camp_id", domain=[('status', '=', 'active')])
    floor_id = fields.Many2one('accommodation.floor', string="Floor", related="checkin_id.floor_id")
    room_id = fields.Many2one('accommodation.room', string="Room", related="checkin_id.room_id")
    bed_id = fields.Many2one('accommodation.bed', string="Bed", related="checkin_id.bed_id")
    checkin_date = fields.Date(string="Check-in Date")
    facilities = fields.Many2many("accommodation.facility", string="Facility Items")
    facility_items = fields.One2many('facility.checklist.item', 'checklist_id', string="Facility Items Checklist")
    remark = fields.Text(string="Remark")
    condition_checked = fields.Boolean(string="Condition Checked")
    
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        checked_in_employees = self.env['accommodation.check.in'].search([
            ('status', '=', 'checked_in')
        ]).mapped('employee_id.id')
        
        return {'domain': {'employee_id': [('id', 'in', checked_in_employees)]}}
    
    @api.onchange('employee_id')
    def _onchange_set_checkin_details(self):
        if self.employee_id:
            checkin_record = self.env['accommodation.check.in'].search([
                ('employee_id', '=', self.employee_id.id), 
                ('status', '=', 'checked_in')
            ], limit=1)
            
            if checkin_record:
                self.checkin_id = checkin_record.id
                self.camp_id = checkin_record.camp_id.id
                self.floor_id = checkin_record.floor_id.id
                self.room_id = checkin_record.room_id.id
                self.bed_id = checkin_record.bed_id.id
                self.checkin_date = checkin_record.check_in_date
                self.facilities = [(6, 0, checkin_record.facilities.ids)]
                
                self.facility_items = [(5, 0, 0)]
                facility_items = []
                for facility in checkin_record.facilities:
                    facility_items.append((0, 0, {
                        'facility_id': facility.id,
                        'status': 'ok',  
                        'remark': '',    
                    }))
                self.facility_items = facility_items
    
            
class FacilityChecklistItem(models.Model):
    _name = 'facility.checklist.item'
    _description = 'Facility Checklist Item'

    checklist_id = fields.Many2one('accommodation.check.list', string="Checklist", ondelete='cascade')
    customer_checklist_id = fields.Many2one('customer.checklist', string="Customer Checklist", ondelete='cascade')
    facility_id = fields.Many2one('accommodation.facility', string="Facility Item")
    status = fields.Selection([
        ('pending', 'Pending'),
        ('ok', 'OK'),
        ('damaged', 'Damaged'),
        ('missing', 'Missing'),
    ], string="Status", default='ok')
    remark = fields.Text(string="Remark")