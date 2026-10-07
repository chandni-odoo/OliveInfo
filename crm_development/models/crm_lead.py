from odoo import models, fields, api, _
import re

class CrmServiceLine(models.Model):
    _inherit = 'crm.service.line'
    
    unit_price = fields.Float(string="Unit Price", digits='Product Price')
    cost = fields.Float(string="Cost", digits='Product Price')
    margin = fields.Float(
        string="Margin", 
        compute='_compute_margin',
        store=True,
        digits='Product Price'
    )
    
    etd = fields.Date(string="ETD")
    brand_id = fields.Many2one('product.brand', string="Brand")
    
    @api.depends('unit_price', 'cost')
    def _compute_margin(self):
        for line in self:
            line.margin = line.unit_price - line.cost
    
    # Auto-set cost and unit price when product is selected
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_price = self.product_id.list_price
            self.cost = self.product_id.standard_price
            self.brand_id = self.product_id.brand_id
            self.product_uom = self.product_id.uom_id.id
            self.available_quantity = self.product_id.qty_available

class IndentRequestLine(models.Model):
    _inherit = "indent.request.line"

    brand_id = fields.Many2one('product.brand', string="Brand")

class CRMLead(models.Model):
    _inherit = 'crm.lead'

    def button_create_rfq_mro(self):
        line_list = []

        text = re.compile('<.*?>')
        message = re.sub(text, '', self.description)
        description = str(message) + '  ' + str(self.partner_id.name)

        for lines in self.service_ids:
            note_add = lines.lead_id.name + ' | UOM: ' + str(lines.product_uom.name) + ' | Date: ' + str(
                lines.start_date) + '  ' + str(
                lines.end_date) + ' | Standard Hours: ' + str(lines.std_hrs) + ' | Available Qty: ' + str(
                lines.available_quantity) + ' | Brand: ' + str(lines.brand_id.name)
            
            brand_id = lines.brand_id.id if lines.brand_id else False
            
            vals = {'product_id': lines.product_id.id,
                    'date': lines.start_date,
                    'quantity': lines.product_uom_qty,
                    'product_uom': lines.product_uom.id,
                    'available_qty': lines.available_quantity,
                    'name': lines.product_id.name,
                    'note': note_add,
                    'branch_id': self.branch_id.id,
                    'brand_id': brand_id,
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

        group = self.env.ref('crm_development.rfq_request_approved_group', raise_if_not_found=False)

        if group and group.users:
            msg = _("An RFQ has been created for this lead (%s). Please review and take action.") % (self.name)
            self.message_post(body=msg, partner_ids=group.users.mapped('partner_id').ids)
            model_id = self.env['ir.model'].sudo().search([('model', '=', 'crm.lead')], limit=1)
            activity_type = self.env['mail.activity.type'].sudo().search([('name', '=', 'RFQ create Alert')], limit=1)
            
            if not activity_type:
                activity_type = self.env['mail.activity.type'].sudo().create({
                    'name': 'RFQ create Alert',
                    'category': 'default',
                })

            for approver in group.users:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': model_id.id,
                    'res_model': 'crm.lead',
                    'res_id': self.id,
                    'res_name': f'RFQ Created for Lead {self.name}',
                    'user_id': approver.id,
                    'activity_type_id': activity_type.id,
                    'date_deadline': fields.Datetime.today(),
                })

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
