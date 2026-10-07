# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    employee_status_new = fields.Selection(
        [('general', 'General'), ('idle', 'Idle'), ('stand_by', 'Stand By'), ('on_duty', 'On Duty'),
         ('training', 'Training')], default='on_duty', tracking=True)

    is_week_off_done = fields.Boolean(string="Week Off Done", compute='_compute_is_week_off_done')

    @api.model
    def _compute_is_week_off_done(self):
        for employee in self:
            flag = False
            shifts = self.env['shift.allocation'].search([('employee_id', '=', employee.id)])
            if shifts:
                for shift in shifts:
                    for day in shift.dayofweek_ids.filtered(lambda x: x.date == datetime.now().date()):
                        flag = True
            if flag:
                employee.is_week_off_done = True
            else:
                employee.is_week_off_done = False

    def _compute_active_task(self):
        for employee in self:
            task_ids = employee.task_ids.filtered(lambda x: not x.demobilize_date)
            if len(task_ids.ids) == 1:
                employee.write({'task_id': task_ids.task_id.id})
                if task_ids.task_id.seq_code and task_ids.task_id.name:
                    employee.write({'task_name': task_ids.task_id.seq_code + " " + task_ids.task_id.name})

                    # task_name = fields.Char(string="Task", compute="_compute_active_task")

    task_name = fields.Char(string="Task")
    is_helper = fields.Boolean()
    is_driver = fields.Boolean()
    task_history_ids = fields.One2many('employee.task.history', 'employee_id')

    def name_get(self):
        res = []
        for rec in self:
            name = "%s - %s" % (rec.emp_no, rec.name)
            res += [(rec.id, name)]
        return res

    def create_week_off(self):
        line_ids = False
        for task in self.task_shift_ids:
            for shift in task.shift_allocation_ids.filtered(lambda line: line.employee_id.id == self.id):
                line_ids = []
                week = self.env['week.week'].search([('name', '=', datetime.now().strftime('%A'))], limit=1)
                vals = (0, 0, {
                    'week_id': week.id if week else None,
                    'date': datetime.now().date(),
                    # 'types': 'first_half',
                })
                line_ids.append(vals)
                shift.write({
                    'dayofweek_ids': line_ids
                })
        self.write({
            'dayofweek_ids': line_ids,
        })


class EmployeeTaskHistory(models.Model):
    _name = 'employee.task.history'
    _description = 'Employee Task History'

    task_id = fields.Many2one('project.task', string='Task')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    date_start = fields.Datetime(string='Date Start')
    date_end = fields.Datetime(string='Date End')
    