# -*- coding: utf-8 -*-
from odoo import api, fields, models

class TransferTemplate(models.Model):
    _name = 'transfer.template'
    _description = "Transfer Template"

    name = fields.Char(required=True)
    branch_id = fields.Many2one('res.branch', string="Branch")
    origin_account_ids = fields.One2many('origin.transfer.template.line', 'template_id')
    destination_account_ids = fields.One2many('destination.transfer.template.line', 'template_id')

class OgiginTransferTemplate(models.Model):
    _name = 'origin.transfer.template.line'
    _description = "Origin Transfer Template Line"

    template_id = fields.Many2one('transfer.template')
    account_id = fields.Many2one('account.account', string="Origin Account")

class DestinationTransferTemplate(models.Model):
    _name = 'destination.transfer.template.line'
    _description = "Destination Transfer Template Line"

    template_id = fields.Many2one('transfer.template')
    branch_id = fields.Many2one('res.branch', string="Branch")
    percent = fields.Float(string="Percent")
    account_id = fields.Many2one('account.account', string="Destination Account")