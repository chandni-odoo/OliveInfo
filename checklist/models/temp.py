from  datetime import date
from odoo import api, fields, models


class ChecklistTemplate(models.Model):
    _name = "checklist.template" 
    _description = "Checklist Template"


    name = fields.Char(string='Name')
    req = fields.Char(string='Requirement')
    risk = fields.Char(string='Risk')
    remark =fields.Char(string='Remark')
    requirement_line_ids = fields.One2many('requirement.template','checklist_id',string='Pharmacy Lines')

class RequirementTemplate(models.Model):
    _name = "requirement.template" 
    _description = "Requirement Template"

    req = fields.Char(string='Requirement')
    risk = fields.Char(string='Risk')
    remark = fields.Char(string='Remark')
    checklist_id = fields.Many2one('checklist.template', string='Checklist')
    configuration_id = fields.Many2one('checklist.configuration', string='Configuration')

class ChecklistConfiguration(models.Model):
    _name = "checklist.configuration" 
    _description = "Checklist Configuration"
    _rec_name = 'checklist_id'
    
    date = fields.Date(string='Date')
    approved_id = fields.Many2one('res.users',string='ApprovedBy')
    attachment = fields.Binary(sting='Attachment', copy=False)
    filename = fields.Char(string='Filename', readonly=True)
    checklist_id = fields.Many2one('checklist.template', string='Checklist')
    requirement_line_ids = fields.One2many('requirement.template','configuration_id',string='Pharmacy Lines')

    @api.onchange('checklist_id')
    def onchange_checklist_id(self):
        """Onchange Method for Checklist."""
        if self.checklist_id:
            self.write({'requirement_line_ids':  [(6, 0, self.checklist_id.requirement_line_ids.ids)]})
