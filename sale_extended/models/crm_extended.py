# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    service_ids = fields.One2many("crm.service.line", 'lead_id')
    branch_for = fields.Selection(related='branch_id.branch_for')
    site_count = fields.Integer(compute='_site_count', string='Site Visit')
    food = fields.Boolean('Food')
    accommodation = fields.Boolean('Accommodation')
    transport = fields.Boolean('Transport')
    fat = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='FAT', readonly=True, default=True,
                           compute="_compute_fat")
    customer_id = fields.Char(related="partner_id.address_no", string="Customer")
    credit_limit = fields.Float(related="partner_id.credit_limit", string="Credit Limit")
    ava_credit_bal = fields.Float(related="partner_id.ava_credit_bal", string="Available Balance")

    # Point no 10 PS2
    select_sub_contact = fields.Many2one('res.partner', string="Sub Contact")
    contact_name = fields.Char(
        'Contact Name', tracking=30,
        compute='_compute_contact_name', readonly=False, store=True)

    email_from = fields.Char('Email', tracking=40, index=True, related='select_sub_contact.email', readonly=False, store=True)
    phone = fields.Char('Phone', tracking=50, related='select_sub_contact.phone', readonly=False, store=True)
    mobile = fields.Char('Mobile', related='select_sub_contact.mobile', readonly=False, store=True)
    function = fields.Char('Job Position', related='select_sub_contact.function', readonly=False, store=True)


    @api.depends('select_sub_contact')
    def _compute_contact_name(self):
        """ compute the new values when partner_id has changed """
        for lead in self:
            lead.update(lead._prepare_contact_name_from_partner(lead.select_sub_contact))

    @api.depends('food', 'accommodation', 'transport')
    def _compute_fat(self):
        for rec in self:
            if rec.food or rec.accommodation or rec.transport:
                rec.fat = 'yes'
            else:
                rec.fat = 'no'

    def _site_count(self):
        for rec in self:
            site_ids = self.env['site.visit'].search([('lead_id', '=', rec.id)])
            rec.site_count = len(site_ids.ids)

    def site_visits(self):
        sites = self.env['site.visit'].search([('lead_id', '=', self.id)])
        return {
            'name': _('Site Visit'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'site.visit',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', sites.ids)],
        }

    def create_site_visit(self):
        for record  in self :
            if record.branch_for == 'es':
                print ("This _____ES___________")
                return {
                    'name': ('Site Visit'),
                    'res_model': 'site.visit',
                    'type': 'ir.actions.act_window',
                    'context': {
                        'default_lead_id': self.id,
                        'default_partner_id': self.partner_id.id,
                        'default_branch_id': self.branch_id.id,
                    },
                    'view_mode': 'form',
                    'view_type': 'form',
                    'view_id': self.env.ref("sale_extended.site_visit_form_view").id,
                }


    def action_sale_quotations_new(self):
        res = super(CrmLead, self).action_sale_quotations_new()
        if not self.partner_id:
            res = self.action_new_quotation()
        return res

    def action_new_quotation(self):
        res = super(CrmLead, self).action_new_quotation()
        order_line = []
        for line in self.service_ids:
            order_line.append([0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'product_uom': line.product_uom.id,
                'product_uom_qty': line.product_uom_qty,
                'waste_type_id': line.waste_type_id.id,
                'equipment_type_id': line.equipment_type_id.id,
                'vehicle_type_id': line.vehicle_type_id.id,
                # 'frequency': line.frequency,
                'trip_no': line.trip_no,
                'weekday': line.weekday,
                'time': line.time,
                # 'location_id': line.location_id.id,
                'std_hrs': line.std_hrs,
                'overtime': line.ot_hrs,
                'start_date': line.start_date,
                'end_date': line.end_date,
                'partner_location_id': line.location_id.id,

            }])
        if self.branch_id:
            res.get('context').update({'default_branch_id': self.branch_id.id})
        if self.accommodation:
            res.get('context').update({'default_accommodation': self.accommodation})
        if self.food:
            res.get('context').update({'default_food': self.food})
        if self.transport:
            res.get('context').update({'default_transport': self.transport})
        if order_line:
            res.get('context').update({'default_order_line': order_line})
        if self.contact_name:
            res.get('context').update({'default_contact_name': self.contact_name})
        if self.mobile:
            res.get('context').update({'default_mobile': self.mobile})
        if self.email_from:
            res.get('context').update({'default_email': self.email_from})
        return res

    def _create_customer(self):
        """ Create a partner from lead data and link it to the lead.

        :return: newly-created partner browse record
        """
        Partner = self.env['res.partner']
        contact_name = self.contact_name
        if not contact_name:
            contact_name = Partner._parse_partner_name(self.email_from)[0] if self.email_from else False

        if self.partner_name:
            partner_company = Partner.create(self._prepare_customer_values(self.partner_name, is_company=True))
        elif self.partner_id:
            partner_company = self.partner_id
        else:
            partner_company = None

        if partner_company:
            return partner_company

        if contact_name:
            return Partner.create(self._prepare_customer_values(contact_name, is_company=False,
                                                                parent_id=partner_company.id if partner_company else False))
        return Partner.create(self._prepare_customer_values(self.name, is_company=False))


class CrmServiceLine(models.Model):
    _name = 'crm.service.line'
    _description = "Crm Lead Lines Info"

    lead_id = fields.Many2one('crm.lead')
    product_id = fields.Many2one('product.product', string="Service Name")
    product_uom_qty = fields.Float(string="Quantity", default='1.0',
                                   help=" Quantity  can be   No. of Trips , No. of Loads , No. of Bin Lift , Weight in KG , No. of Gallon , No of Hrs. etc…")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    skills = fields.Many2many('hr.employee.skill', string="Skills")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom = fields.Many2one('uom.uom', string='UoM', required=True,
                                  domain="[('category_id', '=', product_uom_category_id)]")
    fleet_type = fields.Char(string="Fleet Type")
    frequency = fields.Selection(
        [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('on_call', 'On Call')], default='daily',
        string="Freq")
    trip_no = fields.Float(string="No Of Trip")
    weekday = fields.Selection(
        [('1', 'Monday'), ('2', 'Tuesday'), ('3', 'Wednesday'), ('4', 'Thursday'), ('5', 'Friday'), ('6', 'Saturday'),
         ('7', 'Sunday'), ], string='Day Name', required=True, default='1')
    time = fields.Char(string="Time")
    std_hrs = fields.Float(string="Std hrs")
    ot_hrs = fields.Float(string="OT hrs")
    waste_type_id = fields.Many2one('waste.type')
    equipment_type_id = fields.Many2one('equipment.type', string="Eqpt Type")
    vehicle_type_id = fields.Many2one('vehicle.type', string="Vehicle Type")
    # location_id = fields.Many2one('res.partner', string="Location")
    location_id = fields.Many2one('contact.location', string="Location")
    frequency_id = fields.Many2one('so.frequency', string="Frequency")
