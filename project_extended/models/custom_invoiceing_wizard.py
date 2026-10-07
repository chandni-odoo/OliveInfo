# -*- coding: utf-8 -*-
import logging
from calendar import monthrange
from collections import defaultdict
from odoo import models, fields
from odoo.exceptions import UserError

from odoo.odoo import api

_logger = logging.getLogger(__name__)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    date = fields.Date(string="Accounting Date")
    inv_date = fields.Date(string="Invoice Date")


    def _prepare_invoice_charge_values(self, order, name, amount, so_line, inv):
        if so_line.charge_date and so_line.charge_date >= self.date_start_invoice_timesheet and so_line.charge_date <= self.date_end_invoice_timesheet:
            invoice_vals = [(0, 0, {
                'name': "%s - %s" % (so_line.product_id.name, so_line.so_line_id.product_id.name),
                'price_unit': so_line.price_unit,
                'quantity': so_line.quantity,
                'product_id': so_line.product_id.id,
                'product_uom_id': so_line.product_uom.id,
                'tax_ids': [(6, 0, so_line.so_line_id.tax_id.ids)],
                'sale_line_ids': [(6, 0, [so_line.so_line_id.id])],
                'analytic_tag_ids': [(6, 0, so_line.so_line_id.analytic_tag_ids.ids)],
                'analytic_account_id': order.analytic_account_id.id or False,
                'equipment_type_id': so_line.so_line_id.equipment_type_id.id or False,
            })]
            inv.write({
                'invoice_line_ids': invoice_vals,
                'custom_invoice_date': self.inv_date,
                'invoice_date': self.inv_date,
                'date': self.date,
            })
            return invoice_vals

    def _prepare_agency_fee_values(self, order, name, amount, so_line, inv):
        if order.sale_type == 'cost_plus' and so_line._name == 'sale.order.line' and so_line.sale_amount > 0:
            product_id = self.env.ref('project_extended.product_agency_template')
            amount = so_line.sale_amount
            if so_line.agency_fee == 'percentage':
                amount = so_line.price_unit * so_line.sale_amount / 100
            if so_line.agency_fee == 'fix':
                amount = so_line.sale_amount
            if amount > 0:
                invoice_vals = [(0, 0, {
                    'name': "%s - %s - %s - %s" % (
                        so_line.product_id.name, product_id.name, so_line.agency_fee, so_line.employee_id.name),
                    'price_unit': amount,
                    'quantity': 1.0,
                    'equipment_type_id': so_line.equipment_type_id.id or False,
                    'product_id': product_id.id,
                    'product_uom_id': so_line.product_uom.id,
                    'tax_ids': [(6, 0, so_line.tax_id.ids)],
                    'sale_line_ids': [(6, 0, [so_line.id])],
                    'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                    'analytic_account_id': order.analytic_account_id.id or False,
                })]
                inv.write({'invoice_line_ids': invoice_vals})
                return invoice_vals
        else:
            return []

    @api.model
    def remove_invoice_line(self, invoice_id, invoice_line_id):
        # Get the invoice
        invoice = self.env['account.move'].browse(invoice_id)

        # Ensure the invoice is in draft state
        if invoice.state != 'draft':
            raise UserError("You can only delete lines from a draft invoice.")

        # Get the invoice line
        invoice_line = self.env['account.move.line'].browse(invoice_line_id)

        # Ensure the invoice line is part of the invoice
        if invoice_line.move_id.id != invoice_id:
            raise UserError("Invoice line does not belong to the specified invoice.")

        # Delete the invoice line
        invoice_line.unlink()

        return True

    def _prepare_charge_values(self, order, name, amount, extra_charge_id, inv):
        so_line = extra_charge_id.so_line_id
        invoice_vals = []
        if extra_charge_id.charge_type == 'month':
            timesheet_ids = extra_charge_id.so_line_id.task_id.timesheet_ids
            timesheet_ids = timesheet_ids.filtered(lambda time: self.date_start_invoice_timesheet <= time.date <= self.date_end_invoice_timesheet)
            total_timesheet_sum = sum(timesheet_ids.mapped('units_amounts'))
            if timesheet_ids:
                if extra_charge_id.charge == 'qty':
                    if total_timesheet_sum > extra_charge_id.qty:
                        extra_charge_product_id = self.env.ref('custom_trip.product_extra_charge_product')
                        name = "%s - %s" % (extra_charge_product_id.name, so_line.product_id.name),
                        quantity = total_timesheet_sum - extra_charge_id.qty
                        price_unit = extra_charge_id.ec_price
                        product_id = extra_charge_product_id.id
                        extra_charge_product_id = so_line.product_id.id
                    else:
                        minimum_charge_product_id = self.env.ref('custom_trip.product_minimum_charge_product')
                        name = "%s - %s" % (minimum_charge_product_id.name, so_line.product_id.name),
                        price_unit = extra_charge_id.price
                        quantity = extra_charge_id.qty - total_timesheet_sum
                        product_id = minimum_charge_product_id.id
                        extra_charge_product_id = False
                    if quantity > 0:
                        invoice_vals += [(0, 0, {
                            'name': name,
                            'price_unit': price_unit,
                            'quantity': quantity,
                            'product_id': product_id,
                            'extra_charge_product_id': extra_charge_product_id,
                            'product_uom_id': so_line.product_uom.id,
                            'tax_ids': [(6, 0, so_line.tax_id.ids)],
                            'sale_line_ids': [(6, 0, [so_line.id])],
                            'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                            'analytic_account_id': order.analytic_account_id.id or False,
                            'equipment_type_id': so_line.equipment_type_id.id or False,
                        })]
                if extra_charge_id.charge == 'amount':
                    for line in inv.invoice_line_ids:
                        if len(line.sale_line_ids.filtered(lambda line_so: line_so.id == so_line.id)) > 0 and extra_charge_id.price > line.price_subtotal:
                            minimum_charge_product_id = self.env.ref('custom_trip.product_minimum_charge_product')
                            name = "%s - %s" % (minimum_charge_product_id.name, so_line.product_id.name),
                            price_unit = extra_charge_id.price - line.price_subtotal
                            quantity = 1
                            product_id = minimum_charge_product_id.id
                            extra_charge_product_id = False
                            invoice_vals += [(0, 0, {
                                'name': name,
                                'price_unit': price_unit,
                                'quantity': quantity,
                                'product_id': product_id,
                                'extra_charge_product_id': extra_charge_product_id,
                                'product_uom_id': so_line.product_uom.id,
                                'tax_ids': [(6, 0, so_line.tax_id.ids)],
                                'sale_line_ids': [(6, 0, [so_line.id])],
                                'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                                'analytic_account_id': order.analytic_account_id.id or False,
                                'equipment_type_id': so_line.equipment_type_id.id or False,
                            })]
        elif extra_charge_id.charge_type in ['day', 'full_day']:
            timesheet_ids = extra_charge_id.so_line_id.task_id.timesheet_ids
            timesheet_ids = timesheet_ids.filtered(lambda time: self.date_start_invoice_timesheet <= time.date <= self.date_end_invoice_timesheet)
            extra_qty = sum(timesheet_ids.filtered(lambda timesheet_id: timesheet_id.units_amounts > extra_charge_id.qty).mapped('units_amounts'))
            minimum_qty = sum(timesheet_ids.filtered(lambda timesheet_id: timesheet_id.units_amounts < extra_charge_id.qty).mapped('units_amounts'))
            if extra_qty > 0:
                extra_charge_product_id = self.env.ref('custom_trip.product_extra_charge_product')
                name = "%s - %s" % (extra_charge_product_id.name, so_line.product_id.name),
                quantity = extra_qty
                price_unit = extra_charge_id.ec_price
                product_id = extra_charge_product_id.id
                extra_charge_product_id = so_line.product_id.id
                if quantity > 0:
                    invoice_vals += [(0, 0, {
                        'name': name,
                        'price_unit': price_unit,
                        'extra_charge_product_id': extra_charge_product_id,
                        'quantity': quantity - extra_charge_id.qty,
                        'product_id': product_id,
                        'product_uom_id': so_line.product_uom.id,
                        'tax_ids': [(6, 0, so_line.tax_id.ids)],
                        'sale_line_ids': [(6, 0, [so_line.id])],
                        'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                        'analytic_account_id': order.analytic_account_id.id or False,
                        'equipment_type_id': so_line.equipment_type_id.id or False,
                    })]
            if minimum_qty > 0:
                minimum_charge_product_id = self.env.ref('custom_trip.product_minimum_charge_product')
                name = "%s - %s" % (minimum_charge_product_id.name, so_line.product_id.name),
                price_unit = extra_charge_id.price
                quantity = minimum_qty
                product_id = minimum_charge_product_id.id
                if quantity > 0:
                    invoice_vals += [(0, 0, {
                        'name': name,
                        'price_unit': price_unit,
                        'quantity': quantity,
                        'product_id': product_id,
                        'product_uom_id': so_line.product_uom.id,
                        'tax_ids': [(6, 0, so_line.tax_id.ids)],
                        'sale_line_ids': [(6, 0, [so_line.id])],
                        'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                        'analytic_account_id': order.analytic_account_id.id or False,
                        'equipment_type_id': so_line.equipment_type_id.id or False,
                    })]
        inv.write({'invoice_line_ids': invoice_vals})
        return invoice_vals

    def _prepare_additional_eqp_values(self, order, name, amount, order_line_id, inv):
        so_line = order_line_id
        invoice_vals = []

        start = datetime.combine(self.date_start_invoice_timesheet, datetime.min.time())
        end = datetime.combine(self.date_end_invoice_timesheet, datetime.min.time())

        if order_line_id.equipment_qty > 0:
            equipment_qty = sum(order.trip_ids.filtered(lambda
                                                            trip_id: trip_id.date_from >= start and trip_id.date_from <= end and trip_id.invoice_id.id == False and trip_id.equipment_qty > 0 and trip_id.task_id.sale_line_id.id == order_line_id.id).mapped(
                'equipment_qty'))
            # additional_eqp  charge
            product_id = self.env.ref('custom_trip.product_add_equipment_charge_product')
            name = "%s - %s" % (product_id.name, so_line.product_id.name),
            quantity = equipment_qty
            price_unit = order_line_id.rate
            product_id = product_id.id
            if quantity > 0:
                invoice_vals = [(0, 0, {
                    'name': name,
                    'price_unit': price_unit,
                    'quantity': quantity,
                    'product_id': product_id,
                    'product_uom_id': so_line.product_uom.id,
                    'tax_ids': [(6, 0, so_line.tax_id.ids)],
                    'sale_line_ids': [(6, 0, [so_line.id])],
                    'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                    'analytic_account_id': order.analytic_account_id.id or False,
                    'equipment_type_id': so_line.equipment_type_id.id or False,
                })]
                inv.write({'invoice_line_ids': invoice_vals,
                           'custom_invoice_date': self.inv_date,
                           'invoice_date': self.inv_date,
                           'date': self.date,
                           })

            return invoice_vals

    def update_cost_plus(self, sale_orders, inv):
        domain = [('sale_order_id', '=', sale_orders.id), ('cost_plus_id.state', '=', 'approved'),
                  ('billing', '=', True),
                  ('billing_status', '=', False)]
        if self.task_ids:
            domain.append(('task_id', 'in', self.task_ids.ids))
        if self.date_start_invoice_timesheet and self.date_end_invoice_timesheet:
            # domain.append(('cost_plus_id.cost_date', '>=', self.date_start_invoice_timesheet))
            # domain.append(('cost_plus_id.cost_date', '<=', self.date_end_invoice_timesheet))
            domain.append(('cost_plus_line_date', '>=', self.date_start_invoice_timesheet))
            domain.append(('cost_plus_line_date', '<=', self.date_end_invoice_timesheet))
        cost_plus_line = self.env['cost.plus.line'].search(domain)
        for line in cost_plus_line:
            invoice_vals = [(0, 0, {
                'name': "%s-%s" % (line.product_id.name, line.employee_id.name),
                'price_unit': line.amount,
                'quantity': 1,
                # 'equipment_type_id': so_line.equipment_type_id.id or False,
                'product_id': line.product_id.id,
                'product_uom_id': line.uom_id.id,
                # 'tax_ids': [(6, 0, so_line.tax_id.ids)],
                # 'sale_line_ids': [(6, 0, [so_line.id])],
                # 'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                'analytic_account_id': sale_orders.analytic_account_id.id or False,
                'cost_plus_line_id': line.id,
            })]
            inv.write({'invoice_line_ids': invoice_vals})
            line.write({'billing_status': True})

    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        sale_orders.write({'inv_date': self.inv_date})
        if self.advance_payment_method == 'delivered':
            inv = sale_orders.with_context(
                timesheet_start_date=self.date_start_invoice_timesheet,
                timesheet_end_date=self.date_end_invoice_timesheet,
                tasks=self.task_ids
            )._create_invoices(final=self.deduct_down_payments)
            inv.write({'custom_invoice_date': self.inv_date, 'invoice_date': self.inv_date, 'date': self.date})
            self.update_billing_month_inv(sale_orders, inv)
            self.update_charge_inv(sale_orders, inv)
            self.update_cost_plus(sale_orders, inv)
        else:
            self._handle_deposit_invoice(sale_orders)
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}

    def update_billing_month_inv(self, sale_orders, inv):
        order_lines = sale_orders.order_line.filtered(
            lambda l: l.task_id in self.task_ids) if self.task_ids else sale_orders.order_line
        amount, name = self._get_advance_details(sale_orders)

        if sale_orders.sale_type in ['bundle', 'cost_plus']:
            for order_line in order_lines:
                invoice_vals = self._billing_month_values(sale_orders, name, amount, order_line, inv)
                if sale_orders.fiscal_position_id:
                    invoice_vals['fiscal_position_id'] = sale_orders.fiscal_position_id.id

    def _billing_month_values(self, order, name, amount, so_line, inv):
        if order.sale_type not in ['bundle', 'cost_plus'] or so_line._name != 'sale.order.line':
            return []

        invoice_vals = []
        employee_qty_count = defaultdict(lambda: {
            'employee': set(), 'inv_line': set(), 'task': set(), 'soline_id': set(),
            'working_days': 0, 'dates': set(), 'holidays': 0, 'week_off_days': 0, 'leave_days': 0
        })

        # Step 1: Match tasks with sale order lines and invoice lines
        matching_invoice_lines = [
            (task, inv_line, soline) for task in self.task_ids
            for soline in order.order_line if soline.task_id == task
            for inv_line in inv.invoice_line_ids if soline.task_id == inv_line.sale_line_ids.task_id
        ]

        # Step 2: Process employee and invoice line logic
        if matching_invoice_lines:
            for task, inv_line, soline in matching_invoice_lines:
                self._process_timesheets(task, employee_qty_count, inv_line)
                self._process_public_holidays(task, employee_qty_count)
                self._process_week_off(task, employee_qty_count)
                self._process_leave_days(employee_qty_count)

            self._update_invoice_line_values(inv, employee_qty_count, inv_line, order, so_line)

        return invoice_vals

    def _process_timesheets(self, task, employee_qty_count, inv_line):
        for timesheet_line in task.timesheet_ids:
            if timesheet_line.unit_amount == 0:
                continue
            employee = timesheet_line.employee_id
            employee_qty_count[employee]['inv_line'].add(inv_line)
            employee_qty_count[employee]['employee'].add(employee)
            employee_qty_count[employee]['task'].add(timesheet_line.task_id)
            employee_qty_count[employee]['soline_id'].add(timesheet_line.so_line)
            employee_qty_count[employee]['working_days'] += 1
            employee_qty_count[employee]['dates'].add(timesheet_line.date)

    def _process_public_holidays(self, task, employee_qty_count):
        for employee, values in employee_qty_count.items():
            if not values['dates']:
                continue
            date_from, date_to = min(values['dates']), max(values['dates'])
            public_holidays = self.env['resource.calendar.leaves'].search([
                ('task_id', '=', self.task_ids.id),
                ('date_from', '<=', date_to),
                ('date_to', '>=', date_from)
            ])
            employee_qty_count[employee]['holidays'] = len(public_holidays)

    def _process_week_off(self, task, employee_qty_count):
        for shift_allocation in task.shift_allocation_ids:
            allocated_employee = shift_allocation.employee_id
            if allocated_employee not in employee_qty_count:
                continue
            matched_week_dates = set(
                dayofweek.date for dayofweek in allocated_employee.dayofweek_ids
                if any(emp_date.month == dayofweek.date.month and emp_date.year == dayofweek.date.year for emp_date in
                       employee_qty_count[allocated_employee]['dates'])
            )
            employee_qty_count[allocated_employee]['week_off_days'] = len(matched_week_dates)

    def _process_leave_days(self, employee_qty_count):
        for employee, values in employee_qty_count.items():
            min_date, max_date = min(values['dates']), max(values['dates'])
            leave_records = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('request_date_from', '<=', max_date),
                ('request_date_to', '>=', min_date),
                ('state', '=', 'validate')
            ])
            total_leave_days = sum(
                (leave.request_date_to - leave.request_date_from).days + 1 for leave in leave_records)
            employee_qty_count[employee]['leave_days'] = total_leave_days

    def _update_invoice_line_values(self, inv, employee_qty_count, inv_line, order, so_line):
        inv_date = self.inv_date or self.date  # Use invoice date or current date
        if inv_line.product_uom_id.name != 'Month' or not inv_date:
            return

        total_month_days = monthrange(inv_date.year, inv_date.month)[1]

        total_employee_qty_count = 0.0
        first_employee = True
        for employee, values in employee_qty_count.items():
            total_qty = sum([values['working_days'], values['holidays'], values['week_off_days'], values['leave_days']])
            if total_qty == total_month_days:
                total_employee_qty_count += 1

            if first_employee and total_employee_qty_count == 0:
                self._update_account_move_line(inv_line, employee, values, total_qty, so_line)
                first_employee = False
            elif total_employee_qty_count > 0:
                self._update_account_move_line(inv_line, employee, values, total_employee_qty_count, so_line)

    def _update_account_move_line(self, inv_line, employee, values, total_qty, so_line):
        saleline_id = next(iter(values['soline_id']))
        price_unit = saleline_id.price_unit
        price_subtotal = total_qty * price_unit

        query = """
            UPDATE account_move_line
            SET name = '%s',
                quantity = '%s',
                price_unit = '%s',
                price_subtotal = '%s'
            WHERE id = '%s'
        """ % (employee.name, total_qty, price_unit, price_subtotal, inv_line.id)

        self.env.cr.execute(query)

    def _handle_deposit_invoice(self, sale_orders):
        if not self.product_id:
            vals = self._prepare_deposit_product()
            self.product_id = self.env['product.product'].create(vals)
            self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id', self.product_id.id)

        if self.product_id.invoice_policy != 'order':
            raise UserError(
                _('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product.'))

        if self.product_id.type != 'service':
            raise UserError(
                _("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))

        taxes = self.product_id.taxes_id.filtered(
            lambda r: not sale_orders.company_id or r.company_id == sale_orders.company_id)
        tax_ids = sale_orders.fiscal_position_id.map_tax(taxes).ids
        sale_line_obj = self.env['sale.order.line']

        for order in sale_orders:
            amount, name = self._get_advance_details(order)
            analytic_tag_ids = [(4, tag.id, None) for line in order.order_line for tag in line.analytic_tag_ids]

            so_line_values = self._prepare_so_line(order, analytic_tag_ids, tax_ids, amount)
            so_line = sale_line_obj.create(so_line_values)
            inv = self._create_invoice(order, so_line, amount)

            self.update_billing_month_inv(order, inv)