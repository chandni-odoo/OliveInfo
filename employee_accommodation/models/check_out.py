from odoo import models,_, fields, api
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from datetime import date

class AccommodationCheckOut(models.Model):
    _name = 'accommodation.check.out'
    _description = 'Employee Check-Out'
    _rec_name = 'check_out_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    check_out_id = fields.Char("Check-out ID", required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('accommodation.check.out'))
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    checkin_id = fields.Many2one('accommodation.check.in', string="Check-in Record", required=True)
    camp_id = fields.Many2one('accommodation.camp', string="Camp", related="checkin_id.camp_id", readonly=True, domain=[('status', '=', 'active')])
    floor_id = fields.Many2one('accommodation.floor', string="Floor", related="checkin_id.floor_id", readonly=True)
    room_id = fields.Many2one('accommodation.room', string="Room", related="checkin_id.room_id", readonly=True)
    bed_id = fields.Many2one('accommodation.bed', string="Bed", related="checkin_id.bed_id", readonly=True)
    check_out_date = fields.Datetime(string="Check-Out Date", default=fields.Datetime.now, required=True)
    returned_items = fields.Text(string="Returned Items")
    remarks = fields.Text(string="Remarks")
    status = fields.Selection([
        ('pending', 'Pending'),
        ('checked_out', 'Checked Out')
    ], string="Status", default="pending")
    # checklist_id = fields.Many2one('accommodation.check.list', string="Clearence form", readonly=True)
    checklist_id = fields.Many2one('accommodation.check.list', string="Clearence form", readonly=False, store=True)
    checkout_reason = fields.Text(string="Reason")
    
    @api.model
    def _get_checked_in_employees(self):
        return self.env['accommodation.check.in'].search([('status', '=', 'checked_in')]).mapped('employee_id.id')
    
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            checkin_record = self.env['accommodation.check.in'].search([
                ('employee_id', '=', self.employee_id.id),
                ('status', '=', 'checked_in')
            ], limit=1)

            self.checkin_id = checkin_record.id if checkin_record else False
            checklist_record = self.env['accommodation.check.list'].search([
                ('employee_id', '=', self.employee_id.id)
            ], order='create_date desc', limit=1)

            self.checklist_id = checklist_record.id if checklist_record else False
            
    @api.onchange('checkin_id')
    def _onchange_checkin_id(self):
        if self.checkin_id:
            self.employee_id = self.checkin_id.employee_id

    @api.onchange('employee_id')
    def _update_employee_domain(self):
        checked_in_employee_ids = self._get_checked_in_employees()
        return {'domain': {'employee_id': [('id', 'in', checked_in_employee_ids)]}}
            
                
    def action_confirm_checkout(self):
        for record in self:
            if record.status == 'checked_out':
                raise UserError(_("This employee has already been checked out."))
            
            checklist_record = self.env['accommodation.check.list'].search([
                ('employee_id', '=', record.employee_id.id)
            ], order='create_date desc', limit=1)

            if not checklist_record:
                raise ValidationError(_("Cannot proceed with checkout. No clearance form (checklist) found for employee %s. Please create a checklist first.") % record.employee_id.name)
            
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
                    elif item.facility_id.usage == 'employee':  
                        item.facility_id.state = 'available'

            if record.bed_id:
                record.bed_id.write({
                    'status': 'available',
                    'occupied_employee_id': False,
                    'check_in_time': False,
                })

            if record.checkin_id:
                record.checkin_id.write({'status': 'checked_out'})
            
            record.write({
                'status': 'checked_out',
                'checklist_id': checklist_record.id  
            })

            # record.status = 'checked_out'
            
            message = _(
                "Employee %s checked out from %s / Room No. %s / Bed No. %s."
            ) % (record.employee_id.name, record.camp_id.name, record.room_id.name, record.bed_id.name)
            record.employee_id.message_post(body=message, subtype_xmlid="mail.mt_note")
            
            if record.checkin_id.is_vendor_employee:
                    model_id = self.env['ir.model'].sudo().search([('model', '=', 'accommodation.check.out')], limit=1)
                    if model_id:
                        activity_type = self.env['mail.activity.type'].sudo().search([('name', '=', 'Vendor Check-Out Notification')], limit=1)
                        if not activity_type:
                            activity_type = self.env['mail.activity.type'].sudo().create({
                                'name': 'Vendor Check-Out Notification',
                                'category': 'default'
                            })

                        user_group = self.env.ref('employee_accommodation.notification_alert').users
                        for admin in user_group:
                            activity_vals = {
                                'res_model_id': model_id.id,
                                'res_model': 'accommodation.check.out',
                                'res_id': record.id,
                                'res_name': f'Vendor Check-Out: {record.employee_id.name}',
                                'user_id': admin.id,
                                'activity_type_id': activity_type.id,
                                'date_deadline': fields.Datetime.today(),
                            }
                            self.env['mail.activity'].sudo().create(activity_vals)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Checkout completed successfully!'),
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
