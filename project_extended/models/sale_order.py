# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    lpo_count = fields.Integer(compute='compute_lpo_count')
    display_extra_line = fields.Boolean(string="Dispaly Extra lines")
    def compute_lpo_count(self):
        for record in self:
            lpo_control_ids = self.env['lpo.control'].search([('sale_id', '=', record.id)])
            record.lpo_count = len(lpo_control_ids.ids)

    def copy(self, default=None):
        rtn = super(SaleOrder, self).copy(default=default)
        if rtn:
            is_overtime_product = rtn.order_line.filtered('product_template_id.is_overtime_product')
            if is_overtime_product:
                is_overtime_product.sudo().unlink()
        return rtn

    def action_lpo_control(self):
        lpo_control_ids = self.env['lpo.control'].search([('sale_id', '=', self.id)])
        return {
            'name': _('LPO Control'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'lpo.control',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', lpo_control_ids.ids)],
        }

    def create_lpo_control(self):
        sale_line_ids = []
        action = self.env["ir.actions.actions"]._for_xml_id("project_extended.lpo_control_wizard_action")
        for line in self.order_line:
            sale_line_ids.append([0, 0, {
                'sale_order_line_id':line.id,
                'name': line.name,
            }])
        action['context'] = {
            'default_lpo_control_ids': sale_line_ids,
            'default_sale_id':self.id,
        }
        return action


    def get_cost_plus_charges(self):
        cost_plus = self.env['product.category'].search([('name','=','CostPlus')])
        temp = self.env['product.template'].search([('categ_id', '=', cost_plus.id)])
        products = self.env['product.product'].search([('product_tmpl_id','in',temp.ids)])
        for product in products:
            print("Product Template ID:", product.id)
            print("Product ID:", product.product_tmpl_id.id)
            
            so_line_id = self.env['sale.order.line'].search([('order_id','=',self.id)], limit=1)
            if so_line_id:
                existing_charges = self.env['so.additional.charges'].search([('product_id', '=', product.id),
                    ('so_line_id', '=', so_line_id.id)], limit=1)
                if not existing_charges:
                    text = re.compile('<.*?>')
                    remarks = re.sub(text, '', product.description)

                    so = self.env['so.additional.charges'].create({
                            'product_id':product.id,
                            'quantity':1,
                            'product_uom_category_id': product.uom_id.category_id.id,
                            'product_uom':product.uom_id.id,
                            'price_unit':product.list_price,
                            'based_cost':product.based_cost,
                            'recurring':product.recurring,
                            'remarks':remarks,
                            'so_id':so_line_id.order_id.id,
                            'so_line_id':so_line_id.id
                            })
            else:
                raise UserError('Costplus Charges not added for this Sale order without order lines !!!')

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    std_hrs = fields.Float(string="Std hrs")
    employee_id = fields.Many2one('hr.employee', string="Employes")
    sequence_ref = fields.Char(string='Sequence', compute='_sequence_ref')

    @api.depends('order_id.order_line', 'order_id.order_line.product_id')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sequence_ref = no
            for l in line.order_id.order_line:
                no += 1
                l.sequence_ref = no


    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.order_id:
            if self.employee_id:
                task_id = self.task_id
                new_description = "%(line_product_name)s -  %(task_name)s - %(employee_name)s" % {
                            'line_product_name': self.product_id.name,
                            # 'display_name': self.name,
                            'task_name': self.task_id.seq_code,
                            'employee_name':self.employee_id.name,
                }
                employee = self.employee_id
                product_special_ot = self.env.ref('project_extended.product_soc_product_template')
                product_normal_ot = self.env.ref('project_extended.product_noc_product_template')
               
                sale_lineids = self.env['sale.order.line'].search([('task_id','=',task_id.id)])
                for sale in sale_lineids:
                    
                    if sale.product_id == product_special_ot:
                        soc_description = "%(line_product_name)s -  %(task_name)s - %(employee_name)s" % {
                                    'line_product_name': self.product_id.name,
                                    'display_name': 'SOC',
                                    'task_name': sale.task_id.seq_code,
                                    'employee_name':employee.name,
                        }
                        
                        sale.write({'employee_id': employee.id,'name':soc_description})
                    if sale.product_id == product_normal_ot:
                        noc_description = "%(line_product_name)s -  %(task_name)s - %(employee_name)s" % {
                                    'line_product_name': sale.product_id.name,
                                    'display_name': 'NOC',
                                    'task_name': sale.task_id.seq_code,
                                    'employee_name':employee.name,
                        }
                        sale.write({'employee_id': employee.id,'name':noc_description})

                self.write({'product_uom_category_id': self.product_id.uom_id.category_id.id,'name':new_description})

            else:
                description = "%(line_product_name)s -  %(task_name)s" % {
                            'line_product_name': self.product_id.name,
                            'task_name': self.task_id.seq_code,
                }
                self.write({'product_uom_category_id': self.product_id.uom_id.category_id.id,'name':description})
            

            return {
                'domain': {'so_line_id': [('order_id', '=', self.order_id._origin.id)]},
            }

class SaleOrderLine(models.Model):
    _inherit = 'account.move.line'

    equipment_type_id = fields.Many2one('equipment.type', string="Equipment Type")
