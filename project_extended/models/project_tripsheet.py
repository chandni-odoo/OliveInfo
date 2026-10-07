from odoo import api, fields, models, _


class TripSheet(models.Model):
    _name = "trip.sheet"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Trip Sheet"

    trip_sequence = fields.Char(default="New", readonly=True, copy=False)
    status = fields.Selection([('new', 'New'), ('old', 'Old')], string="Status")
    type_of_waste = fields.Selection([('solid', 'Solid'), ('liquid', 'Liquid')], default='solid' ,string="Type Of Waste")
    type_of_sheet = fields.Selection([('normal', 'Normal'), ('compactor', 'Compactor'), ('hazardous', 'Hazardous')], default='normal', string="Type Of Sheet")
    date = fields.Date()
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    project_task = fields.Many2one('project.task', string="Task")
    project = fields.Many2one('project.project', string="Project")
    driver_id = fields.Many2one('res.partner', string="Driver")
    client_id = fields.Many2one('res.partner', string="Client")
    helper_code= fields.Many2one('res.partner', string="Helper")
    km = fields.Float(string="KM")
    equipment_no = fields.Char(string="Equipment No.")
    collection_no = fields.Char(string="Collection No.")
    non_billable = fields.Boolean(string="Non-billable")
    reason_of_cancle = fields.Text(string="Reason of cancel")
    state = fields.Selection([
        ('draft', 'Draft'), 
        ('reschedule', 'Reschedule'),
        ('done', 'Done'), 
        ('cancel', 'Cancel')], default='draft')
    location_from = fields.Char(string="Location From")
    location_to = fields.Char(string="Location To")
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    client_no = fields.Char(string="Client No")
    client_signature = fields.Char(string="Client Signature")
    driver_name = fields.Char(string="Driver Name")
    driver_id = fields.Char(string="Driver Id")
    helper_name = fields.Char(string="Helper Name name")
    helper_id = fields.Char(string="Helper Id")
    skip_delivered_ids = fields.One2many('skip.delivered', 'trip_id', string="Skip Delivered")
    skip_collected_ids = fields.One2many('skip.collected', 'trip_id', string="Skip Collected")
    material_detail_ids = fields.One2many('material.details', 'trip_id', string="Material Details")
    transporters_details_ids = fields.One2many('transporters.details', 'trip_id', string="Transporters Details")
    note = fields.Text(string="Note")
    attachment_ids = fields.Many2many("ir.attachment")
    order_id = fields.Many2one('sale.order', string="sale order")

    @api.model
    def create(self, vals):
        if vals.get('trip_sequence', 'New') == 'New':
            vals['trip_sequence'] = self.env['ir.sequence'].next_by_code('trip.sheet') or '/'
        return super(TripSheet, self).create(vals)

    def button_complete(self):
        print("hello Complete")
        self.write({'state': 'done'})
        return True
    def button_reschedule(self):    
        print("hello reschedule")   
        self.write({'state': 'reschedule'})
        return True  
    def button_cancel(self):
        print("hello Cancel")
        self.write({'state': 'cancel'})
        return True
        

class SkipDelivered(models.Model):
    _name = "skip.delivered"
    _description = "Skip Delivered"

    trip_id = fields.Many2one('trip.sheet', string="Trip")
    date = fields.Date(string="Date")
    skip_no = fields.Char(string="Skip No")
    size = fields.Char(string="Size")
    qty = fields.Float(string="Qty")
    unit = fields.Many2one('uom.uom', string='Unit')


class SkipCollected(models.Model):
    _name = "skip.collected"
    _description = "Skip collected"

    trip_id = fields.Many2one('trip.sheet', string="Trip")
    date = fields.Date(string="Date")
    skip_no = fields.Char(string="Skip No")
    size = fields.Char(string="Size")
    qty = fields.Float(string="Qty")
    unit = fields.Many2one('uom.uom', string='Unit')

class SkipCollected(models.Model):
    _name = "skip.collected"
    _description = "Skip collected"

    trip_id = fields.Many2one('trip.sheet', string="Trip")
    skip_no = fields.Char(string="Skip No")
    size = fields.Char(string="Size")
    qty = fields.Float(string="Qty")
    unit = fields.Many2one('uom.uom', string='Unit')

class MaterialDetail(models.Model):
    _name = "material.details"
    _description = "Material Details"

    trip_id = fields.Many2one('trip.sheet', string="Trip")
    name = fields.Char(string="Shipping Name")
    nos = fields.Char(string="Nos")
    material_type = fields.Char(string="Type")
    grosswt = fields.Float(string="Gross WT")
    tarewt = fields.Float(string="Tare WT")
    netwt = fields.Float(string="Net WT")

class TransportersDetails(models.Model):
    _name = "transporters.details"
    _description = "Transporters Details"

    trip_id = fields.Many2one('trip.sheet', string="Trip")
    name = fields.Char(string="Name")
    telephone_no = fields.Char(string="Telephone No")
    truck_no = fields.Char(string="Truck Plate No")
    