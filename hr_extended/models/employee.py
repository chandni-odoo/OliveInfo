# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_salary_wages = fields.Boolean(string="Salaries and wages")

class EmplopyeeGroup(models.Model):
    _name = 'emplopyee.group'
    _description = "Employee Group"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char("Employee Group ")
    parent_id= fields.Many2one('emplopyee.group')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('emplopyee.group', 'parent_id', 'Child Employee')
    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name', recursive=True,
        store=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name
                
class EmplopyeeSubGroup(models.Model):
    _name = 'emplopyee.sub.group'
    _description = "Employee Sub Group"
    # _parent_name = "parent_sub_group_id"
    # _parent_store = True
    # _rec_name = 'complete_name'
    # _order = 'complete_name'

    name = fields.Char("Employee Sub Group")
    parent_id= fields.Many2one('emplopyee.group',string="Parent")
    # parent_path = fields.Char(index=True)
    # child_ids = fields.One2many('emplopyee.sub.group', 'parent_id', 'Child Employee')
    # complete_name = fields.Char(
    #     'Complete Name', compute='_compute_complete_name', recursive=True,
    #     store=True)

    # @api.depends('name', 'parent_id.complete_name')
    # def _compute_complete_name(self):
    #     for category in self:
    #         if category.parent_id:
    #             category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
    #         else:
    #             category.complete_name = category.name

class EmplpoyeeCategory(models.Model):
    _name = 'emp.category'
    _description = "Employee Category"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char("Employee Categories ")
    parent_id= fields.Many2one('emp.category')
    parent_path = fields.Char(index=True)
    child_id = fields.One2many('emp.category', 'parent_id', 'Child Employee')
    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name', recursive=True,
        store=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name


class TypeofVisa(models.Model):
    _name = 'visa.type'
    _description = "Visa Type"

    name = fields.Char("Visa Name")

class TravelSector(models.Model):
    _name = 'travel.sector'
    _description = "Travel Sector"

    name = fields.Char("Travel Sector")
    amount = fields.Float("Amount", required=True)


class HrDocument(models.Model):
    _name = 'hr.document'
    _description = "Hr Document"

    name = fields.Char("Document Type")
    is_passport = fields.Boolean('Is Passport')
    national_id = fields.Boolean('National ID')
    visa_id = fields.Boolean('Visa ID')

class HrPassportControl(models.Model):
    _name = 'hr.passport.control'
    _description = "Hr Passport Control"

    name = fields.Char("Passport Control")
    status = fields.Selection([('in', 'In'),('out','Out')], default='in')


class HrInsurance(models.Model):
    _name = 'hr.insurance'
    _description = "Hr Insurance"

    name = fields.Char("Insurance Type")

class HrDrivingLicence(models.Model):
    _name = 'driving.licence'
    _description = "Driving Licence"

    name = fields.Char("License Type")

class DisciplinaryAction(models.Model):
    _name = 'disciplinary.action'
    _description = "Disciplinary Action"

    name = fields.Char("Disciplinary Action")

class DisciplinaryAction(models.Model):
    _name = 'contact.type'
    _description = "Contact Type"

    name = fields.Char("Contact Type")
    contact_name = fields.Selection([('contact', 'Contact'), ('partner','Partner'), ('employee','Employee')], default='contact')

class EthiniCode(models.Model):
    _name = 'ethinic.code'
    _description = "Ethini Code"

    name = fields.Char("Religion Name")
    code = fields.Char()

class CertificateType(models.Model):
    _name = 'certificate.type'
    _description = "Certificate Type"

    name = fields.Char("Certificate Type")
