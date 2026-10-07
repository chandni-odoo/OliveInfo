# -*- coding: utf-8 -*-

from odoo import models,fields,api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from pytz import timezone, UTC
import pytz
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta

class EmployeeLeaveWizard(models.TransientModel):
    _name = 'employee.leave.wizard'
    _description = "Employee leave Type"

    leave_type_id = fields.Many2one('hr.leave.type')

    def action_create_leave(self):
        active_model = self.env.context.get('active_model')
        active_id = self.env[active_model].browse(self.env.context.get('active_id'))
        contract_id = self.env['hr.contract'].search([('employee_id', '=', active_id.id),('state', '=', 'open')], limit=1)
        if not contract_id:
            raise ValidationError(("Employee %s does not have any running contract . Please create on employee.") % (active_id.id.name))
        today = datetime.now().replace(minute=30, hour=10, second=00)
        user_tz = self.env.user.tz or self.env.context.get('tz') or 'UTC'
        local = pytz.timezone(user_tz)
        today_date_from = local.localize(today).astimezone(pytz.utc)
        date_to_hours = today + timedelta(hours=int(contract_id.work_hours))
        today_date_to = local.localize(date_to_hours).astimezone(pytz.utc)
        date_from = today_date_from.strftime('%Y-%m-%d %H:%M:%S')
        date_to = today_date_to.strftime('%Y-%m-%d %H:%M:%S')
        leave_id = self.env['hr.leave'].create({
            'holiday_status_id':  self.leave_type_id.id or self.leave_type_id,
            'employee_id': active_id.id,
            'request_date_from': fields.Date.today(),
            'request_date_to': fields.Date.today(),
            'date_from': date_from,
            'date_to': date_to,
            'number_of_days': 1,
            })
        return leave_id