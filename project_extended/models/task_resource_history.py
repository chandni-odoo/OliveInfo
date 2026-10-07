# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, timedelta


class TaskResourceHistory(models.Model):
    _name = 'task.resource.history'
    _description = "Task Resource History"

    date_start = fields.Datetime(string='Start Date')
    date_end = fields.Datetime(string='End Date')
    demobilize_date = fields.Datetime(string='Demobilize Date')
    task_id = fields.Many2one('project.task')
    employee_id = fields.Many2one('hr.employee')
    resource_change_type = fields.Selection([('add', 'Add'), ('replace', 'Replace')], default='add', required=True,
                                            string="Type")
    planning_id = fields.Many2one('planning.slot', ondelete='cascade')
    existing_resource_id = fields.Many2one('hr.employee')
    total_hours = fields.Float(string="Hours From", compute='_hours_count')
    remarks = fields.Text(string="Reason")
    is_demobilize = fields.Boolean('Demobilize ?', compute='_compute_demobilize')

    def _compute_demobilize(self):
        for record in self:
            record.is_demobilize = False
            if record.demobilize_date and record.demobilize_date.date() < fields.Date.today():
                record.is_demobilize = True

    def _hours_count(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                # get difference
                delta = rec.date_start - rec.date_end
                sec = delta.total_seconds()
                hours = sec / (60 * 60)
                rec.total_hours = hours
            else:
                rec.total_hours = 0.0

    @api.model
    def default_get(self, fields_list):
        res = super(TaskResourceHistory, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        return res

    @api.onchange('date_end')
    def _onchange_date_end(self):
        #comment by shon for error "AttributeError: 'bool' object has no attribute 'time'"
        # if self._origin:
        #     time = self.planning_id.end_datetime.time()
        #     new_date = self.date_end + timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)
        #     self.planning_id.write({
        #         'end_datetime': new_date
        #     })
        if self._origin:
            if self.planning_id.end_datetime:
                time = self.planning_id.end_datetime.time()  # Ensure end_datetime exists
                new_date = self.date_end + timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)
                self.planning_id.write({
                    'end_datetime': new_date
                })
            else:
                # Handle the case where end_datetime is False/None
                self.planning_id.write({
                    'end_datetime': self.date_end
                })

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self._origin:
            if self.planning_id.start_datetime:
                time = self.planning_id.start_datetime.time()
                new_date = self.date_start + timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)
                self.planning_id.write({
                    'start_datetime': new_date
                })
            else:
                # Handle the case where end_datetime is False/None
                self.planning_id.write({
                    'start_datetime': self.date_start
                })


class ProjectTask(models.Model):
    _inherit = "project.task"

    def name_get(self):
        res = []
        for rec in self:
            if rec.seq_code and rec.name:
                name = "%s - %s" % (rec.seq_code, rec.name)
                res += [(rec.id, name)]
        return res

    @api.onchange('resource_history_ids', 'resource_history_ids.resource_change_type',
                  'resource_history_ids.employee_id')
    def _onchange_employee_id(self):
        add_employee = []
        replace_employee = []
        for resource in self.resource_history_ids.filtered(lambda x: x.resource_change_type and x.employee_id):
            if resource.resource_change_type == "add":
                add_employee.append((4, resource.employee_id.id))
            if resource.resource_change_type == "replace":
                replace_employee.append((3, resource.existing_resource_id.id))
                add_employee.append((4, resource.employee_id.id))
        self.resource_ids = replace_employee
        self.resource_ids = add_employee


class TaskDemobilize(models.TransientModel):
    _name = "task.demobilize"
    _description = "Task demobilize"

    date = fields.Datetime(string='End Date')
    remarks = fields.Text(string="Reason")

    # new changes by shon
    def action_approve(self):
        if self.env.context.get('active_model') == 'task.resource.history':
            task_resource_id = self.env['task.resource.history'].browse(self.env.context.get('active_id'))
            if task_resource_id.planning_id.end_datetime:
                time = task_resource_id.planning_id.end_datetime.time()
                new_date = self.date + timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)

                task_resource_id.planning_id.write({
                    'end_datetime': new_date
                })
                task_resource_id.write({'demobilize_date': self.date, 'remarks': self.remarks})
            else:
                # Handle case when end_datetime is not set
                task_resource_id.write({'demobilize_date': self.date, 'remarks': self.remarks})

        elif self.env.context.get('active_model') == 'planning.slot':
            planning = self.env['planning.slot'].browse(self.env.context.get('active_id'))
            if planning.end_datetime:
                time = planning.end_datetime.time()
                new_date = self.date + timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)
                planning.write({
                    'end_datetime': new_date
                })
                planning.task_resource_history_id.write(
                    {'date_end': new_date, 'demobilize_date': self.date, 'remarks': self.remarks})
            else:
                # Handle case when end_datetime is not set
                planning.write({'demobilize_date': self.date, 'remarks': self.remarks})

    # new changes ganesh
    # def action_approve(self):
    #     if self.env.context.get('active_model') == 'task.resource.history':
    #         task_resource_id = self.env['task.resource.history'].browse(self.env.context.get('active_id'))
    #
    #         time = task_resource_id.planning_id.end_datetime.time()
    #         new_date = self.date + timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)
    #
    #         task_resource_id.planning_id.write({
    #             'end_datetime': new_date
    #         })
    #         task_resource_id.write({'demobilize_date': self.date, 'remarks': self.remarks})
    #     elif self.env.context.get('active_model') == 'planning.slot':
    #         planning = self.env['planning.slot'].browse(self.env.context.get('active_id'))
    #         time = planning.end_datetime.time()
    #         new_date = self.date + timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)
    #         planning.write({
    #             'end_datetime': new_date
    #         })
    #         planning.task_resource_history_id.write(
    #             {'date_end': new_date, 'demobilize_date': self.date, 'remarks': self.remarks})


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.depends('task_ids')
    def _compute_task(self):
        # print("_________-DEEPTHI RAVINDRANDEEPTHI RAVINDRAN")

        for employee_id in self:
            shift_allocation = []

            today = date.today()
            task_ids = employee_id.task_ids.filtered(
                lambda sol: not sol.demobilize_date or sol.demobilize_date and sol.demobilize_date.date() > today)
            # @chandni
            # print ("_____________-CHANDNI GLOBALTECKZ")
            # print ("___________________________________-",task_ids)
            task = [task.task_id.id for task in task_ids if task.date_start.date() <= today <= task.date_end.date()]
            customers_list = []
            saleorder_list = []
            supervisors_list = []
            for shift_task in self.env['project.task'].browse(task):
                for shift in shift_task.shift_allocation_ids:
                    if shift.employee_id.id == employee_id.id and shift.date_from.date() <= today <= shift.date_to.date():

                        shift_allocation.append(shift.shift_id.id)
                        # Customer
                        if shift_task.partner_id and shift_task.partner_id.id:
                            customers_list.append(shift_task.partner_id.id)
                        if shift_task.sale_order_id and shift_task.sale_order_id.id:
                            saleorder_list.append(shift_task.sale_order_id.id)
                        if shift_task.emp_id and shift_task.emp_id.id:
                            supervisors_list.append(shift_task.emp_id.id)

            employee_id.write({'task_shift_ids': task if task and task[0] else None,
                               'tasks_shift_allocation_ids': shift_allocation,
                               'customer_ids': customers_list,
                               'sale_order_ids': saleorder_list,
                               'supervisor_ids': supervisors_list,
                               'group_by_task_shift': task if task and task[0] else None,
                               'group_by_shift_allocation': shift_allocation,
                               'group_by_customer_ids': customers_list,
                               'group_by_sale_order_ids': saleorder_list,
                               'group_by_supervisor_ids': supervisors_list,
                               })
            if len(task_ids.ids) == 1:

                employee_id.write({
                    'task_id': task_ids.task_id.id,
                    'store_task_id': task_ids.task_id.id,
                    'emp_id': task_ids.task_id.emp_id.id,
                    'task_record_id': task_ids.task_id.id,
                    'task_record_name': "%s - %s" % (task_ids.task_id.seq_code, task_ids.task_id.name,
                                                     )})
                if employee_id.task_record_id:
                    employee_id.write({
                        'sale_order_id': task_ids.task_id.sale_order_id.id,
                        'partner_id': task_ids.task_id.partner_id.id,
                    })

            else:
                employee_id.write({'task_id': False, 'task_record_id': False, 'store_task_id': False, })

    task_ids = fields.One2many('task.resource.history', 'employee_id', string="Task")

    task_id = fields.Many2one('project.task', string='Task', compute=_compute_task, readonly=True)
    task_shift_ids = fields.Many2many('project.task', string="Tasks", compute=_compute_task, readonly=True)
    group_by_task_shift = fields.Many2many('project.task', 'tasks_shift_groupby_rel', 'task_employee_id', 'customer_id',
                                           string="Shift Tasks")

    tasks_shift_allocation_ids = fields.Many2many('hr.shift',
                                                  'tasks_shift_allocation_rel', 'task_shift_id', 'allocation_id',
                                                  'Shift Allocation', compute=_compute_task)

    group_by_shift_allocation = fields.Many2many('hr.shift',
                                                 'tasks_shift_allocation_groupby_rel', 'task_shift_id', 'allocation_id',
                                                 string="Shift Allocations")

    customer_ids = fields.Many2many('res.partner', 'tasks_shift_customer_rel', 'task_employee_id', 'customer_id',
                                    string="Customer", compute=_compute_task)
    group_by_customer_ids = fields.Many2many('res.partner', 'tasks_shift_customer_groupby_rel', 'task_employee_id',
                                             'customer_id', string="Customer")

    sale_order_ids = fields.Many2many('sale.order', 'tasks_shift_saleorder_rel', 'task_employee_id', 'sale_order_id',
                                      string="Sale Order", compute=_compute_task)
    group_by_sale_order_ids = fields.Many2many('sale.order', 'tasks_shift_saleorder_groupby_rel', 'task_employee_id',
                                               'sale_order_id', string="Sale Order")

    supervisor_ids = fields.Many2many('hr.employee', 'tasks_shift_supervisor_rel', 'task_employee_id', 'supervisor_id',
                                      string="Task Supervisors", compute=_compute_task)
    group_by_supervisor_ids = fields.Many2many('hr.employee', 'tasks_shift_supervisor_groupby_rel', 'task_employee_id',
                                               'supervisor_id',
                                               string="Task Supervisors")

    store_task_id = fields.Many2one('project.task', string='Task Ref')
    task_record_id = fields.Char(string="Task ID")
    task_record_name = fields.Char(string="Task Name")
    partner_id = fields.Many2one('res.partner', string='Customer')
    user_id = fields.Many2one('res.users', string='Supervisor')
    emp_id = fields.Many2one('hr.employee', string='Supervisor')

    # @api.onchange('task_shift_ids')
    # def onchange_employee_task_report(self):
    #     for rec in self:
    #         print ("REC_____________________")
    #         if rec.task_shift_ids:
    #             print ("TTTTTTTTT_______________________",rec.task_shift_ids.ids)
    #             rec.group_by_task_shift = [(6,0,rec.task_shift_ids.ids)]
