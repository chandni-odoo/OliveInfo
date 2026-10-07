# -*- coding: utf-8 -*-
from odoo import api, fields, models

from odoo.exceptions import UserError, ValidationError


class SaleCustomerApprove(models.TransientModel):
    _name = "sale.customer.approve"
    _description = "Customer Approve"
    _inherit = ['mail.thread']

    data_file = fields.Binary(string="Signed Quote")
    file_name = fields.Char('Filename')
    remarks = fields.Text(string="Remarks")

    def action_approve(self):
        # Chandni@globalteckz
        """ Customer Approval Notification """
        sale_id = self.env['sale.order'].browse(self.env.context.get('active_id'))
        sapproved_id = self.env['sale.approval'].search([('document_type', '=', 'customer_approve')], limit=1)
        # if not sapproved_id:
        #     raise ValidationError("Setup for Email Sale Customer Approval Notification")

        customer_approve = sapproved_id.approval_line_ids.mapped('user_id')
        mail_temp = self.env.ref('pways_sale_approval.sending_mail_template')
        quotation_number = sale_id.name
        customer_name = sale_id.partner_id.name
        subject = f"Quotation Approved by Customer: {quotation_number} for {customer_name}"
        if mail_temp:
            for user in customer_approve:
                if user.email:
                    body = """
                    <div>
                        <p>Dear Recipient  """ + str(user.display_name) + """,
                        <br/><br/>
                        Pleased to inform you that the Quotation for """ + str(customer_name) + """ under """ + str(
                        quotation_number) + """ has been approved by Customer. Kindly proceed with the further process accordingly.
                        <br></br>
                        Thank you.
                        <br/>
                    <div>"""
                    mail_temp.send_mail(sale_id.id, email_values={
                        'email_to': user.email,
                        'subject': subject,
                        'body_html': body,
                    }, force_send=True)
        # SALES-PERSON
        if sale_id.user_id:
            body = """
                <div>
                    <p>Dear Recipient  """ + str(sale_id.user_id.display_name) + """,
                    <br/><br/>
                    Pleased to inform you that the Quotation for """ + str(customer_name) + """ under """ + str(
                quotation_number) + """ has been approved by Customer. Kindly proceed with the further process accordingly.
                    <br></br>
                    Thank you.
                    <br/>
                <div>"""
            mail_temp.send_mail(sale_id.id, email_values={
                'email_to': sale_id.user_id.email,
                'subject': subject,
                'body_html': body,
            }, force_send=True)
        #Customer Service Send Email
        search_ids = self.env['email.notification.management'].search([])[-1].id
        email_mgmt_id = self.env['email.notification.management'].browse(search_ids)

        if email_mgmt_id:
            customer_service_email = email_mgmt_id.customer_service_email
            scheduler_email = email_mgmt_id.scheduler_email

            if mail_temp:
                """ Customer Service Email """
                if customer_service_email:
                    body = """
                        <div>
                        <p>Dear Recipient  """ + str(sale_id.user_id.display_name) + """,
                        <br/><br/>
                        Pleased to inform you that the Quotation for """ + str(customer_name) + """ under """ + str(
                        quotation_number) + """ has been approved by Customer. Kindly proceed with the further process accordingly.
                        <br></br>
                        Thank you.
                        <br/>
                    <div>"""
                    mail_temp.send_mail(sale_id.id, email_values={
                        'email_to': customer_service_email,
                        'subject': subject,
                        'body_html': body,
                    }, force_send=True)

        body_msg = ''
        attachments = self.env['ir.attachment'].sudo().create({
            'name': sale_id.name,
            'type': 'binary',
            'datas': self.data_file,
            'res_model': 'sale.order',
            'res_id': sale_id.id,
            'res_name': self.file_name,
            'public': True,
        })
        if self.remarks:
            body_msg = "<b>" + self.remarks + "</b>"
        sale_id.message_post(body=body_msg, attachments=[attachments.ids])
        sale_id.write({'state': 'customer_approve'})
