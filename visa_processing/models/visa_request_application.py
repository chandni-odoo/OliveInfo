from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta, datetime

class VisaRequestApplication(models.Model):
    _name = 'visa.request.application'
    _description = 'Visa Request Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('visa.request.application') or 'New', tracking=True)
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    state = fields.Selection([
        ('new', 'New'),
        ('submit', 'Submitted'),
        ('pending', 'Pending'),
        ('process', 'Processing'),
        ('complete', 'Completed'),
        ('reject', 'Rejected'),
        ('cancel', 'Cancelled')
    ], string='Status', default='new', tracking=True)
    recruitment_app_number = fields.Many2one('hr.applicant', string='Applicant', required=True, domain=lambda self: self._get_applicant_domain(), context={'show_applicant_no': True})
    employee_name = fields.Char(string='Employee Name', related='recruitment_app_number.partner_name', readonly=True)
    employee_number = fields.Char(string='Employee Number')
    job_position = fields.Many2one('hr.job', string='Job Position', related='recruitment_app_number.job_id', readonly=True)
    gender = fields.Selection(related='recruitment_app_number.gender', readonly=True, store=True,)
    business_unit = fields.Many2one('res.branch', string='Business Unit', related='recruitment_app_number.branch_id', readonly=True)
    nationality = fields.Many2one('res.country', string='Nationality', related='recruitment_app_number.country_id', readonly=True, store=True,)
    passport_number = fields.Char(string='Passport Number', related='recruitment_app_number.passport_no', readonly=True)
    passport_expiry = fields.Date(string='Passport Expiry', related='recruitment_app_number.passport_expiry_date', readonly=True)
    qid_number = fields.Char(string='QID Number', related='recruitment_app_number.qid_no', readonly=True)
    date_of_birth = fields.Date(string='Date of Birth', related='recruitment_app_number.birth_date', readonly=True)
    visa_process_type = fields.Selection([
        ('qvc', 'QVC'),
        ('non_qvc', 'NON-QVC'),
        ('change_employer', 'Change of Employer'),
        ('work_permit', 'Work Permit'),
        ('secondment', 'Secondment')], 
        string='Visa Process Type', required=True)
    
    qvc_country_id = fields.Many2one('qvc.country', string='QVC Country')
    qvc_center_id = fields.Many2one('qvc.center', string='QVC Center',
        domain="[('country_id', '=', qvc_country_id)]")
    visa_applicable = fields.Boolean(string='Visa Applicable')
    
    vp_number_id = fields.Many2one('visa.quota', string='VP Number')
    visa_profession_id = fields.Many2one(
        'visa.quota.line',
        string='VISA Profession',
        compute='_compute_available_professions',
        store=True,
        readonly=False,
        domain="[('quota_id', '=', vp_number_id), ('nationality_id', '=', nationality), ('gender', '=', gender)]"
    )
    visa_number = fields.Char(string='VISA Number', readonly=True, states={'submit': [('readonly', False)], 'complete': [('readonly', True)]})

    # QVC Process Fields
    qvc_visa_application_date = fields.Date(string='VISA Application Date', readonly=True, states={'submit': [('readonly', False)]})
    qvc_payment_date = fields.Date(string='QVC Payment Date', readonly=True, states={'submit': [('readonly', False)]})
    qvc_appointment_date = fields.Date(string='QVC Appointment Date', readonly=True, states={'submit': [('readonly', False)]})
    qvc_visa_payment_date = fields.Date(string='VISA Payment Date', readonly=True, states={'submit': [('readonly', False)]})
    qvc_visa_issue_date = fields.Date(string='VISA Issue Date', readonly=True, states={'submit': [('readonly', False)]})
    qvc_qatar_first_entry_date = fields.Date(string='Qatar First Entry Date', readonly=True, states={'submit': [('readonly', False)]})
    qvc_qid_apply_date = fields.Date(string='QID Apply Date', readonly=True, states={'submit': [('readonly', False)]})

    # Non-QVC Process Fields
    non_qvc_visa_application_date = fields.Date(string='VISA Application Date', readonly=True, states={'submit': [('readonly', False)]})
    non_qvc_visa_payment_date = fields.Date(string='VISA Payment Date', readonly=True, states={'submit': [('readonly', False)]})
    non_qvc_visa_issue_date = fields.Date(string='VISA Issue Date', readonly=True, states={'submit': [('readonly', False)]})
    non_qvc_qatar_first_entry_date = fields.Date(string='Qatar First Entry Date', readonly=True, states={'submit': [('readonly', False)]})
    non_qvc_medical_application_date = fields.Date(string='Medical Application Date', readonly=True, states={'submit': [('readonly', False)]})
    non_qvc_medical_appointment_date = fields.Date(string='Medical Appointment Date', readonly=True, states={'submit': [('readonly', False)]})
    non_qvc_fingerprint_application_date = fields.Date(string='Finger Print Application Date', readonly=True, states={'submit': [('readonly', False)]})
    non_qvc_fingerprint_appointment_date = fields.Date(string='Fingerprint Appointment Date', readonly=True, states={'submit': [('readonly', False)]})
    non_qvc_employment_contract = fields.Boolean(string='Employment Contract Attachment', readonly=True, states={'submit': [('readonly', False)]})
    non_qvc_qid_payment_date = fields.Date(string='QID Payment Date', readonly=True, states={'submit': [('readonly', False)]})

    # Change of Employer/Secondment Fields
    change_employer_noc = fields.Boolean(string='NOC', readonly=True, states={'submit': [('readonly', False)]})
    change_employer_company_documents = fields.Boolean(string='Company Documents', readonly=True, states={'submit': [('readonly', False)]})
    change_employer_application_date = fields.Date(string='Application Date', readonly=True, states={'submit': [('readonly', False)]})
    change_employer_application_no = fields.Char(string='Change of Employer Application No', readonly=True, states={'submit': [('readonly', False)]})
    change_employer_application_status = fields.Selection([
        ('approved', 'Approved'),
        ('rejected', 'Rejected')], 
        string='Application Status', readonly=True, states={'submit': [('readonly', False)]})
    change_employer_employee_contract = fields.Boolean(string='Employee Contract', readonly=True, states={'submit': [('readonly', False)]})
    change_employer_transfer_payment_date = fields.Date(string='Transfer Payment Date', readonly=True, states={'submit': [('readonly', False)]})

    # Work Permit Fields
    work_permit_photo = fields.Boolean(string='Photo', readonly=True, states={'submit': [('readonly', False)]})
    work_permit_qid = fields.Boolean(string='QID', readonly=True, states={'submit': [('readonly', False)]})
    work_permit_sponsor_id = fields.Boolean(string='Sponsor ID', readonly=True, states={'submit': [('readonly', False)]})
    work_permit_education_certificate_arabic = fields.Boolean(string='Education Certificate Arabic', readonly=True, states={'submit': [('readonly', False)]})
    work_permit_application_no = fields.Char(string='Application No', readonly=True, states={'submit': [('readonly', False)]})
    work_permit_application_date = fields.Date(string='Application Date', readonly=True, states={'submit': [('readonly', False)]})
    work_permit_pcc = fields.Boolean(string='PCC', readonly=True, states={'submit': [('readonly', False)]})
    work_permit_employee_contract = fields.Boolean(string='Employee Contract', readonly=True, states={'submit': [('readonly', False)]})
    work_permit_payment_date = fields.Date(string='Work Permit Payment Date', readonly=True, states={'submit': [('readonly', False)]})
    work_permit_validity_from = fields.Date(string='Validity From', readonly=True, states={'submit': [('readonly', False)]})
    work_permit_expiry_date = fields.Date(string='Expiry Date', readonly=True, states={'submit': [('readonly', False)]})

    days_left = fields.Integer(
        string='Days Left',
        compute='_compute_days_left',
        store=True,
        compute_sudo=True,
    )
    document_line_ids = fields.One2many(
        'visa.request.document.line',
        'visa_request_id',
        string='Applicant Documents',
        compute='_compute_applicant_details',
        store=True,
        readonly=False  
    )
    
    # Salary Lines
    salary_line_ids = fields.One2many(
        'visa.request.salary.line',
        'visa_request_id',
        string='Salary Components',
        compute='_compute_applicant_details',
        store=True,
        readonly=False  
    )

    @api.model
    def _get_applicant_domain(self):
        active_applicant_ids = self.env['visa.request.application'].search([
            ('state', 'not in', ['reject', 'cancel']),
            ('recruitment_app_number', '!=', False)
        ]).mapped('recruitment_app_number.id')
        context_applicant_id = self._context.get('default_recruitment_app_number')
        if context_applicant_id:
            active_applicant_ids = [aid for aid in active_applicant_ids if aid != context_applicant_id]
            
        return [('id', 'not in', active_applicant_ids)] if active_applicant_ids else []

    
    @api.constrains('recruitment_app_number')
    def _check_duplicate_applicant(self):
        for record in self:
            if record.state not in ['reject', 'cancel'] and record.recruitment_app_number:
                existing = self.search([
                    ('recruitment_app_number', '=', record.recruitment_app_number.id),
                    ('state', 'not in', ['reject', 'cancel']),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing:
                    raise ValidationError(
                        _("Applicant %s already has an active visa request (Reference: %s)") % 
                        (record.recruitment_app_number.display_name, existing.name)
                    )
    
    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            self.env['ir.model.fields'].clear_caches()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('visa.request.application') or 'New'
        records = super().create(vals_list)
        return records


    @api.onchange('visa_process_type')
    def _onchange_visa_process_type(self):
        if self.visa_process_type != 'qvc':
            self.qvc_country_id = False
            self.qvc_center_id = False

    @api.depends('vp_number_id', 'nationality', 'gender')
    def _compute_available_professions(self):
        for record in self:
            if not all([record.vp_number_id, record.nationality, record.gender]):
                record.visa_profession_id = False

    @api.onchange('vp_number_id')
    def _onchange_vp_number_id(self):
        if self.vp_number_id and (self.vp_number_id != self.visa_profession_id.quota_id):
            self.visa_profession_id = False

    def _update_quota_used_count(self):
        for application in self:
            if application.vp_number_id and application.nationality and application.gender:
                quota_lines = self.env['visa.quota.line'].search([
                    ('quota_id', '=', application.vp_number_id.id),  
                    ('nationality_id', '=', application.nationality.id),
                    ('gender', '=', application.gender),
                ])
                quota_lines._compute_used_count()
    
    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ['vp_number_id', 'state', 'nationality', 'gender']):
            self._update_quota_used_count()
        return res
    
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered(lambda r: r.state in ['submit','process','pending', 'complete'])._update_quota_used_count()
        return records
    

    @api.depends('non_qvc_qatar_first_entry_date', 
                 'qvc_qatar_first_entry_date', 
                 'visa_process_type')
    def _compute_days_left(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.visa_process_type == 'non_qvc' and record.non_qvc_qatar_first_entry_date:
                deadline = record.non_qvc_qatar_first_entry_date + timedelta(days=30)
                record.days_left = (deadline - today).days
            elif record.visa_process_type == 'qvc' and record.qvc_qatar_first_entry_date:
                deadline = record.qvc_qatar_first_entry_date + timedelta(days=30)
                record.days_left = (deadline - today).days
            else:
                record.days_left = 0

    def read(self, fields=None, load='_classic_read'):
        """ Override read to force recompute when record is accessed """
        self._compute_days_left()
        return super(VisaRequestApplication, self).read(fields=fields, load=load)


    # @api.depends('non_qvc_qatar_first_entry_date', 'qvc_qatar_first_entry_date', 'visa_process_type')
    # def _compute_days_left(self):
    #     today = fields.Date.today()
    #     for record in self:
    #         if record.visa_process_type == 'non_qvc' and record.non_qvc_qatar_first_entry_date:
    #             deadline = record.non_qvc_qatar_first_entry_date + timedelta(days=30)
    #             record.days_left = (deadline - today).days
    #         elif record.visa_process_type == 'qvc' and record.qvc_qatar_first_entry_date:
    #             deadline = record.qvc_qatar_first_entry_date + timedelta(days=30)
    #             record.days_left = (deadline - today).days
    #         else:
    #             record.days_left = 0


    def action_submit(self):
        for record in self:
            record.state = 'submit'
        self._update_quota_used_count()
        return True

    def action_complete(self):
        for record in self:
            record.write({
                'state': 'complete'
            })
        self._update_quota_used_count()
        return True

    def action_cancel(self):
        for record in self:
            record.state = 'cancel'
        self._update_quota_used_count()
        return True

    def action_draft(self):
        for record in self:
            record.state = 'new'
        return True
    
    def action_pending(self):
        for record in self:
            record.state = 'pending'
        self._update_quota_used_count()
        return True

    def action_process(self):
        for record in self:
            record.state = 'process'
        self._update_quota_used_count()
        return True

    def action_reject(self):
        for record in self:
            record.state = 'reject'
        self._update_quota_used_count()
        return True
    
    
    @api.depends('recruitment_app_number')
    def _compute_applicant_details(self):
        for application in self:
            if application.recruitment_app_number:
               
                document_lines = []
                for doc in application.recruitment_app_number.ducument_line_ids.filtered(lambda x: x.status == 'active'):
                    document_lines.append((0, 0, {
                        'document_type_id': doc.document_line_id.id,
                        'document_number': doc.document_number,
                        'valid_from': doc.valid_from,
                        'valid_to': doc.valid_to,
                        'issue_place': doc.doc_issue_place,
                        'status': doc.status,
                        'attachment': doc.attachment,
                        # 'source_document_id': doc.id,
                        'remarks': doc.remarks
                    }))
                application.document_line_ids = document_lines
                salary_lines = []
                for salary in application.recruitment_app_number.salary_line_ids:
                    salary_lines.append((0, 0, {
                        'salary_component_id': salary.salary_component_id.id,
                        'amount': salary.amount,
                        'currency_id': salary.currency_id.id,
                        'notes': salary.notes
                    }))
                application.salary_line_ids = salary_lines
            else:
                application.document_line_ids = False
                application.salary_line_ids = False

        
    # Override write to ensure recomputation when visa request state changes
    def write(self, vals):
        result = super(VisaRequestApplication, self).write(vals)
        if 'state' in vals:
            for record in self:
                if record.recruitment_app_number:
                    self.env['hr.applicant'].browse(record.recruitment_app_number.id)._compute_has_visa_request()
        return result
    


    @api.constrains('vp_number_id', 'nationality', 'gender', 'state')
    def _check_quota_availability(self):
        for record in self:
            if record.state in ['submit', 'process', 'complete'] and record.vp_number_id and record.nationality and record.gender:
                quota_lines = self.env['visa.quota.line'].search([
                    ('quota_id', '=', record.vp_number_id.id),
                    ('nationality_id', '=', record.nationality.id),
                    ('gender', '=', record.gender),
                ])
                
                if quota_lines:
                    total_remaining = sum(line.remaining_count for line in quota_lines)
                    if total_remaining <= 0:
                        raise ValidationError(
                            _("Visa quota has been exhausted for this nationality (%s) and gender (%s). "
                            "Total remaining count: %d") % 
                            (record.nationality.name, record.gender, total_remaining)
                        )
                else:
                    raise ValidationError(
                        _("No visa quota line found for this nationality (%s) and gender (%s).") % 
                        (record.nationality.name, record.gender)
                    )

    # @api.model_create_multi
    # def create(self, vals_list):
    #     records = super().create(vals_list)
    #     # Check quota availability for new records in relevant states
    #     for record in records:
    #         if record.state in ['submit','pending', 'process']:
    #             record._check_quota_availability()
    #     return records

    def write(self, vals):
        res = super().write(vals)
        # Check quota availability when state changes to submit/process
        if 'state' in vals and vals['state'] in ['submit', 'pending','process']:
            for record in self:
                record._check_quota_availability()
        return res



class QvcCountry(models.Model):
    _name = 'qvc.country'
    _description = 'QVC Country'
    
    name = fields.Char(string='Country Name', required=True)
    code = fields.Char(string='Country Code')
    active = fields.Boolean(string='Active', default=True)

class QvcCenter(models.Model):
    _name = 'qvc.center'
    _description = 'QVC Center'
    
    name = fields.Char(string='Center Name', required=True)
    country_id = fields.Many2one('qvc.country', string='Country', required=True)
    address = fields.Text(string='Address')
    active = fields.Boolean(string='Active', default=True)

class VisaRequestDocumentLine(models.Model):
    _name = 'visa.request.document.line'
    _description = 'Visa Request Document Line'

    visa_request_id = fields.Many2one('visa.request.application', string='Visa Request')
    document_type_id = fields.Many2one('hr.document', string='Document Type', required=True)
    document_number = fields.Char(string='Document Number')
    valid_from = fields.Date(string='Valid From')
    valid_to = fields.Date(string='Valid To')
    issue_place = fields.Char(string='Issue Place')
    status = fields.Selection([
        ('active', 'Active'),
        ('history', 'History')
    ], string='Status', default='active')
    # attachment = fields.Binary(string='Attachment', related='source_document_id.attachment', store=True)
    attachment = fields.Binary(string='Attachment')
    source_document_id = fields.Many2one('document.line', string='Source Document')
    remarks = fields.Char(string='Remarks')

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-create document in hr.applicant when new line is added"""
        records = super(VisaRequestDocumentLine, self).create(vals_list)
        
        for record in records:
            if record.visa_request_id.recruitment_app_number:
                if record.source_document_id:
                    continue
                
                existing_doc = self.env['document.line'].search([
                    ('applicant_id', '=', record.visa_request_id.recruitment_app_number.id),
                    ('document_line_id', '=', record.document_type_id.id),
                    ('document_number', '=', record.document_number),
                    ('status', '=', 'active')
                ], limit=1)
                
                if existing_doc:
                    record.write({'source_document_id': existing_doc.id})
                else:
                    new_doc = self.env['document.line'].create({
                        'applicant_id': record.visa_request_id.recruitment_app_number.id,
                        'document_line_id': record.document_type_id.id,
                        'document_number': record.document_number,
                        'valid_from': record.valid_from,
                        'valid_to': record.valid_to,
                        'doc_issue_place': record.issue_place,
                        'status': record.status,
                        'attachment': record.attachment,
                        'remarks': record.remarks,
                        'receipt_no': False,
                        'receipt_date': False,
                    })
                    record.write({'source_document_id': new_doc.id})
        
        return records
    
    def write(self, vals):
        """Auto-sync changes to hr.applicant document line"""
        result = super(VisaRequestDocumentLine, self).write(vals)
        
        for record in self:
            if record.source_document_id and record.visa_request_id.recruitment_app_number:
                update_vals = {}
                
                if 'document_type_id' in vals:
                    update_vals['document_line_id'] = record.document_type_id.id
                if 'document_number' in vals:
                    update_vals['document_number'] = record.document_number
                if 'valid_from' in vals:
                    update_vals['valid_from'] = record.valid_from
                if 'valid_to' in vals:
                    update_vals['valid_to'] = record.valid_to
                if 'issue_place' in vals:
                    update_vals['doc_issue_place'] = record.issue_place
                if 'status' in vals:
                    update_vals['status'] = record.status
                if 'attachment' in vals:
                    update_vals['attachment'] = record.attachment
                if 'remarks' in vals:
                    update_vals['remarks'] = record.remarks
                
                if update_vals:
                    record.source_document_id.write(update_vals)
        
        return result
    
    def unlink(self):
        """Mark as history in both visa request and hr.applicant"""
        for record in self:
            if record.source_document_id:
                # Mark source document as history in hr.applicant
                record.source_document_id.write({'status': 'history'})
            
            # Mark the visa request document line as history instead of deleting
            record.write({'status': 'history'})
        
        # Don't call super().unlink() if you want to keep the records as history
        # If you want to actually delete, use the code below instead
        return super(VisaRequestDocumentLine, self).unlink()


class VisaRequestSalaryLine(models.Model):
    _name = 'visa.request.salary.line'
    _description = 'Visa Request Salary Line'
    
    visa_request_id = fields.Many2one('visa.request.application', string='Visa Request')
    salary_component_id = fields.Many2one('salary.component', string='Salary Component', required=True)
    amount = fields.Float(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                default=lambda self: self.env.company.currency_id)
    notes = fields.Text(string='Notes')
    