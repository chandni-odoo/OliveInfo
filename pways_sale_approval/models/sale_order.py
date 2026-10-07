# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime

from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"


    state = fields.Selection([
        ('costing', 'Costing'),
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('customer_approve', 'Customer Approve'),
        ('agreement', 'Agreement'),
        ('pre_approval', 'Pre Approval'),
        ('to approve', 'To Approve'),
        ('to_reject', 'Rejected'),
        ('revisions', 'REVISIONS'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3)
    has_approval = fields.Boolean(compute="_compute_has_approval")
    sale_history_ids = fields.One2many('sale.approval.history', 'sale_id', string="Sale History", readonly=True)
    reject_reason = fields.Text(string="Reject Reason", copy=False)
    sale_approval = fields.Boolean(compute="_compute_sale_approval")
    previous_state = fields.Char(string="Previous State")

    def _compute_sale_approval(self):
        for sale in self:
            approval_lines = self.env['sale.approval.lines'].search([
                ('approval_id.document_type', '=', self.state),
                ('limit', '<=', sale.amount_total),
            ])
            print('approval_lines++++++++++', approval_lines)
            print('sale.sale_history_ids++++++++', sale.sale_history_ids)
            if sale.sale_history_ids and (sale.state == sale.previous_state) and all(
                    [line.status == ('approve') for line in sale.sale_history_ids]):
                sale.sale_approval = False
            elif approval_lines:
                sale.sale_approval = True
            else:
                sale.sale_approval = False

    def _compute_has_approval(self):
        for sale in self:
            approval_id = sale.sale_history_ids.filtered(
                lambda x: x.status == 'pending' and x.user_id.id == self.env.user.id)
            is_rejected = any([status == 'reject' for status in sale.sale_history_ids.mapped('status')])
            if not is_rejected and sale.state == 'to approve' and approval_id and approval_id.status == 'pending':
                sale.has_approval = True
            else:
                sale.has_approval = False

    def action_approval(self):
        pending_approval = self.sale_history_ids.filtered(lambda
                                                              x: x.user_id.id == self.env.user.id and x.status == 'pending' and x.document_type == self.previous_state)
        pending_approval.write({'status': 'approve', 'date_done': datetime.now()})

        # activity = self.env['mail.activity'].search([('res_id', '=', self.id), ('user_id', '=', self.env.user.id)])
        print('activity++++++++++++++', self.activity_ids)
        for act in self.activity_ids.filtered(lambda u: u.user_id.id == self.env.user.id):
            act.action_done()

        model_id = self.env['ir.model'].sudo().search([('model', '=', 'sale.order')], limit=1)
        activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Sale Approval Update')],
                                                                        limit=1)
        if not activity_type_id:
            activity_type_id = self.env['mail.activity.type'].create({
                'name': 'Sale Approval Update',
                'res_model': 'sale.order',
            })
        activity_vals = {'res_model_id': model_id.id,
                         'res_model': 'sale.order',
                         'res_id': self.id,
                         'res_name': 'Sale Order Approval Update',
                         'user_id': self.user_id.id,
                         'activity_type_id': activity_type_id.id,
                         'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')
                         }
        print("activity_vals+_+_+_+", activity_vals)
        activity_id = self.env['mail.activity'].sudo().create(activity_vals)

        # # @chandni@globalteckz
        # """ Costing Approval Notification """
        for rec in self:
            all_approved = all(h.status == 'approve' for h in rec.sale_history_ids)
            print ("ALl Approved______________",all_approved)
            if all_approved == True:
                if rec.previous_state == 'costing':
                    print ("Rec state____",rec.state)
                    sapproved_id = self.env['sale.approval'].search([('document_type', '=', 'costing')], limit=1)
                    customer_approve = sapproved_id.approval_line_ids.mapped('user_id')
                    mail_temp = self.env.ref('pways_sale_approval.sending_mail_template')
                    costing_number = rec.name
                    customer_name = rec.partner_id.name
                    subject = f"Costing Approved: {costing_number} for {customer_name}"
                    # # APPROVAL
                    # if mail_temp:
                    #     for user in customer_approve:
                    #         if user.email:
                    #             body = """
                    #             <div>
                    #                 <p>Dear Recipient  """ + str(user.name) + """,
                    #                 <br/><br/>
                    #                     Pleased to inform you that the costing for """ + str(
                    #                 customer_name) + """ under """ + str(costing_number) + """ 
                    #                     has been approved. Kindly proceed with the quotation process accordingly.
                    #                 <br></br>
                    #                 Thank you.
                    #                 <br/>
                    #                 <br/>
                    #             <div> """
                    #             mail_temp.send_mail(rec.id, email_values={
                    #                 'email_to': user.email,
                    #                 'subject': subject,
                    #                 'body_html': body,
                    #             }, force_send=True)
                    # SALES-PERSON
                    if rec.user_id:
                        body = """
                            <div> 
                                <p>Dear Recipient  """ + str(rec.user_id.name) + """,
                                <br/><br/>
                                    Pleased to inform you that the costing for """ + str(customer_name) + """ under """ + str(
                            costing_number) + """ 
                                    has been approved. Kindly proceed with the quotation process accordingly.
                                <br></br>
                                Thank you.
                                <br/>
                                <br/>
                            <div> """
                        sales_person_mail = mail_temp.send_mail(rec.id, email_values={
                            'email_to': rec.user_id.email,
                            'subject': subject,
                            'body_html': body,
                        }, force_send=True)
                    print("SAles PErson_________", sales_person_mail)

        if self.sale_history_ids and all([line.status == 'approve' for line in self.sale_history_ids]):
            vals = {'state': self.previous_state}

            # If approval is completed for Pre Approval,
            # enable the Confirm button
            if self.previous_state == 'pre_approval':
                vals['pre_approval_completed'] = True

            self.write(vals)
        return True

        # if self.sale_history_ids and all([line.status == 'approve' for line in self.sale_history_ids]):
        #     self.write({'state': self.previous_state})

    def too_approve(self):
        self.previous_state = self.state

        # Pre-approval is not completed yet
        if self.state == 'pre_approval':
            self.pre_approval_completed = False

        data = []
        approval_lines = self.env['sale.approval.lines'].search([
            ('limit', '<=', self.amount_total),
            ('approval_id.branch_id', '=', self.branch_id.id),
            ('approval_id.document_type', '=', self.state),
        ])
        user_list = []
        for line in approval_lines:
            data.append((0, 0, {'user_id': line.user_id.id, 'document_type': line.approval_id.document_type}))
            user_list.append(line.user_id)
        self.sale_history_ids = data
        self.write({'state': 'to approve'})

        model_id = self.env['ir.model'].sudo().search([('model', '=', 'sale.order')], limit=1)
        activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Sale Approval Notification')],
                                                                        limit=1)
        if not activity_type_id:
            activity_type_id = self.env['mail.activity.type'].create({
                'name': 'Sale Approval Notification',
                'res_model': 'sale.order',
            })
        for user in user_list:
            activity_vals = {'res_model_id': model_id.id,
                             'res_model': 'sale.order',
                             'res_id': self.id,
                             'res_name': 'Sale Order To Be Assigned',
                             'user_id': user.id,
                             'activity_type_id': activity_type_id.id,
                             'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')
                             }
            print("activity_vals+_+_+_+", activity_vals)
            activity_id = self.env['mail.activity'].sudo().create(activity_vals)


class SaleApprovalsHistory(models.Model):
    _name = "sale.approval.history"
    _description = "Approval History"

    sale_id = fields.Many2one('sale.order', string="Sale Request")
    user_id = fields.Many2one('res.users', string="Approver")
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approve', 'Approved'),
        ('reject', 'Rejected')], default='pending', copy=False, string="Approval Status")
    date_done = fields.Datetime(string="Approval Date")
    document_type = fields.Selection(
        [('costing', 'Costing'), ('draft', 'Quotation'), ('customer_approve', 'Customer Approve'),
         ('agreement', 'Agreement'), ('pre_approval', 'Pre Approval'), ('sale', 'Sales Order')], string='Approval Type',
        required=True)
