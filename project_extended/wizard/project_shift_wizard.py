from odoo import models, fields, api, _
from datetime import datetime, date

class OverTimeWizard(models.TransientModel):
    _name = "project.shift.wizard"
    _description="ProjectShiftWizard"

    employee_id = fields.Many2one('hr.employee',required=True, string="Resource")
    from_date = fields.Date(string="Date From")
    to_date = fields.Date(string="Date To")
    from_hour = fields.Datetime(string="Hours From")
    to_hour = fields.Datetime(string="Hours To")
    weekend_date = fields.Date(string="Weekend Dates")


    def button_create_over_time(self):
        print('ITTTTTTTTTTTTTTTS WORKKKKKKKKKKKED')

class AllocationWizard(models.TransientModel):
    _inherit = "allocation.wizard"

    def _prepare_shift_value(self):
        res = super(AllocationWizard, self)._prepare_shift_value()
        if self._context.get('active_model') == 'project.task' and self._context.get('active_id'):
            res['task_id'] = self._context.get('active_id')
        return res
