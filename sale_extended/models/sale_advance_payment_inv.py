# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta, datetime
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)
from calendar import monthrange
from odoo.tools import float_is_zero, html_keep_url, is_html_empty

from odoo.tools.safe_eval import safe_eval
from collections import defaultdict


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
                'task_id': so_line.task_id.id,
                'product_uom_id': so_line.product_uom.id,
                'tax_ids': [(6, 0, so_line.so_line_id.tax_id.ids)],
                'sale_line_ids': [(6, 0, [so_line.so_line_id.id])],
                'analytic_tag_ids': [(6, 0, so_line.so_line_id.analytic_tag_ids.ids)],
                'analytic_account_id': order.analytic_account_id.id or False,
                'equipment_type_id': so_line.so_line_id.equipment_type_id.id or False,
                'employee_id': so_line.employee_id.id if so_line.employee_id else False,
            })]
            inv.write({'invoice_line_ids': invoice_vals,
                       'custom_invoice_date': self.inv_date,
                       'invoice_date': self.inv_date,
                       'date': self.date,
                       })
            return invoice_vals
        elif so_line.recurring and so_line.task_id in self.task_ids:
                invoice_vals = [(0, 0, {
                    'name': "%s - %s" % (so_line.product_id.name, so_line.so_line_id.product_id.name),
                    'price_unit': so_line.price_unit,
                    'quantity': so_line.quantity,
                    'task_id': so_line.task_id.id or False,
                    'product_id': so_line.product_id.id,
                    'product_uom_id': so_line.product_uom.id,
                    'tax_ids': [(6, 0, so_line.so_line_id.tax_id.ids)],
                    'sale_line_ids': [(6, 0, [so_line.so_line_id.id])],
                    'analytic_tag_ids': [(6, 0, so_line.so_line_id.analytic_tag_ids.ids)],
                    'analytic_account_id': order.analytic_account_id.id or False,
                    'equipment_type_id': so_line.so_line_id.equipment_type_id.id or False,
                    'employee_id': so_line.employee_id.id if so_line.employee_id else False,
                })]
                inv.write({'invoice_line_ids': invoice_vals,
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
                    'name': "%s -%s - %s - %s" % (
                        so_line.product_id.name, product_id.name, so_line.agency_fee, so_line.employee_id.name),
                    'price_unit': amount,
                    'quantity': 1.0,
                    'task_id': so_line.task_id.id,
                    'equipment_type_id': so_line.equipment_type_id.id or False,
                    'product_id': product_id.id,
                    'product_uom_id': so_line.product_uom.id,
                    'tax_ids': [(6, 0, so_line.tax_id.ids)],
                    'sale_line_ids': [(6, 0, [so_line.id])],
                    'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                    'analytic_account_id': order.analytic_account_id.id or False,
                    'employee_id': so_line.employee_id.id if so_line.employee_id else False,
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
            # self._billing_month_values(order, name, amount, so_line, inv)
            timesheet_ids = extra_charge_id.so_line_id.task_id.timesheet_ids
            timesheet_ids = timesheet_ids.filtered(lambda
                                                       time: time.date >= self.date_start_invoice_timesheet and time.date <= self.date_end_invoice_timesheet)
            total_timesheet_sum = sum(timesheet_ids.mapped('units_amounts'))
            if timesheet_ids:
                if extra_charge_id.charge == 'qty':
                    # if so_line.qty_delivered > extra_charge_id.qty: #need to add the timsheet of month and minus with extrachargeid.qty
                    if total_timesheet_sum > extra_charge_id.qty:
                        # Extra charge
                        extra_charge_product_id = self.env.ref('custom_trip.product_extra_charge_product')
                        name = "%s - %s" % (extra_charge_product_id.name, so_line.product_id.name),
                        # quantity = so_line.qty_delivered - extra_charge_id.qty #need to add the timsheet of month and minus with extrachargeid.qty
                        quantity = total_timesheet_sum - extra_charge_id.qty
                        price_unit = extra_charge_id.ec_price
                        product_id = extra_charge_product_id.id
                        extra_charge_product_id = so_line.product_id.id
                    else:
                        # Minimum charge
                        minimum_charge_product_id = self.env.ref('custom_trip.product_minimum_charge_product')
                        name = "%s - %s" % (minimum_charge_product_id.name, so_line.product_id.name),
                        price_unit = extra_charge_id.price
                        # quantity = extra_charge_id.qty - so_line.qty_delivered  #need to add the timsheet of month and minus with extrachargeid.qty
                        quantity = extra_charge_id.qty - total_timesheet_sum
                        product_id = minimum_charge_product_id.id
                        extra_charge_product_id = False
                    if  quantity > 0:
                        invoice_vals = invoice_vals + [(0, 0, {
                            'name': name,
                            'price_unit': price_unit,
                            'quantity': quantity,
                            'product_id': product_id,
                            'task_id': so_line.task_id.id,
                            'extra_charge_product_id': extra_charge_product_id,
                            'product_uom_id': so_line.product_uom.id,
                            'tax_ids': [(6, 0, so_line.tax_id.ids)],
                            'sale_line_ids': [(6, 0, [so_line.id])],
                            'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                            'analytic_account_id': order.analytic_account_id.id or False,
                            'equipment_type_id': so_line.equipment_type_id.id or False,
                            'employee_id': so_line.employee_id.id if so_line.employee_id else False,
                        })]
                if extra_charge_id.charge == 'amount':
                    for line in inv.invoice_line_ids:
                        if len(line.sale_line_ids.filtered(
                                lambda line_so: line_so.id == so_line.id)) > 0 and extra_charge_id.price > line.price_subtotal:
                            minimum_charge_product_id = self.env.ref('custom_trip.product_minimum_charge_product')
                            name = "%s - %s" % (minimum_charge_product_id.name, so_line.product_id.name),
                            price_unit = extra_charge_id.price - line.price_subtotal
                            quantity = 1
                            product_id = minimum_charge_product_id.id
                            extra_charge_product_id = False
                            invoice_vals = invoice_vals + [(0, 0, {
                                'name': name,
                                'price_unit': price_unit,
                                'quantity': quantity,
                                'product_id': product_id,
                                'task_id': so_line.task_id.id,
                                'extra_charge_product_id': extra_charge_product_id,
                                'product_uom_id': so_line.product_uom.id,
                                'tax_ids': [(6, 0, so_line.tax_id.ids)],
                                'sale_line_ids': [(6, 0, [so_line.id])],
                                'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                                'analytic_account_id': order.analytic_account_id.id or False,
                                'equipment_type_id': so_line.equipment_type_id.id or False,
                                'employee_id': so_line.employee_id.id if so_line.employee_id else False,
                            })]
                if extra_charge_id.charge_type == 'day':
                    timesheet_ids = extra_charge_id.so_line_id.task_id.timesheet_ids
                    timesheet_ids = timesheet_ids.filtered(lambda
                                                               time: time.date >= self.date_start_invoice_timesheet and time.date <= self.date_end_invoice_timesheet)
                    extra_qty = sum(
                        timesheet_ids.filtered(lambda timesheet_id: timesheet_id.units_amounts > extra_charge_id.qty).mapped(
                            'units_amounts'))
                    minimum_qty = sum(
                        timesheet_ids.filtered(lambda timesheet_id: timesheet_id.units_amounts < extra_charge_id.qty).mapped(
                            'units_amounts'))
                    if extra_qty > 0:
                        # Extra charge
                        extra_charge_product_id = self.env.ref('custom_trip.product_extra_charge_product')
                        name = "%s - %s" % (extra_charge_product_id.name, so_line.product_id.name),
                        quantity = extra_qty
                        price_unit = extra_charge_id.ec_price
                        product_id = extra_charge_product_id.id
                        extra_charge_product_id = so_line.product_id.id
                        if quantity > 0:
                            invoice_vals = invoice_vals + [(0, 0, {
                                'name': name,
                                'price_unit': price_unit,
                                'extra_charge_product_id': extra_charge_product_id,
                                'quantity': quantity - extra_charge_id.qty,
                                'product_id': product_id,
                                'task_id': so_line.task_id.id,
                                'product_uom_id': so_line.product_uom.id,
                                'tax_ids': [(6, 0, so_line.tax_id.ids)],
                                'sale_line_ids': [(6, 0, [so_line.id])],
                                'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                                'analytic_account_id': order.analytic_account_id.id or False,
                                'equipment_type_id': so_line.equipment_type_id.id or False,
                                'employee_id': so_line.employee_id.id if so_line.employee_id else False,
                            })]
                    if minimum_qty > 0:
                        # Minimum charge
                        minimum_charge_product_id = self.env.ref('custom_trip.product_minimum_charge_product')
                        name = "%s - %s" % (minimum_charge_product_id.name, so_line.product_id.name),
                        price_unit = extra_charge_id.price
                        quantity = minimum_qty
                        product_id = minimum_charge_product_id.id
                        if quantity > 0:
                            invoice_vals = invoice_vals + [(0, 0, {
                                'name': name,
                                'price_unit': price_unit,
                                'quantity': extra_charge_id.qty - quantity,
                                'product_id': product_id,
                                'task_id': so_line.task_id.id,
                                'product_uom_id': so_line.product_uom.id,
                                'tax_ids': [(6, 0, so_line.tax_id.ids)],
                                'sale_line_ids': [(6, 0, [so_line.id])],
                                'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                                'analytic_account_id': order.analytic_account_id.id or False,
                                'equipment_type_id': so_line.equipment_type_id.id or False,
                                'employee_id': so_line.employee_id.id if so_line.employee_id else False,
                            })]
                if extra_charge_id.charge_type == 'full_day':
                    timesheet_ids = extra_charge_id.so_line_id.task_id.timesheet_ids
                    for timesheet_date in timesheet_ids.mapped('date'):
                        timesheet_ids = timesheet_ids.filtered(lambda
                                                                   time: time.date >= self.date_start_invoice_timesheet and time.date <= self.date_end_invoice_timesheet)

                        extra_qty = sum(timesheet_ids.filtered(lambda timesheet_id: timesheet_id.date > timesheet_date).mapped(
                            'units_amounts'))
                        minimum_qty = sum(
                            timesheet_ids.filtered(lambda timesheet_id: timesheet_id.date < timesheet_date).mapped(
                                'units_amounts'))

                        if extra_qty > 0:
                            # Extra charge
                            extra_charge_product_id = self.env.ref('custom_trip.product_extra_charge_product')
                            name = "%s - %s" % (extra_charge_product_id.name, so_line.product_id.name),
                            quantity = extra_qty
                            price_unit = extra_charge_id.ec_price
                            product_id = extra_charge_product_id.id
                            extra_charge_product_id = so_line.product_id.id
                            if quantity > 0:
                                invoice_vals = invoice_vals + [(0, 0, {
                                    'name': name,
                                    'price_unit': price_unit,
                                    'extra_charge_product_id': extra_charge_product_id,
                                    'quantity': quantity - extra_charge_id.qty,
                                    'product_id': product_id,
                                    'task_id': so_line.task_id.id,
                                    'product_uom_id': so_line.product_uom.id,
                                    'tax_ids': [(6, 0, so_line.tax_id.ids)],
                                    'sale_line_ids': [(6, 0, [so_line.id])],
                                    'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                                    'analytic_account_id': order.analytic_account_id.id or False,
                                    'equipment_type_id': so_line.equipment_type_id.id or False,
                                    'employee_id': so_line.employee_id.id if so_line.employee_id else False,
                                })]
                        if minimum_qty > 0:
                            # Minimum charge
                            minimum_charge_product_id = self.env.ref('custom_trip.product_minimum_charge_product')
                            name = "%s - %s" % (minimum_charge_product_id.name, so_line.product_id.name),
                            price_unit = extra_charge_id.price
                            quantity = minimum_qty
                            product_id = minimum_charge_product_id.id
                            if quantity > 0:
                                invoice_vals = invoice_vals + [(0, 0, {
                                    'name': name,
                                    'price_unit': price_unit,
                                    'quantity': extra_charge_id.qty - quantity,
                                    'product_id': product_id,
                                    'task_id': so_line.task_id.id,
                                    'product_uom_id': so_line.product_uom.id,
                                    'tax_ids': [(6, 0, so_line.tax_id.ids)],
                                    'sale_line_ids': [(6, 0, [so_line.id])],
                                    'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                                    'analytic_account_id': order.analytic_account_id.id or False,
                                    'equipment_type_id': so_line.equipment_type_id.id or False,
                                    'employee_id': so_line.employee_id.id if so_line.employee_id else False,
                                })]
                inv.write({'invoice_line_ids': invoice_vals,
                           'custom_invoice_date': self.inv_date,
                           'invoice_date': self.inv_date,
                           'date': self.date,
                           })
                return invoice_vals

    def _prepare_additional_eqp_values(self, order, name, amount, order_line_id, inv):
        so_line = order_line_id
        invoice_vals = []

        start = datetime.combine(self.date_start_invoice_timesheet, datetime.min.time())
        end = datetime.combine(self.date_end_invoice_timesheet, datetime.min.time())

        if order_line_id.equipment_qty > 0:
            if order.trip_ids.filtered(lambda trip_id: trip_id.date_from):
                equipment_qty = sum(order.trip_ids.filtered(lambda trip_id:
                                                            trip_id.date_from and isinstance(trip_id.date_from, datetime)
                                                            and trip_id.date_from >= start
                                                            and trip_id.date_from <= end
                                                            and not trip_id.invoice_id  # Simplified check for False
                                                            and trip_id.equipment_qty > 0
                                                            and trip_id.task_id.sale_line_id
                                                            and trip_id.task_id.sale_line_id.id == order_line_id.id
                                                            ).mapped('equipment_qty'))

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
                        'task_id': so_line.task_id.id,
                        'product_uom_id': so_line.product_uom.id,
                        'tax_ids': [(6, 0, so_line.tax_id.ids)],
                        'sale_line_ids': [(6, 0, [so_line.id])],
                        'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                        'analytic_account_id': order.analytic_account_id.id or False,
                        'equipment_type_id': so_line.equipment_type_id.id or False,
                        'employee_id': so_line.employee_id.id if so_line.employee_id else False,
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
                'employee_id': line.employee_id.id,
            })]
            inv.write({'invoice_line_ids': invoice_vals})
            line.write({'billing_status': True})

    def update_charge_inv(self, sale_orders, inv):
        # for sale order line based on task
        if self.task_ids:
            order_lines = sale_orders.order_line.filtered(lambda l: l.task_id in self.task_ids)
        else:
            order_lines = sale_orders.order_line

        amount, name = self._get_advance_details(sale_orders)
        # for addtionl_charge_line in sale_orders.addtionl_charge_sale_order_ids.filtered(
        #         lambda order: order.recurring or order.charge_date == sale_orders.inv_date):
        for addtionl_charge_line in sale_orders.addtionl_charge_sale_order_ids:
            invoice_vals = self._prepare_invoice_charge_values(sale_orders, name, amount, addtionl_charge_line, inv)
            if sale_orders.fiscal_position_id:
                invoice_vals['fiscal_position_id'] = sale_orders.fiscal_position_id.id

        if sale_orders.sale_type == 'cost_plus':
            for order_line in order_lines:
                invoice_vals = self._prepare_agency_fee_values(sale_orders, name, amount, order_line, inv)
                if sale_orders.fiscal_position_id:
                    invoice_vals['fiscal_position_id'] = sale_orders.fiscal_position_id.id

        for extra_charge_id in sale_orders.extra_charge_ids:
            invoice_vals = self._prepare_charge_values(sale_orders, name, amount, extra_charge_id, inv)
            if sale_orders.fiscal_position_id:
                invoice_vals['fiscal_position_id'] = sale_orders.fiscal_position_id.id

        for order_line_id in order_lines:
            invoice_vals = self._prepare_additional_eqp_values(sale_orders, name, amount, order_line_id, inv)
            if sale_orders.fiscal_position_id:
                invoice_vals['fiscal_position_id'] = sale_orders.fiscal_position_id.id

    def update_billing_month_inv(self, sale_orders, inv):
        if self.task_ids:
            order_lines = sale_orders.order_line.filtered(lambda l: l.task_id in self.task_ids)
        else:
            order_lines = sale_orders.order_line

        amount, name = self._get_advance_details(sale_orders)

        if sale_orders.sale_type in ['bundle', 'cost_plus']:
            for order_line in order_lines:
                invoice_vals = self._billing_month_values(sale_orders, name, amount, order_line, inv)
                if sale_orders.fiscal_position_id:
                    invoice_vals['fiscal_position_id'] = sale_orders.fiscal_position_id.id

    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        sale_orders.write({'inv_date': self.inv_date})
        order_line = sale_orders.order_line.filtered(
            lambda line: line.product_uom.id == self.env.ref("sale_extended.product_uom_month").id)
        if self.advance_payment_method == 'delivered':
            inv = sale_orders.with_context(
                timesheet_start_date=self.date_start_invoice_timesheet,
                timesheet_end_date=self.date_end_invoice_timesheet,
                tasks=self.task_ids,
            )._create_invoices(final=self.deduct_down_payments)
            inv.write({'custom_invoice_date': self.inv_date, 'invoice_date': self.inv_date, 'date': self.date})

            self.update_charge_inv(sale_orders, inv)
            self.update_cost_plus(sale_orders, inv)
            self.update_billing_month_inv(sale_orders, inv)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                amount, name = self._get_advance_details(order)

                if self.product_id.invoice_policy != 'order':
                    raise UserError(
                        _('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(
                        _("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(
                    lambda r: not order.company_id or r.company_id == order.company_id)
                tax_ids = order.fiscal_position_id.map_tax(taxes).ids
                analytic_tag_ids = []
                for line in order.order_line:
                    analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]

                so_line_values = self._prepare_so_line(order, analytic_tag_ids, tax_ids, amount)
                so_line = sale_line_obj.create(so_line_values)
                inv = self._create_invoice(order, so_line, amount)
                self.update_charge_inv(sale_orders, inv)
                self.update_cost_plus(sale_orders, inv)
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}


    def _cleanup_generic_lines_old(self, invoices):
        # Ensure invoices is a list
        if not isinstance(invoices, (list, tuple)) or not all(
                isinstance(inv, self.env['account.move']) for inv in invoices):
            invoices = [invoices]  # Convert to a list if it's a single invoice or not valid

        for inv in invoices:
            # Create a list of IDs to delete
            line_ids_to_delete = []

            for line in inv.invoice_line_ids:
                # Check if the product's UoM name is 'Month' and line name matches product name
                if line.product_uom_id.name == "Month" and line.name == line.product_id.name:
                    line_ids_to_delete.append(line.id)
                    move = line.move_id
                    move_line_balance = line.balance

                    # Execute raw SQL to delete invoice lines if there are any to delete
                    if line_ids_to_delete:
                        delete_query = "DELETE FROM account_move_line WHERE id IN %s"
                        self.env.cr.execute(delete_query, (tuple(line_ids_to_delete),))

    def _billing_month_values(self, order, name, amount, so_line, inv):
        if order.sale_type in ['bundle', 'cost_plus'] and so_line._name == 'sale.order.line':
            invoice_vals = []
            if self.task_ids:
                # Step 1: Match tasks with sale order lines and invoice lines
                matching_invoice_lines = []
                if order.order_line:
                    for task in self.task_ids:
                        for soline in order.order_line:
                            if soline.task_id == task:
                                # Finding related invoice lines
                                for inv_line in inv.invoice_line_ids:
                                    # Check if the sale line's task_id matches with the invoice line's sale_line_id's task_id
                                    if soline.task_id == inv_line.sale_line_ids.task_id:
                                        print("Matching Invoice Line:", inv_line)
                                        matching_invoice_lines.append((task, inv_line, soline))
                # Step 2: Proceed with employee and invoice line logic
                if matching_invoice_lines:
                    for task, inv_line, soline in matching_invoice_lines:
                        # Types of Employee count
                        if order.sale_type == 'bundle':
                            employee_qty_count = defaultdict(
                                lambda: {'employee': set(), 'inv_line': set(), 'task': set(), 'soline_id': set(),
                                         'working_days': 0, 'dates': set(), 'holidays': 0, 'week_off_days': 0})
                        elif order.sale_type == 'cost_plus':
                            employee_qty_count = defaultdict(
                                lambda: {'employee': set(), 'inv_line': set(), 'task': set(), 'soline_id': set(),
                                         'working_days': 0, 'dates': set(), 'holidays': 0, 'week_off_days': 0,
                                         'leave_days': 0})
                        elif order.sale_type == 'standard':
                            employee_qty_count = defaultdict(
                                lambda: {'employee': set(), 'inv_line': set(), 'task': set(), 'soline_id': set(),
                                         'working_days': 0, 'dates': set(), 'week_off_days': 0})
                        # Timesheet Employee count
                        for timesheet_line in task.timesheet_ids:
                            start_date = self.date_start_invoice_timesheet  # comment by shon -  min(values['dates'])  # Start date
                            end_date = self.date_end_invoice_timesheet  # comment by shon -  max(values['dates'])  # End date
                            timesheet_date = timesheet_line.date

                            if start_date <= timesheet_date <= end_date:
                                if timesheet_line.unit_amount != 0.00:
                                    employee = timesheet_line.employee_id
                                    date = timesheet_line.date
                                    employee_qty_count[employee]['inv_line'].add(inv_line)
                                    employee_qty_count[employee]['employee'].add(employee)
                                    employee_qty_count[employee]['task'].add(timesheet_line.task_id)
                                    employee_qty_count[employee]['soline_id'].add(timesheet_line.so_line)
                                    employee_qty_count[employee]['working_days'] += 1
                                    employee_qty_count[employee]['dates'].add(date)
                        for employee, values in employee_qty_count.items():

                            # Ensure there are dates available to calculate min and max
                            if values['dates']:
                                # Employee public holiday Count
                                date_from = self.date_start_invoice_timesheet # comment by shon -  min(values['dates'])  # Start date
                                date_to = self.date_end_invoice_timesheet # comment by shon -  max(values['dates'])  # End date

                                # Search for public holidays within the specified date range
                                public_holidays = self.env['resource.calendar.leaves'].search([
                                    ('task_id', '=', self.task_ids.id),
                                    ('date_from', '<=', date_to),  # Holidays that start before or on the end date
                                    ('date_to', '>=', date_from)  # Holidays that end after or on the start date
                                ])

                                # Set the holidays count for the employee based on the search result
                                if public_holidays:
                                    employee_qty_count[employee]['holidays'] = len(public_holidays)

                                # Search week off dates
                                emp_week_off = self.env['hr.day.of.week'].search([
                                    ('employee_id', '=', employee.id),
                                    ('date', '<=', date_to),  # Holidays that start before or on the end date
                                    ('date', '>=', date_from)  # Holidays that end after or on the start date
                                ])

                                # Set the emp_week_off count for the employee based on the search result
                                if emp_week_off:
                                    employee_qty_count[employee]['week_off_days'] = len(emp_week_off)

                                min_date = self.date_start_invoice_timesheet  # comment by shon - min(values['dates'])
                                max_date = self.date_end_invoice_timesheet  # comment by shon - max(values['dates'])

                                date_format = "%Y-%m-%d"
                                min_date_str = min_date.strftime(date_format)
                                max_date_str = max_date.strftime(date_format)

                                leave_records = self.env['hr.leave'].search([
                                    ('employee_id', '=', employee.id),
                                    ('request_date_from', '<=', max_date_str),
                                    ('request_date_to', '>=', min_date_str),
                                    ('state', '=', 'validate')
                                ])

                                total_leave_days = 0
                                for leave in leave_records:
                                    leave_duration = (leave.request_date_to - leave.request_date_from).days + 1
                                    total_leave_days += leave_duration
                                employee_qty_count[employee]['leave_days'] = total_leave_days

                        inv_date = self.inv_date if self.inv_date else self.date  # invoice date or current date

                        if inv_line.product_uom_id.name == 'Month' and not inv_line.type_id:
                            if inv_date:
                                total_month_days = monthrange(inv_date.year, inv_date.month)[1]
                                total_employee_qty_count = 0.0
                                first_employee = True
                                for employee, values in employee_qty_count.items():
                                    if employee:
                                        emp_name = employee.display_name
                                        woking_days = values['working_days']
                                        holidays = values['holidays']
                                        week_off_days = values['week_off_days']
                                        leave_days = values['leave_days']
                                        total_qty = round((woking_days + holidays + week_off_days + leave_days)/ total_month_days,4)

                                        # total_qty = (values['working_days'] + values['holidays'] + values[
                                        #     'week_off_days'] + values['leave_days'])

                                        saleline = values['soline_id']
                                        saleline_id = next(iter(saleline))

                                        invoice_vals.append((0, 0, {
                                            'name': "%s-%s" % (inv_line.product_id.name, employee.name),
                                            'price_unit': saleline_id.price_unit,
                                            'quantity': total_qty,
                                            'product_id': inv_line.product_id.id,
                                            'product_uom_id': inv_line.product_uom_id.id,
                                            'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                                            'analytic_account_id': order.analytic_account_id.id or False,
                                        }))

                                        # if total_qty == total_month_days:
                                        #     total_employee_qty_count += 1
                                        # if first_employee:
                                        #     if total_employee_qty_count == 0:
                                        #         invoice_line_id = inv_line.id
                                        #         saleline = values['soline_id']
                                        #         saleline_id = next(iter(saleline))
                                        #         price_unit = saleline_id.price_unit
                                        #         price_subtotal = total_qty * price_unit
                                        #         # Update account_move_line when no employee count matches total month days
                                        #         query = """
                                        #                UPDATE account_move_line
                                        #                SET name = '%s',
                                        #                    quantity = '%s',
                                        #                    price_unit = '%s',
                                        #                    price_subtotal = '%s'
                                        #                WHERE id = '%s'
                                        #            """ % (
                                        #             employee.name, total_qty, price_unit, price_subtotal,
                                        #             invoice_line_id)
                                        #         self.env.cr.execute(query)
                                        #         first_employee = False
                                        #
                                        #     elif total_employee_qty_count > 0:
                                        #         invoice_line_id = inv_line.id
                                        #         saleline = values['soline_id']
                                        #         saleline_id = next(iter(saleline))
                                        #         price_unit = saleline_id.price_unit
                                        #         price_subtotal = total_employee_qty_count * price_unit
                                        #         emp = values['employee']
                                        #         task = values['task']
                                        #         # Format the SQL query string with string interpolation
                                        #         print('===last\n', total_employee_qty_count)
                                        #         query = """
                                        #                UPDATE account_move_line
                                        #                SET quantity='%s',
                                        #                    price_unit='%s',
                                        #                    price_subtotal='%s'
                                        #                WHERE id='%s'
                                        #            """ % (
                                        #             total_employee_qty_count, price_unit, price_subtotal,
                                        #             invoice_line_id)
                                        #         # Execute the query
                                        #         self.env.cr.execute(query)
                                        #         first_employee = False
                                        #
                                        # else:
                                        #     daily_rates = (price_unit / total_month_days)
                                        #     invoice_vals.append((0, 0, {
                                        #         'name': "%s-%s" % (inv_line.product_id.name, employee.name),
                                        #         'price_unit': total_qty * daily_rates,
                                        #         'quantity': 1,
                                        #         'product_id': inv_line.product_id.id,
                                        #         'product_uom_id': inv_line.product_uom_id.id,
                                        #         'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                                        #         'analytic_account_id': order.analytic_account_id.id or False,
                                        #     }))
                                        #     print('$$$$$$$$$$\n\n\n', invoice_vals)

                        inv.write({'invoice_line_ids': invoice_vals,
                                   'custom_invoice_date': self.inv_date,
                                   'invoice_date': self.inv_date,
                                   'date': self.date,
                                   })
                        return invoice_vals
