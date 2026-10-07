# -*- coding: utf-8 -*-
from odoo import fields, api, models, _

class HRholidays(models.Model):
	_inherit = 'resource.calendar.leaves'

	special_holidays = fields.Boolean(string="Special Holidays")

class Contract(models.Model):
    _inherit = 'hr.contract'

    rule_line_ids = fields.One2many('hr.ot.rule.line', 'contract_id', string="OT Rule Line")

class HrOtType(models.Model):
	_name = "hr.ot.type"
	_description = "Hr OT Types"

	name = fields.Char(string="Name")
	code = fields.Char(string="Code")

class HrOtRule(models.Model):
	_name = "hr.ot.rule"
	_description = "HR Ot Type"

	name = fields.Char(string="Name")
	ot_type_id = fields.Many2one("hr.ot.type", string="Type")

class HrOtRuleLine(models.Model):
	_name = "hr.ot.rule.line"
	_description = "HR Ot Type Line"

	ot_rule_id = fields.Many2one('hr.ot.rule', string="Overtime Rule")
	ot_type_id = fields.Many2one(related='ot_rule_id.ot_type_id', string="Overtime Type")
	contract_id = fields.Many2one('hr.contract', string="Hr Contract")
	ot_type = fields.Selection([('fix', 'Fix'), ('percentage', 'Percentage')], string="Base On", default="fix")
	fix_amount = fields.Float(string="Fix Amount")
	per_amount = fields.Float(string="Percentage Amount")
	per_based_on = fields.Selection([('BASIC', 'BASIC'), ('GROSS', 'GROSS'), ('NET', 'NET')], string="Base On", default="BASIC")
