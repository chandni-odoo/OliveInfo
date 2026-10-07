# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ContractApprovalProcess(models.Model):
    _name = 'contract.approval.process'
    _description = 'Record Approval'


    name = fields.Char(string='Name')
    approver_ids = fields.One2many('contract.approval.process.line', 'approval_id')
    activity_type_id = fields.Many2one('mail.activity.type', string='Activity Type For Notification')
    
    
    
    
    
class ContractApprovalProcessLine(models.Model):
    _name = 'contract.approval.process.line'
    _description = 'Record Approval Line'


    user_id = fields.Many2one('res.users',string='User')
    approval_id = fields.Many2one('contract.approval.process',string='Approval')
    
    
class ContractApprovalRecords(models.Model):
    _name = 'contract.approval.records'
    _description = 'Contract Approval Records'


    contract_id = fields.Many2one('hr.contract', string='Contract')
    user_id = fields.Many2one('res.users', string='User')
    state = fields.Selection([('pending', 'Pending'), ('approved', 'Approved'),('rejected','Rejected')], string='State')
    active = fields.Boolean(string='Active')
    contract_active = fields.Boolean(string='Contract Active')
    activity_id = fields.Many2one('mail.activity', string='Activity')