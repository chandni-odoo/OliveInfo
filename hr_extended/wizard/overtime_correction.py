from odoo import models,fields,api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError

class OvertimeCorrection(models.TransientModel):
    _name = 'overtime.correction'
    _description = "OverTime Correction"

    employee_ids = fields.Many2many('hr.employee', string="Employees")

    @api.model
    def default_get(self, fields):
        vals = super(OvertimeCorrection, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            attendance_ids = self.env['hr.attendance'].browse(active_ids)
            vals['employee_ids'] = attendance_ids.mapped('employee_id')
        return vals

    def action_employee_overtime_corrections(self):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            overtime_id = self.env['bt.hr.overtime']
            attendance_ids = self.env['hr.attendance'].browse(active_ids)
            if attendance_ids:
                overtime_ids = self.env['bt.hr.overtime'].search([('attendance_id', 'in', attendance_ids.ids), ('state', '=', 'draft')])
                if overtime_ids:
                    overtime_ids.sudo().unlink()
                attendance_ids.sudo().write({'overtime_created': False})
