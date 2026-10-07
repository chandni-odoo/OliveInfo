from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.tools.translate import _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _send_notifications(self, partner, expiring_docs, recipient_emails, branch_name):
        today = fields.Date.today()
        
        recipient_users = self.env['res.users'].search([
            ('login', 'in', recipient_emails)
        ])
        
        if not recipient_users:
            return
            
        activity_type = self.env['mail.activity.type'].sudo().search(
            [('name', '=', f'Employee Document Expiry - {branch_name}')], 
            limit=1
        )
        if not activity_type:
            activity_type = self.env['mail.activity.type'].sudo().create({
                'name': f'Employee Document Expiry - {branch_name}',
                'category': 'default'
            })
        
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', 'res.partner')], 
            limit=1
        )
        
        doc_list = "\n".join([
            f"- {doc.document_line_id.name} (Expires: {doc.valid_to})" 
            for doc in expiring_docs
        ])
        
        message = _(
            f"Employee %s has documents expiring soon:\n%s\n\n"
            "Please review and renew these documents."
        ) % (partner.name, doc_list)
        
        for user in recipient_users:
            self.env['bus.bus']._sendone(
                user.partner_id,
                'simple_notification',
                {
                    'title': f'{branch_name} Employee Document Expiry',
                    'message': f'{partner.name} has documents expiring soon',
                    'sticky': True,
                    'warning': True,
                }
            )
            
            existing_activity = self.env['mail.activity'].sudo().search([
                ('res_model_id', '=', model_id.id),
                ('res_id', '=', partner.id),
                ('user_id', '=', user.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done'),
            ], limit=1)
            
            if not existing_activity:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': model_id.id,
                    'res_model': 'res.partner',
                    'res_id': partner.id,
                    'user_id': user.id,
                    'activity_type_id': activity_type.id,
                    'summary': f'{branch_name} Employee Document Expiry',
                    'note': message,
                    'date_deadline': today,
                })

    def _check_document_expiry_notification(self):
        today = fields.Date.today()
        notification_date = today + relativedelta(days=15)  
        
        branch_config = {
            '2037': ['clinton.murzello@dulsco.qa'],
            '20037': ['clinton.murzello@dulsco.qa'],
            '2030': ['mariquit.gonzales@dulsco.qa'],
            '20030': ['mariquit.gonzales@dulsco.qa'],
            '2040': ['serlexier.cerezo@dulsco.qa'],
            '20040': ['serlexier.cerezo@dulsco.qa'],
        }
        
        partners = self.env['res.partner'].search([
            ('document_line_ids.valid_to', '<=', notification_date),
            ('document_line_ids.valid_to', '>=', today),
            ('document_line_ids.status', '=', 'active'),
            ('branch_id.code', 'in', list(branch_config.keys())),
            ('customer_rank', '>', 0)
        ])
        
        for partner in partners:
            branch_code = partner.branch_id.code
            if branch_code not in branch_config:
                continue
                
            expiring_docs = partner.document_line_ids.filtered(
                lambda d: d.valid_to <= notification_date and 
                          d.valid_to >= today and 
                          d.status == 'active'
            )
            
            if expiring_docs:
                self._send_notifications(
                    partner, 
                    expiring_docs, 
                    branch_config[branch_code], 
                    partner.branch_id.name
                )

    @api.model
    def _cron_check_document_expiry(self):
        self._check_document_expiry_notification()


    def _send_supplier_notifications(self, partner, expiring_docs, recipient_emails, branch_name):
        today = fields.Date.today()
        
        recipient_users = self.env['res.users'].search([
            ('login', 'in', recipient_emails)
        ])
        
        if not recipient_users:
            return
            
        activity_type = self.env['mail.activity.type'].sudo().search(
            [('name', '=', f'Supplier Document Expiry - {branch_name}')], 
            limit=1
        )
        if not activity_type:
            activity_type = self.env['mail.activity.type'].sudo().create({
                'name': f'Supplier Document Expiry - {branch_name}',
                'category': 'default'
            })
        
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', 'res.partner')], 
            limit=1
        )
        
        doc_list = "\n".join([
            f"- {doc.document_line_id.name} (Expires: {doc.valid_to})" 
            for doc in expiring_docs
        ])
        
        message = _(
            f"Supplier %s has documents expiring soon:\n%s\n\n"
            "Please review and renew these documents."
        ) % (partner.name, doc_list)
        
        for user in recipient_users:
            self.env['bus.bus']._sendone(
                user.partner_id,
                'simple_notification',
                {
                    'title': f'{branch_name} Supplier Document Expiry',
                    'message': f'{partner.name} has documents expiring soon',
                    'sticky': True,
                    'warning': True,
                }
            )
            
            existing_activity = self.env['mail.activity'].sudo().search([
                ('res_model_id', '=', model_id.id),
                ('res_id', '=', partner.id),
                ('user_id', '=', user.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done'),
            ], limit=1)
            
            if not existing_activity:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': model_id.id,
                    'res_model': 'res.partner',
                    'res_id': partner.id,
                    'user_id': user.id,
                    'activity_type_id': activity_type.id,
                    'summary': f'{branch_name} Supplier Document Expiry',
                    'note': message,
                    'date_deadline': today,
                })

    def _check_supplier_document_expiry_notification(self):
        today = fields.Date.today()
        notification_date = today + relativedelta(days=15)  
        
        branch_config = {
            '2037': ['vinoth.kumar@dulsco.qa', 'mazher.mohammed@dulsco.qa'],
            '20037': ['vinoth.kumar@dulsco.qa', 'mazher.mohammed@dulsco.qa'],
            '2030': ['vinoth.kumar@dulsco.qa', 'mazher.mohammed@dulsco.qa'],
            '20030': ['vinoth.kumar@dulsco.qa', 'mazher.mohammed@dulsco.qa'],
            '2040': ['vinoth.kumar@dulsco.qa', 'mazher.mohammed@dulsco.qa'],
            '20040': ['vinoth.kumar@dulsco.qa', 'mazher.mohammed@dulsco.qa'],
        }
        
        suppliers = self.env['res.partner'].search([
            ('document_line_ids.valid_to', '<=', notification_date),
            ('document_line_ids.valid_to', '>=', today),
            ('document_line_ids.status', '=', 'active'),
            ('branch_id.code', 'in', list(branch_config.keys())),
            ('supplier_rank', '>', 0)  
        ])
        
        for supplier in suppliers:
            branch_code = supplier.branch_id.code
            if branch_code not in branch_config:
                continue
                
            expiring_docs = supplier.document_line_ids.filtered(
                lambda d: d.valid_to <= notification_date and 
                          d.valid_to >= today and 
                          d.status == 'active'
            )
            
            if expiring_docs:
                self._send_supplier_notifications(
                    supplier, 
                    expiring_docs, 
                    branch_config[branch_code], 
                    supplier.branch_id.name
                )

    @api.model
    def _cron_check_supplier_document_expiry(self):
        self._check_supplier_document_expiry_notification()


class HrDocumentLine(models.Model):
    _inherit = 'hr.document.line'

    partner_id = fields.Many2one('res.partner', string="Customer")
    customer_name = fields.Char(related='partner_id.name', store=True)
    address_no = fields.Char(related='partner_id.address_no', store=True)
    branch_id = fields.Many2one(related='partner_id.branch_id', string="Branch", store=True)


    