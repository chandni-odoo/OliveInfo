from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HrAbsentee(models.Model):
    _name = 'hr.absentee'
    _description = 'Employee Absenteeism'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )
    absent_date = fields.Date(
        string='Absent Date',
        required=True,
        default=fields.Date.context_today
    )
    reason = fields.Text(string='Reason')

    @api.constrains('employee_id', 'absent_date')
    def _check_duplicate_with_leave(self):
        for record in self:
            duplicate_absentee = self.search([
                ('employee_id', '=', record.employee_id.id),
                ('absent_date', '=', record.absent_date),
                ('id', '!=', record.id)
            ])
            if duplicate_absentee:
                raise ValidationError(
                    "An absentee record already exists for this employee on the same date."
                )