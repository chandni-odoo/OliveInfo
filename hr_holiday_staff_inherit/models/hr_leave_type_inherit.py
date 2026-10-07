from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare
from datetime import date, datetime
import math
from odoo.tools.float_utils import float_round

class HrHolidaysType(models.Model):
    _inherit = "hr.leave.type"


    def _get_days_request(self):
        self.ensure_one()
        exist_allowing_leave = 0
        pre_total_allowed_staff_leave = 0
        # For single staff allow extra leave
        # if self.employee_requests == 'yes':
        if 'employee_id' in self.env.context:
            employee_id = self.env.context.get('employee_id')[0]

            allocation_with_accural = self.env['hr.leave.allocation'].search(
                [('holiday_status_id', '=', self.id),
                 ('employee_id', '=', employee_id), ('allocation_type', '=', 'accrual')])

            if allocation_with_accural:

                start_date = allocation_with_accural.date_from
                today_date = date.today()
                timedelta = today_date - start_date
                completed_days = timedelta.days
                fraction_year = completed_days / 365
                whole = math.floor(fraction_year)
                curent_service_year = fraction_year - whole
                year_whole = math.ceil(fraction_year)

                accrual_line = []
                for accrual_ratio in allocation_with_accural.accrual_plan_id.level_ids:
                    if accrual_ratio.start_count <= completed_days:
                        accrual_line.append(accrual_ratio)
                print('complteeddd ratio', accrual_line)


                if accrual_line and len(accrual_line) == 1:
                    exist_allowing_leave = (1 - curent_service_year) * 365 * accrual_line[0].added_value

                elif accrual_line and len(accrual_line) != 1:
                    length = len(accrual_line)
                    exist_allowing_leave = (1 - curent_service_year) * 365 * accrual_line[length - 1].added_value

                total_allowed_staff_leave = exist_allowing_leave + self.virtual_remaining_leaves
                pre_total_allowed_staff_leave = format(total_allowed_staff_leave, '.2f')

        

        return (self.name, {
            'remaining_leaves': ('%.2f' % self.remaining_leaves).rstrip('0').rstrip('.'),
            'virtual_remaining_leaves': ('%.2f' % self.virtual_remaining_leaves).rstrip('0').rstrip('.'),
            'max_leaves': ('%.2f' % self.max_leaves).rstrip('0').rstrip('.'),
            'leaves_taken': ('%.2f' % self.leaves_taken).rstrip('0').rstrip('.'),
            'virtual_leaves_taken': ('%.2f' % self.virtual_leaves_taken).rstrip('0').rstrip('.'),
            'exist_allowing_leave': ('%.2f' % exist_allowing_leave).rstrip('0').rstrip('.'),
            'pre_total_allowed_staff_leave': pre_total_allowed_staff_leave,
            'request_unit': self.request_unit,
            'employee_requests': self.employee_requests,
            'icon': self.sudo().icon_id.url,
        }, self.requires_allocation, self.id)


