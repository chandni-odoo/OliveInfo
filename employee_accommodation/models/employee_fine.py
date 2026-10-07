from odoo import models, fields, api, _
from datetime import datetime

class EmployeeDisciplinaryAction(models.Model):
    _name = 'employee.accommodation.disciplinary'
    _description = 'Employee Disciplinary Actions'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    employee_id = fields.Many2one(
        'hr.employee', 
        string="Employee", 
        required=True,
        domain=lambda self: [('id', 'in', self._get_checked_in_employees())]
    )
    action_type_id = fields.Many2one('disciplinary.action', string="Action Type", required=True)
    reason_id = fields.Many2one('action.reason', string="Reason", required=True)
    date = fields.Date(string="Date", required=True)
    fine_amount = fields.Float(string="Fine Amount")
    remarks = fields.Text(string="Remarks")
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string="Severity", required=True)

    @api.model
    def _get_checked_in_employees(self):
        return self.env['accommodation.check.in'].search([
            ('status', '=', 'checked_in')
        ]).mapped('employee_id.id')
        
    @api.model
    def create(self, vals):
        record = super(EmployeeDisciplinaryAction, self).create(vals)
        if record.employee_id:
            existing_record = self.env['disciplinary.action.line'].search([
                ('employee_id', '=', record.employee_id.id),
                ('action_type_id', '=', record.action_type_id.id),
                ('date', '=', record.date),
            ], limit=1)
            
            if not existing_record:
                self.env['disciplinary.action.line'].create({
                    'employee_id': record.employee_id.id,
                    'action_type_id': record.action_type_id.id,
                    'action': record.reason_id.id,
                    'date': record.date,
                    'action_amount': record.fine_amount,
                    'remarks': record.remarks,
                    'severity': record.severity,
                })
            else:
                existing_record.write({
                    'action_amount': record.fine_amount,
                    'remarks': record.remarks,
                    'severity': record.severity,
                })
                
        if record.fine_amount and record.fine_amount > 0:
            message = _("A fine of %s has been imposed on %s.") % (record.fine_amount, record.employee_id.name)
            record.message_post(body=message)

            model_id = record.env['ir.model'].sudo().search([('model', '=', 'employee.accommodation.disciplinary')], limit=1)
            if model_id:
                activity_type = record.env['mail.activity.type'].sudo().search([('name', '=', 'Fine Notification')], limit=1)
                if not activity_type:
                    activity_type = record.env['mail.activity.type'].sudo().create({
                        'name': 'Fine Notification',
                        'category': 'default'
                    })

                hr_users = record.env.ref('employee_accommodation.disciplinary_notification_alert').users  
                for hr_user in hr_users:
                    activity_vals = {
                        'res_model_id': model_id.id,
                        'res_model': 'employee.accommodation.disciplinary',
                        'res_id': record.id,
                        'res_name': f'Fine Imposed on {record.employee_id.name}',
                        'user_id': hr_user.id,
                        'activity_type_id': activity_type.id,
                        'date_deadline': fields.Datetime.today(),
                    }
                    record.env['mail.activity'].sudo().create(activity_vals)

        return record
        

    
