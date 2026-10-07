# -*- coding: utf-8 -*-
from odoo import api, models, fields, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    job_stage_category = fields.Selection([
        ('danger', 'Danger'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('secondary', 'Secondary'),
        ('info', 'Info'),
        ('muted', 'Muted'),
        ('primary', 'Primary'),
    ], compute="_compute_job_stage_category", store=True)

    @api.depends('jobstage_id')
    def _compute_job_stage_category(self):
        for record in self:
            if record.jobstage_id.name == "Cancelled":
                record.job_stage_category = "danger"
            elif record.jobstage_id.name == "Done":
                record.job_stage_category = "success"
            elif record.jobstage_id.name == "In Progress":
                record.job_stage_category = "warning"
            elif record.jobstage_id.name == "Hold":
                record.job_stage_category = "secondary"
            elif record.jobstage_id.name == "Final Collection":
                record.job_stage_category = "muted"
            elif record.jobstage_id.name == "To Do":
                record.job_stage_category = "info"
            else:
                record.job_stage_category = "primary"

    site_contact = fields.Char(string="Site Contact")
    site_contact_number = fields.Char(string="Contact Number")
    schedule_id = fields.Many2one('shift.schedule', string="Shift Schedule")
    alternate_skip_types_ids = fields.Many2many(
        'equipment.type',
        'task_equipment_skip_types_rel'
        'skip_types_id',
        'task_id',
        string='Alternate Skip Types',
    )

    collection_mode = fields.Selection([
        ('fix', 'Fix'),
        ('on_call', 'On Call')
    ], string="Collection Mode", default='fix')

    vehicle_permit_ids = fields.Many2many(
        'vehicle.permit',
        'task_vehicle_permit_rel'
        'permit_id',
        'task_id',
        string='Vehicle Permits',
    )
    skip_permit_ids = fields.Many2many(
        'vehicle.permit',
        'task_vehicle_permit_rel'
        'permit_id',
        'task_id',
        string='Skip Permits',
    )
    frequency_value = fields.Selection(
        selection=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('on_call', 'On Call')],  # Adjust based on your actual selection values
        string="Computed Frequency",
        compute="_compute_frequency_value",
        store=True
    )

    @api.depends('frequency_id.frequency')
    def _compute_frequency_value(self):
        for task in self:
            task.frequency_value = task.frequency_id.frequency if task.frequency_id else False

    landfill_id = fields.Many2one('fleet.landfill', string="Landfill", required=True, default=lambda self: self._get_default_landfill())
    latitude = fields.Float(string="Latitude", digits='Lat-Long')
    longitude = fields.Float(string="Longitude", digits='Lat-Long')
    is_mtech_view = fields.Boolean(compute="_compute_is_mtech_view", store=False, default=False)
    job_stage_id = fields.Many2one(
        'job.order.stage',
        string="Job Order Stage",
    )

    jobstage_id = fields.Many2one(
        'job.order.stage',
        string="Stage",
        default=lambda self: self._default_job_stage()
    )

    @api.model
    def _get_default_landfill(self):
        """Return the ID of the 'N/A' landfill record."""
        landfill = self.env['fleet.landfill'].search([('name', '=', 'N/A')], limit=1)
        if landfill:
            return landfill.id
        # Optional: create it if not found
        return self.env['fleet.landfill'].create({'name': 'N/A'}).id

    def _default_job_stage(self):
        return self.env['job.order.stage'].search([('name', '=', 'To Do')], limit=1).id


    @api.depends_context('default_is_mtech_view')
    def _compute_job_stage(self):
        for record in self:
            if record.is_mtech_view:
                todo_stage = self.env['job.order.stage'].search([('name', '=', 'To Do')], limit=1)
                record.jobstage_id = todo_stage.id if todo_stage else False
            else:
                record.jobstage_id = False

    def action_schedule_and_planning(self):
        view_id = self.env.ref('mtech_vehicle_extended.view_shift_schedule_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule & Planing'),
            'view_mode': 'form',
            'res_model': 'shift.schedule',
            'target': 'new',
            'context': {'default_task_id': self.id,
                        'default_collection_mode': self.collection_mode,
                        # 'default_landfill_id': self.landfill_id.id,
                        'default_frequency': self.frequency_value,
                        'default_number_of_skips': self.sale_order_id.order_line[0].equipment_qty,
                        'default_vehicle_type': self.vehicle_type_id.id,
                        'default_permits_ids': [(6, 0, self.vehicle_permit_ids.ids)],
                        },
            'views': [[view_id, 'form']],
        }

    @api.depends_context('default_is_mtech_view')
    def _compute_is_mtech_view(self):
        for record in self:
            record.is_mtech_view = self.env.context.get('default_is_mtech_view', False)


class Frequency(models.Model):
    _inherit = "so.frequency"
    _description = "So Frequency"

    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('on_call', 'On Call'),
    ], string="Frequency")
