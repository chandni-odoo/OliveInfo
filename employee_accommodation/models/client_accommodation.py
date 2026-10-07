from odoo import models, fields, api
from datetime import datetime, timedelta


class ClientAccommodation(models.Model):
    _name = 'client.accommodation'
    _description = 'Customer Rental Contract'
    _rec_name = 'client_accommodation_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    client_accommodation_id = fields.Char(string="Accommodation ID", required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('client.accommodation'))
    sale_order_id = fields.Many2one('sale.order', string="Quotation/Sales Order", required=True)
    customer_id = fields.Many2one('res.partner', string="Customer", related='sale_order_id.partner_id', readonly=True)
    contact_number = fields.Char(string="Contact Number", related='customer_id.phone', readonly=True)
    contact_person = fields.Char(string="Contact Person",related='sale_order_id.contact_name', readonly=True )
    rental_date = fields.Date(string="Agreement Date", required=True)
    payment_terms = fields.Many2one('account.payment.term', string="Payment Terms", related='sale_order_id.payment_term_id', readonly=True)
    start_date = fields.Date(string="Start Date", related='sale_order_id.start_date', required=True)
    end_date = fields.Date(string="End Date", related='sale_order_id.end_date')
    terms_conditions = fields.Many2one("terms.condition", string="Terms and Conditions", related='sale_order_id.terms_id', readonly=True)
    description = fields.Html(string="Description", related='terms_conditions.description', readonly=True)
    notes = fields.Html(string="Notes")
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id.id)
    rental_type = fields.Selection([
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string="Rental Type", required=True, default='monthly')
    maintenance_by = fields.Selection([
        ('landlord', 'Landlord'),
        ('tenant', 'Tenant')
    ], string="Maintenance By", required=True, default='landlord')
    signed_by = fields.Char(string="Signed by")
    designation = fields.Char(string="Designation")
    unit_type = fields.Selection([('camp', 'Camp'), ('floor', 'Floor'), ('room', 'Room'), ('bed', 'Bed')], string="Unit Type")
    camp_id = fields.Many2one('accommodation.camp', string="Camp", domain=[('status', '=', 'active')])
    allowed_people = fields.Integer(string="Allowed People")
    num_of_units = fields.Integer(string="No. of Units", required=True)
    room_type_ids = fields.Many2many(
        'room.type', 
        string="Room Types"
    )
    with_facilities = fields.Boolean(string="With Facilities")
    facilities = fields.Many2many("accommodation.facility", string="Assigned Items", domain="[('state', '=', 'available')]")
    rate_unit = fields.Monetary(string="Rate per Unit")
    rental_amount = fields.Monetary(string="Rental Amount", compute="_compute_rental_amount", store=True)
    product_ids = fields.One2many('lease.agreement.line', 'lease_id', string="Lease Products")
    
    @api.depends('num_of_units', 'rate_unit')
    def _compute_rental_amount(self):
        for record in self:
            record.rental_amount = record.num_of_units * record.rate_unit
            
    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        for record in self:
            if record.sale_order_id:
                record.product_ids = [(5, 0, 0)]
                products = []
                for line in record.sale_order_id.order_line:
                    products.append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'quantity': line.product_uom_qty,
                        'price_unit': line.price_unit,
                        'product_uom': line.product_uom.id,
                        'currency_id': line.currency_id.id,
                    }))
                record.product_ids = products

    def _notify_tenancy_expiry(self):
        today = fields.Date.today()
        notification_days = 60  
        missed_days = 5  

        notification_target_date = today + timedelta(days=notification_days)  
        missed_start_date = notification_target_date - timedelta(days=missed_days)  

        contracts = self.search([
            ('end_date', '>=', missed_start_date),
            ('end_date', '<=', notification_target_date)  
        ])

        if contracts:
            notification_user = self.env.ref('employee_accommodation.tenancy_contract_notification_alert').users
            for contract in contracts:
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', contract.id),
                    ('res_model', '=', self._name),
                    ('summary', '=', 'Tenancy Contract Expiry')
                ], limit=1)

                if not existing_activity:
                    contract.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=notification_user.id,
                        note=f"The tenancy contract for {contract.customer_id.name} is expiring on {contract.end_date}.",
                        summary="Tenancy Contract Expiry"
                    )

class LeaseAgreementLine(models.Model):
    _name = 'lease.agreement.line'
    _description = 'Lease Agreement Line'

    lease_id = fields.Many2one('client.accommodation', string="Lease Agreement")
    product_id = fields.Many2one('product.product', string="Product")
    name = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity")
    price_unit = fields.Float(string="Unit Price")
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    currency_id = fields.Many2one('res.currency', string="Currency")

    
    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.amount = line.quantity * line.unit_price
            
            
            
class RoomType(models.Model):
    _name = 'room.type'
    _description = 'Room Type'

    name = fields.Char(string="Room Type", required=True)
    

