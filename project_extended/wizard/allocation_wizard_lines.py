from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError


class HrShiftDayofWeek(models.Model):
    _inherit = 'hr.day.of.week'
    _description = "Hr day of weeks"


class AllocationWizard(models.TransientModel):
    _inherit = "allocation.wizard.lines"

    hr_day_of_week_id = fields.Many2one('hr.day.of.week', string='Hr Day Of Week Id')

    # @api.onchange('week_id', 'types')
    # def _onchange_week_id(self):
    #     if self._origin:
    #         self.hr_day_of_week_id.write({
    #             'week_id': self.week_id.id,
    #             'types': self.types,
    #         })

    # def create(self, vals):
    #     for line in vals:
    #         planning = self.env['planning.slot'].browse(line.get('planning_id'))
    #         week = self.env['hr.day.of.week'].create({
    #             'week_id': line.get('week_id'),
    #             'types': line.get('types'),
    #             'shift_allocation_id': planning.shift_allocation_id.id,
    #         })
    #         line.update({
    #             'hr_day_of_week_id': week.id,
    #         })
    #
    #     res = super(AllocationWizard, self).create(vals)
    #     return res
