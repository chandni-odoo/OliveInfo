from odoo import models,fields,api, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone, UTC
from odoo.exceptions import ValidationError
import time
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta

class EmployeeTaskBulkReported(models.TransientModel):
    _name = 'employee.task.reported.wizard'
    _description = "Employee Task Bulk Report "


    task_ids = fields.Many2many('project.task', string="Task")

    @api.model
    def default_get(self, fields):
        vals = super(EmployeeTaskBulkReported, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            task_ids = self.env['project.task'].browse(active_ids)
            vals['task_ids'] = task_ids
        return vals


    def action_task_bulk_reported(self):
        for task in self.task_ids:
            employee_ids = task.resource_ids | task.resource_history_ids.mapped('employee_id')
            for record in employee_ids:
                contract_id = self.env['hr.contract'].search([('employee_id', '=', record.id),('state', '=', 'open')], limit=1)
                if not contract_id:
                    raise ValidationError(("Employee %s does not have any running contract . Please create on employee.") % (record.name))

                date = fields.Date.today()
                shift_allocation = self.env['shift.allocation'].search([('employee_id', '=', record.id), ('state', '=', 'in_progress'), ('date_from', '<=' , date), ('date_to', '>=',  date)], limit=1)
                if not shift_allocation and not shift_allocation.shift_id:
                    raise ValidationError(("Employee %s does not have any shift . Please create shift.") % (record.name))
                if not shift_allocation.shift_id.hours_from:
                    raise ValidationError(("Employee %s does not have set shift time. Please set shift time.") % (record.name))

                date_start = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) + " 00:00:00" 
                if date_start:
                    date_start = fields.Datetime.from_string(date_start) + timedelta(hours=int(shift_allocation.shift_id.hours_from))
                    date_end = date_start + timedelta(hours=int(task.std_hrs))
                    self.env['resource.reporting'].create({
                        'emp_name': record.name,
                        'emp_id': record.id ,
                        'emp_code': record.emp_no,
                        'task_id': task.id,
                        'project_id': task.project_id.id,
                        'branch_id': task.branch_id.id,
                        'billable': record.billable,
                        'date': datetime.now()
                    })

                    self.env['hr.attendance'].create({
                        'employee_id': record.id,
                        'task_id': task.id,
                        'check_in': date_start,
                        'check_out': date_end,
                        'branch_id': contract_id.branch_id.id
                    })
        return True
