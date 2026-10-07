# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    branch_id = fields.Many2one('res.bank.branch',string="Branch")
    iban_no = fields.Char(string="IBAN No")

class Bank(models.Model):
    _inherit = 'res.bank'
    
    branch_ids = fields.One2many('res.bank.branch', 'bank_id', string="Branch")
    swift_code = fields.Char(string="Swift Code")
    iban_no = fields.Char(string="IBAN No")
    bsb_no = fields.Char(string="BSB Number")
    ifsc_code = fields.Char(string="IFSC Code")
    beneficiary_name = fields.Char(string="Beneficiary Name")
    branch_name = fields.Char(string="Branch Name")
    account_no = fields.Char(string="Account No")

class ResBankBranch(models.Model):
    _name = 'res.bank.branch'
    _description = "Branch"
    _rec_name = 'branch_name'

    bank_id = fields.Many2one('res.bank')
    branch_name = fields.Char(string="Branch Name", required=True)
    branch_code = fields.Char(string="Branch Code", required=True)
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    zip = fields.Char(string='Zip')
    city = fields.Char(string='City')
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    ifsc_code = fields.Char(string="IFSC Code",required=True)
    swift_code = fields.Char(string="Swift Code", required=True)
    iban_no = fields.Char(string="IBAN No")
    bsb_no = fields.Char(string="BSB Number")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
