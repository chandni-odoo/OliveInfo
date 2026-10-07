from odoo import models, fields, api

class SimpleDashboard(models.Model):
    _name = "simple.dashboard"
    _description = "Simple Dashboard"

    name = fields.Char(string='Dashboard', default='Dashboard')
    trip_sheet_count = fields.Integer(string="Trip Sheet", compute="_compute_trip_sheet_count")
    shift_opration_count = fields.Integer(string="Shift Opration", compute="_compute_shift_opration_count")
    fleet_count = fields.Integer(string="Fleet", compute="_compute_fleet_count")
    project_task_count = fields.Integer(string="Tasks", compute="_compute_project_tasks_count")

    def _compute_trip_sheet_count(self):
        for record in self:
            record.trip_sheet_count = self.env['custom.trip.sheet'].search_count([])

    def _compute_shift_opration_count(self):
        for record in self:
            record.shift_opration_count = self.env['operation.schedule'].search_count([])

    def _compute_fleet_count(self):
        for record in self:
            record.fleet_count = self.env['fleet.vehicle'].search_count([])

    def _compute_project_tasks_count(self):
        for record in self:
            record.project_task_count = self.env['project.task'].search_count([])


    def action_open_project_tasks(self):
        return {
            'name': 'Tasks',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_trip_sheet(self):
        return {
            'name': 'Trip Sheet',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.trip.sheet',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_shift_opration(self):
        return {
            'name': 'Opration Schedule',
            'type': 'ir.actions.act_window',
            'res_model': 'operation.schedule',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_fleet(self):
        return {
            'name': 'Fleet Vehicles',
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle',
            'view_mode': 'list,form',
            'target': 'current',
        }
