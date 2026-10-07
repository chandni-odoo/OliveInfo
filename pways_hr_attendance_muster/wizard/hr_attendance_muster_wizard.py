from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HrAttendanceMuster(models.TransientModel):
    _name = "hr.attendance.muster"
    _description = "HR Attandance Muster"

    date_from = fields.Date(string='Date From', required=True, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True, default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    branch_ids = fields.Many2many('res.branch', string="Branch")
    batch_ids = fields.Many2many('payroll.batch', string="Batch")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(muster.date_from > muster.date_to for muster in self):
            raise ValidationError(_("Attendance Muster 'Date From' must be earlier 'Date To'."))


    def create_employee_muster(self):
        data = {
            'date_from': self.date_from,
            'date_to' : self.date_to,
            'branch_ids': self.branch_ids.ids,
            'batch_ids': self.batch_ids.ids,
        }
        print('data+++++++++++++++', data)
        return self.env.ref('pways_hr_attendance_muster.attendance_muster_report_xlsx').report_action(self, data=data)
