# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import ValidationError
from datetime import datetime


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    # def _compute_coll_del_status(self):
    #     for rec in self:
    #         if len(rec.skip_load_ids.ids) > 0:
    #             loader_id = self.env['skip.loader'].search([('id', 'in', rec.skip_load_ids.ids)], limit=1,
    #                                                        order="id desc")
    #             if loader_id and loader_id.coll_del:
    #                 rec.write({'coll_del_status': loader_id.coll_del, 'task_id': loader_id.task_id.id})
    #         # else:
    #             # rec.write({'coll_del_status': 'collection'})

    size = fields.Char(string="Size")
    skip_load_ids = fields.One2many('skip.loader', 'maintenance_equ_id', string="Skip loder")
    coll_del_status = fields.Selection([('collection', 'Available'), ('delivery', 'Not Available')],
                                       string="Collection/Delivery")#, compute="_compute_coll_del_status")
    task_id = fields.Many2one('project.task', string="Task")


class SkipLoader(models.Model):
    _name = "skip.loader"
    _order = 'id desc'

    @api.onchange('tare_wt', 'gross_wt')
    def _onchange_net_wt(self):
        for rec in self:
            rec.net_wt = rec.gross_wt - rec.tare_wt

    @api.onchange('coll_del')
    def _onchange_coll_del(self):
        if self.trip_id.task_id and self.coll_del == 'collection':
            loader_ids = self.env['maintenance.equipment'].search([('task_id', '=', self.trip_id.task_id.id)]).filtered(
                lambda x: x.coll_del_status == 'delivery')
            return {'domain': {'maintenance_equ_id': [('id', 'in', loader_ids.ids)]}}
        elif self.trip_id.task_id and self.coll_del == 'delivery':
            loader_ids = self.env['maintenance.equipment'].search(
                [('equipment_type_id', '=', self.trip_id.equipment_type_id.id), ('coll_del_status', '=', 'collection')])
            return {'domain': {'maintenance_equ_id': [
                ('id', 'in', loader_ids.filtered(lambda a: a.coll_del_status == 'collection').ids)]}}
        else:
            loader_ids = self.env['maintenance.equipment'].search(
                [('equipment_type_id', '=', self.trip_id.equipment_type_id.id), ('coll_del_status', '=', 'collection')])
            return {'domain': {'maintenance_equ_id': [('id', 'in', loader_ids.ids)]}}

    # equipment_line_id = fields.Many2one('maintenance.equipment', string="Maintenance Equipment Trip line")
    trip_id = fields.Many2one('custom.trip.sheet', string="Trip")
    slh = fields.Selection([('shl', 'SHL'), ('tnk', 'TNK'), ('hzw', 'HZW'), ('mw', 'MW')], string="SHL")
    coll_del = fields.Selection(
        [('collection', 'Collection'), ('delivery', 'Delivery'), ('visit', 'Visit'), ('lift', 'Lift')],
        string="Collection/Delivery", default="collection")
    haz_material = fields.Selection(
        [('carbon', 'Carbon Waste'), ('medical', 'Medical Waste'), ('chemical', 'Chemical Waste')],
        string="Shipping Name/Type/Hazardous Material")
    packing = fields.Selection([('box', 'Boxes'), ('bag', 'Bags'), ('container', 'Container')], string="Packing")
    skip_no = fields.Char(string="Skip No")
    skip_size = fields.Char(string="Skip Size")
    qty = fields.Float(string="Billable Qty")
    equipment_qty = fields.Float(string="Equipment Qty")
    so_equipment_qty = fields.Float(string="So Equipment Qty", compute="_compute_so_equipment_qty")
    unit_id = fields.Many2one('uom.uom', string='UOM', readonly=True,
                              related="trip_id.task_id.sale_line_id.product_uom")
    gross_wt = fields.Float(string="Gross Wt")
    tare_wt = fields.Float(string="Tare Wt")
    net_wt = fields.Float(string="Net Wt")
    nos = fields.Integer(string="Nos.")
    kg = fields.Integer(string="Kg")
    volume = fields.Integer(string="CBM/Volume")
    maintenance_equ_id = fields.Many2one('maintenance.equipment', string="Equipment Skip Nos", domain="[('category_id', '=', 'Skip')]")
    maintenance_equipment_ids = fields.Many2many(
        "maintenance.equipment",
        "skip_loader_maintenance_equipment_rel",
        "loader_id", "equipment_id",
        string="Equipment Type"
    )
    size = fields.Char(string="Size", related="maintenance_equ_id.size", readonly="1")
    task_id = fields.Many2one('project.task', string="Task", related="trip_id.task_id")
    customer_id = fields.Many2one('res.partner', string="Customer", related="task_id.partner_id")
    vehicle_type_id = fields.Many2one('vehicle.type', string="Vehicle Type.", related="task_id.vehicle_type_id")
    driver_id = fields.Many2one('hr.employee', string="Driver", domain="[('is_driver','=', True)]",
                                related="trip_id.driver_id")
    vehicle_no_id = fields.Many2one('fleet.vehicle', string="Vehicle No.", related="trip_id.vehicle_no_id")
    date_from = fields.Datetime(string="Date", related="trip_id.date_from")
    partner_location_id = fields.Many2one('contact.location', string="Location", related="trip_id.site", readonly="1")
    billable = fields.Boolean(string="Billable", default=True)

    # @api.depends('maintenance_equipment_ids.size')
    # def _compute_size(self):
    #     for record in self:
    #         # Convert non-string values (like False) to an empty string
    #         sizes = [str(size) for size in record.maintenance_equipment_ids.mapped('size') if size]
    #         record.size = ", ".join(sizes)

    @api.onchange('coll_del')
    def coll_del_onchange(self):
        for loder_id in self:
            if loder_id.coll_del == 'collection':
                loder_id.billable = True
            else:
                loder_id.billable = False

    def _compute_so_equipment_qty(self):
        for loder_id in self:
            loder_id.so_equipment_qty = 0
            if loder_id.task_id and loder_id.equipment_qty > 0:
                loder_id.so_equipment_qty = loder_id.equipment_qty - loder_id.task_id.sale_line_id.equipment_qty

    def write(self, vals):

        timesheet = self.env['account.analytic.line'].search([('tripsheet_custom_id', '=', self.trip_id.id)])

        res = super(SkipLoader, self).write(vals)

        total_hrs = sum(self.trip_id.skip_load_ids.mapped('qty'))
        equipment_qty = sum(self.trip_id.skip_load_ids.mapped('equipment_qty'))
        timesheet.update({
            'units_amounts': total_hrs,
            'unit_amount': equipment_qty,
        })

        return res


class CompactorTripSheet(models.Model):
    _name = "compactor.trip.sheet"

    compactor_trip_id = fields.Many2one('custom.trip.sheet', string="Trip")
    date_from = fields.Datetime(string="Date From")
    date_to = fields.Datetime(string="Date To")
    driver_id = fields.Many2one('hr.employee', string="Driver", domain="[('is_driver','=', True)]")
    helper_ids = fields.Many2many('hr.employee', string="Helper", domain="[('is_helper','=', True)]")
    maintenance_equ_id = fields.Many2one('maintenance.equipment', string="Skip Nos")
    maintenance_equipment_ids = fields.Many2many(
        "maintenance.equipment",
        "compactor_maintenance_equipment_rel",
        "trip_sheet_id", "equipment_id",
        string="Equipment Type"
    )
    size = fields.Char(string="Size", compute="_compute_size", store=True, readonly="1")
    # bin_size = fields.Char(string="Skip/Bin Size")
    bin_lift = fields.Integer(string="Billable Qty")  # update the string of bin lift field
    billable_qty = fields.Integer(string="Bin Lift/Collection")
    weight = fields.Integer(string="Weight")
    cbm = fields.Integer(string="CBM")
    billable = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Billable", default="yes")
    reason = fields.Text(string="Reason")
    remark = fields.Text(string="Remark")
    trip_type = fields.Selection([('trip', 'Trip'), ('visit', 'Visit')], string="Type", default="trip")
    landfill = fields.Selection([('mesaid', 'Mesaid Yard'), ('dulsco', 'Dulsco Yard')], string="Landfill")
    equipment_qty = fields.Float(string="Equipment Qty")
    so_equipment_qty = fields.Float(string="So Equipment Qty", compute="_compute_so_equipment_qty")

    @api.depends('maintenance_equipment_ids.size')
    def _compute_size(self):
        for record in self:
            # Convert non-string values (like False) to an empty string
            sizes = [str(size) for size in record.maintenance_equipment_ids.mapped('size') if size]
            record.size = ", ".join(sizes)

    def _compute_so_equipment_qty(self):
        for loder_id in self:
            loder_id.so_equipment_qty = 0
            if loder_id.compactor_trip_id.task_id and loder_id.equipment_qty > 0:
                loder_id.so_equipment_qty = loder_id.equipment_qty - loder_id.compactor_trip_id.task_id.sale_line_id.equipment_qty

    def unlink(self):
        for res in self:
            timesheet = self.env['account.analytic.line'].search([('tripsheet_compactor_id', '=', res.id)])
            for time in timesheet:
                time.unlink()
        return super(CompactorTripSheet, self).unlink()

    def write(self, vals):
        res = super(CompactorTripSheet, self).write(vals)

        units_amounts = sum(
            self.compactor_trip_id.compactor_trip_ids.filtered(lambda a: a.billable == 'yes').mapped('bin_lift'))
        new_vals = {
            'date': datetime.strftime(self.date_from, '%Y-%m-%d'),
            'employee_id': self.driver_id.id,
            'unit_amount': self.bin_lift,
            'units_amounts': units_amounts,
        }

        timesheet = self.env['account.analytic.line'].search([('tripsheet_compactor_id', '=', self.id)])
        timesheet.update(new_vals)

        for compact_line in self.compactor_trip_id.compactor_trip_ids:
            timesheet = self.env['account.analytic.line'].search([('tripsheet_compactor_id', '=', compact_line.id)])
            timesheet.update({
                'units_amounts': units_amounts
            })

        return res


class SkipNo(models.Model):
    _name = "skip.no"

    name = fields.Char(string="Name")
    equipment_qty = fields.Float(string="Equipment Qty")


class Timesheet(models.Model):
    _inherit = "account.analytic.line"

    tripsheet_compactor_id = fields.Many2one('compactor.trip.sheet', string="Compactor ID")
    tripsheet_custom_id = fields.Many2one('custom.trip.sheet', string="Custom Id")


class CustomTripSheet(models.Model):
    _name = "custom.trip.sheet"
    _rec_name = 'sequence'

    # def _get_skip_no(self):
    #     for rec in self.skip_ids:
    #         rec.skip_no = len(rec.ids)

    def _compute_task_collection(self):
        self.is_collection = False
        if self.task_id:
            skip_loder_ids = self.env['skip.loader'].search(
                [('task_id', '=', self.task_id), ('coll_del', '=', 'delivery')])
            if len(skip_loder_ids.ids) > 0:
                self.is_collection = True

    landfill = fields.Selection([('mesaid', 'Mesaid Yard'), ('dulsco', 'Dulsco Yard')], string="Landfill")
    sequence = fields.Char(string="Sequence")
    req_seq = fields.Char(string="Reqn No")
    trip_type = fields.Selection([('trip', 'Trip'), ('visit', 'Visit'), ('delivery','Delivery')], default='trip', string="Type", store=True)
    date = fields.Date('Date', default=fields.date.today())
    site = fields.Many2one('contact.location', string="Location", related="task_id.partner_location_id", readonly="1")
    vendor_name = fields.Many2one('res.partner', string="Vendor Name(OutSourced)", related="task_id.vendor_name_id")
    treatment_company = fields.Many2one('res.partner', string="Treatment Company",
                                        related="task_id.treatment_company_id")
    auth_person = fields.Many2one('res.partner', string="Authorised Person")
    weight = fields.Float(string='Weight')
    customer_id = fields.Many2one('res.partner', string="Customer", related="task_id.partner_id", store=True)
    vehicle_no_id = fields.Many2one('fleet.vehicle', string="Vehicle No.", store=True)
    trailer_no_id = fields.Many2one('fleet.vehicle', string="Trailer No.", domain="[('is_trailer','=', True)]")
    task_id = fields.Many2one('project.task', string="Task")
    waste_type_id = fields.Many2one('waste.type', related="task_id.waste_type_id")
    compactor = fields.Boolean(string="Compactor Tripsheet", readonly='False', related="vehicle_type_id.compactor")
    driver_id = fields.Many2one('hr.employee', string="Driver", domain="[('is_driver','=', True)]", store=True)
    helper_ids = fields.Many2many('hr.employee', string="Helper", domain="[('is_helper','=', True)]")
    km = fields.Float(string="KM")
    equipment_type_id = fields.Many2one('equipment.type', string="Equipment Type.", related="task_id.equipment_type_id")
    vehicle_type_id = fields.Many2one('vehicle.type', string="Vehicle Type.", related="task_id.vehicle_type_id")
    non_billable = fields.Boolean(string="Non-billable")
    signature = fields.Binary(string="Signature")
    reason = fields.Text(string="Reason")
    km_from = fields.Char(string="Km")
    km_to = fields.Char(string="Km To")
    date_from = fields.Datetime(string="Date")
    date_to = fields.Datetime(string="Date To")
    skip_load_ids = fields.One2many('skip.loader', 'trip_id', string="Skip")
    compactor_trip_ids = fields.One2many('compactor.trip.sheet', 'compactor_trip_id', string="Compactor Trip")
    reason = fields.Text(string="Reason")
    mobile = fields.Char(string="Mobile No.")
    remark = fields.Text(string="Remark")
    # order_id = fields.Many2one('sale.order', string="sale order")
    skip_ids = fields.Many2many('skip.no', string="Skip Nos.")
    skip_no = fields.Integer(string="No. Skips")
    is_record_readonly = fields.Boolean(string="Is Readonly")
    maintenance_equ_id = fields.Many2one('maintenance.equipment', string="Customer")
    maintenance_equipment_ids = fields.Many2many('maintenance.equipment', 'maintenance_equipment_trip_rel', 'equipment_id', 'trip_id', string="Customer")
    size = fields.Char(string="Size", related="maintenance_equ_id.size")
    is_collection = fields.Boolean(string="Collection", compute="_compute_task_collection")
    equipment_qty = fields.Float(string="Equipment Qty", compute='compute_equipment_qty')
    invoice_id = fields.Many2one('account.move', string="Invoice", readonly=True)
    stage = fields.Selection(
        [('draft', 'Draft'), ('done', 'Completed'), ('completed', 'Done'),
          ('cancel', 'Cancel'), ('hold', 'Hold')],
        string="Stage", default='draft', copy=False)
    attachment_id = fields.Binary(string="Attachment")

    billable_qty = fields.Integer(string="Billable Qty", compute="_compute_billable_qty")
    additional_on_call = fields.Boolean(string="Additional On Call?")
    call_date = fields.Datetime(string="Call Date")
    requested_by = fields.Char(string="Requested By")
    on_call = fields.Boolean(string="On Call", default=False)
    # partner_id = fields.Many2one('res.partner', string="Partner",related="customer_id", store=True)
    partner_id = fields.Many2one(
        'res.partner', 
        string="Partner",
        compute='_compute_partner_id',
        store=True,
        readonly=False
    )

    vehicle_type_from_vehicle = fields.Many2one(
        'vehicle.type', 
        string="Vehicle Type", 
        related='vehicle_no_id.vehicle_type_id', 
        store=True, 
        readonly=True
    )

    @api.depends('customer_id')
    def _compute_partner_id(self):
        for record in self:
            if record.customer_id:
                record.partner_id = record.customer_id

    task_seq_code = fields.Char(
        string="Task Sequence", 
        related="task_id.seq_code", 
        store=True
    )
    
    sale_order_id = fields.Many2one(
        'sale.order', 
        string="Sale Order", 
        related="task_id.sale_line_id.order_id", 
        store=True
    )


    _sql_constraints = [
        ('req_seq_unique',
         'unique(req_seq)',
         'Tripsheet No Has to be Unique!')
    ]

    # @api.constrains("req_seq")
    # def check_req_seqn(self):
    #     """Method to check duration should be greater than zero"""
    #     record_id = self.search([('req_seq', '=', self.req_seq), ('id', '!=', self.id)])
    #     if len(record_id.ids) > 0:
    #         raise ValidationError(_("Tripsheet No Has to be Unique!"))

        


    # @api.depends('maintenance_equipment_ids.size')
    # def _compute_size(self):
    #     for record in self:
    #         # Convert non-string values (like False) to an empty string
    #         sizes = [str(size) for size in record.maintenance_equipment_ids.mapped('size') if size]
    #         record.size = ", ".join(sizes)

    def unlink(self):
        trips = self.compactor_trip_ids
        for trip in trips:
            timesheet = self.env['account.analytic.line'].search([('tripsheet_compactor_id', '=', trip.id)])
            for time in timesheet:
                time.unlink()
        timesheet = self.env['account.analytic.line'].search([('tripsheet_custom_id', '=', self.id)])
        print('timesheet______________', timesheet)
        for time in timesheet:
            time.unlink()
        return super(CustomTripSheet, self).unlink()

    def _compute_billable_qty(self):
        for record in self:
            if record.compactor:
                # record.billable_qty = sum(
                #     record.compactor_trip_ids.filtered(lambda a: a.billable == True).mapped('bin_lift'))
                count = 0
                for com in record.compactor_trip_ids:
                    if com.billable:
                        count = count + com.bin_lift
                record.billable_qty = count
            else:
                record.billable_qty = sum(record.skip_load_ids.filtered(lambda a: a.billable).mapped('qty'))

    def compute_equipment_qty(self):
        for trip_id in self:
            so_equipment_qty = False
            if trip_id.compactor:
                so_equipment_qty = sum(
                    trip_id.compactor_trip_ids.filtered(lambda a: a.billable == 'yes').mapped('so_equipment_qty'))
            else:
                so_equipment_qty = sum(
                    trip_id.skip_load_ids.filtered(lambda a: a.billable).mapped('so_equipment_qty'))
            trip_id.equipment_qty = so_equipment_qty

    @api.model
    def create(self, vals):
        if vals.get('sequence', _('New')) == _('New'):
            vals['sequence'] = self.env['ir.sequence'].next_by_code('custom.trip.sheet')
        if not vals.get('req_seq'):
            vals['req_seq'] = vals.get('sequence')
        return super(CustomTripSheet, self).create(vals)

    def button_back_to_draft(self):
        for record in self:
            record.write({'stage': 'draft'})
            print("____ stage", record.stage)


    def button_approve(self):
        timesheet_ref = self.env['account.analytic.line']
        for record in self:
            record.is_record_readonly = True
            if record.compactor:
                for record_compactor in self.compactor_trip_ids:
                    timesheet_id = timesheet_ref.sudo().create({
                        'date': record_compactor.date_from.date() if record_compactor.date_from else False,
                        'name': record.req_seq,
                        'unit_amount': record_compactor.bin_lift,
                        'task_id': record.task_id.id,
                        'units_amounts': sum(
                            record.compactor_trip_ids.filtered(lambda a: a.billable == 'yes').mapped('bin_lift')),
                        'employee_id': record_compactor.driver_id.id,
                        'tripsheet_compactor_id': record_compactor.id,
                    })
                    record.task_id.write({'timesheet_ids': [(4, timesheet_id.id)]})
            else:
                timesheet_id = timesheet_ref.sudo().create({
                    'date': record.date_from.date(),
                    'name': record.req_seq,
                    'unit_amount': sum(record.skip_load_ids.filtered(lambda a: a.billable).mapped('qty')),
                    'units_amounts': sum(record.skip_load_ids.filtered(lambda a: a.billable).mapped('qty')),
                    'task_id': record.task_id.id,
                    'employee_id': record.driver_id.id,
                    'is_trip_type_visit': True if record.trip_type == 'trip' else False,
                    'tripsheet_custom_id': record.id
                })
                record.task_id.write({'timesheet_ids': [(4, timesheet_id.id)]})
            record.write({'stage': 'done'})


class ProjectTask(models.Model):
    _inherit = 'project.task'
    _order = 'id desc'

    is_outsource_vendor = fields.Boolean(string="Outsource Vendor")
    is_treatment_company = fields.Boolean(string="Treatment Company")
    vendor_name_id = fields.Many2one('res.partner', string="Vendor Name(OutSourced)")
    treatment_company_id = fields.Many2one('res.partner', string="Treatment Company")
    trip_sheet_ids = fields.One2many('custom.trip.sheet', 'task_id')
    equipment_qty = fields.Float(string="Equipment Qty", compute='compute_equipment_qty')

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('seq_code', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def compute_equipment_qty(self):
        # self.equipment_qty = self.sale_line_id.equipment_qty
        for rec in self:
            for sale_line in rec.sale_line_id:
                rec.equipment_qty = sale_line.equipment_qty

    # user_ids = fields.Many2many('res.users', relation='project_task_user_rel', column1='task_id', column2='user_id',
    #     string='Supervisor', default=lambda self: not self.env.user.share and self.env.user, context={'active_test': False}, tracking=True)


class Vehicle(models.Model):
    _inherit = 'fleet.vehicle'

    is_trailer = fields.Boolean(string="Is Trailer")

    def name_get(self):
        res_list = []
        for rec in self:
            if rec.license_plate and rec.model_id:
                res_list.append((rec.id, rec.license_plate + '/' + rec.model_id.name))
            else:
                res_list.append((rec.id, rec.name))
        return res_list


class ExtraChargeSoWizard(models.Model):
    _name = "so.extra.charge.wizard"
    _description = "Sale Order Line Extra Charge"

    charge_type = fields.Selection([('month', 'Month'), ('day', 'Trip'), ('full_day', 'Day')], string="Charge Type",
                                   help="Minimum Calculation by ( e.g. Month, Trip, Daily etc.)")
    charge = fields.Selection([('qty', 'Qty'), ('amount', 'Amount')], string="Based On")
    price = fields.Float(string="Minimum Rate / Amount chargeable")
    qty = fields.Float(string="Quantity", Help="Minimum Quantity Chargeable")

    # extra charge
    ec_charge_type = fields.Selection([('month', 'Month'), ('day', 'Day')], string="Charge Type")
    ec_price = fields.Float(string="Price/Unit Rate",
                            help="Rate for additional quantity if actual quantity exceeds minimum quantity")
    ec_unit_id = fields.Many2one('uom.uom', string="Unit of Mesure")

    so_line_id = fields.Many2one('sale.order.line', string="Order Line")
    is_trip_extra = fields.Boolean(string="Trip Extra Charges")

    def button_generate_charges(self):
        for charges in self:
            self.so_line_id.order_id.write({'extra_charge_ids': ([(4, charges.id)])})

    @api.model
    def default_get(self, fields):
        vals = super(ExtraChargeSoWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if self.env.context.get('active_model') == 'sale.order.line' and active_ids:
            line_id = self.env['sale.order.line'].browse(active_ids)
            vals['so_line_id'] = line_id.id
            if line_id.product_uom.lumpsum_check:
                vals['is_trip_extra'] = True
        return vals


class ExtraChargeSo(models.Model):
    _name = 'so.extra.charge'
    _rec_name = "so_line_id"

    charge_type = fields.Selection([('month', 'Month'), ('day', 'Day')], string="Charge Type")
    charge = fields.Selection([('qty', 'Qty'), ('amount', 'Amount')], string="Based On")
    price = fields.Float(string="Price")
    qty = fields.Float(string="Qty")

    # extra charge
    ec_charge_type = fields.Selection([('month', 'Month'), ('day', 'Day')], string="Charge Type")
    ec_price = fields.Float(string="Price")
    ec_unit_id = fields.Many2one('uom.uom', string="Unit of Mesure")
    so_line_id = fields.Many2one('sale.order.line', string="Order Line")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    extra_charge_id = fields.Many2one('so.extra.charge', string="Extra Charge")
    equipment_qty = fields.Float(string="Equip. Qty")
    rate = fields.Float(string="Addtn Equip. Rate")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    extra_charge_ids = fields.Many2many('so.extra.charge.wizard', string="Extra Charge")
    trip_ids = fields.Many2many('custom.trip.sheet', compute='compute_trip_sheet')

    def compute_trip_sheet(self):
        trip_ids = self.tasks_ids.mapped('trip_sheet_ids').ids
        self.write({'trip_ids': ([(6, 0, trip_ids)])})


#  sale order to invoice update with Trip sheet Additional On Call using add Extra Charge flow

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def update_charge_inv(self, sale_orders, inv):
        res = super(SaleAdvancePaymentInv, self).update_charge_inv(sale_orders, inv)
        order = sale_orders
        for extra in order.extra_charge_ids:
            for line in order.order_line:
                if extra.so_line_id == line and extra.is_trip_extra:
                    additionall_call_spend_time = 0
                    if extra.so_line_id.product_uom.lumpsum_check:
                        for sheet in extra.so_line_id.task_id.timesheet_ids:
                            trip_sheet = sheet.name
                            trip_sheet_id = self.env['custom.trip.sheet'].search([('req_seq', '=', trip_sheet)])
                            if trip_sheet_id:
                                if trip_sheet_id.date_from.date() >= self.date_start_invoice_timesheet and trip_sheet_id.date_from.date() <= self.date_end_invoice_timesheet:
                                    if trip_sheet_id.additional_on_call:
                                        additionall_call_spend_time += sheet.unit_amount
                    """ Extra Cahrges Add for Addition call Spen Time """
                    if additionall_call_spend_time > 0 and extra.is_trip_extra and extra.so_line_id.product_uom.lumpsum_check:
                        extra_charge_product_id = self.env.ref('custom_trip.product_extra_charge_product')
                        name = "%s - %s" % (extra_charge_product_id.name, extra.so_line_id.product_id.name),
                        invoice_vals = [(0, 0, {
                            'name': name,
                            'price_unit': extra.ec_price,
                            'quantity': additionall_call_spend_time,
                            'product_id': self.env.ref('custom_trip.product_extra_charge_product').id,
                            'product_uom_id': extra.ec_unit_id.id,
                            'analytic_tag_ids': [(6, 0, extra.so_line_id.analytic_tag_ids.ids)],
                            'analytic_account_id': order.analytic_account_id.id or False,
                            'move_id': inv.id,
                            'equipment_type_id': extra.so_line_id.equipment_type_id.id or False,
                        })]
                        inv.update({'invoice_line_ids': invoice_vals})
        return res
