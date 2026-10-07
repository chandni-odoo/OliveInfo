 # -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError,Warning,ValidationError,AccessError

class OtApproval(models.TransientModel):
    _name = 'ot.approval'
    _description = 'Overtime Approval'

    employee_ids = fields.Many2many('hr.employee', string="Employee")
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Waiting Approval')])

    @api.model
    def default_get(self, vals):
        res = super(OtApproval, self).default_get(vals)
        active_ids = self._context.get('active_ids')
        hr_overtimes = self.env['bt.hr.overtime'].browse(active_ids)
        if active_ids:
            employee_ids = hr_overtimes.mapped('employee_id')
            for ot_id in hr_overtimes.filtered(lambda o:  o.state == 'cancel' or  o.state == 'validate' or o.state == 'refuse'):
                if ot_id:
                    raise ValidationError("check state in cancel approval and refuse")
            if all([ot_id.state == 'confirm' for ot_id in hr_overtimes]):
                res['state'] = 'confirm'
            if all([ot_id.state == 'draft' for ot_id in hr_overtimes]):
                res['state'] = 'draft'
            res['employee_ids'] = employee_ids
        return res

    def action_submit(self):
        active_ids = self._context.get('active_ids')
        selected_overtime = self.env['bt.hr.overtime'].browse(active_ids)
        for ot_id in selected_overtime:
            ot_id.write({'state':'confirm'})

    def action_approve(self):
        active_ids = self._context.get('active_ids')
        selected_overtime = self.env['bt.hr.overtime'].browse(active_ids)
        for ot_id in selected_overtime:
            ot_id.write({'state':'validate'})

    def action_refuse(self):
        active_ids = self._context.get('active_ids')
        selected_overtime = self.env['bt.hr.overtime'].browse(active_ids)
        for ot_id in selected_overtime:
            ot_id.write({'state':'refuse'})
