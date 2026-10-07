# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class CustomerRegion(models.Model):
    _name = 'customer.region'
    _description = "Different Types of Region"

    name = fields.Char("Region", required=True)

class CustomerSector(models.Model):
    _name = 'customer.sector'
    _description = "Types Of Sector"
    
    name = fields.Char("Sector", required=True)

class Industry(models.Model):
    _name = 'main.industry'
    _description = " Types Of Industry"

    name = fields.Char("Industry", required=True)

class HrLocation(models.Model):
    _name = 'hr.location'
    _description = "Location Information"

    name = fields.Char("Location", required=True)

class GradeType(models.Model):
    _name = 'grade.type'
    _description = "Grade Type"

    name = fields.Char("Grade", required=True)

class CustomerSegment(models.Model):
    _name = 'customer.segment'
    _description = "Segment Information"

    name = fields.Char("Segment Name", required=True)

class HoldReason(models.Model):
    _name = 'hold.reason'
    _description = "Types Of Hold Reasons"

    name = fields.Char("Reason Name", required=True)

class HrEmployeeLine(models.Model):
    _inherit = 'hr.document.line'

    customer_id = fields.Many2one('customer.onboarding.request')
    supplier_id = fields.Many2one('supplier.onboarding.request')
    partner_id = fields.Many2one('res.partner')

class FrequencyDays(models.Model):
    _name = 'frequency.days'
    _description = "Frequency Days"

    name = fields.Char("Frequency Name", required=True)
    days = fields.Integer(string="Days")
