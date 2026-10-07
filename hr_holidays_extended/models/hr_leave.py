from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare
from datetime import timedelta, datetime, time

class Leave(models.Model):
    _inherit = "hr.leave"

    employee_id = fields.Many2one('hr.employee', string='Employee')

    # @api.constrains('state', 'number_of_days', 'holiday_status_id', 'holiday_allocation_id.total_accrual_days')
    # def _check_holidays(self):
    #     for holiday in self:
    #         if holiday.holiday_type != 'employee' or not holiday.employee_id or not holiday.holiday_status_id or holiday.holiday_status_id.requires_allocation == 'no':
    #             continue
    #         if float_compare(holiday.holiday_allocation_id.total_accrual_days, 0, precision_digits=2) == -1:# or float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
    #                 raise ValidationError(_('The number of remaining time off is not sufficient for this time off type.\n'
    #                                         'Please also check the time off waiting for validation.') + '\n- %s' % holiday.display_name)
    #         mapped_days = holiday.holiday_status_id.get_employees_days([holiday.employee_id.id], holiday.date_from)
    #         leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]
    #         if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
    #                 raise ValidationError(_('The number of remaining time off is not sufficient for this time off type.\n'
    #                                         'Please also check the time off waiting for validation.') + '\n- %s' % holiday.display_name)
