from odoo import models, fields, api
from datetime import date

class ProjectTask(models.Model):
    _inherit = 'project.task'

    last_invoice_date = fields.Date(
        string="Last Invoice Date",
        compute='_compute_last_invoice_details',
        store=True
    )
    last_invoice_number = fields.Char(
        string="Last Invoice Number",
        compute='_compute_last_invoice_details',
        store=True
    )
    task_uom = fields.Many2one(
        'uom.uom', 
        string="Unit of Measure",
        related='sale_line_id.product_uom',
        readonly=True,
        store=True
    )
    unit_price = fields.Float(
        string="Unit Price",
        related='sale_line_id.price_unit',
        readonly=True,
        store=True
    )
    agency_fee = fields.Selection(
        [('fix', 'Fix'), ('percentage', 'Percentage')], 
        string="Agency Fee Type",
        related='sale_line_id.agency_fee',
        readonly=True
    )
    amount = fields.Float(
        string="Amount",
        related='sale_line_id.sale_amount',
        readonly=True,
        store=True
    )
    delivered = fields.Float(
        string="Delivered",
        related='sale_line_id.qty_delivered',
        readonly=True,
        store=True
    )
    invoiced = fields.Float(
        string="Invoiced",
        related='sale_line_id.qty_invoiced',
        readonly=True,
        store=True
    )
    new_overtime = fields.Float(
        string="Overtime",
        related='sale_line_id.overtime',
        readonly=True,
        store=True
    )
    spe_overtime = fields.Float(
        string="Special Overtime",
        related='sale_line_id.sp_overtime',
        readonly=True,
        store=True
    )
    additional_rate = fields.Float(
        string="Additional Equipment Rate",
        related='sale_line_id.rate',
        readonly=True,
        store=True,
    )
    branch_for = fields.Selection([('hro', 'HRO'), ('mro', 'MRO'), ('es', 'ES')], string='Branch For',related='branch_id.branch_for',readonly=True)

    unbilled_value = fields.Float(
        string="Unbilled Value",
        compute='_compute_unbilled_value',
        store=True,
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='partner_id.currency_id'
    )

    # @api.depends('partner_id', 'partner_id.invoice_ids')
    # def _compute_last_invoice_details(self):
    #     for task in self:
    #         if task.partner_id:
    #             invoices = self.env['account.move'].search([
    #                 ('partner_id', '=', task.partner_id.id),
    #                 ('move_type', 'in', ['out_invoice', 'out_refund']),
    #             ], order='invoice_date desc, name desc', limit=1)
                
    #             if invoices:
    #                 task.last_invoice_date = invoices[0].invoice_date
    #                 task.last_invoice_number = invoices[0].name
    #             else:
    #                 task.last_invoice_date = False
    #                 task.last_invoice_number = False
    #         else:
    #             task.last_invoice_date = False
    #             task.last_invoice_number = False

    # @api.depends('partner_id', 'partner_id.invoice_ids')
    # def _compute_last_invoice_details(self):
    #     for task in self:
    #         if task.partner_id:
    #             domain = [
    #                 ('partner_id', '=', task.partner_id.id),
    #                 ('move_type', 'in', ['out_invoice', 'out_refund']),
    #                 ('invoice_line_ids.task_id', '=', task.id),  
    #             ]
                
    #             invoices = self.env['account.move'].search(
    #                 domain,
    #                 order='invoice_date desc, name desc', 
    #                 limit=1
    #             )
                
    #             if invoices:
    #                 task.last_invoice_date = invoices[0].invoice_date
    #                 task.last_invoice_number = invoices[0].name
    #             else:
    #                 partner_invoices = self.env['account.move'].search([
    #                     ('partner_id', '=', task.partner_id.id),
    #                     ('move_type', 'in', ['out_invoice', 'out_refund']),
    #                 ], order='invoice_date desc, name desc', limit=1)
                    
    #                 if partner_invoices:
    #                     task.last_invoice_date = partner_invoices[0].invoice_date
    #                     task.last_invoice_number = partner_invoices[0].name
    #                 else:
    #                     task.last_invoice_date = False
    #                     task.last_invoice_number = False
    #         else:
    #             task.last_invoice_date = False
    #             task.last_invoice_number = False

    @api.depends('sale_line_id.order_id.invoice_ids', 'sale_line_id.order_id.name')
    def _compute_last_invoice_details(self):
        for task in self:
            task.last_invoice_date = False
            task.last_invoice_number = False
        
            so = task.sale_line_id.order_id if task.sale_line_id else False
            
            if not so:
                continue 
                
            domain = [
                '|',
                ('invoice_line_ids.task_id', '=', task.id),
                '&',
                    ('invoice_origin', '=', so.name),  
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
            ]
            
            invoices = self.env['account.move'].search(
                domain,
                order='invoice_date desc, name desc',
                limit=1
            )
            
            if invoices:
                task.last_invoice_date = invoices[0].invoice_date
                task.last_invoice_number = invoices[0].name



    @api.depends('timesheet_ids', 'trip_sheet_ids', 'last_invoice_date', 'unit_price', 'additional_rate', 'branch_for', 
                 'timesheet_ids.unit_amount', 'timesheet_ids.date', 'timesheet_ids.unbilled_yes_no', 
                 'overtime_lines_ids.ot_hour', 'overtime_lines_ids.ot_date', 'overtime_lines_ids.ot_type','task_uom', 'task_uom.name','sale_line_id.order_id.advance_billing')
    def _compute_unbilled_value(self):
        today = date.today()
        for task in self:
            # ✅ ADVANCE BILLING 
            if task.sale_line_id and task.sale_line_id.order_id.advance_billing:
                task.unbilled_value = 0.0
                continue

            if not task.last_invoice_date:
                task.unbilled_value = 0.0
                continue

            if task.branch_for == 'es':
                # ES Branch Calculation
                valid_trips = task.trip_sheet_ids.filtered(
                    lambda t: t.date_from and 
                    fields.Datetime.to_datetime(t.date_from).date() > task.last_invoice_date and
                    fields.Datetime.to_datetime(t.date_from).date() <= today and
                    not t.non_billable and
                    (not t.remark or t.remark != 'Exception')
                )
                
                billable_amount = sum(trip.billable_qty * task.unit_price for trip in valid_trips)
                equipment_amount = sum(trip.equipment_qty * task.additional_rate for trip in valid_trips)
                task.unbilled_value = billable_amount + equipment_amount

            elif task.branch_for == 'hro':
                
                excluded_uoms = ['month', 'months', 'lumpsum','week', 'weeks','day', 'days']
                if task.task_uom and task.task_uom.name.lower() not in [u.lower() for u in excluded_uoms]:

                    regular_timesheets = task.timesheet_ids.filtered(
                        lambda t: t.date and 
                        fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(t.date).date() <= today and
                        t.unbilled_yes_no != 'no'
                        # t.ref != 'Exception'
                    )
                    regular_hrs_amount = sum(t.unit_amount * task.unit_price for t in regular_timesheets)

                    normal_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= today and
                        o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                    )
                    normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

                    special_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= today and
                        o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                    )
                    special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)

                    task.unbilled_value = regular_hrs_amount + normal_ot_amount + special_ot_amount

                elif task.task_uom and task.task_uom.name.lower() in ['week', 'weeks']:
                    valid_timesheets = task.timesheet_ids.filtered(
                        lambda t: t.date and 
                        fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(t.date).date() <= today and
                        t.unbilled_yes_no != 'no'
                        # t.ref != 'Exception'
                    )
                    
                    if not valid_timesheets:
                        task.unbilled_value = 0.0
                        continue
                        
                    max_date = max(valid_timesheets.mapped('date'))
                    max_date = fields.Datetime.to_datetime(max_date).date()

                    # Weekly calculation
                    days_diff = (max_date - task.last_invoice_date).days
                    week_diff = days_diff / 7
                    
                    unbilled_period_amount = week_diff * task.unit_price
                    
                    # Calculate Agency Fee
                    agency_fee_amount = 0.0
                    if task.agency_fee == 'fix' and task.amount:
                        agency_fee_amount = task.amount * week_diff
                    elif task.agency_fee == 'percentage' and task.amount:
                        agency_fee_amount = (task.unit_price * task.amount / 100) * week_diff
                    
                    # Calculate OT amounts
                    normal_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= today and
                        o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                    )
                    normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

                    special_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= today and
                        o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                    )
                    special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)
                    
                    # Final calculation
                    task.unbilled_value = unbilled_period_amount + agency_fee_amount + normal_ot_amount + special_ot_amount

                elif task.task_uom and task.task_uom.name.lower() in ['day', 'days']:

                    valid_days = task.timesheet_ids.filtered(
                        lambda t: t.date and 
                        fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(t.date).date() <= today and
                        t.unit_amount > 0 and
                        t.unbilled_yes_no != 'no'
                        # t.ref != 'Exception'
                    ).mapped('date')
                    
                    # Count distinct days
                    day_count = len(set(valid_days))
                    regular_hrs_amount = day_count * task.unit_price

                    normal_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= today and
                        o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                    )
                    normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

                    special_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= today and
                        o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                    )
                    special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)

                    task.unbilled_value = regular_hrs_amount + normal_ot_amount + special_ot_amount

                else:
                    valid_timesheets = task.timesheet_ids.filtered(
                        lambda t: t.date and 
                        fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(t.date).date() <= today and
                        t.unbilled_yes_no != 'no'
                        # t.ref != 'Exception'
                    )
                    
                    if not valid_timesheets:
                        task.unbilled_value = 0.0
                        continue
                        
                    max_date = max(valid_timesheets.mapped('date'))
                    max_date = fields.Datetime.to_datetime(max_date).date()

                    month_diff = (max_date.year - task.last_invoice_date.year) * 12 + (max_date.month - task.last_invoice_date.month)
                    
                    unbilled_month_amount = month_diff * task.unit_price
                    
                    # Calculate Agency Fee
                    agency_fee_amount = 0.0
                    if task.agency_fee == 'fix' and task.amount:
                        agency_fee_amount = task.amount * month_diff
                    elif task.agency_fee == 'percentage' and task.amount:
                        agency_fee_amount = (task.unit_price * task.amount / 100) * month_diff
                    
                    # Calculate OT amounts
                    normal_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= today and
                        o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                    )
                    normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

                    special_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= today and
                        o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                    )
                    special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)
                    
                    # Final calculation
                    task.unbilled_value = unbilled_month_amount + agency_fee_amount + normal_ot_amount + special_ot_amount
            else:
                task.unbilled_value = (task.delivered - task.invoiced) * task.unit_price if task.delivered > task.invoiced else 0.0
