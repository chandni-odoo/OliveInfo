from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    site_visit_id = fields.Many2one('site.visit')


class SiteVisit(models.Model):
    _name = 'site.visit'
    _description = "Site Visit"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(readonly=True, default="New")
    date = fields.Date(string="Date", required=True)
    partner_id = fields.Many2one('res.partner', string="Client Name", required=True)
    customer_id = fields.Char(related="partner_id.address_no", string="Code")
    # location_id = fields.Many2one('res.partner', string="Location")
    location_id = fields.Many2one('contact.location', string="Location")
    nature_of_business = fields.Text(string="Nature of Business")
    number_of_units = fields.Text(string="Number of Units/Floors")
    waste_type_ids = fields.Many2many('waste.type', string="Type of Waste")
    product_id = fields.Many2many('product.product', string="Type of Waste")
    of_bins = fields.Float(string="Number of Bins")
    # size_of_bins = fields.Float(string="Size of Bins")
    equipment_type_ids = fields.Many2many('equipment.type', string="Size of Bins.")
    collection_type = fields.Selection(
        [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('on_call', 'On Call')], default='daily')
    no_of_loads = fields.Float(string="No. of Loads/Month")
    collection_frequency = fields.Char()
    # collection_frequency = fields.Many2one('so.frequency') #BLUESTAR
    preferred_timing = fields.Char()
    # vehicle_ids = fields.Many2many('fleet.vehicle')
    vehicle_ids = fields.Many2many('vehicle.type')
    lead_id = fields.Many2one('crm.lead')
    operations = fields.Text(string="Operation Remarks")
    attachment_ids = fields.One2many("ir.attachment", 'site_visit_id')
    branch_id = fields.Many2one('res.branch', string="Branch")
    latitude = fields.Float('Geo Latitude', digits=(10, 7))
    longitude = fields.Float('Geo Longitude', digits=(10, 7))
    prepared_id = fields.Many2one('res.users', string="Prepared By", default=lambda self: self.env.user)

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('site.visit') or _('New')
        return super(SiteVisit, self).create(vals)
