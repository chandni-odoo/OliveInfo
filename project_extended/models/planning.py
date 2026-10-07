from odoo import models, fields, api, _
from datetime import datetime, timedelta
import calendar
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

DEFAULT_FACTURX_DATE_FORMAT = '%m%d%Y'
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError


class Planning(models.Model):
    _inherit = 'planning.slot'

    resource_change_type = fields.Selection([('add', 'Add'), ('replace', 'Replace')], default='add', required=True)
    resource_ids = fields.Many2many('hr.employee', string="Resource")

    shift_id = fields.Many2one("hr.shift")

    task_resource_id = fields.Many2one(
        'project.task', string="Task")
    existing_resource_id = fields.Many2one('hr.employee', string="Existing Resource")

    week_ids = fields.One2many('allocation.wizard.lines', 'planning_id', string="Weeks")


    task_resource_history_id = fields.Many2one('task.resource.history', string='Resource History')
    shift_allocation_id = fields.Many2one('shift.allocation', string='Shift Allocation')

    emp_code = fields.Char('Code', readonly=True)
    warning_message = fields.Html('Warning', readonly=True, store=False)

    def btn_demobilize(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Demobilize',
            'view_type': 'form',
            'res_model': 'task.demobilize',
            'view_id': self.env.ref('project_extended.task_demobilize_wizard_form_view').id,
            'view_mode': 'form',
            'target': 'new'
        }

    @api.onchange('end_datetime')
    def _onchange_end_datetime(self):
        if self._origin:
            self.task_resource_history_id.write({
                'date_end': self.end_datetime.date()
            })

    @api.onchange('start_datetime')
    def _onchange_start_datetime(self):
        if self._origin:
            self.task_resource_history_id.write({
                'date_start': self.start_datetime.date()
            })

    def extend_planning(self):
        for planning in self:
            planning.copy()

    # @api.onchange('task_resource_id')
    # def _onchange_task_id(self):
    #     trade_task_emp_ids = []
    #     if self.task_resource_id.trade_task_count > 0 and self.task_resource_id.trade_test:
    #         for trade_test_id in self.env['trade.test.record'].search(
    #                 [('task_id', '=', self.task_resource_id.id), ('status', '=', 'pass')]):
    #             trade_task_emp_ids.append(trade_test_id.employee_id.id)
    #         domain = [('store_task_id', '=', False), ('id', 'in', trade_task_emp_ids), ('emp_status', '=', 'active')]
    #     elif self.task_resource_id.trade_task_count == 0 and self.task_resource_id.trade_test:
    #         domain = [('id', 'in', [])]
    #     else:
    #         domain = [('store_task_id', '=', False), ('billable', '=', True), ('emp_status', '=', 'active'),
    #                   ('product_ids', 'in', self.task_resource_id.sale_line_id.product_id.id)]
    #     print('domain+++++++++++++++++++++++++++', domain)

    #     task = self.task_resource_id
    #     if task:
    #         stop_warning = self.env['stop.warning'].search([])
    #         if task.remaining_amount <= 0:
    #             if stop_warning and stop_warning.stop_check:
    #                 raise UserError('LPO has been restricted .... STOP')
    #             if stop_warning and stop_warning.warning_check:
    #                 self.warning_message = """<bWarning: Insufficient balance in LPO<b/>"""

    #     # need to uncomment
    #     if self.resource_change_type == 'replace':
    #         return {'domain': {'resource_ids': domain, 'existing_resource_id': [('id', 'in', self.task_resource_id.resource_ids.ids)]}}
    #     else:
    #         return {'domain': {'resource_ids': domain}}


    @api.onchange('task_resource_id')
    def _onchange_task_id(self):
        trade_task_emp_ids = []
        if self.task_resource_id.trade_task_count > 0 and self.task_resource_id.trade_test:
            for trade_test_id in self.env['trade.test.record'].search(
                    [('task_id', '=', self.task_resource_id.id), ('status', '=', 'pass')]):
                trade_task_emp_ids.append(trade_test_id.employee_id.id)
            domain = [('store_task_id', '=', False), ('id', 'in', trade_task_emp_ids), ('emp_status', '=', 'active')]
        elif self.task_resource_id.trade_task_count == 0 and self.task_resource_id.trade_test:
            domain = [('id', 'in', [])]
        else:
            domain = [('billable', '=', True), ('emp_status', '=', 'active'),
                    ('product_ids', 'in', self.task_resource_id.sale_line_id.product_id.id)]
        
        today = fields.Date.today()
        excluded_employee_ids = []
        
        active_allocations = self.env['task.resource.history'].search([
            ('date_end', '>=', today),
            ('employee_id', '!=', False),
            '|',
            ('demobilize_date', '=', False),
            ('demobilize_date', '>=', today)
        ])
        
        excluded_employee_ids = list(set(active_allocations.mapped('employee_id.id')))
        
        if self.task_resource_id:
            current_task_employee_ids = self.task_resource_id.resource_ids.ids
            excluded_employee_ids = list(set(excluded_employee_ids + current_task_employee_ids))
        
        if excluded_employee_ids:
            domain.append(('id', 'not in', excluded_employee_ids))

        if self.resource_change_type == 'replace':
            return {'domain': {
                'resource_ids': domain, 
                'existing_resource_id': [('id', 'in', self.task_resource_id.resource_ids.ids)]
            }}
        else:
            return {'domain': {'resource_ids': domain}}
        

    # @api.onchange('task_resource_id')
    # def _onchange_task_id(self):
    #     trade_task_emp_ids = []
    #     if self.task_resource_id.trade_task_count > 0 and self.task_resource_id.trade_test:
    #         for trade_test_id in self.env['trade.test.record'].search(
    #                 [('task_id', '=', self.task_resource_id.id), ('status', '=', 'pass')]):
    #             trade_task_emp_ids.append(trade_test_id.employee_id.id)
    #         domain = [('store_task_id', '=', False), ('id', 'in', trade_task_emp_ids), ('emp_status', '=', 'active')]
    #     elif self.task_resource_id.trade_task_count == 0 and self.task_resource_id.trade_test:
    #         domain = [('id', 'in', [])]
    #     else:
    #         domain = [('store_task_id', '=', False), ('billable', '=', True), ('emp_status', '=', 'active'),
    #                 ('product_ids', 'in', self.task_resource_id.sale_line_id.product_id.id)]
        
    #     # Add condition to exclude employees with active allocations that aren't demobilized
    #     if self.task_resource_id:
    #         today = fields.Date.today()
    #         # Find employees with active allocations (date_end >= today) AND (no demobilize date OR demobilize_date >= today)
    #         excluded_employee_ids = self.env['task.resource.history'].search([
    #             ('task_id', '=', self.task_resource_id.id),
    #             ('date_end', '>=', today),
    #             ('employee_id', '!=', False),
    #             '|',
    #             ('demobilize_date', '=', False),
    #             ('demobilize_date', '>=', today)
    #         ]).mapped('employee_id.id')
            
    #         if excluded_employee_ids:
    #             domain.append(('id', 'not in', excluded_employee_ids))

    #     # task = self.task_resource_id
    #     # if task:
    #     #     stop_warning = self.env['stop.warning'].search([])
    #     #     if task.remaining_amount <= 0:
    #     #         if stop_warning and stop_warning.stop_check:
    #     #             raise UserError('LPO has been restricted .... STOP')
    #     #         if stop_warning and stop_warning.warning_check:
    #     #             self.warning_message = """<bWarning: Insufficient balance in LPO<b/>"""

    #     if self.resource_change_type == 'replace':
    #         return {'domain': {'resource_ids': domain, 'existing_resource_id': [('id', 'in', self.task_resource_id.resource_ids.ids)]}}
    #     else:
    #         return {'domain': {'resource_ids': domain}}



    @api.onchange('resource_change_type')
    def _onchange_resource_change_type(self):
        if self.resource_id:
            self.existing_resource_id = self.resource_id.id
        else:
            self.existing_resource_id = False

    def custom_create_planning(self, create_list):
        print('\n\ncreate_list++++++++++++++new method+++', create_list)
        for planning in create_list:
            aa = dict(planning)
            aa.update({
                'is_check': '1',
            })
            self.env['planning.slot'].create(aa)

    def find_week_days(self, week, line):
        week_id = self.env['week.week'].browse(line[2].get('week_id'))
        code = week_id.code
        if code == '0':
            days = week[calendar.MONDAY]
        if code == '1':
            days = week[calendar.TUESDAY]
        if code == '2':
            days = week[calendar.WEDNESDAY]
        if code == '3':
            days = week[calendar.THURSDAY]
        if code == '4':
            days = week[calendar.FRIDAY]
        if code == '5':
            days = week[calendar.SATURDAY]
        if code == '6':
            days = week[calendar.SUNDAY]

        return days

    def _prepaire_days_of_week_lines(self, rec, employee_id):
        days_of_week_lines = []
        d = {}

        if ' ' in rec.get('start_datetime'):
            date_from = datetime.strptime(rec.get('start_datetime'), '%Y-%m-%d %H:%M:%S').date()
            date_end = datetime.strptime(rec.get('end_datetime'), '%Y-%m-%d %H:%M:%S').date()
        else:
            date_from = datetime.strptime(rec.get('start_datetime'), '%Y-%m-%d')
            date_end = datetime.strptime(rec.get('end_datetime'), '%Y-%m-%d')

        date_from = date_from + timedelta(days=1)
        if date_from and date_end:
            date_array = (date_from + timedelta(days=x) for x in range(0, (date_end - date_from).days))
            for date_object in date_array:
                month_year = "{}-{}".format(date_object.year, date_object.month)
                if month_year not in d:
                    d.update({month_year: calendar.monthcalendar(date_object.year, date_object.month)})

            for line in rec.get('week_ids'):
                for i, cal in d.items():
                    week_selection_ids = self.env['week.selection'].browse(line[2].get('week_selection_ids')[0][2])
                    for wk in week_selection_ids:  # correct
                        if len(cal) > int(wk.code) - 1:
                            week = cal[int(wk.code) - 1]
                            days = self.find_week_days(week, line)
                            if days:
                                full_date = "{}-{}".format(i, days)
                                date_obj = datetime.strptime(full_date, DEFAULT_SERVER_DATE_FORMAT)
                                if date_obj.date() >= date_from and date_obj.date() <= date_end:
                                    week_id = self.env['week.week'].browse(line[2].get('week_id'))
                                    days_of_week_lines.append((0, 0, {
                                        'date': date_obj,
                                        'week_id': week_id.id,
                                        'employee_id': employee_id.id,
                                        'types': line[2].get('types')
                                    }))

                                # if date_obj.date() >= date_from and date_obj.date() <= date_end:
                                # days_of_week_lines.append((0, 0, {
                                #     'date': date_obj,
                                #     'week_id': line[2].get('week_id'),
                                #     'employee_id': employee_id.id,
                                #     'types': line[2].get('types'),
                                # }))
        print('days_of_week_lines++++++++', days_of_week_lines)
        return days_of_week_lines

    

    # Point no 2 PS2
    @api.model_create_multi
    def create(self, vals_list):
        print('vals_list++++++++++++++++', vals_list)
        if isinstance(vals_list, list) and len(vals_list) >= 1:
            if vals_list[0].get('resource_ids'):
                if not vals_list[0].get('is_check'):
                    resource_ids = vals_list[0].get('resource_ids')[0][2]
                    employees = self.env['hr.employee'].browse(resource_ids)
                    print('\nemployees++++++++++++++', employees)

                    create_list = []

                    for emp in employees:
                        aa = dict(vals_list[0])
                        aa.update({
                            'resource_ids': [(6, 0, [emp.id])]
                        })

                        shift = self.env['hr.shift'].browse(aa.get('shift_id'))

                        start_hr = str(shift.hours_from).split('.')[0]
                        start_minutes = str(shift.hours_from).split('.')[1][:2]
                        if ' ' in aa.get('start_datetime'):
                            start = datetime.strptime(aa.get('start_datetime'), '%Y-%m-%d %H:%M:%S')
                        else:
                            start = datetime.strptime(aa.get('start_datetime'), '%Y-%m-%d')
                        # start = datetime.strptime(aa.get('start_datetime'), '%Y-%m-%d %H:%M:%S')

                        if int(start_minutes) == 5:
                            start_minutes = str(start_minutes) + '0'
                        minutes = (int(start_minutes) / 100) * 60 / 100
                        round_minutes = round(minutes, 2)
                        final_minutes = str(round_minutes).split('.')[1]
                        if len(final_minutes) == 1:
                            final_minutes = str(final_minutes) + '0'

                        start_hr = start.replace(hour=int(start_hr))
                        final_start = start_hr + timedelta(minutes=int(final_minutes))

                        end_hr = str(shift.hours_to).split('.')[0]
                        end_minutes = str(shift.hours_to).split('.')[1]
                        if ' ' in aa.get('end_datetime'):
                            end = datetime.strptime(aa.get('end_datetime'), '%Y-%m-%d %H:%M:%S')
                        else:
                            end = datetime.strptime(aa.get('end_datetime'), '%Y-%m-%d')
                        # end = datetime.strptime(aa.get('end_datetime'), '%Y-%m-%d %H:%M:%S')

                        if int(end_minutes) == 5:
                            end_minutes = str(end_minutes) + '0'
                        minutes = (int(end_minutes) / 100) * 60 / 100
                        round_minutes = round(minutes, 2)
                        final_minutes = str(round_minutes).split('.')[1]
                        if len(final_minutes) == 1:
                            final_minutes = str(final_minutes) + '0'

                        end_hr = end.replace(hour=int(end_hr))
                        final_end = end_hr + timedelta(minutes=int(final_minutes))

                        aa.update({
                            'start_datetime': str(final_start - timedelta(hours=3)),
                            'end_datetime': str(final_end - timedelta(hours=3)),
                        })

                        create_list.append(aa)

                    print('create_list+++++++++++++', create_list)
                    for rec in create_list:
                        if rec.get('task_resource_id') and len(rec.get('resource_ids')) > 0:

                            hr_shift = self.env['hr.shift'].browse(rec.get('shift_id'))
                            project_task = self.env['project.task'].browse(rec.get('task_resource_id'))
                            hr_employee = self.env['hr.employee'].browse(rec.get('resource_ids')[0][2][0])

                            # for employee_id in res.resource_ids:
                            task_resource_history = self.env['task.resource.history'].create({
                                'resource_change_type': rec.get('resource_change_type'),
                                'date_start': rec.get('start_datetime'),
                                'date_end': rec.get('end_datetime'),
                                'task_id': rec.get('task_resource_id'),
                                'employee_id': hr_employee.id,
                                'existing_resource_id': rec.get('existing_resource_id'),
                                # 'planning_id': rec.get('id'),
                            })
                            self.env['employee.task.history'].create({
                                'task_id': rec.get('task_resource_id'),
                                'employee_id': hr_employee.id,
                                'date_start': rec.get('start_datetime'),
                                'date_end': rec.get('end_datetime'),
                            })

                            shift_allocation = False
                            if rec.get('shift_id'):

                                vals = {
                                    'date_from': rec.get('start_datetime'),
                                    'date_to': rec.get('end_datetime'),
                                    'shift_id': rec.get('shift_id'),
                                    'shift_type_id': hr_shift.shift_type_id.id,
                                    'description': rec.get('name'),
                                    'state': 'in_progress',
                                    'employee_id': hr_employee.id,
                                    'task_id': project_task.id,
                                }
                                lines = self._prepaire_days_of_week_lines(rec, hr_employee)
                                if lines:
                                    vals.update({'dayofweek_ids': lines})
                                shift_allocation = self.env['shift.allocation'].create(vals)

                            planning_vals = {

                                'resource_id': hr_employee.resource_id.id,
                                'project_id': project_task.project_id.id,
                                'task_id': project_task.id,
                                'sale_line_id': project_task.sale_line_id.id,
                                # new added
                                'task_resource_history_id': task_resource_history.id if task_resource_history else False,
                                'shift_allocation_id': shift_allocation.id if shift_allocation else False,
                            }

                            rec.update(planning_vals)
                    self.custom_create_planning(create_list[1:])
                    res = super().create(create_list[0])
                    s_five_hours = res.start_datetime + timedelta(hours=5)
                    s_five_thirty_hours = s_five_hours + timedelta(minutes=30)
                    e_five_hours = res.end_datetime + timedelta(hours=5)
                    e_five_thirty_hours = e_five_hours + timedelta(minutes=30)
                    res.write({'start_datetime': s_five_thirty_hours, 'end_datetime': e_five_thirty_hours})
                    res.task_resource_history_id.write({
                        'planning_id': res.id
                    })
                    res.shift_allocation_id.write({
                        'planning_id': res.id
                    })
                    res.write({'emp_code': res.resource_id.employee_id.emp_no})

                    return res

            if vals_list[0].get('is_check'):
                vals_list[0].pop('is_check')
        print('\n\n\n\n++++++++++++REST ALL vals_list+++++++++++++++++++', vals_list)
        res = super().create(vals_list)
        s_five_hours = res.start_datetime + timedelta(hours=5)
        s_five_thirty_hours = s_five_hours + timedelta(minutes=30)
        e_five_hours = res.end_datetime + timedelta(hours=5)
        e_five_thirty_hours = e_five_hours + timedelta(minutes=30)
        res.write({'start_datetime': s_five_thirty_hours, 'end_datetime': e_five_thirty_hours})
        res.task_resource_history_id.write({
            'planning_id': res.id
        })
        res.shift_allocation_id.write({
            'planning_id': res.id
        })
        res.write({'emp_code': res.resource_id.employee_id.emp_no})
        return res



class AllocationWizard(models.TransientModel):
    _inherit = "allocation.wizard.lines"

    week_selection_ids = fields.Many2many(
        'week.selection',
        string='Week Selections',
        default=lambda self: self._default_week_selections()
    )

    def _default_week_selections(self):
        return self.env['week.selection'].search([]).ids