# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo import api, fields, models, exceptions, _

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    active = fields.Boolean('Active', default=True)

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        res = super(HrAttendance, self)._check_validity()
        for attendance in self:
            hr_contract_ids = attendance.employee_id.contract_ids.filtered(lambda x: x.state == 'open')
            if not hr_contract_ids and attendance.employee_id.hr_employee_type == 'own':
                raise ValidationError(_("Employee does not have any running contract"))
            for hr_contract in hr_contract_ids:
                if not hr_contract.date_start:
                    raise ValidationError(_("Start date not found in contract"))
                check_in = attendance.check_in.date()
                if hr_contract.date_start > check_in:
                    pass
                    # raise ValidationError(_("Contract start date is smaller then attendance check in date"))
        return res

    @api.model
    def archive_old_attendance(self):
        today = datetime.today().date()
        three_months_ago = today - relativedelta(months=3)
        last_day_of_three_months_ago = (three_months_ago.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)
        old_attendances = self.env['hr.attendance'].search([
            ('check_in', '<=', last_day_of_three_months_ago)
        ])
        old_attendances.write({'active': False})
        return True

    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ Verifies if check_in is earlier than check_out and if task_shift_id and task_shift_allocation_ids are set. """
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                if attendance.employee_id.task_shift_ids or attendance.employee_id.tasks_shift_allocation_ids:
                    if attendance.check_out < attendance.check_in:
                        raise exceptions.ValidationError(_('"Check Out" time cannot be earlier than "Check In" time.'))