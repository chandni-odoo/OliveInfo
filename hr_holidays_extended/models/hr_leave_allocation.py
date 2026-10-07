from odoo import api, fields, models, _


class HolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    total_accrual_days = fields.Float(string="Total Accrual Days", compute="compute_total_accrual_days", store=True)
    is_staff = fields.Boolean(string="Staff")

    @api.depends('is_staff', 'accrual_plan_id')
    def compute_total_accrual_days(self):
        for rec in self:
            if rec.allocation_type == 'accrual' and rec.accrual_plan_id and rec.is_staff:
                level_ids = rec.accrual_plan_id.level_ids.sorted('sequence')
                for level in level_ids:
                    if level.frequency == 'daily':
                        rec.total_accrual_days = level.added_value * 365
                    if level.frequency == 'weekly':
                        rec.total_accrual_days = level.added_value * 52
                    if level.frequency == 'monthly':
                        rec.total_accrual_days = level.added_value * 12
                    if level.frequency == 'bimonthly':
                        rec.total_accrual_days = level.added_value * 24
                    if level.frequency == 'yearly':
                        rec.total_accrual_days = level.added_value * 1
                    if level.frequency == 'biyearly':
                        rec.total_accrual_days = level.added_value * 2
            else:
                rec.total_accrual_days = 0.0
