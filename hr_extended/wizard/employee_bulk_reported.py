from odoo import models,fields,api, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone, UTC
from odoo.exceptions import ValidationError

class EmployeeBulkReportedWizard(models.TransientModel):
    _name = 'employee.report.wizard'
    _description = "Employee Bulk Report "

    employee_ids = fields.Many2many('hr.employee', string="Employees")

    @api.model
    def default_get(self, fields):
        vals = super(EmployeeBulkReportedWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            employee_ids = self.env['hr.employee'].browse(active_ids)
            vals['employee_ids'] = employee_ids
        return vals

    def action_employee_bulk_reported(self):
        for record in self.employee_ids:
            record.action_create_attendance()
        return True
