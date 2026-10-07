from odoo import models, fields, api, _
from datetime import datetime


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    is_peoplesolve_partner = fields.Boolean(string="Is Partner")
    peoplesolve_emp_partner_id = fields.Many2one('res.partner', string="Partner")

    @api.model
    def create(self, values):
        res = super(HrEmployee, self).create(values)
        if values.get('is_peoplesolve_partner'):
            partner = {'name': res.name,
                       'phone': res.work_phone,
                       'email': res.work_email,
                       'mobile': res.mobile_phone,
                       'is_customer': True}
            partner_id = self.env['res.partner'].sudo().create(partner)
            if partner_id and res:
                res.peoplesolve_emp_partner_id = partner_id.id
        return res


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    is_service_portal = fields.Boolean(string="Service Portal")
