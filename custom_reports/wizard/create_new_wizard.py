# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class CreateClientWizard(models.TransientModel):
    _name = 'project.task.wizard'
    _description = "Project Task Wizard"

    start_to = fields.Date(string="Start Date")
    end_to = fields.Date(string="End Date")
    task_id = fields.Many2one('project.task', string="Task")
    vendor_id = fields.Many2one('res.partner', string="Vendor")

    def create_excel(self):
        client = self.env['project.task'].search([])
        data = {
            'start_to': self.start_to,
            'end_to': self.end_to,
            'task_id': self.task_id.id,
            'vendor_id': self.vendor_id.id,
        }
        return self.env.ref('custom_reports.action_report_client_timesheet').report_action(self, data=data)

    def create_excel_vendor(self):
        client = self.env['project.task'].search([])
        data = {
            'start_to': self.start_to,
            'end_to': self.end_to,
            'task_id': self.task_id.id,
            'vendor_id': self.vendor_id.id,
        }
        return self.env.ref('custom_reports.action_report_vendor_timesheet').report_action(self, data=data)
