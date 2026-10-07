# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class Product(models.Model):
    _inherit = "product.template"

    is_overtime_product = fields.Boolean(
        string="Is Overtime Product",
        help="Allow Crate Overtime Product"
        )
    based_cost = fields.Selection([
        ('one_time_cost', 'One-time Cost'),
        ('annual_charges', 'Annual Charges(rec)'),
        ('annual_privilege_leave', 'Annual/Privilege Leave'),
        ('service_charge', 'End of Service Charges'),
        ('es', 'ES')],
        string="Costing")
    recurring = fields.Boolean('Recurring')

    @api.onchange('based_cost')
    def onchange_based_cost(self):
        for rec in self:
            if rec.based_cost in ('annual_charges','annual_privilege_leave'):
                print("Test____________")
                rec.recurring = True
