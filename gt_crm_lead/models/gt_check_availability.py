# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
from datetime import datetime
import re
import datetime


class IndentRequest(models.Model):
    _inherit = 'indent.request'

    crm_id = fields.Many2one('crm.lead', string='Crm')


class CRMLead(models.Model):
    _inherit = 'crm.lead'

    check_branch_mps = fields.Boolean(compute='check_branch_compute', store=True)
    indent_request_done = fields.Boolean(string='Done Indent Request', default=False)

    @api.depends('branch_id')
    def check_branch_compute(self):
        for rec in self:
            rec.check_branch_mps = False
            if rec.branch_id.branch_group_id.name == 'MPS':
                rec.check_branch_mps = True

    def action_view_indent_request(self):
        view_id = self.env.ref("purchase_indent_request.view_indent_request_from")
        domain = [("crm_id", '=', self.id)]
        indent_request = self.env['indent.request'].search([('crm_id', '=', self.id)])
        return {
            'name': 'Indent Request',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'indent.request',
            'res_id': indent_request.id,
        }

    # Point no 20 PS2
    def button_check_availability(self):
        for line in self.service_ids:
            emp_id = self.env['hr.employee'].search(
                [('product_ids', '=', line.product_id.id), ('emp_status', '=', 'active'),
                 ('billable', '=', True)])
            print('line________________', emp_id, len(emp_id))
            counter = 0
            if emp_id:
                counter = len(emp_id.filtered(lambda x: not x.task_shift_ids))
                print('counter++++++++++++++++', counter)
            line.write({'available_quantity': counter})

    def button_subcontractor_indent(self):
        line_list = []

        text = re.compile('<.*?>')
        message = re.sub(text, '', self.description)
        description = str(message) + '  ' + str(self.partner_id.name)

        for lines in self.service_ids:
            note_add = lines.lead_id.name + ' | UOM: ' + str(lines.product_uom.name) + ' | Date ' + str(
                lines.start_date) + '  ' + str(
                lines.end_date) + ' | Standard Hours ' + str(lines.std_hrs) + ' | Available Qty ' + str(
                lines.available_quantity)

            vals = {'product_id': lines.product_id.id,
                    'date': lines.start_date,
                    'quantity': lines.product_uom_qty,
                    'product_uom': lines.product_uom.id,
                    'available_qty': lines.available_quantity,
                    'name': lines.product_id.name,
                    'note': note_add,
                    'branch_id': self.branch_id.id,
                    }
            line_list.append((0, 0, vals))

        branch_id = self._context.get('allowed_branch_ids')[0]
        dep_id = self.env['hr.department'].search([('name', 'like', 'Sales')], limit=1)
        warehouse = self.env['stock.warehouse'].search([('name', 'like', 'Head Office Store')], limit=1)
        purchase = self.env['purchase.type'].search([('name', 'like', 'PR - Price Inquiry (Indent)')], limit=1)

        indent_vals = {
            'user_id': self.env.user.id,
            'branch_id': self.branch_id.id,
            'request_lines_ids': line_list,
            'department_id': dep_id.id if dep_id else False,
            'warehouse_id': warehouse.id if warehouse else False,
            'type_purchase': purchase.id if purchase else False,
            'remarks': description,
            'crm_id': self.id
        }
        indent_id = self.env['indent.request'].create(indent_vals)
        self.update({'indent_request_done': True})

        template = self.env['mail.template'].sudo().search([('name', 'ilike', 'Procurement Group')], limit=1)
        if template:
            subject = _("Indent Request Created")
            email_management = self.env['email.notification.management'].search([])
            for proc in email_management:
                if proc.procurement_email:
                    body = """
                                <div>
                                    RFQ Created for CRM """ + str(self.name) + """ .
                                    <br></br>
                                    Thank You.
                                </div>
                                """
                    template.send_mail(self.id, email_values={
                        'email_from': self.env.user.email or '',
                        'email_to': proc.procurement_email,
                        'subject': subject,
                        'body_html': body,
                    }, force_send=True)


class AvailableQuantity(models.Model):
    _inherit = "crm.service.line"

    available_quantity = fields.Float(string='Available Quantity')
