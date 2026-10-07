# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from pytz import timezone, UTC
from datetime import timedelta
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import pytz
import datetime


class EmployeeIdleTime(models.TransientModel):
    _name = "idle.timesheet.wizard"
    _description = "Idle Timesheet Wizard"

    # employee_id = fields.Many2many('hr.employee', string="Employee ID")
    # date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    branch_id = fields.Many2many('res.branch', string='Branch ID')

    def create_excelsheet(self):
        client = self.env['project.task'].search([])
        data = {
            'date_to': self.date_to,
            # 'date_from': self.date_from,
            # 'employee_id': self.employee_id.ids,
            'branch_id': self.branch_id.ids,
        }

        return self.env.ref('project_extended.report_idle_timesheet_action').report_action(self, data=data)