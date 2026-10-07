from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class VisaQuota(models.Model):
    _name = 'visa.quota'
    _description = 'Visa Quota Details'
    _rec_name = 'batch_number'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    batch_number = fields.Char(string='Batch Number', readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('visa.quota') or 'New', tracking=True)
    vp_number = fields.Char(string='VP Number', required=True, tracking=True)
    visa_type_id = fields.Many2one('visa.type', string='Type of VISA', required=True, tracking=True)
    validity_from_date = fields.Date(string='Validity From Date', required=True, tracking=True)
    validity_to_date = fields.Date(string='Validity To Date', required=True, tracking=True)
    associated_to = fields.Many2one('res.partner', string='Associated To', required=True, domain=[('is_company', '=', False)], tracking=True)
    quota_line_ids = fields.One2many('visa.quota.line', 'quota_id', string='Visa Quota Lines')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('batch_number', 'New') == 'New':
                vals['batch_number'] = self.env['ir.sequence'].next_by_code('visa.quota') or 'New'
        
        records = super().create(vals_list)
        return records
    
    def name_get(self):
        result = []
        for record in self:
            name = record.vp_number
            if record.batch_number:
                name = f"{record.vp_number} ({record.batch_number})" 
            result.append((record.id, name))
        return result
        

class VisaQuotaLine(models.Model):
    _name = 'visa.quota.line'
    _description = 'Visa Quota Line Details'
    _order = 'id desc'
    _rec_name = 'profession'
    
    quota_id = fields.Many2one('visa.quota', string='Visa Quota', required=True, ondelete='cascade')
    nationality_id = fields.Many2one('res.country', string='Nationality', required=True)
    profession = fields.Char(string='VISA Profession', required=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female')
    ], string='Gender', required=True)
    approved_count = fields.Integer(string='Approved VISA Count', required=True, default=0)
    used_count = fields.Integer(string='Used VISA Count', compute='_compute_used_count', store=True)
    remaining_count = fields.Integer(string='Remaining VISA Count', compute='_compute_remaining', store=True)
    
    @api.depends('approved_count', 'used_count')
    def _compute_remaining(self):
        for line in self:
            line.remaining_count = line.approved_count - line.used_count
    

    @api.depends('quota_id', 'profession', 'nationality_id', 'gender')
    def _compute_used_count(self):
        for line in self:
            domain = [
                ('vp_number_id', '=', line.quota_id.id),
                ('visa_profession_id', '=', line.id), 
                ('nationality', '=', line.nationality_id.id),
                ('gender', '=', line.gender),
                ('state', 'in', ['submit', 'process','pending','complete']),
            ]
            line.used_count = self.env['visa.request.application'].search_count(domain)
