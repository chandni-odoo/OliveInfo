# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResourceReporting(models.Model):
    _name = 'resource.reporting'
    _description = "resource_reporting"

    emp_id = fields.Many2one('hr.employee')
    emp_name = fields.Char(string="Name", required=True)
    emp_code = fields.Char(string="Emp Code")
    branch_id = fields.Many2one('res.branch', string='Branch')
    task_id = fields.Many2one('project.task', string="Task")
    project_id = fields.Many2one('project.project', string='Projects')
    billable = fields.Boolean(string="Billable")
    date = fields.Datetime(string="Date")
