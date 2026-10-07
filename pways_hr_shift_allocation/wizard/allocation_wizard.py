from odoo import models, fields, api, _
from datetime import datetime, timedelta
import calendar
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

DEFAULT_FACTURX_DATE_FORMAT = '%m%d%Y'
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class AllocationWizard(models.TransientModel):
    _name = "allocation.wizard.lines"

    planning_id = fields.Many2one('planning.slot', string="Weeks")
    wizard_id = fields.Many2one('allocation.wizard', string="Weeks")
    week_id = fields.Many2one('week.week', string="Weeks")
    code = fields.Char(string="Day No")
    l_code = fields.Char(string="Leave Code")
    types = fields.Selection([('first_half', 'First Half'), ('second_half', 'Second Half')])
    week_selection_ids = fields.Many2many('week.selection', string="WeekSelection")
    

    @api.onchange('week_id')
    def OnchangeWeek(self):
        if self.week_id:
            self.code = self.week_id.code
            self.l_code = self.week_id.l_code
            self.types = self.week_id.types if self.week_id.l_code == 'H' else None


class AllocationWizard(models.TransientModel):
    _name = "allocation.wizard"
    _description = "allocation.wizard"

    description = fields.Text()
    date_from = fields.Date()
    date_to = fields.Date()
    shift_id = fields.Many2one("hr.shift", required=True)
    employee_ids = fields.Many2many("hr.employee", required=True)
    week_ids = fields.One2many('allocation.wizard.lines', 'wizard_id', string="Weeks")

    @api.model
    def default_get(self, fields):
        vals = super(AllocationWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if self.env.context.get('active_model') == 'hr.employee' and active_ids:
            vals['employee_ids'] = active_ids

        return vals
    
    

    def find_week_days(self, week, line):
        if line.week_id.code == '0':
            days = week[calendar.MONDAY]
        if line.week_id.code == '1':
            days = week[calendar.TUESDAY]
        if line.week_id.code == '2':
            days = week[calendar.WEDNESDAY]
        if line.week_id.code == '3':
            days = week[calendar.THURSDAY]
        if line.week_id.code == '4':
            days = week[calendar.FRIDAY]
        if line.week_id.code == '5':
            days = week[calendar.SATURDAY]
        if line.week_id.code == '6':
            days = week[calendar.SUNDAY]
        return days

    def _prepaire_days_of_week_lines(self, employee_id):
        days_of_week_lines = []
        d = {}
        if self.date_from and self.date_to:
            date_array = (self.date_from + timedelta(days=x) for x in range(0, (self.date_to - self.date_from).days))
            for date_object in date_array:
                month_year = "{}-{}".format(date_object.year, date_object.month)
                if month_year not in d:
                    d.update({month_year: calendar.monthcalendar(date_object.year, date_object.month)})
            for line in self.week_ids:
                for i, cal in d.items():
                    for wk in line.week_selection_ids:
                        if len(cal) > int(wk.code) - 1:
                            week = cal[int(wk.code) - 1]
                            days = self.find_week_days(week, line)
                            if days:
                                full_date = "{}-{}".format(i, days)
                                date_obj = datetime.strptime(full_date, DEFAULT_SERVER_DATE_FORMAT)
                                if date_obj.date() >= self.date_from and date_obj.date() <= self.date_to:
                                    days_of_week_lines.append((0, 0, {
                                        'date': date_obj,
                                        'week_id': line.week_id.id,
                                        'employee_id': employee_id.id,
                                        'types': line.types
                                    }))
        return days_of_week_lines

    def _prepare_shift_value(self):
        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'shift_id': self.shift_id.id,
            'shift_type_id': self.shift_id.shift_type_id and self.shift_id.shift_type_id.id,
            'description': self.description,
            'state': 'in_progress',
        }

    def bulk_allocation(self):
        vals = self._prepare_shift_value()
        for emp in self.employee_ids:
            vals['employee_id'] = emp.id
            lines = self._prepaire_days_of_week_lines(emp)
            vals['dayofweek_ids'] = lines
            self.env['shift.allocation'].create(vals)
