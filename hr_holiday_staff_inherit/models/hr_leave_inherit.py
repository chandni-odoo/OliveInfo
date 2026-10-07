from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare
from datetime import date, datetime
import math

class HrHolidays(models.Model):
    _inherit = "hr.leave"

    staff_leave_available = fields.Float('Available Staff Leave',readonly=1, stored=True)
    staff_leave_bool = fields.Boolean('Available Leave Bool',readonly=1)

    @api.onchange('employee_ids','holiday_status_id')
    def _onchange_avail_staff_leave(self):
        if self.employee_id and self.holiday_status_id:
            if self.holiday_status_id.employee_requests == 'yes':

                allocation_with_accural = self.env['hr.leave.allocation'].search(
                    [('holiday_status_id', '=', self.holiday_status_id.id),
                     ('employee_id', '=', self.employee_id.id), ('allocation_type', '=', 'accrual')])

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
                        exist_allowing_leave = (1 - curent_service_year) * 365 * accrual_line[
                            length - 1].added_value

                    total_allowed_staff_leave = exist_allowing_leave + self.holiday_status_id.virtual_remaining_leaves
                    self.staff_leave_available = format(total_allowed_staff_leave, '.2f')
                    self.staff_leave_bool = True
            else:
                self.staff_leave_bool = False
        else:
            self.staff_leave_bool = False

    @api.constrains('state', 'number_of_days', 'holiday_status_id')
    def _check_holidays(self):

        mapped_days = self.holiday_status_id.get_employees_days((self.employee_id | self.employee_ids).ids)
        for holiday in self:
            if holiday.holiday_type != 'employee' \
                    or not holiday.employee_id and not holiday.employee_ids \
                    or holiday.holiday_status_id.requires_allocation == 'no':
                continue
            if  holiday.holiday_status_id.is_paid == False and holiday.employee_id:
                leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]


                # For single staff allow extra leave
                # elif holiday.holiday_status_id.is_paid:
                #     pass
                if holiday.holiday_status_id.is_paid == False and holiday.holiday_status_id.employee_requests == 'yes':
                    allocation_with_accural = self.env['hr.leave.allocation'].search(
                        [('holiday_status_id', '=', holiday.holiday_status_id.id),
                         ('employee_id', '=', holiday.employee_id.id), ('allocation_type', '=', 'accrual')])

                    if not allocation_with_accural.accrual_plan_id:
                        raise ValidationError(
                            _('Please configure the accrual plan for the %s type for the %s.',
                              holiday.holiday_status_id.name, holiday.employee_id.name))

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


                    if len(accrual_line) == 0:
                        raise ValidationError(
                            _('Please configure the level ratio for the accrual plan for the %s type for the %s.',
                              allocation_with_accural.accrual_plan_id.name))

                    if len(accrual_line) == 1:

                        # allowed_leave = accrual_line[0].added_value * year_whole * 365
                        # exist_allow_leave = curent_service_year * 365 * accrual_line[0].added_value
                        exist_allow_leave = (1 - curent_service_year) * 365 * accrual_line[0].added_value

                    elif len(accrual_line) != 1:
                        length = len(accrual_line)
                        # allowed_leave = accrual_line[length - 1].added_value * year_whole * 365
                        exist_allow_leave = curent_service_year * 365 * accrual_line[length - 1].added_value
                        exist_allow_leave = (1 - curent_service_year) * 365 * accrual_line[length - 1].added_value

                    actual_avail_leaves = float(exist_allow_leave) + leave_days[
                        'virtual_remaining_leaves'] + holiday.number_of_days
                    check_avail_leave = float(exist_allow_leave) + leave_days['virtual_remaining_leaves']
                    precision_check_avail_leave = format(check_avail_leave, '.2f')


                    if float(precision_check_avail_leave) < 0:
                        raise ValidationError(
                            _('The number of remaining time off is not sufficient for this time off type.\n'
                              'Your Available timeoff is %s Days only for the %s Employee.', format(actual_avail_leaves, '.2f') , holiday.employee_id.name))


                elif holiday.holiday_status_id.is_paid == False and float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 \
                        or float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
                    raise ValidationError(
                        _('The number of remaining time off is not sufficient for this time off type.\n'
                          'Please also check the time off waiting for validation.'))
                # elif holiday.holiday_status_id.employee_requests == 'no' and holiday.holiday_status_id.is_paid == False:
                #     raise ValidationError(_('The number of remaining time off is not sufficient for this time off type.\n'
                #                             'Please also check the time off waiting for validation.') + '\n- %s' % holiday.display_name)


            else:
                unallocated_employees = []
                for employee in holiday.employee_ids:
                    leave_days = mapped_days[employee.id][holiday.holiday_status_id.id]

                    # For Multiple Staffs

                    if  holiday.holiday_status_id.is_paid == False and holiday.holiday_status_id.employee_requests == 'yes':
                        allocation_with_accural = self.env['hr.leave.allocation'].search(
                            [('holiday_status_id', '=', holiday.holiday_status_id.id),
                             ('employee_id', '=', employee.id), ('allocation_type', '=', 'accrual')])

                        if not allocation_with_accural.accrual_plan_id:
                            raise ValidationError(
                                _('Please configure the accrual plan for the %s type for the %s.',
                                  holiday.holiday_status_id.name, employee.name))

                        start_date = employee.date_started
                        today_date = date.today()
                        timedelta = today_date - start_date
                        completed_days = timedelta.days
                        fraction_year = completed_days / 365
                        whole = math.floor(fraction_year)
                        curent_service_year = fraction_year - whole
                        year_whole = math.ceil(fraction_year)

                        accrual_line = []
                        for accrual_ratio in allocation_with_accural.accrual_plan_id.level_ids:
                            print('1111111111111111111111111', accrual_ratio)
                            if accrual_ratio.start_count <= completed_days:
                                accrual_line.append(accrual_ratio)
                        print('complteeddd ratio', accrual_line)

                        if len(accrual_line) == 0:
                            raise ValidationError(
                                _('Please configure the level ratio for the accrual plan for the %s type for the %s.',
                                  allocation_with_accural.accrual_plan_id.name))

                        if len(accrual_line) == 1:
                            # allowed_leave = accrual_line[0].added_value * year_whole * 365
                            # exist_allow_leave = curent_service_year * 365 * accrual_line[0].added_value
                            exist_allow_leave = (1 - curent_service_year) * 365 * accrual_line[0].added_value

                        elif len(accrual_line) != 1:
                            length = len(accrual_line)
                            # allowed_leave = accrual_line[length - 1].added_value * year_whole * 365
                            # exist_allow_leave = curent_service_year * 365 * accrual_line[length - 1].added_value
                            exist_allow_leave = (1 - curent_service_year) * 365 * accrual_line[
                                length - 1].added_value

                        actual_avail_leaves = float(exist_allow_leave) + leave_days[
                            'virtual_remaining_leaves'] + holiday.number_of_days
                        check_avail_leave = float(exist_allow_leave) + leave_days['virtual_remaining_leaves']
                        precision_check_avail_leave = format(check_avail_leave, '.2f')
                        print('actual_avail_leavesactual_avail_leaves------', actual_avail_leaves)
                        # efsdgfdg

                        if float(precision_check_avail_leave) < 0:
                            raise ValidationError(
                                _('The number of remaining time off is not sufficient for this time off type.\n'
                                  'Your Available timeoff is %s Days only for the %s Employee.',
                                  format(actual_avail_leaves, '.2f'), employee.name))

                    elif float_compare(leave_days['remaining_leaves'], self.number_of_days, precision_digits=2) == -1 \
                            or float_compare(leave_days['virtual_remaining_leaves'], self.number_of_days,
                                             precision_digits=2) == -1:
                        unallocated_employees.append(employee.name)
                if  holiday.holiday_status_id.is_paid == False and unallocated_employees:
                    raise ValidationError(
                        _('The number of remaining time off is not sufficient for this time off type.\n'
                          'Please also check the time off waiting for validation.')
                        + _('\nThe employees that lack allocation days are:\n%s',
                            (', '.join(unallocated_employees))))

            

    # @api.constrains('state', 'number_of_days', 'holiday_status_id')
    # def _check_holidays(self):
    #     for holiday in self:
    #         print('datetetetet-------', holiday.date_from)
    #         print('datetetetet-------', type(holiday.date_from))
    #         if holiday.holiday_type != 'employee' or not holiday.employee_id or holiday.holiday_status_id.requires_allocation == 'no':
    #             continue
    #         mapped_days = holiday.holiday_status_id.get_employees_days([holiday.employee_id.id], holiday.date_from)
    #
    #         leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]
    #
    #         if holiday.holiday_status_id.employee_requests == 'yes':
    #             for employee in holiday.employee_ids:
    #                 allocation_with_accural = self.env['hr.leave.allocation'].search(
    #                     [('holiday_status_id', '=', holiday.holiday_status_id.id),
    #                      ('employee_id', '=', employee.id), ('allocation_type', '=', 'accrual')])
    #
    #                 if not allocation_with_accural.accrual_plan_id:
    #                     raise ValidationError(
    #                         _('Please configure the accrual plan for the %s type for the %s.',
    #                           holiday.holiday_status_id.name, employee.name))
    #
    #                 start_date = employee.date_started
    #                 today_date = date.today()
    #                 timedelta = today_date - start_date
    #                 completed_days = timedelta.days
    #                 fraction_year = completed_days / 365
    #                 whole = math.floor(fraction_year)
    #                 curent_service_year = fraction_year - whole
    #                 year_whole = math.ceil(fraction_year)
    #
    #                 accrual_line = []
    #                 for accrual_ratio in allocation_with_accural.accrual_plan_id.level_ids:
    #                     print('1111111111111111111111111', accrual_ratio)
    #                     if accrual_ratio.start_count <= completed_days:
    #                         accrual_line.append(accrual_ratio)
    #                 print('complteeddd ratio', accrual_line)
    #
    #                 if len(accrual_line) == 0:
    #                     raise ValidationError(
    #                         _('Please configure the level ratio for the accrual plan for the %s type for the %s.',
    #                           allocation_with_accural.accrual_plan_id.name))
    #
    #                 if len(accrual_line) == 1:
    #                     allowed_leave = accrual_line[0].added_value * year_whole * 365
    #                     exist_allow_leave = curent_service_year * 365 * accrual_line[0].added_value
    #                     used_allow_leave = (1 - curent_service_year) * 365 * accrual_line[0].added_value
    #
    #                 elif len(accrual_line) != 1:
    #                     length = len(accrual_line)
    #                     allowed_leave = accrual_line[length - 1].added_value * year_whole * 365
    #                     exist_allow_leave = curent_service_year * 365 * accrual_line[length - 1].added_value
    #                     used_allow_leave = (1 - curent_service_year) * 365 * accrual_line[length - 1].added_value
    #
    #                 actual_avail_leaves = float(exist_allow_leave) + leave_days[
    #                     'virtual_remaining_leaves'] + holiday.number_of_days
    #                 check_avail_leave = float(exist_allow_leave) + leave_days['virtual_remaining_leaves']
    #                 precision_check_avail_leave = format(actual_avail_leaves, '.2f')
    #                 print('actual_avail_leavesactual_avail_leaves------', actual_avail_leaves)
    #                 # efsdgfdg
    #
    #                 if check_avail_leave < 0:
    #                     raise ValidationError(
    #                         _('The number of remaining time off is not sufficient for this time off type.\n'
    #                           'Your Available timeoff is %s Days only.', precision_check_avail_leave))
    #
    #
    #
    #
    #         elif float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or float_compare(
    #                 leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
    #             raise ValidationError(_('The number of remaining time off is not sufficient for this time off type.\n'
    #                                     'Please also check the time off waiting for validation.'))
