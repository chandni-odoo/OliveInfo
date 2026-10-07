from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    camp_details = fields.Text(string="Camp Information", compute="_compute_camp_details", store=False)
    
    def _compute_camp_details(self):
        for employee in self:
            check_in_record = self.env['accommodation.check.in'].search([
                ('employee_id', '=', employee.id),
                ('status', '=', 'checked_in')
            ], limit=1)
            
            if check_in_record:
                employee.camp_details = f"{check_in_record.camp_id.name} / Room No. {check_in_record.room_id.name} /Bed No. {check_in_record.bed_id.name}"
                continue
            
            check_out_record = self.env['accommodation.check.out'].search([
                ('employee_id', '=', employee.id)
            ], limit=1, order='check_out_date desc')
            
            if check_out_record:
                checkout_date = check_out_record.check_out_date
                checkout_date_str = checkout_date.strftime('%d/%m/%Y') if checkout_date else ''
            
                checkout_reason = check_out_record.checkout_reason or ''
                
                if checkout_date_str:
                    message = f"Checked Out on {checkout_date_str}"
                    if checkout_reason:
                        message += f" - Reason: {checkout_reason}"
                    employee.camp_details = message
                else:
                    employee.camp_details = "Checked Out"
                continue
            
            old_check_in = self.env['accommodation.check.in'].search([
                ('employee_id', '=', employee.id),
                ('status', '=', 'checked_out')
            ], limit=1, order='write_date desc')
            
            if old_check_in:
                checkout_date = old_check_in.write_date.strftime('%d/%m/%Y')
                employee.camp_details = f"Previously at {old_check_in.camp_id.name} / Room No. {old_check_in.room_id.name} - Checked Out on {checkout_date}"
            else:
                employee.camp_details = False
    
    
    def action_open_housing(self):
        self.ensure_one()
        check_in_record = self.env['accommodation.check.in'].search([
            ('employee_id', '=', self.id),
            ('status', '=', 'checked_in')
        ], limit=1)

        if check_in_record:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Check-In Details',
                'res_model': 'accommodation.check.in',
                'res_id': check_in_record.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            check_out_record = self.env['accommodation.check.out'].search([
                ('employee_id', '=', self.id),
            ], limit=1, order='write_date desc')

            if check_out_record:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Check-Out Details',
                    'res_model': 'accommodation.check.out',
                    'res_id': check_out_record.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'New Check-In',
                    'res_model': 'accommodation.check.in',
                    'view_mode': 'form',
                    'target': 'current',
                    'context': {'default_employee_id': self.id},
                }
    
