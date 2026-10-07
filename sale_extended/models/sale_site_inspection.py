from odoo import models, fields, api, _


class SaleSiteInspection(models.Model):
    _name = 'sale.site.inspection'
    _description = "Sale Site Inspection"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(readonly=True, default="New")
    branch_id = fields.Many2one('res.branch', string="Branch")
    customer_id  = fields.Char(related="company_id.address_no", string="Code")
    date = fields.Date(string="Date", required=True)
    company_id = fields.Many2one('res.partner', string="Company Name", required=True)
    # location_id = fields.Many2one('res.partner', string='Location')
    partner_location_id = fields.Many2one('contact.location', string='Location')
    contact_person_id = fields.Many2one("res.partner", string="Contact Person")
    mobile = fields.Char(string="Mobile")
    email = fields.Char(string="Email")
    no_of_manpower = fields.Char(string="No. of Manpower", default="1")
    nature_of_business  = fields.Char(string="Nature of Business")
    job_id  = fields.Char(string="Nature of Job")
    hazard_id = fields.Char(string="Hazards at Site")
    job_nature = fields.Char(string="Job Nature & Hazard Briefing to Employees")
    ppe_requirement = fields.Char(string="PPE Requirements")
    # availability  = fields.Char(string="Availability of at site")
    is_first_aid = fields.Boolean(string="First Aid")
    is_drinking_water = fields.Boolean(string="Drinking Water")
    is_resting_area  = fields.Boolean(string="Resting Area")
    additional_info  = fields.Char(string="Additional Information")
    other_competator = fields.Char(string="Any other Competitor")
    no_of_workers = fields.Integer('No. of Men working', default="1")
    salary_range = fields.Char("Salary Range")
    note = fields.Char(string="Comments/Notes")
    prepared_id = fields.Many2one('res.users', string="Prepared By", default=lambda self: self.env.user)
    verified_id = fields.Many2one('res.users', string="Verified By")
    approved_id = fields.Many2one('res.users', string="Approved By")
    assign_id = fields.Many2one('res.users', string="Assigned to")
    sale_id = fields.Many2one('sale.order')
    latitude = fields.Float('Geo Latitude', digits=(10, 7))
    longitude = fields.Float('Geo Longitude', digits=(10, 7))

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('sale.site.inspection') or _('New')
        return super(SaleSiteInspection, self).create(vals)
    
    def write(self, vals):
        res = super(SaleSiteInspection, self).write(vals)

        model_id = self.env['ir.model'].sudo().search([('model', '=', 'sale.site.inspection')], limit=1)
        activity_vals = {'res_model_id': model_id.id,
                         'res_model': 'sale.site.inspection',
                         'res_id': self.id,
                         'res_name': 'Site Inspection Updated Please Check!!!',
                         'user_id': self.sale_id.user_id.id,
                         # 'activity_type_id': contract_approval_id.activity_type_id.id,
                         'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')}
        activity_id = self.env['mail.activity'].create(activity_vals)
        print('activity_id++++++++++++++', activity_id)

        return res
