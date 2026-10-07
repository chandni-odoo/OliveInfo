# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class VisaProfession(models.Model):
    _name = 'visa.profession'
    _description = 'Visa Profession'
    
    name = fields.Char("Visa Profession", required=True)

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    applicant_no = fields.Char('Application No')
    app_status = fields.Selection([('ic', 'Intial Contact'),('approved','Approved'),('hired','Hired')], default='ic',string="Application Status")
    status_date = fields.Date()
    exp_salary = fields.Float('Expected Salary')
    hours_available = fields.Char()
    first_interview_date = fields.Date()
    application_date = fields.Date()
    date_available = fields.Date('Available Date')
    attachment = fields.Binary('Attachment')
    #NEW
    country_id = fields.Many2one('res.country', string="Nationality")
    visa_profession_id = fields.Many2one('visa.profession')
    passport_no = fields.Char()
    passport_expiry_date = fields.Date()
    qid_no = fields.Char()
    qid_date = fields.Date(string="QID Expiry Date")
    gender = fields.Selection([('male', 'Male'),('female', 'Female'),('other', 'Other')])
    metrash_registered_mobile = fields.Char()
    ducument_line_ids = fields.One2many('document.line','applicant_id')

    def create_employee_from_applicant(self):
        res = super(HrApplicant,self).create_employee_from_applicant()
        employee = False
        for applicant in self:
            contact_name = False
            if applicant.partner_id:
                address_id = applicant.partner_id.address_get(['contact'])['contact']
                contact_name = applicant.partner_id.display_name
            else:
                if not applicant.partner_name:
                    raise UserError(_('You must define a Contact Name for this applicant.'))
                new_partner_id = self.env['res.partner'].create({
                    'is_company': False,
                    'type': 'private',
                    'name': applicant.partner_name,
                    'email': applicant.email_from,
                    'phone': applicant.partner_phone,
                    'mobile': applicant.partner_mobile
                })
                applicant.partner_id = new_partner_id
                address_id = new_partner_id.address_get(['contact'])['contact']
            data = []
            for line in applicant.ducument_line_ids:
                data.append([0, 0, {
                    'document_line_id': line.document_line_id.id or False,
                    'document_number': line.document_number or False,
                    'valid_from': line.valid_from or False,
                    'valid_to': line.valid_to or False,
                    'doc_issue_place': line.doc_issue_place or False,
                    'status': line.status or False,
                    'receipt_no': line.receipt_no or False,
                    'receipt_date': line.receipt_date or False,
                    'remarks': line.remarks or False,
                    'attachment': line.attachment or False,
                    }])
            if applicant.partner_name or contact_name:
                employee_data = {
                    'default_name': applicant.partner_name or contact_name,
                    'default_job_id': applicant.job_id.id,
                    'default_job_title': applicant.job_id.name,
                    'address_home_id': address_id,
                    'default_department_id': applicant.department_id.id or False,
                    'default_address_id': applicant.company_id and applicant.company_id.partner_id
                            and applicant.company_id.partner_id.id or False,
                    'default_work_email': applicant.department_id and applicant.department_id.company_id
                            and applicant.department_id.company_id.email or False,
                    'default_work_phone': applicant.department_id.company_id.phone,
                    'form_view_initial_mode': 'edit',
                    'default_applicant_id': applicant.ids,
                    'default_country_id': applicant.country_id.id,
                    'default_visa_profession_id': applicant.visa_profession_id.id,
                    'default_passport_id': applicant.passport_no,
                    'default_passport_expiry_date': applicant.passport_expiry_date,
                    'default_qid_no': applicant.qid_no,
                    'default_qid_validity': applicant.qid_date,
                    'default_gender': applicant.gender,
                    'default_metrash_register_no': applicant.metrash_registered_mobile,
                    'default_ducument_line_ids': data or False,
                    }
        dict_act_window = self.env['ir.actions.act_window']._for_xml_id('hr.open_view_employee_list')
        dict_act_window['context'] = employee_data
        return dict_act_window

    @api.model
    def create(self, vals):
        vals['applicant_no'] = self.env['ir.sequence'].next_by_code('hr.applicant') or 'New'
        return super(HrApplicant, self).create(vals)

class HrDocumentLine(models.Model):
    _name = 'document.line'
    _description = "Document Line"

    applicant_id =fields.Many2one('hr.applicant')
    document_line_id = fields.Many2one('hr.document','Document Type')
    document_number = fields.Char('Document No')
    valid_from = fields.Date()
    valid_to = fields.Date()
    doc_issue_place =fields.Char('Document Place ')
    status = fields.Selection([('active', 'Active'),('history','History')], default='active')
    receipt_no = fields.Char('Receipt No')
    receipt_date = fields.Date()
    remarks = fields.Char()
    attachment = fields.Binary('Attachment')