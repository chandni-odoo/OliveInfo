from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CustomTripSheet(models.Model):
    _inherit = "custom.trip.sheet"


    def _check_partner_blacklist(self, partner):
        if partner and partner.is_customer_black_list:
            raise ValidationError(_(
                "Customer '%s' is blacklisted. Please check with finance department."
            ) % partner.name)

    def _check_lpo_balance(self, sale_order):
        if not sale_order:
            return
            
        lpo_control = self.env['lpo.control'].search([
            ('sale_id', '=', sale_order.id)
        ], limit=1)
        
        if lpo_control and lpo_control.total_po_value != 0 and lpo_control.total_available_balance <= 0:
            raise ValidationError(_(
                "Insufficient PO Balance for Sale Order %s\n"
                "Total PO Value: %s\n"
                "Available Balance: %s\n"
                "Please coordinate with finance department."
            ) % (
                sale_order.name,
                lpo_control.total_po_value,
                lpo_control.total_available_balance
            ))

    @api.constrains('partner_id', 'task_id')
    def _check_partner_and_lpo_status(self):
        for record in self:
            if record.partner_id:
                self._check_partner_blacklist(record.partner_id)
                if record.partner_id.hold_option in ['hold', 'credit_block']:
                    raise ValidationError(_("Customer/order is on hold, please check with finance"))
            
            if record.task_id and record.task_id.sale_order_id:
                self._check_lpo_balance(record.task_id.sale_order_id)
    
    @api.model
    def create(self, vals):
        if vals.get('partner_id'):
            partner = self.env['res.partner'].browse(vals['partner_id'])
            self._check_partner_blacklist(partner)
            if partner.hold_option in ['hold', 'credit_block']:
                raise ValidationError(_("Customer/order is on hold, please check with finance"))
        
        record = super(CustomTripSheet, self).create(vals)
    
        if record.task_id and record.task_id.sale_order_id:
            self._check_lpo_balance(record.task_id.sale_order_id)
        
        return record
    
    def write(self, vals):
        for record in self:
            partner_id = vals.get('partner_id', record.partner_id.id)
            if partner_id:
                partner = self.env['res.partner'].browse(partner_id)
                self._check_partner_blacklist(partner)
                if partner.hold_option in ['hold', 'credit_block']:
                    raise ValidationError(_("Customer/order is on hold, please check with finance"))
            
            task_id = vals.get('task_id', record.task_id.id)
            if task_id:
                task = self.env['project.task'].browse(task_id)
                if task.sale_order_id:
                    self._check_lpo_balance(task.sale_order_id)
        
        return super(CustomTripSheet, self).write(vals)

    @api.onchange('partner_id', 'task_id')
    def _onchange_partner_or_task(self):
        warning = False
        partner = None
        sale_order = None
        
        if self.partner_id:
            partner = self.partner_id
        elif self.task_id and self.task_id.partner_id:
            partner = self.task_id.partner_id
        
        if partner:
            if partner.is_customer_black_list:
                warning = {
                    'title': _("Customer Blacklisted"),
                    'message': _(
                        "Customer '%s' is blacklisted.\n"
                        "You may not be able to save this trip sheet.\n"
                        "Please consult with finance department."
                    ) % partner.name
                }
            elif partner.hold_option in ['hold', 'credit_block']:
                warning = {
                    'title': _("Customer on Hold"),
                    'message': _(
                        "Customer '%s' is on %s status.\n"
                        "You may not be able to save this trip sheet.\n"
                        "Please consult with finance department."
                    ) % (partner.name, partner.hold_option)
                }
        
        if not warning and self.task_id and self.task_id.sale_order_id:
            sale_order = self.task_id.sale_order_id
            lpo_control = self.env['lpo.control'].search([
                ('sale_id', '=', sale_order.id)
            ], limit=1)
            
            if lpo_control and lpo_control.total_po_value != 0 and lpo_control.total_available_balance <= 0:
                warning = {
                    'title': _("Insufficient PO Balance"),
                    'message': _(
                        "Sale Order %s has insufficient PO balance.\n"
                        "Total PO Value: %s\n"
                        "Available Balance: %s\n"
                        "Please coordinate with finance department."
                    ) % (sale_order.name, lpo_control.total_po_value, lpo_control.total_available_balance)
                }
        
        if warning:
            return {'warning': warning}


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    
    def _get_partner_to_check(self, record):
        if record.sale_order_id and record.sale_order_id.partner_id:
            return record.sale_order_id.partner_id
        return None
    
    def _check_partner_blacklist(self, partner):
        if partner and partner.is_customer_black_list:
            raise ValidationError(_(
                "Customer '%s' is blacklisted. Please check with finance department."
            ) % partner.name)

    def _check_lpo_balance(self, sale_order):
        if not sale_order:
            return
            
        lpo_control = self.env['lpo.control'].search([
            ('sale_id', '=', sale_order.id)
        ], limit=1)
        
        if lpo_control and lpo_control.total_po_value != 0 and lpo_control.total_available_balance <= 0:
            raise ValidationError(_(
                "Insufficient PO Balance for Sale Order %s\n"
                "Total PO Value: %s\n"
                "Available Balance: %s\n"
                "Please coordinate with finance department."
            ) % (
                sale_order.name,
                lpo_control.total_po_value,
                lpo_control.total_available_balance
            ))

    @api.constrains('sale_order_id', 'partner_id')
    def _check_partner_and_lpo_status(self):
        for record in self:
            partner = self._get_partner_to_check(record)
            
            if partner:
                self._check_partner_blacklist(partner)
                if partner.hold_option in ['hold', 'credit_block']:
                    raise ValidationError(_("Customer/order is on hold, please check with finance"))
            
            if record.sale_order_id:
                self._check_lpo_balance(record.sale_order_id)
    
    @api.model
    def create(self, vals):
        # Skip validation for overtime-created attendance
        if vals.get('overtime_created'):
            return super(HrAttendance, self).create(vals)
        
        if vals.get('sale_order_id'):
            sale_order = self.env['sale.order'].browse(vals['sale_order_id'])
            
            if sale_order and sale_order.partner_id:
                self._check_partner_blacklist(sale_order.partner_id)
                if sale_order.partner_id.hold_option in ['hold', 'credit_block']:
                    raise ValidationError(_("Customer/order is on hold, please check with finance"))
            
            self._check_lpo_balance(sale_order)
        
        return super(HrAttendance, self).create(vals)
    
    def write(self, vals):
        # ---------------------------------------------------------
        # 1. Skip validation during Archive / Unarchive
        # ---------------------------------------------------------
        if set(vals.keys()) == {'active'}:
            return super(HrAttendance, self).write(vals)

        # ---------------------------------------------------------
        # 2. Skip validation for overtime creation/update
        # ---------------------------------------------------------
        if vals.get('overtime_created'):
            return super(HrAttendance, self).write(vals)
        
        for record in self:
            # Also skip if the existing attendance is overtime created
            if record.overtime_created:
                continue
            
            sale_order = None
            
            if 'sale_order_id' in vals:
                sale_order_id = vals['sale_order_id']
                if sale_order_id:
                    sale_order = self.env['sale.order'].browse(sale_order_id)
                    
                    if sale_order and sale_order.partner_id:
                        self._check_partner_blacklist(sale_order.partner_id)
                        if sale_order.partner_id.hold_option in ['hold', 'credit_block']:
                            raise ValidationError(_("Customer/order is on hold, please check with finance"))
            elif record.sale_order_id:
                sale_order = record.sale_order_id
                if sale_order.partner_id:
                    self._check_partner_blacklist(sale_order.partner_id)
                    if sale_order.partner_id.hold_option in ['hold', 'credit_block']:
                        raise ValidationError(_("Customer/order is on hold, please check with finance"))
            
            if sale_order:
                self._check_lpo_balance(sale_order)
        
        return super(HrAttendance, self).write(vals)

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        warning = False
        if self.sale_order_id:
            if self.sale_order_id.partner_id:
                if self.sale_order_id.partner_id.is_customer_black_list:
                    warning = {
                        'title': _("Customer Blacklisted"),
                        'message': _(
                            "Customer '%s' is blacklisted.\n"
                            "You may not be able to save this attendance.\n"
                            "Please consult with finance department."
                        ) % self.sale_order_id.partner_id.name
                    }
                elif self.sale_order_id.partner_id.hold_option in ['hold', 'credit_block']:
                    warning = {
                        'title': _("Customer on Hold"),
                        'message': _(
                            "Customer '%s' is on %s status.\n"
                            "You may not be able to save this attendance.\n"
                            "Please consult with finance department."
                        ) % (self.sale_order_id.partner_id.name, self.sale_order_id.partner_id.hold_option)
                    }
            
            if not warning:
                lpo_control = self.env['lpo.control'].search([
                    ('sale_id', '=', self.sale_order_id.id)
                ], limit=1)
                
                if lpo_control and lpo_control.total_po_value != 0 and lpo_control.total_available_balance <= 0:
                    warning = {
                        'title': _("Insufficient PO Balance"),
                        'message': _(
                            "Sale Order %s has insufficient PO balance.\n"
                            "Total PO Value: %s\n"
                            "Available Balance: %s\n"
                            "Please coordinate with finance department."
                        ) % (self.sale_order_id.name, lpo_control.total_po_value, lpo_control.total_available_balance)
                    }
        
        if warning:
            return {'warning': warning}

    

class SaleOrder(models.Model):
    _inherit = 'sale.order'


    is_partner_blacklisted = fields.Boolean(
        string="Is Partner Blacklisted",
        compute='_compute_partner_status',
        store=True,
        help="Indicates if the partner is blacklisted"
    )
    
    is_partner_credit_blocked = fields.Boolean(
        string="Is Partner Credit Blocked",
        compute='_compute_partner_status',
        store=True,
        help="Indicates if the partner has credit blocked"
    )

    @api.depends('partner_id', 'partner_id.is_customer_black_list', 'partner_id.credit_block')
    def _compute_partner_status(self):
        for order in self:
            order.is_partner_blacklisted = order.partner_id.is_customer_black_list if order.partner_id else False
            order.is_partner_credit_blocked = order.partner_id.credit_block == 'yes' if order.partner_id else False

    @api.constrains('partner_id', 'state')
    def _check_partner_restrictions(self):
        for order in self:
            if order.partner_id:
                if order.partner_id.is_customer_black_list:
                    raise ValidationError(_(
                        "Customer '%s' is blacklisted. Please check with the finance department."
                    ) % order.partner_id.name)
                
                if order.partner_id.hold_option in ['hold', 'credit_block']:
                    raise ValidationError(
                        "Customer/order is on hold, please check with finance."
                    )


    # def _check_partner_blacklist(self, partner):
    #     if partner and partner.is_customer_black_list:
    #         raise ValidationError(_(
    #             "Customer '%s' is blacklisted. Please check with finance department."
    #         ) % partner.name)
        
    # @api.model
    # def create(self, vals):
    #     partner = self.env['res.partner'].browse(vals.get('partner_id'))
    #     if partner:
    #         self._check_partner_blacklist(partner)
    #         if partner.hold_option in ['hold', 'credit_block']:
    #             raise ValidationError("Customer/order is on hold, please check with finance.")
    #     return super(SaleOrder, self).create(vals)

    # def write(self, vals):
    #     if set(vals.keys()) == {'trip_ids'}:
    #         return super(SaleOrder, self).write(vals)
            
    #     for order in self:
    #         if order.partner_id:
    #             self._check_partner_blacklist(order.partner_id)
    #             if order.partner_id.hold_option in ['hold', 'credit_block']:
    #                 raise ValidationError("Customer/order is on hold, please check with finance.")
    #     return super(SaleOrder, self).write(vals)
    

    
class Lead(models.Model):
    _inherit = 'crm.lead'

    is_partner_blacklisted = fields.Boolean(
        string="Is Partner Blacklisted",
        compute='_compute_partner_status',
        store=True,
        help="Indicates if the partner is blacklisted"
    )
    
    is_partner_credit_blocked = fields.Boolean(
        string="Is Partner Credit Blocked",
        compute='_compute_partner_status',
        store=True,
        help="Indicates if the partner has credit blocked"
    )

    @api.depends('partner_id', 'partner_id.is_customer_black_list', 'partner_id.credit_block')
    def _compute_partner_status(self):
        for lead in self:
            lead.is_partner_blacklisted = lead.partner_id.is_customer_black_list if lead.partner_id else False
            lead.is_partner_credit_blocked = lead.partner_id.credit_block == 'yes' if lead.partner_id else False


    def _check_partner_blacklist(self, partner):
        if partner and partner.is_customer_black_list:
            raise ValidationError(_(
                "Customer '%s' is blacklisted. Please check with finance department."
            ) % partner.name)

    @api.constrains('partner_id')
    def _check_partner_hold_status(self):
        for record in self:
            if record.partner_id:
                self._check_partner_blacklist(record.partner_id)
                if record.partner_id.hold_option in ['hold', 'credit_block']:
                    raise ValidationError(_("Customer/order is on hold, please check with finance"))

    @api.model
    def create(self, vals):
        if vals.get('partner_id'):
            partner = self.env['res.partner'].browse(vals['partner_id'])
            self._check_partner_blacklist(partner)
            if partner.hold_option in ['hold', 'credit_block']:
                raise ValidationError(_("Customer/order is on hold, please check with finance"))
        return super(Lead, self).create(vals)
    
    def write(self, vals):
        for record in self:
            partner_id = vals.get('partner_id', record.partner_id.id)
            if partner_id:
                partner = self.env['res.partner'].browse(partner_id)
                self._check_partner_blacklist(partner)
                if partner.hold_option in ['hold', 'credit_block']:
                    raise ValidationError(_("Customer/order is on hold, please check with finance"))
        return super(Lead, self).write(vals)

    

class PlanningSlot(models.Model):
    _inherit = 'planning.slot'
    
    def _check_partner_blacklist(self, partner):
        if partner and partner.is_customer_black_list:
            raise ValidationError(_(
                "Customer '%s' is blacklisted. Please check with finance department."
            ) % partner.name)

    def _check_customer_hold_status(self):
        for slot in self:
            if slot.task_resource_id and slot.task_resource_id.partner_id:
                partner = slot.task_resource_id.partner_id
                self._check_partner_blacklist(partner)
                if partner.hold_option in ('hold', 'credit_block'):
                    raise ValidationError(_(
                        "Customer '%s' is on %s status. \n"
                        "Task: %s\n"
                        "Please check with finance."
                    ) % (partner.name, partner.hold_option, slot.task_resource_id.name))
    
    def _check_lpo_balance(self):
        for slot in self:
            if slot.task_resource_id and slot.task_resource_id.sale_order_id:
                sale_order = slot.task_resource_id.sale_order_id
                lpo_control = self.env['lpo.control'].search([
                    ('sale_id', '=', sale_order.id)
                ], limit=1)
                
                if lpo_control and lpo_control.total_po_value != 0 and lpo_control.total_available_balance <= 0:
                    raise ValidationError(_(
                        "Insufficient PO Balance for Sale Order %s\n"
                        "Task: %s\n"
                        "Total PO Value: %s\n"
                        "Available Balance: %s\n"
                        "Please coordinate with finance department."
                    ) % (
                        sale_order.name,
                        slot.task_resource_id.name,
                        lpo_control.total_po_value,
                        lpo_control.total_available_balance
                    ))

    @api.model
    def create(self, vals):
        record = super(PlanningSlot, self).create(vals)
        record._check_customer_hold_status()
        record._check_lpo_balance()
        return record

    def write(self, vals):
        result = super(PlanningSlot, self).write(vals)
        self._check_customer_hold_status()
        self._check_lpo_balance()
        return result

    @api.onchange('task_resource_id')
    def _onchange_task_resource_id(self):
        warning = False
        if self.task_resource_id:
            if self.task_resource_id.partner_id:
                partner = self.task_resource_id.partner_id
                if partner.is_customer_black_list:
                    warning = {
                        'title': _("Customer Blacklisted"),
                        'message': _(
                            "Customer '%s' is blacklisted.\n"
                            "Please consult with finance department."
                        ) % partner.name
                    }
                elif partner.hold_option in ('hold', 'credit_block'):
                    warning = {
                        'title': _("Customer on Hold"),
                        'message': _(
                            "Customer '%s' is on %s status.\n"
                            "Please consult with finance department."
                        ) % (partner.name, partner.hold_option)
                    }
            
            if not warning and self.task_resource_id.sale_order_id:
                so = self.task_resource_id.sale_order_id
                lpo_control = self.env['lpo.control'].search([
                    ('sale_id', '=', so.id)
                ], limit=1)
                
                if lpo_control and lpo_control.total_po_value != 0 and lpo_control.total_available_balance <= 0:
                    warning = {
                        'title': _("Insufficient PO Balance"),
                        'message': _(
                            "Sale Order %s has insufficient PO balance.\n"
                            "Total PO Value: %s\n"
                            "Available Balance: %s\n"
                            "Please coordinate with finance department."
                        ) % (so.name, lpo_control.total_po_value, lpo_control.total_available_balance)
                    }
        
        if warning:
            return {'warning': warning}