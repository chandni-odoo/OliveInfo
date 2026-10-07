# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError
from datetime import date, timedelta, datetime
from datetime import date, timedelta
import logging
from itertools import groupby

_logger = logging.getLogger(__name__)
import json
import calendar
from calendar import monthrange
from odoo.tools import float_is_zero, html_keep_url, is_html_empty

from odoo.tools.safe_eval import safe_eval
from collections import defaultdict


class Frequency(models.Model):
    _name = "so.frequency"
    _description = "So Frequency"

    name = fields.Char('Name')


class AdditionalCharges(models.Model):
    _name = "so.additional.charges"
    _description = "So Additional Charges"
    _rec_name = 'product_id'

    recurring = fields.Boolean('Recurring')
    remarks = fields.Text(string="Remarks")
    price_unit = fields.Float('Unit Price', default=0.0)
    amount = fields.Float(string='Amount')
    so_id = fields.Many2one('sale.order', string="Sale Order")
    so_line_id = fields.Many2one('sale.order.line', string="Sale Order Line")
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity', default=1.0)
    product_uom_category_id = fields.Many2one('uom.category')
    product_uom = fields.Many2one('uom.uom', string='UoM', required=True,
                                  domain="[('category_id', '=', product_uom_category_id)]")
    charge_date = fields.Date(string="Date")
    based_cost = fields.Selection([
        ('one_time_cost', 'One-time Cost'),
        ('annual_charges', 'Annual Charges(rec)'),
        ('annual_privilege_leave', 'Annual/Privilege Leave'),
        ('service_charge', 'End of Service Charges'),
        ('es', 'ES')],
        string="Costing")
    employee_id = fields.Many2one(related='so_line_id.employee_id', string="Employee")
    sequence_ref = fields.Char(related='so_line_id.sequence_ref', string='Sequence')
    task_id = fields.Many2one(related='so_line_id.task_id', string="Task")

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id and self.so_id:
            self.write({'product_uom_category_id': self.product_id.uom_id.category_id.id})
            return {
                'domain': {
                    'so_line_id': [('order_id', '=', self.so_id._origin.id)],
                },
            }


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.today())
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.today())
    inv_date = fields.Date(string="inv Date")
    sale_type = fields.Selection([('standard', 'Standard'), ('bundle', 'Bundle'), ('cost_plus', 'Cost Plus')],
                                 default='standard', string="Type")
    contract_type = fields.Selection([('limited', 'Limited'), ('unlimited', 'Unlimited')], default='limited',
                                     string="Contract")
    partner_location_id = fields.Many2one('contact.location', string="Location")
    attachment_ids = fields.Many2many('ir.attachment', string='Attachment')
    attachment_id = fields.Binary(string='LPO')
    is_costing = fields.Boolean()
    costing_date = fields.Datetime(index=True, default=fields.Datetime.now)
    state = fields.Selection([
        ('costing', 'Costing'),
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('customer_approve', 'Customer Approve'),
        ('agreement', 'Agreement'),
        ('pre_approval', 'Pre Approval'),
        ('revisions', 'REVISIONS'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3)
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Invoice Address',
        readonly=True, required=True,
        states={'costing': [('readonly', False)], 'draft': [('readonly', False)], 'sent': [('readonly', False)],
                'sale': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Address', readonly=True, required=True,
        states={'costing': [('readonly', False)], 'draft': [('readonly', False)], 'sent': [('readonly', False)],
                'sale': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        required=True, readonly=True,
        states={'costing': [('readonly', False)], 'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=1,
        help="If you change the pricelist, only newly added lines will be affected.")
    onboarding_count = fields.Integer(compute='compute_onboarding_count', string="Onboarding")
    so_sitevisit_count = fields.Integer(compute='_compute_so_sitevisit_count', string='Site Visit')
    site_count = fields.Integer(compute='_site_count', string='Site Visit')
    so_agreement_count = fields.Integer(compute='_so_agreement_count', string='Agreement')
    food = fields.Boolean('Food')
    accommodation = fields.Boolean('Accommodation')
    transport = fields.Boolean('Transport')
    fat = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='FAT', readonly=True, default=True,
                           compute="_compute_fat")
    branch_for = fields.Selection(related="branch_id.branch_for")
    credit_limit = fields.Float(related="partner_id.credit_limit", string="Credit Limit")
    ava_credit_bal = fields.Float(related="partner_id.ava_credit_bal", string="Available Balance")
    # Point no 7 PS2
    # ava_credit_bal = fields.Float(string="Available Balance", compute='_compute_availabe_balance')
    customer_id = fields.Char(related="partner_id.address_no", string="Customer Code")
    is_customer_onboarding = fields.Boolean(compute="_compute_is_customer_onboarding")
    document_line_ids = fields.Many2many('hr.document.line', compute="_compute_document_line_ids", store=True,
                                         readonly=False)
    instruction = fields.Text(string='Instruction')
    scope_of_work = fields.Text(string='Scope of Work')
    subject = fields.Char(string='Subject')
    min_contract = fields.Char(string='Minimum Contract Period')
    duration_in_days = fields.Integer('Duration in Days', compute='_compute_duration_in_days')
    week_of_no = fields.Integer(string='Week Off No', compute='_compute_week_of_no')
    week_of = fields.Many2many('week.week', string='Week Off')
    total_week_off = fields.Integer(string='Total Week Off', compute='_compute_week_of_total')
    total_working_days = fields.Integer(string='Total Working Days', compute='_compute_week_of_total')
    no_of_bins = fields.Float(string="No. Of Bins")
    terms_id = fields.Many2one('terms.condition', string="Terms and Conditions",
                               default=lambda self: self.env['terms.condition'].search(
                                   [('condition_type', '=', 'sale')], limit=1))
    agreement_id = fields.Many2one('sale.agreement', string="Agreement")

    addtionl_charge_sale_order_ids = fields.One2many('so.additional.charges', 'so_id', 'Additional Charge', copy=True)
    contact_name = fields.Char(string='Contact Name')
    email = fields.Char('Email', readonly=False, store=True)
    mobile = fields.Char('Mobile', readonly=False, store=True)
    frequency_id = fields.Many2one('so.frequency', string="Frequency")
    help_quantity = fields.Text(readonly=True,
                                default="PS - Quantity can be No. of head count / Resources / People or any other units. \nES - Quantity can be No. of Trips, No. of Loads, No. of Bin Lift, Weight in KG, No. of Gallon, No. of Hrs etc.")

    display_extra_line = fields.Boolean(string="Dispaly Extra lines", default=False)
    is_hold = fields.Boolean(string="Is Hold")
    hold_reason = fields.Char(string="Hold Reason")
    trip_sheet_email = fields.Char(string='Trip Sheet Email')
    trip_sheet_whatsapp = fields.Char(string='Trip Sheet Whatsapp')
    advance_billing = fields.Boolean(string="Advance Billing")
    pre_approval_completed = fields.Boolean(
        string="Pre Approval Completed",
        default=False,
        copy=False
    )

    ####### code for HRO Branch Invoice creation ######################
    @api.model
    def _prepare_invoice(self):
        start_date = self.env.context.get('timesheet_start_date')
        end_date = self.env.context.get('timesheet_end_date')

        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_lines = self._billing_values(start_date, end_date)
        invoice_vals['invoice_line_ids'] += invoice_lines
        invoice_vals['narration'] = False
        return invoice_vals

    def _billing_values(self, start_date=None, end_date=None):
        employee_qty_count = self._initialize_employee_qty_count()
        inv_date = self.inv_date if self.inv_date else datetime.today()
        total_month_days = monthrange(inv_date.year, inv_date.month)[1]

        return self._prepare_invoice_lines(employee_qty_count, total_month_days, start_date, end_date)

    def _initialize_employee_qty_count(self):
        if self.sale_type == 'bundle':
            return defaultdict(lambda: {'employee': set(), 'inv_line': set(), 'task': set(), 'soline_id': set(),
                                        'working_days': 0, 'dates': set(), 'holidays': 0, 'week_off_days': 0})
        elif self.sale_type == 'cost_plus':
            return defaultdict(lambda: {'employee': set(), 'inv_line': set(), 'task': set(), 'soline_id': set(),
                                        'working_days': 0, 'dates': set(), 'holidays': 0, 'week_off_days': 0,
                                        'leave_days': 0})
        elif self.sale_type == 'standard':
            return defaultdict(lambda: {'employee': set(), 'inv_line': set(), 'task': set(), 'soline_id': set(),
                                        'working_days': 0, 'dates': set(), 'week_off_days': 0})

    def _populate_employee_data(self, so_line, employee_qty_count, start_date=None, end_date=None):
        timesheet_start_date = self._context.get('timesheet_start_date')
        timesheet_end_date = self._context.get('timesheet_end_date')
        for timesheet_line in so_line.task_id.timesheet_ids.filtered(
                lambda x: x.date >= timesheet_start_date and x.date <= timesheet_end_date):
            if timesheet_line.unit_amount > 0.00:
                emp = timesheet_line.employee_id.name
                employee = timesheet_line.employee_id
                date = timesheet_line.date
                employee_qty_count[employee]['employee'].add(employee)
                employee_qty_count[employee]['task'].add(timesheet_line.task_id)
                employee_qty_count[employee]['working_days'] += 1
                employee_qty_count[employee]['dates'].add(date)

            for employee, values in employee_qty_count.items():
                date_from, date_to = min(values['dates']), max(values['dates'])
                values['holidays'] = self._calculate_holidays(employee, start_date, end_date, timesheet_line.task_id)
                values['week_off_days'] = self._calculate_week_off_days(employee, start_date, end_date,
                                                                        timesheet_line.task_id)
                values['leave_days'] = self._calculate_leave_days(employee, start_date, end_date)
        return employee_qty_count

    def _prepare_invoice_lines(self, employee_qty_count, total_month_days, start_date, end_date):
        self.ensure_one()
        global note
        invoice_vals = []
        note_section = []
        if self.branch_for == 'hro':
            my_task = self._context.get('tasks')
            sale_lines = self.order_line.filtered(lambda l: l.product_uom.name == "Month")
            if my_task:
                select_lines = sale_lines.filtered(lambda l: l.task_id in my_task)
            else:
                select_lines = sale_lines

            for line in select_lines:
                 # 📌 If Advance Billing is enabled, skip timesheet-based logic
                if self.advance_billing and line.product_id.code not in ['SOC', 'NOC']:
                    account_id = line.product_id.property_account_income_id.id or \
                                line.product_id.categ_id.property_account_income_categ_id.id
                    subtotal = line.price_unit * line.product_uom_qty
                    
                    invoice_vals.append((0, 0, {
                        'name': "%s (Advance Billing)" % (line.product_id.name),
                        'price_unit': line.price_unit,
                        'price_subtotal': subtotal,
                        'quantity': line.product_uom_qty,
                        'product_id': line.product_id.id,
                        'employee_id': line.employee_id.id if line.employee_id else False,
                        'task_id': line.task_id.id,
                        'product_uom_id': line.product_uom.id,
                        'account_id': account_id
                    }))
                    continue  # skip normal HRO calculation

            # 🟢 Existing logic for normal HRO billing
                employee_qty_count = self._initialize_employee_qty_count()
                self._populate_employee_data(line, employee_qty_count, start_date, end_date)
                # For each employee, create an invoice line
                for employee, values in employee_qty_count.items():
                    emp_name = employee.display_name
                    total_qty = 0

                    if self.sale_type == 'bundle':
                        working_days = values['working_days']
                        holidays = values['holidays']
                        week_off = values['week_off_days']
                        lev = values['leave_days']
                        total_qty = (values['working_days'] + values['holidays'] + values[
                            'week_off_days']) / total_month_days
                        total_qty = round(total_qty, 6)

                        work_days = int(working_days + holidays + week_off)
                        note = f"Note Days: {work_days}  / {total_month_days} = {total_qty},Man Days -(WH-{working_days},H-{holidays},WO-{week_off}) "

                    elif self.sale_type == 'cost_plus':
                        working_days = values['working_days']
                        holidays = values['holidays']
                        week_off = values['week_off_days']
                        lev = values['leave_days']
                        total_qty = (values['working_days'] + values['holidays'] + values['week_off_days'] + values[
                            'leave_days']) / total_month_days
                        total_qty = round(total_qty, 6)

                        work_days = int(working_days + holidays + week_off + lev)
                        note = f"Note Days: {work_days} / {total_month_days} = {total_qty}  Man Days -(WH-{working_days},H-{holidays},WO-{week_off},L-{lev})"

                    elif self.sale_type == 'standard':
                        working_days = values['working_days']
                        week_off = values['week_off_days']
                        total_qty = (values['working_days'] + values['week_off_days']) / total_month_days
                        total_qty = round(total_qty, 6)

                        work_days = int(working_days + week_off)
                        note = f"Note Days: {work_days}  / {total_month_days} = {total_qty} Man Days -(WH-{working_days},WO-{week_off})"

                    account_id = line.product_id.property_account_income_id.id or line.product_id.categ_id.property_account_income_categ_id.id
                    # Ensure total_qty does not exceed 1
                    total_qty = min(total_qty, 1)
                    price_unit_adjusted = line.price_unit * total_qty if total_qty > 1 else line.price_unit
                    subtotal = line.price_unit * total_qty

                    invoice_vals.append((0, 0, {
                        'name': "%s-%s-%s" % (line.product_id.name, employee.display_name, note),
                        'price_unit': price_unit_adjusted,
                        'price_subtotal': subtotal,
                        'quantity': total_qty,
                        'product_id': line.product_id.id,
                        'employee_id': employee.id,
                        'task_id': line.task_id.id,
                        'product_uom_id': line.product_uom.id,
                        'account_id': account_id

                    }))

        # 📌 Remove zero subtotal lines in ALL branches before returning
        # invoice_vals = [line for line in invoice_vals if line and isinstance(line, tuple) and len(line) > 2 and isinstance(line[2], dict) and line[2].get('price_subtotal', 0) != 0]
        return invoice_vals

    def _calculate_holidays(self, employee, date_from, date_to, tasks_id):
        emp_name = employee.display_name
        public_holidays = self.env['resource.calendar.leaves'].search([
            # ('task_id', '=', tasks_id.id),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
            ('resource_id', '=', False)
        ])

        task_holidays = self.env['task.calendar.leaves'].search([
            ('task_id', '=', tasks_id.id),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from)
        ])

        # task_holidays = self.env['task.calendar.leaves'].search([
        #     ('task_id', '=', tasks_id.id),
        #     ('date_to', '>=', date_to),
        #     ('date_from', '<=', date_from)
        # ])

        public_holidays = len(public_holidays)
        task_holidays = len(task_holidays)
        total_holidays = (public_holidays) + (task_holidays)

        return total_holidays

    def _calculate_week_off_days(self, employee, date_from, date_to, task_id):
        emp_name = employee.display_name
        emp_week_off = self.env['shift.allocation'].search([
            ('task_id', '=', task_id.id),
            ('employee_id', '=', employee.id),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from)
        ])
        # Filter dayofweek_ids by date_from and date_to
        filtered_dayofweek_ids = emp_week_off.mapped('dayofweek_ids').filtered(
            lambda day: date_from <= day.date <= date_to
        )
        # Count the filtered dayofweek_ids
        week_off_days_count = len(filtered_dayofweek_ids)
        return week_off_days_count

        # commented by shon on 01 feb 2025
        # emp_week_off = len(emp_week_off.dayofweek_ids)
        #
        # # emp_week_off = self.env['hr.day.of.week'].search([
        # #     ('employee_id', '=', employee.id),
        # #     ('date', '<=', date_to),
        # #     ('date', '>=', date_from)
        # # ])
        # return (emp_week_off)

    def _calculate_leave_days(self, employee, date_from, date_to):
        emp_name = employee.display_name
        leave_records = self.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
            ('state', '=', 'validate')
        ])
        total_leave_days = 0
        for leave in leave_records:
            # Check if either condition is true for the current leave record
            if leave.holiday_status_id.is_paid or leave.holiday_status_id.work_entry_type_id.is_paid:
                # Calculate the overlap between the leave and the specified date range
                leave_start = max(leave.request_date_from, date_from)
                leave_end = min(leave.request_date_to, date_to)
                total_leave_days += (leave_end - leave_start).days + 1
                tot = total_leave_days
            else:
                total_leave_days = 0
        return total_leave_days

    def _create_invoices(self, grouped=False, final=False, date=None):
        self.ensure_one()
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']

        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0  # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id)
            current_section_vals = None
            down_payments = order.env['sale.order.line']

            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)

            if not any(not line.display_type for line in invoiceable_lines):
                continue

            invoice_line_vals = []
            down_payment_section_added = False
            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    # Create a dedicated section for the down payments
                    # (put at the end of the invoiceable_lines)
                    invoice_line_vals.append(
                        (0, 0, order._prepare_down_payment_section_line(
                            sequence=invoice_item_sequence,
                        )),
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1
                invoice_line_vals.append(
                    (0, 0, line._prepare_invoice_line(
                        sequence=invoice_item_sequence,
                    )),
                )
                invoice_item_sequence += 1

            # if product name and lable are same then remove the line
            if invoice_line_vals and order.branch_for == 'hro':
                # Filter out lines where 'sequence' is 0
                invoice_line_vals = [line for line in invoice_line_vals if line[2]['product_uom_id'] != 112]
            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise self._nothing_to_invoice_error()

        # 2) Manage 'grouped' parameter: group by (partner_id, currency_id).
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            invoice_vals_list = sorted(
                invoice_vals_list,
                key=lambda x: [
                    x.get(grouping_key) for grouping_key in invoice_grouping_keys
                ]
            )
            for grouping_keys, invoices in groupby(invoice_vals_list,
                                                   key=lambda x: [x.get(grouping_key) for grouping_key in
                                                                  invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.

        # As part of the invoice creation, we make sure the sequence of multiple SO do not interfere
        # in a single invoice. Example:
        # SO 1:
        # - Section A (sequence: 10)
        # - Product A (sequence: 11)
        # SO 2:
        # - Section B (sequence: 10)
        # - Product B (sequence: 11)
        #
        # If SO 1 & 2 are grouped in the same invoice, the result will be:
        # - Section A (sequence: 10)
        # - Section B (sequence: 10)
        # - Product A (sequence: 11)
        # - Product B (sequence: 11)
        #
        # Resequencing should be safe, however we resequence only if there are less invoices than
        # orders, meaning a grouping might have been done. This could also mean that only a part
        # of the selected SO are invoiceable, but resequencing in this case shouldn't be an issue.
        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env['sale.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence,
                                                                                   old=line[2]['sequence'])
                    sequence += 1

        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
        moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        if final:
            moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_invoice_into_refund_credit_note()
        for move in moves:
            move.message_post_with_view('mail.message_origin_link',
                                        values={'self': move, 'origin': move.line_ids.mapped('sale_line_ids.order_id')},
                                        subtype_id=self.env.ref('mail.mt_note').id
                                        )
        return moves

    ####################################################################

    @api.depends('order_id.order_line', 'order_id.order_line.product_id')
    def hide_show_extra_line(self):
        product_special_ot = self.env.ref('project_extended.product_soc_product_template')
        product_normal_ot = self.env.ref('project_extended.product_noc_product_template')

        product_specialot = self.env['product.product'].search([('default_code', '=', 'SOC')], limit=1)
        product_normalot = self.env['product.product'].search([('default_code', '=', 'NOC')], limit=1)
        for order in self:
            for line in order.order_line:
                if line.product_id in [product_special_ot, product_normal_ot, product_specialot, product_normalot]:
                    line.write({
                        'display_extra_line': True,
                        'active': False,
                    })
                    order.write({'display_extra_line': True})
                else:
                    query = "UPDATE sale_order_line set active='%s' where order_id='%s'" % (True, line.order_id.id)
                    self.env.cr.execute(query)

                    order.write({'display_extra_line': False})

    # def check_credit_control_cron(self):
    #     sale_order = self.env['sale.order'].search([('state', '=', 'sale')])
    #     for sale in sale_order:
    #         sale._compute_availabe_balance()

    # @api.model
    # @api.depends('partner_id')
    # def _compute_availabe_balance(self):
    #     account_move = self.env['account.move']
    #     for rec in self:
    #         rec.ava_credit_bal = 0.00
    #         credit_limit = rec.credit_limit

    #         invoices = account_move.search([('partner_id', '=', rec.partner_id.id), ('move_type', '=', 'out_invoice'),
    #                                         ('payment_state', 'in', ['not_paid', 'not_paid', 'partial'])])
    #         total_unpaid_invoice = sum([invoice.amount_residual for invoice in invoices])

    #         sales = self.search([('partner_id', '=', rec.partner_id.id), ('state', '=', 'sale')])
    #         # sales = self.search([('partner_id', '=', rec.partner_id.id)])
    #         total_unbilled = 0
    #         # print('sales+++++++++++++++++++', sales)
    #         for s in sales:
    #             # print('s.branch++++++++++++++', s.branch_for)
    #             min_qty = s.extra_charge_ids[0].qty if s.extra_charge_ids else 0
    #             if s.branch_for == 'es':
    #                 print("Type______ELSE______", s.sale_type)
    #                 for line in s.order_line:
    #                     check_qty = line.qty_delivered - line.qty_invoiced
    #                     if check_qty >= min_qty:
    #                         total_unbilled = total_unbilled + (check_qty * line.price_unit)
    #                     else:
    #                         total_unbilled = total_unbilled + (min_qty * line.price_unit)
    #             elif s.branch_for == 'hro':
    #                 print("Type______ELSE_IF_____", s.sale_type)
    #                 for line in s.order_line:
    #                     unit_price = line.price_unit
    #                     if line.sale_amount != 0:
    #                         if line.agency_fee == 'fix':
    #                             unit_price = line.price_unit + line.sale_amount
    #                         if line.agency_fee == 'percentage':
    #                             unit_price = ((line.price_unit * line.sale_amount) / 100) + line.price_unit

    #                     u_price = 0
    #                     if line.product_uom.name == 'Month' or line.product_uom.lumpsum_check:
    #                         u_price = unit_price / 30 / 8
    #                     elif line.product_uom.name == 'Week':
    #                         u_price = unit_price / 7 / 8
    #                     elif line.product_uom.name == 'Days':
    #                         u_price = unit_price / 8
    #                     total_unbilled = total_unbilled + ((line.qty_delivered - line.qty_invoiced) * u_price)
    #             else:
    #                 print("Type______ELSE______", s.sale_type)
    #                 for line in s.order_line:
    #                     total_unbilled = total_unbilled + ((line.qty_delivered - line.qty_invoiced) * line.price_unit)

    #         balance = credit_limit - total_unpaid_invoice - total_unbilled
    #         print('\n\n\nbalance+++++++++++++++', balance)
    #         print('\n\n\ntotal_unbilled+++++++++++++++', total_unbilled)
    #         rec.ava_credit_bal = balance
    #         rec.partner_id.ava_credit_bal = balance
    #         rec.partner_id.ava_unbilled_bal = total_unbilled
            # if rec.partner_id.credit_limit == 0 and rec.partner_id.ava_credit_bal <= 0:
            #     rec.partner_id.credit_block = 'yes'
            # rec.is_hold = False
            # rec.hold_reason = None
            # if rec.partner_id.hold_option == 'hold':
            #     rec.is_hold = True
            #     rec.hold_reason = rec.partner_id.hold_reason


    def _compute_so_sitevisit_count(self):
        for rec in self:
            rec.so_sitevisit_count = self.env['site.visit'].search_count([('lead_id', '=', rec.opportunity_id.id)])

    def action_view_task(self):
        self.ensure_one()

        list_view_id = self.env.ref('project.view_task_tree2').id
        form_view_id = self.env.ref('project.view_task_form2').id

        action = {'type': 'ir.actions.act_window_close'}
        task_projects = self.tasks_ids.mapped('project_id')
        if len(task_projects) == 1 and len(
                self.tasks_ids) > 1:  # redirect to task of the project (with kanban stage, ...)
            action = self.with_context(active_id=task_projects.id).env['ir.actions.actions']._for_xml_id(
                'project.act_project_project_2_project_task_all')
            action['domain'] = [('id', 'in', self.tasks_ids.ids)]
            if action.get('context'):
                eval_context = self.env['ir.actions.actions']._get_eval_context()
                eval_context.update({'active_id': task_projects.id})
                action_context = safe_eval(action['context'], eval_context)
                action_context.update(eval_context)
                action['context'] = action_context
        else:
            action = self.env["ir.actions.actions"]._for_xml_id("project.action_view_task")
            action['context'] = {}  # erase default context to avoid default filter
            action.setdefault('context', {})
            if len(self.tasks_ids) > 1:  # cross project kanban task
                action['views'] = [[False, 'kanban'], [list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'],
                                   [False, 'calendar'], [False, 'pivot']]
            elif len(self.tasks_ids) == 1:  # single task -> form view
                action['views'] = [(form_view_id, 'form')]
                action['res_id'] = self.tasks_ids.id
                action['context'].update({'task_id': self.tasks_ids.id})
        # filter on the task of the current SO
        action['context'].update({'search_default_sale_order_id': self.id})
        return action

    @api.depends('partner_id')
    def _compute_is_customer_onboarding(self):
        for code in self:
            if code.customer_id:
                code.is_customer_onboarding = False
            else:
                code.is_customer_onboarding = True

    @api.onchange('terms_id')
    def onchange_terms_id(self):
        self.note = self.terms_id.description

    @api.depends('partner_id', 'partner_id.document_line_ids')
    def _compute_document_line_ids(self):
        for order in self:
            document_ids = self.env['hr.document.line'].search([('id', 'in', order.partner_id.document_line_ids.ids)])
            order.document_line_ids = document_ids.ids

    def get_total_week_off(self):
        if not self.start_date or not self.end_date:
            return 0.0

        delta = self.end_date - self.start_date
        days_list = []
        total_count = 0
        for i in range(delta.days + 1):
            day = self.start_date + timedelta(days=i)
            days_list.append(calendar.day_name[day.weekday()])
        for day in self.week_of.mapped('name'):
            total_count += days_list.count(day)
        return total_count

    def _compute_week_of_total(self):
        for order in self:
            order.total_week_off = order.get_total_week_off()
            order.total_working_days = order.duration_in_days - order.total_week_off

    def _compute_week_of_no(self):
        for order in self:
            order.week_of_no = len(order.week_of)

    def _compute_duration_in_days(self):
        for order in self:
            duration_in_days = 0.0
            if order.start_date and order.end_date:
                days_diff = (order.end_date - order.start_date).days
                duration_in_days = days_diff + 1 if days_diff > 0 else 0
            order.duration_in_days = duration_in_days

    @api.model
    def create(self, vals):
        branch = self.env.context.get('default_branch_id')
        if branch and vals.get('branch_id'):
            vals.update({'branch_id': branch})
        branch_id = self.env['res.branch'].browse(vals.get('branch_id'))
        if (branch_id and not branch_id.sale_sequence_id):
            raise ValidationError(_('Please set sale sequence on branch!'))
        sequence = branch_id.sale_sequence_id
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = sequence.next_by_id()
        return super(SaleOrder, self).create(vals)

    @api.depends('food', 'accommodation', 'transport')
    def _compute_fat(self):
        for rec in self:
            if rec.food or rec.accommodation or rec.transport:
                rec.fat = 'yes'
            else:
                rec.fat = 'no'

    def _site_count(self):
        for rec in self:
            rec.site_count = self.env['sale.site.inspection'].search_count([('sale_id', '=', rec.id)])

    def _so_agreement_count(self):
        for rec in self:
            rec.so_agreement_count = self.env['sale.agreement'].search_count([('sale_id', '=', rec.id)])

    def site_inspection(self):
        sites = self.env['sale.site.inspection'].search([('sale_id', '=', self.id)])
        return {
            'name': _('Site Inspection'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.site.inspection',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', sites.ids)],
        }

    def so_agreement(self):
        agreements = self.env['sale.agreement'].search([('sale_id', '=', self.id)])
        return {
            'name': _('Agreement'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.agreement',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', agreements.ids)],
        }

    def so_site_visit(self):
        if self.opportunity_id:
            side_visit_ids = self.env['site.visit'].search([('lead_id', '=', self.opportunity_id.id)])
            return {
                'name': _('Site Visit'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'site.visit',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', side_visit_ids.ids)],
            }

    def create_site_inspection(self):
        return {
            'name': ('Site Inspection'),
            'res_model': 'sale.site.inspection',
            'type': 'ir.actions.act_window',
            'context': {
                'default_sale_id': self.id,
                'default_branch_id': self.branch_id.id,
                'default_date': self.date_order,
                'default_company_id': self.partner_id.id,
            },
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref("sale_extended.sale_site_inspection_form_view").id,
        }

    # Point no 6 PS2
    # Comment Site inspection : HRO  [Site Inspection not required]
    def action_confirm(self):
        if self._context.get('action_confirm') == True:
            self._context.get('action_confirm') == True
            return super(SaleOrder, self).action_confirm()
        elif self.branch_for == 'mro':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Site Inspection Wizard',
                'res_model': 'site.inspection.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                    'default_sale_id': self.id, },
                'view_id': self.env.ref('sale_extended.site_inspection_wizard_form_view').id,
                'target': 'new',
            }
        else:
            self._context.get('action_confirm') == True
            return super(SaleOrder, self).action_confirm()

    def compute_onboarding_count(self):
        for rec in self:
            rec.onboarding_count = self.env['customer.onboarding.request'].search_count([('sale_id', '=', rec.id)])

    def onboarding_request(self):
        onboarding_ids = self.env['customer.onboarding.request'].search([('sale_id', '=', self.id)])
        return {
            'name': _('Onboarding Request'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'customer.onboarding.request',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', onboarding_ids.ids)],
        }

    def create_onboarding_request(self):
        return {
            'name': ('Onboarding Request'),
            'res_model': 'customer.onboarding.request',
            'type': 'ir.actions.act_window',
            'context': {
                'default_sale_id': self.id,
                'default_branch_id': self.branch_id.id,
                'default_customer_id': self.customer_id,
                'default_mobile': self.mobile,
                'default_payment_term_id': self.payment_term_id.id,
                'default_partner_id': self.partner_id.id,
                'default_email': self.opportunity_id.email_from if self.opportunity_id else '',
                'default_phone': self.opportunity_id.phone if self.opportunity_id else '',
                'default_website': self.opportunity_id.website if self.opportunity_id else '',
            },
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref("sale_extended.customer_onboarding_request_view_form").id,
        }

    def create_quotation_new(self):
        self.write({'state': 'draft'})

    def create_pre_approval(self):
        self.write({'state': 'pre_approval'})
        # chandni@globalteckz
        for rec in self:
            sapproved_id = self.env['sale.approval'].search([('document_type', '=', 'pre_approval')], limit=1)
            # if not sapproved_id:
            #     raise ValidationError("Setup for Email Sale Approval Pre-Approval Notification")
            customer_approve = sapproved_id.approval_line_ids.mapped('user_id')
            mail_temp = self.env.ref('pways_sale_approval.sending_mail_template')
            quotation_number = rec.name
            customer_name = rec.partner_id.name
            subject = f"Sales Order waiting for Pre-Approval: {quotation_number} for {customer_name}"
            if mail_temp:
                for user in customer_approve:
                    if user.email:
                        body = """
                            <div> 
                                <p>Dear Recipient  """ + str(user.name) + """,
                                <br/><br/>
                                Kindly request your approval for the sales order preapproval of """ + str(
                            customer_name) + """ under """ + str(quotation_number) + """.
                                Your prompt attention to this matter is greatly appreciated.
                                <br></br>
                                Thank you.
                                <br/>
                            <div> """

                        mail_temp.send_mail(self.id, email_values={
                            'email_to': user.email if user else None,
                            'subject': subject,
                            'body_html': body,
                        }, force_send=True)

            # SALES-PERSON
            if rec.user_id:
                body = """
                            <div> 
                                <p>Dear Recipient  """ + str(rec.user_id.name) + """,
                                <br/><br/>
                                Kindly request your approval for the sales order preapproval of """ + str(
                    customer_name) + """ under """ + str(quotation_number) + """.
                                Your prompt attention to this matter is greatly appreciated.
                                <br></br>
                                Thank you.
                                <br/>
                            <div> """

                mail_temp.send_mail(self.id, email_values={
                    'email_to': rec.user_id.email if rec.user_id else None,
                    'subject': subject,
                    'body_html': body,
                }, force_send=True)

    def create_agreement(self):
        agreement_line_ids = []
        # action = self.env["ir.actions.actions"]._for_xml_id("sale_extended.action_view_of_sale_agreement")
        for line in self.order_line:
            agreement_line_ids.append([0, 0, {
                'product_id': line.product_id and line.product_id.id,
                'name': line.product_id.name,
                'product_uom_qty': line.product_uom_qty,
                'period': line.period,
                'duration': line.duration,
                'start_date': line.start_date,
                'end_date': line.end_date,
                'contract_type': line.contract_type,
                'price_unit': line.price_unit,
                'agency_fee': line.agency_fee,
                'sale_amount': line.sale_amount,
                'overtime': line.overtime,
                'std_hrs': line.std_hrs,
                'ot_hrs': line.ot_hrs,
                'employee_id': line.employee_id.id if line.employee_id else False,
                # 'overtime': line.overtime,
                # 'overtime': line.overtime,
                'sp_overtime': line.sp_overtime,
                'tax_id': [(4, t.id) for t in line.tax_id],
                'price_subtotal': line.price_subtotal,
            }])
        return {
            'name': ('Agreement'),
            'res_model': 'sale.agreement',
            'type': 'ir.actions.act_window',
            'context': {
                'default_sale_id': self.id,
                'default_branch_id': self.branch_id.id,
                'default_partner_id': self.partner_id.id,
                'default_food': self.food,
                'default_accommodation': self.accommodation,
                'default_transport': self.transport,
                'default_sale_type': self.sale_type,
                'default_company_id': self.company_id.id,
                'default_payment_term_id': self.payment_term_id.id,
                'default_street': self.company_id.street,
                'default_street2': self.company_id.street2,
                'default_zip': self.company_id.zip,
                'default_city': self.company_id.city,
                'default_state_id': self.company_id.state_id.id,
                'default_country_id': self.company_id.country_id.id,
                'default_agreement_line_ids': agreement_line_ids,
                'default_tax_totals_json': self.tax_totals_json,
            },
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref("sale_extended.sale_agreement_form_view").id,
        }

    def get_agreement(self):
        return self.env['sale.agreement'].search([('sale_id', '=', self.id)], limit=1)

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        down_payment_line_ids = []
        invoiceable_line_ids = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        task = self._context.get('tasks')

        if task:
            order_line = self.order_line.filtered(lambda l: l.task_id in task)
        else:
            order_line = self.order_line
        for line in order_line:  # to select order line based on task
            # print('line+++++++++++++++++', line, line.product_uom, line.product_uom.lumpsum_check)

            if line.product_uom.lumpsum_check:
                invoiceable_line_ids.append(line.id)
                continue
            if line.display_type == 'line_section':
                # Only invoice the section if one of its lines is invoiceable
                pending_section = line
                continue
            if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
                continue
            if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final) or line.display_type == 'line_note':
                if line.is_downpayment:
                    # Keep down payment lines separately, to put them together
                    # at the end of the invoice, in a specific dedicated section.
                    down_payment_line_ids.append(line.id)
                    continue
                if pending_section:
                    invoiceable_line_ids.append(pending_section.id)
                    pending_section = None
                invoiceable_line_ids.append(line.id)
        return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    period = fields.Integer(string="Period")
    duration = fields.Selection(
        [('hour', 'Hour'), ('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year')], default='hour',
        string="Duration")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    contract_type = fields.Selection([('limited', 'Limited'), ('unlimited', 'Unlimited')], default='limited',
                                     string="Contract")
    agency_fee = fields.Selection([('fix', 'Fix'), ('percentage', 'Percentage')], default='fix', string="Agency Fee")
    sale_amount = fields.Float(string='Amount')
    overtime = fields.Float(string="Overtime")
    sp_overtime = fields.Float(string="Special Overtime")
    std_hrs = fields.Float(string="Std hrs", default=8)
    std_working_hrs = fields.Float(string="Std Working hrs")
    ot_hrs = fields.Float(string="OT hrs")
    waste_type_id = fields.Many2one('waste.type')
    equipment_type_id = fields.Many2one('equipment.type', string="Equip. Type")
    vehicle_type_id = fields.Many2one('vehicle.type')
    frequency_id = fields.Many2one('so.frequency', string="Frequency")
    frequency = fields.Selection(
        [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('on_call', 'On Call')], default='daily',
        string="Freq")
    trip_no = fields.Float(string="No Of Trip")
    no_of_bins = fields.Float(string="No. Of Bins")
    weekday = fields.Selection(
        [('1', 'Monday'), ('2', 'Tuesday'), ('3', 'Wednesday'), ('4', 'Thursday'), ('5', 'Friday'), ('6', 'Saturday'),
         ('7', 'Sunday'), ], string='Day Name', required=True, default='1')
    time = fields.Char(string="Time")
    # location_id = fields.Many2one('res.partner', string="Location")
    partner_location_id = fields.Many2one('contact.location', string="Location")
    # frequency_id = fields.Many2one('frequency.days', string="Frequency")
    month_days = fields.Integer(string='Month Days')
    trade_test = fields.Boolean('Trade Test')
    own_bin = fields.Char('Own Bin')
    customer_bin = fields.Char('Customer Bin')

    # Globalteckz
    display_extra_line = fields.Boolean(string="Dispaly Extra lines", default=False)
    active = fields.Boolean(string="Archive/Unarchive", default=True)

    def duplicate_order_line(self):
        duplicated_lines = self.env['sale.order.line']

        for line in self:
            special_sale_line_id = self.env['sale.order.line'].search([('product_id', '=',
                                                                        self.env.ref(
                                                                            'project_extended.product_soc_product_template').id or False)])
            normal_sale_line_id = self.env['sale.order.line'].search([('product_id', '=',
                                                                       self.env.ref(
                                                                           'project_extended.product_noc_product_template').id or False)])
            duplicated_lines = self.env['sale.order.line']

            new_line = line.copy(default={'order_id': line.order_id.id})

            if line.order_id.state == 'draft':
                new_description = "%(line_product_name)s" % {
                    'line_product_name': new_line.product_id.name
                }
                new_line.write({'name': new_description})
                duplicated_lines += new_line
                duplicated_lines.write({'name': new_description, 'employee_id': False})

                task = line.task_id
                # so addition line charges add in sale order duplicate order
                additional = self.env['so.additional.charges'].search(
                    [('so_line_id', '=', line.id), ('so_id', '=', line.order_id.id)])

                for so_addditional in additional:
                    if not special_sale_line_id or normal_sale_line_id:
                        duplicated_charge_line = so_addditional.copy()
                        duplicated_charge_line.write({'so_line_id': new_line.id, 'so_id': new_line.order_id.id})

            if line.order_id.state == 'sale':
                new_description = "%(line_product_name)s -  %(task_name)s " % {
                    'line_product_name': new_line.product_id.name,
                    'task_name': new_line.task_id.seq_code,
                }
                new_line.write({'name': new_description})
                duplicated_lines += new_line
                duplicated_lines.write({'name': new_description, 'employee_id': False})

                task = line.task_id
                # so addition line charges add in sale order duplicate order
                additional = self.env['so.additional.charges'].search(
                    [('so_line_id', '=', line.id), ('so_id', '=', line.order_id.id)])

                for so_addditional in additional:
                    duplicated_charge_line = so_addditional.copy()
                    duplicated_charge_line.write({'so_line_id': new_line.id, 'so_id': new_line.order_id.id})

    def _timesheet_create_task_prepare_values(self, project):
        res = super(SaleOrderLine, self)._timesheet_create_task_prepare_values(project)
        self.ensure_one()
        planned_hours = self._convert_qty_company_hours(self.company_id)
        sale_line_name_parts = self.name.split('\n')
        title = sale_line_name_parts[0] or self.product_id.name
        description = '<br/>'.join(sale_line_name_parts[1:])
        return {
            'name': title if project.sale_line_id else '%s: %s' % (self.order_id.name or '', title),
            'planned_hours': planned_hours,
            'partner_id': self.order_id.partner_id.id,
            'email_from': self.order_id.partner_id.email,
            'description': description,
            'project_id': project.id,
            'sale_line_id': self.id,
            'sale_order_id': self.order_id.id,
            'company_id': project.company_id.id,
            'user_ids': False,  # force non assigned task, as created as sudo()
            'waste_type_id': self.waste_type_id and self.waste_type_id.id,
            'equipment_type_id': self.equipment_type_id and self.equipment_type_id.id,
            'vehicle_type_id': self.vehicle_type_id and self.vehicle_type_id.id,
            'partner_location_id': self.partner_location_id.id,
            'frequency_id': self.frequency_id.id,
            'branch_id': self.order_id.branch_id and self.order_id.branch_id.id,
            'hazardous': self.product_id.hazardous,
            'no_of_trip': self.trip_no,
            'weekday': self.weekday,
            'time': self.time,
            'own_bin': self.own_bin,
            'customer_bin': self.customer_bin,
            
        }

    @api.depends('analytic_line_ids.project_id', 'project_id.pricing_type')
    def _compute_qty_delivered(self):
        # added qty_delivered base on timesheet after update emp repoted
        lines_by_analytic = self.filtered(lambda sol: sol.qty_delivered_method == 'timesheet')
        for line in lines_by_analytic:
            timesheet_id = self.env['account.analytic.line'].search([('so_line', 'in', line.ids)])
            timesheet_id.write({'product_uom_id': line.product_uom.id})
        super(SaleOrderLine, self)._compute_qty_delivered()

    def _purchase_service_create(self, quantity=False):
        """ On Sales Order confirmation, some lines (services ones) can create a purchase order line and maybe a purchase order.
            If a line should create a RFQ, it will check for existing PO. If no one is find, the SO line will create one, then adds
            a new PO line. The created purchase order line will be linked to the SO line.
            :param quantity: the quantity to force on the PO line, expressed in SO line UoM
        """
        PurchaseOrder = self.env['purchase.order']
        supplier_po_map = {}
        sale_line_purchase_map = {}
        for line in self:
            line = line.with_company(line.company_id)
            # determine vendor of the order (take the first matching company and product)
            suppliers = line.product_id._select_seller(quantity=line.product_uom_qty, uom_id=line.product_uom)
            if not suppliers:
                raise UserError(
                    _("There is no vendor associated to the product %s. Please define a vendor for this product.") % (
                        line.product_id.display_name,))
            supplierinfo = suppliers[0]
            partner_supplier = supplierinfo.name  # yes, this field is not explicit .... it is a res.partner !

            # determine (or create) PO
            purchase_order = supplier_po_map.get(partner_supplier.id)
            if not purchase_order:
                purchase_order = PurchaseOrder.search([
                    ('partner_id', '=', partner_supplier.id),
                    ('state', '=', 'draft'),
                    ('company_id', '=', line.company_id.id),
                ], limit=1)
            if 'service' not in self.mapped('product_id').mapped('detailed_type'):
                if not purchase_order:
                    values = line._purchase_service_prepare_order_values(supplierinfo)
                    purchase_order = PurchaseOrder.create(values)
                else:  # update origin of existing PO
                    so_name = line.order_id.name
                    origins = []
                    if purchase_order.origin:
                        origins = purchase_order.origin.split(', ') + origins
                    if so_name not in origins:
                        origins += [so_name]
                        purchase_order.write({
                            'origin': ', '.join(origins)
                        })
                supplier_po_map[partner_supplier.id] = purchase_order

                # add a PO line to the PO
                values = line._purchase_service_prepare_line_values(purchase_order, quantity=quantity)
                purchase_line = line.env['purchase.order.line'].create(values)

                # link the generated purchase to the SO line
                sale_line_purchase_map.setdefault(line, line.env['purchase.order.line'])
                sale_line_purchase_map[line] |= purchase_line
            continue
        return sale_line_purchase_map

    def _prepare_invoice_line(self, **optional_values):
        self.ensure_one()
        # employee_id = False
        employee_id = self.employee_id.id if self.employee_id else False

        # Handle advance billing for HRO branch
        if (self.order_id.branch_id.branch_for == 'hro' and self.order_id.advance_billing and self.product_id.code not in ['SOC', 'NOC']):
            res = {
                'display_type': self.display_type,
                'sequence': self.sequence,
                'name': "%s (Advance Billing)" % self.name,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom.id,
                'task_id': self.task_id.id,
                'quantity': self.product_uom_qty,
                'discount': self.discount,
                'price_unit': self.price_unit,
                'tax_ids': [(6, 0, self.tax_id.ids)],
                'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
                'sale_line_ids': [(4, self.id)],
                'equipment_type_id': self.equipment_type_id.id or False,
                'employee_id': employee_id,
            }
            if self.order_id.analytic_account_id:
                res['analytic_account_id'] = self.order_id.analytic_account_id.id
            if optional_values:
                res.update(optional_values)
            if self.display_type:
                res['account_id'] = False
            # Skip if subtotal is zero
            # if (res['price_unit'] * res['quantity']) == 0:
            #     return False
            return res
        
        # original logic
        inv_date = self.order_id.inv_date
        timesheet_ids = self.order_id.order_line.task_id.timesheet_ids
        # timesheet_ids = timesheet_ids.filtered(lambda time: time.date >= self.date_start_invoice_timesheet and time.date <= self.date_end_invoice_timesheet)
        # total_timesheet_sum = sum(timesheet_ids.mapped('units_amounts'))

        qty_delivered = self.qty_delivered
        # print ("Inv date_______________", inv_date)
        total_month_days = calendar.monthrange(inv_date.year, inv_date.month)[1]
        if inv_date:
            task_id = self.env['project.task'].search([('sale_line_id', '=', self.id)])
            if len(task_id.shift_allocation_ids.ids) > 0:
                shift_hours = len(task_id.shift_allocation_ids.dayofweek_ids.filtered(
                    lambda x: x.date and x.date >= fields.Datetime.now().replace(year=inv_date.year,
                                                                                 month=inv_date.month,
                                                                                 day=1).date() and x.date <= fields.Datetime.now().replace(
                        year=inv_date.year, month=inv_date.month, day=total_month_days).date()).ids) * self.std_hrs
                qty_delivered += shift_hours
            if len(task_id.public_holidays_ids.ids) > 0:
                public_holidays_days = 1
                for public_holidays in task_id.public_holidays_ids:
                    public_holidays_count = public_holidays.date_to - public_holidays.date_from
                    public_holidays_days += public_holidays_count.days
                total_public_holidays_days = public_holidays_days * self.std_hrs
                qty_delivered += total_public_holidays_days
        if self.product_uom.id == self.env.ref("sale_extended.product_uom_month").id:
            total_month_days = calendar.monthrange(inv_date.year, inv_date.month)[1]
            price_unit = (self.price_unit / total_month_days / self.std_hrs) * qty_delivered
            quantity = self.product_uom_qty
        else:
            if self.task_id.timesheet_ids:
                # timesheet_start_date = self._context.get('timesheet_start_date')
                # timesheet_end_date = self._context.get('timesheet_end_date')
                price_unit = self.price_unit
                # sum = 0
                # for timesheet in self.task_id.timesheet_ids.filtered(lambda x: x.date >= timesheet_start_date and x.date <= timesheet_end_date):
                #     print("!!!!!!!!!!!!!\n\n\n\n\n\n\n\n", timesheet)
                #     sum += timesheet.units_amounts
                quantity = self.qty_delivered
            else:
                extra_charge = self.env['so.extra.charge.wizard'].search([('so_line_id', '=', self.id)], limit=1)
                quantity = extra_charge.qty
                price_unit = extra_charge.price

        if self.product_uom.lumpsum_check:
            quantity = 1

        if self.order_id.branch_id.branch_for == 'es':
            new_description = "%(line_product_name)s /  %(waste_type_id)s / %(partner_location_id)s" % {
                'line_product_name': self.name,
                'waste_type_id': 'Waste Type : ' + (self.waste_type_id.name or 'N/A'),
                'partner_location_id': 'Location : ' + (self.partner_location_id.name or 'N/A'),
            }
            timesheet_start_date = self._context.get('timesheet_start_date')
            timesheet_end_date = self._context.get('timesheet_end_date')
            sum = 0
            for timesheet in self.task_id.timesheet_ids.filtered(
                    lambda x: x.date >= timesheet_start_date and x.date <= timesheet_end_date):
                sum += timesheet.unit_amount
            quantity = sum
        else:
            new_description = self.name

        if self.order_id.branch_id.branch_for == 'hro':
            sum = 0
            timesheet_start_date = self._context.get('timesheet_start_date')
            timesheet_end_date = self._context.get('timesheet_end_date')

            if self.product_id.code == 'NOC':
                new_description = self.name
                # Sum the overtime for weekdays only (ot_types identifies weekdays)
                for overtime in self.task_id.overtime_lines_ids.filtered(
                        lambda x: x.ot_date >= timesheet_start_date and x.ot_date <= timesheet_end_date and x.ot_type.code == 'NOD'):
                    sum += overtime.ot_hour
                quantity = sum

            elif self.product_id.code == 'SOC':
                new_description = self.name
                # Sum the overtime for weekend days only (ot_types identifies weekends and sepcial)
                for overtime in self.task_id.overtime_lines_ids.filtered(
                        lambda x: x.ot_date >= timesheet_start_date and x.ot_date <= timesheet_end_date and x.ot_type.code in ['WDS', 'SPHD']):
                    sum += overtime.ot_hour
                quantity = sum

            else:
                new_description = self.name
                # Sum the regular timesheet values for other products
                for timesheet in self.task_id.timesheet_ids.filtered(
                        lambda x: x.date >= timesheet_start_date and x.date <= timesheet_end_date):
                    sum += timesheet.unit_amount
                quantity = sum

        res = {
            'display_type': self.display_type,
            'sequence': self.sequence,
            # 'name': self.name,
            'name': new_description,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'task_id': self.task_id.id,
            'quantity': quantity,
            'discount': self.discount,
            'price_unit': price_unit,
            'tax_ids': [(6, 0, self.tax_id.ids)],
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'sale_line_ids': [(4, self.id)],
            'equipment_type_id': self.equipment_type_id.id or False,
            'employee_id': employee_id,
        }
        if self.order_id.analytic_account_id:
            res['analytic_account_id'] = self.order_id.analytic_account_id.id
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        # 📌 Skip if subtotal is zero
        # if (res['price_unit'] * res['quantity']) == 0:
        #     return False
        return res

    def _timesheet_create_project(self):
        project_id = super(SaleOrderLine, self)._timesheet_create_project()
        if project_id and project_id.sale_order_id:
            project_id.write({
                'branch_id': project_id.sale_order_id.branch_id.id,
                'contact_name': project_id.sale_order_id.contact_name,
                'mobile': project_id.sale_order_id.mobile,
            })
        return project_id


class SiteWizard(models.Model):
    _name = "site.inspection.wizard"
    _description = "Site Inspection Wizard"

    user_id = fields.Many2one('res.users', 'Assignee')
    sale_id = fields.Many2one('sale.order', 'Sale Order')
    crm_id = fields.Many2one('crm.lead', 'Crm Lead')
    site_inspection_id = fields.Many2one('sale.site.inspection', 'Site Inspection')
    site_visit_id = fields.Many2one('site.visit', string='Site Visit')

    # PS2 Point no 6
    def send_mail_to_assignee(self):
        vals = {}
        _model = self._context.get('active_model')

        model_id = False
        if _model == 'sale.order':
            vals.update(
                {'sale_id': self.sale_id.id, 'date': self.sale_id.date_order, 'assign_id': self.user_id.id,
                 'company_id': self.sale_id.partner_id.id, 'branch_id': self.sale_id.branch_id.id, })
            site_id = self.env['sale.site.inspection'].create(vals)
            self.update({'site_inspection_id': site_id.id})
            model_id = self.env['ir.model'].sudo().search([('model', '=', 'sale.site.inspection')], limit=1)
        if _model == 'crm.lead':
            vals.update({'lead_id': self.crm_id.id, 'date': datetime.now(), 'branch_id': self.crm_id.branch_id.id,
                         'partner_id': self.crm_id.partner_id.id, })
            site_id = self.env['site.visit'].create(vals)
            self.update({'site_visit_id': site_id.id})
            model_id = self.env['ir.model'].sudo().search([('model', '=', 'site.visit')], limit=1)

        activity_vals = {'res_model_id': model_id.id,
                         'res_model': 'sale.site.inspection',
                         'res_id': site_id.id if site_id else None,
                         'res_name': 'Site Created Please Check!!!',
                         'user_id': self.user_id.id,
                         # 'activity_type_id': contract_approval_id.activity_type_id.id,
                         'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')}

        activity_id = self.env['mail.activity'].create(activity_vals)
        # Globalteckz
        """ Site Inspection using Generated Notification for Company"""
        if self.env['email.notification.management'].search([]):
            search_ids = self.env['email.notification.management'].search([])[-1].id
            email_mgmt_id = self.env['email.notification.management'].browse(search_ids)

            if email_mgmt_id:
                customer_service_email = email_mgmt_id.customer_service_email
                scheduler_email = email_mgmt_id.scheduler_email

                mail_temp = self.env.ref('pways_sale_approval.sending_mail_template')

                if mail_temp:
                    quotation_number = self.sale_id.name
                    customer_name = self.sale_id.partner_id.name
                    subject = f"Notification: Sales Order Generated {quotation_number} for {customer_name}"
                    """ Customer Service Email """
                    if customer_service_email:
                        body = """
                            <div> 
                                <p>Dear Recipient,
                                <br/>
                                <br/>
                         
                                Inform you that a sales order has been successfully generated in your name """ + str(
                            customer_name) + """ under """ + str(quotation_number) + """ <br/>.
                                Please review the details of the sales order and proceed with the necessary actions as soon as possible.
    
                                <br></br>
                                Thank you.
                                <br/>
                                <br/>
                            <div> """
                        mail_temp.send_mail(self.id, email_values={
                            'email_to': customer_service_email,
                            'subject': subject,
                            'body_html': body,
                        }, force_send=True)
                    """ Scheduler Email """
                    if scheduler_email:
                        body = """
                            <div> 
                                <p>Dear Recipient,
                                <br/>
                                <br/>
                         
                                Inform you that a sales order has been successfully generated in your name """ + str(
                            customer_name) + """ under """ + str(quotation_number) + """ <br/>.
                                Please review the details of the sales order and proceed with the necessary actions as soon as possible.
    
                                <br></br>
                                Thank you.
                                <br/>
                                <br/>
                            <div> """
                        mail_temp.send_mail(self.id, email_values={
                            'email_to': scheduler_email,
                            'subject': subject,
                            'body_html': body,
                        }, force_send=True)

        # mail_template = self.env.ref('sale_extended.site_inspection_email_template')
        # mail_template.send_mail(self.id, force_send=True)
        if _model == 'sale.order':
            self.sale_id.with_context({'action_confirm': True}).action_confirm()

    def confirm_dont_send(self):
        self.sale_id.with_context({'action_confirm': True}).action_confirm()


# sale order to invoice update with new changes flow


#####################################################

# self.env.cr.execute("""
#     UPDATE account_move_line
#     SET name = %s-%s,
#         quantity = %s,
#         price_unit = %s,
#         price_subtotal = %s
#     WHERE id = %s
# """, (inv_line.product_id.name, employee.name, total_qty, daily_rate, price_subtotal, inv_line.id))

# print(f"Updated first invoice line: {inv_line.id} with qty: {total_qty} and daily rate: {daily_rate}")
# breakpoint()

# first_employee = True
# print("values['soline_id']", values['soline_id'])
# print("Employe_____111111111", employee, inv_line.name)
# for so_line_id in inv_line.sale_line_ids:
#     print("so_line_id______", so_line_id)
#     daily_rate = inv_line.price_unit / total_month_days
#     print("daily_rate____________", daily_rate)
#     # Update the invoice lines based on the first employee and subsequent employees
#     total_qty = values['working_days'] + values['holidays'] + values['week_off_days'] + values['leave_days']
#     print("total_qty>>>>>>>>>>>>>>>>", total_qty)
#     if total_qty == total_month_days:
#         total_employee_qty_count += 1
#         print("total_employee_qty_count_>>>>>>>>>>\n", total_employee_qty_count)
#         if first_employee:
#             print("Employe_____222222222222", employee, values, inv_line.name)
#             if total_employee_qty_count > 0:
#                 # print("IF_________________first line", inv_line, total_employee_qty_count, so_line_id.price_unit)
#                 price_subtotal = total_employee_qty_count * so_line_id.price_unit

#                 # Update account_move_line for the first employee
#                 self.env.cr.execute("""
#                     UPDATE account_move_line
#                     SET quantity = %s,
#                         price_unit = %s,
#                         price_subtotal = %s
#                     WHERE id = %s
#                 """, (total_employee_qty_count, so_line_id.price_unit, price_subtotal, inv_line.id))

#                 print(f"Updated first invoice line: {inv_line.id} with qty: {total_qty} and daily rate: {daily_rate}")
#                 first_employee = False  # Set to False after the first employee is processed
#             else:
#                 print("ELSE______________first line", inv_line, total_qty, daily_rate)
#                 price_subtotal = total_qty * daily_rate

#                 # Update account_move_line when no employee count matches total month days
#                 self.env.cr.execute("""
#                     UPDATE account_move_line
#                     SET name = %s-%s,
#                         quantity = %s,
#                         price_unit = %s,
#                         price_subtotal = %s
#                     WHERE id = %s
#                 """, (inv_line.product_id.name, employee.name, total_qty, daily_rate, price_subtotal, inv_line.id))

#                 print(f"Updated first invoice line: {inv_line.id} with qty: {total_qty} and daily rate: {daily_rate}")
#                 first_employee = False
#         else:
#             # For subsequent employees, prepare new invoice lines
#             print("ELSE_____________", total_qty, daily_rate)
#             invoice_vals.append((0, 0, {
#                 'name': "%s-%s" % (inv_line.product_id.name, employee.name),
#                 'price_unit': daily_rate,
#                 'quantity': total_qty,
#                 'product_id': inv_line.product_id.id,
#                 'product_uom_id': inv_line.product_uom_id.id,
#                 'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
#                 'analytic_account_id': order.analytic_account_id.id or False,
#             }))
# breakpoint()
# inv.write({'invoice_line_ids': invoice_vals,
#            'custom_invoice_date': self.inv_date,
#            'invoice_date': self.inv_date,
#            'date': self.date,
#            })
# return invoice_vals

#                 if first_employee:
#                     if total_employee_qty_count > 0:
#                         print("IF_________________first line", inv_line, total_employee_qty_count, so_line_id.price_unit)
#                         price_subtotal = total_employee_qty_count * so_line_id.price_unit
#                         self.env.cr.execute("""
#                                 UPDATE account_move_line
#                                 SET quantity = %s,
#                                     price_unit = %s,
#                                     price_subtotal = %s
#                                 WHERE id = %s
#                             """, (total_employee_qty_count, so_line_id.price_unit, price_subtotal, inv_line.id))
#                         print(f"Updated first employee invoice line: {inv_line.id} with qty: {total_qty} and daily rate: {daily_rate}")
#                         first_employee = False
#                     if total_employee_qty_count == 0:
#                         print("ELSE______________first line", inv_line, total_qty, daily_rate)
#                         price_subtotal = total_qty * daily_rate
#                         self.env.cr.execute("""
#                                 UPDATE account_move_line
#                                 SET quantity = %s,
#                                     price_unit = %s,
#                                     price_subtotal = %s
#                                 WHERE id = %s
#                             """, (total_qty, daily_rate, price_subtotal, inv_line.id))
#                         print(f"Updated first employee invoice line: {inv_line.id} with qty: {total_qty} and daily rate: {daily_rate}")
#                         first_employee = False
#                 else:
#                     print("ELSE_____________", total_qty, daily_rate)
#                     invoice_vals = invoice_vals + [(0, 0, {
#                         'name': "%s-%s" % (inv_line.product_id.name, inv_line.employee_id.name),
#                         'price_unit': daily_rate,
#                         'quantity': total_qty,
#                         'product_id': inv_line.product_id.id,
#                         'product_uom_id': inv_line.product_uom_id.id,
#                         'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
#                         'analytic_account_id': order.analytic_account_id.id or False,
#                     })]
# inv.write({'invoice_line_ids': invoice_vals,
#            'custom_invoice_date': self.inv_date,
#            'invoice_date': self.inv_date,
#            'date': self.date,
#            })
# return invoice_vals

# inv_date = self.inv_date if self.inv_date else self.date  # invoice date or current date
# qty_inv = 0.0
# if inv_line.product_uom_id.name == 'Month':
#     if inv_date:
#         total_month_days = monthrange(inv_date.year, inv_date.month)[1]
#         daily_rate = inv_line.price_unit / total_month_days
#     print('!!!!!!!!!\n\n', inv_line)

#     self.env.cr.execute("""
#             UPDATE account_move_line
#             SET quantity = %s,
#                 price_unit = %s
#             WHERE id = %s
#         """, (total_qty, daily_rate, inv_line.id))

#     print(f"Updated first employee invoice line: {inv_line.id} with qty: {total_qty} and daily rate: {daily_rate}")
#     first_employee = False
# else:
#     invoice_vals = invoice_vals + [(0, 0, {
#         'name': "%s-%s" % (inv_line.product_id.name, inv_line.employee_id.name),
#         'price_unit': daily_rate,
#         'quantity': total_qty,
#         'product_id': inv_line.product_id.id,
#         'product_uom_id': inv_line.product_uom_id.id,
#         'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
#         'analytic_account_id': order.analytic_account_id.id or False,
#     })]
#     print("___invoice_vals_",invoice_vals)

# print('\n\ninvoice_vals++++++Month uom bundle sale type value++++++++++', invoice_vals)
# inv.write({'invoice_line_ids': invoice_vals,
#            'custom_invoice_date': self.inv_date,
#            'invoice_date': self.inv_date,
#            'date': self.date,
#            })
# return invoice_vals


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_value_compute = fields.Boolean('value')
    cost_plus_line_id = fields.Many2one('cost.plus.line', string="Cost Plus Line")


class AccountMove(models.Model):
    _inherit = 'account.move'

    def write(self, vals):
        record_id = super(AccountMove, self).write(vals)
        line_ids = self.invoice_line_ids.filtered(lambda sol: sol.extra_charge_product_id)
        for line in line_ids:
            ref_product_id = self.invoice_line_ids.filtered(
                lambda inv_line: inv_line.product_id.id == line.extra_charge_product_id.id and inv_line.id != line.id)
            if line.is_value_compute == False:
                before_qty = ref_product_id.quantity
                ref_product_id.quantity = ref_product_id.quantity - line.quantity
                for move_line_id in ref_product_id.move_id.line_ids:
                    if move_line_id.debit:
                        move_line_id.debit = move_line_id.debit - line.quantity * ref_product_id.price_unit
                    line.is_value_compute = True
        return record_id
