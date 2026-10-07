# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.exceptions import AccessError
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class CostPlus(models.Model):
    _name = "cost.plus"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Cost Plus'

    name = fields.Char(string="Name", readonly=True)
    cost_date = fields.Date(string="Date", default=datetime.today(), readonly=True)
    cost_line_ids = fields.One2many('cost.plus.line', 'cost_plus_id', string="Cost Line")
    reject_reason = fields.Text(string="Reject Reason", readonly=True)
    state = fields.Selection([('new', 'New'), ('pending', 'Pending'), ('approved', 'Approved'), ('reject', 'Rejected')],
                             string='State', default='new', track_visibility='onchange')
    is_approved = fields.Boolean(string="Is Approved", default=False)
    users_count = fields.Integer(string="Users Count", compute="_compute_users_count")

    cost_approval_history_ids = fields.One2many('cost.approval.history', 'cost_approve_id', string="Cost History")

    can_create_earning = fields.Boolean(
        string="Can Create Earning",
        compute='_compute_can_create_earning',
        store=False 
    )
    
    button_status = fields.Selection([
        ('can_create', 'Can Create'),
        ('already_created', 'Already Created'),
        ('not_available', 'Not Available')
    ], string="Button Status", compute='_compute_button_status', store=False)

    @api.depends('cost_line_ids.payroll_status', 'cost_line_ids.payroll', 'state')
    def _compute_can_create_earning(self):
        for record in self:
            record.can_create_earning = (
                record.state not in ['pending', 'new', 'reject'] and
                any(line.payroll and not line.payroll_status for line in record.cost_line_ids)
            )

    @api.depends('cost_line_ids.payroll_status', 'cost_line_ids.payroll', 'state')
    def _compute_button_status(self):
        for record in self:
            if record.state in ['pending', 'new', 'reject']:
                record.button_status = 'not_available'
            elif any(line.payroll and not line.payroll_status for line in record.cost_line_ids):
                record.button_status = 'can_create'
            else:
                record.button_status = 'already_created'
                


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('cost.plus') or _('New')

        approved_group = self.env.ref("sale_extended.cost_plus_approved_group")
        # if self.env.user not in approved_group.users:
        #     raise AccessError(_("You do not have the necessary permissions to create this record."))

        record = super(CostPlus, self).create(vals)

        self.env['cost.plus.line'].create_manager_notification(record)
        cost_approval_history_values = []
        for user in approved_group.users:
            cost_approval_history_values.append((0, 0, {
                'user_id': user.id,
            }))
        record.write({'cost_approval_history_ids': cost_approval_history_values})
        return record

    @api.depends('state')
    def _compute_users_count(self):
        for record in self:
            if record.message_partner_ids:
                count = len(record.message_partner_ids.ids)
                record.users_count = count
            else:
                record.users_count = 0

    def action_approve(self):
        self.ensure_one()
        
        # Log and update approval status for each approval history record
        for approval_history in self.cost_approval_history_ids:
            print(f"approval_history___________User ID: {self.env.uid}, Approval History User ID: {approval_history.user_id.id}")
            
            if approval_history.user_id.id == self.env.uid:
                approval_history.write({
                    'status': 'approve', 
                    'date_done': datetime.now()
                })
                # Mark any pending mail activity as done
                activity = self.env['mail.activity'].search([
                    ('res_model', '=', 'cost.plus'),
                    ('res_id', '=', self.id),
                    ('user_id', '=', self.env.uid),
                    ('activity_type_id.name', '=', 'Cost Plus To Be Assign')
                ])
                
                if activity:
                    activity.action_done()
        
        # If all approval histories are approved, change the state to 'approved'
        if all(approval_history.status == 'approve' for approval_history in self.cost_approval_history_ids):
            self.write({'state': 'approved'})
            
            # Mark any pending mail activity as done
            activity = self.env['mail.activity'].search([
                ('res_model', '=', 'cost.plus'),
                ('res_id', '=', self.id),
                ('user_id', '=', self.env.uid),
                ('activity_type_id.name', '=', 'Cost Plus To Be Assign')
            ])
            
            if activity:
                activity.action_done()
        
        # If all approval histories are rejected, change the state to 'reject'
        if all(approval_history.status == 'reject' for approval_history in self.cost_approval_history_ids):
            self.write({'state': 'reject'})
        
        # Fetch users from the specific group and log activity for each user
        users = self.env.ref("sale_extended.cost_plus_approved_group").users
        for user in users:
            print(f"User {user.name} has the approval group assigned.")
        
        # Optionally, create activity or log messages when approved
        if self.state == 'approved':
            self.message_post(body=f"Cost Plus approved by {self.env.user.name}.")


    def action_reject(self):
        for rec in self:
            approved_group = self.env.ref("sale_extended.cost_plus_approved_group")
            if self.env.user not in approved_group.users:
                raise AccessError(_("You do not have the necessary permissions to Reject this record."))
            for approval_history in self.cost_approval_history_ids:
                if approval_history.user_id.id == self.env.uid:
                    approval_history.write({'status': 'reject', 'date_done': datetime.now()})
                    if approval_history.status == 'reject':
                        self.write({'state': 'reject'})
                        activity = self.env['mail.activity'].search([
                            ('res_model', '=', 'cost.plus'),
                            ('res_id', '=', self.id),
                            ('user_id', '=', self.env.uid),
                            ('activity_type_id.name', '=', 'Cost Plus To Be Assign')
                        ])

                        if activity:
                            activity.action_done()

    # def create_other_earning(self):  
    #     # Check if any line already has payroll_status=True
    #     if any(line.payroll_status for line in self.cost_line_ids):
    #         raise UserError(_("Cannot create earnings - some lines have already been processed!"))
        
    #     # Check if there are payable lines
    #     payable_lines = self.cost_line_ids.filtered(lambda x: x.payroll and not x.payroll_status)
    #     if not payable_lines:
    #         raise UserError(_("No payable lines available for processing!"))
        
    #     line1 = self.cost_line_ids[0]
    #     input_type = self.env['hr.payslip.input.type'].search([('name', '=', line1.product_id.name)], limit=1)
    #     if not input_type:
    #         input_type = self.env['hr.payslip.input.type'].create({
    #             'name': line1.product_id.name,
    #             'code': line1.product_id.name,
    #             'type': 'allowance',
    #         })
    #     line_list = []
    #     total_amt = sum(self.cost_line_ids.filtered(lambda x: x.payroll and not x.payroll_status).mapped('amount'))
    #     for line in self.cost_line_ids.filtered(lambda x: x.payroll and not x.payroll_status):
    #         input_type = self.env['hr.payslip.input.type'].search([('name', '=', line.product_id.name)], limit=1)
    #         if not input_type:
    #             input_type = self.env['hr.payslip.input.type'].create({
    #                 'name': line.product_id.name,
    #                 'code': line.product_id.name,
    #                 'type': 'allowance',
    #             })
    #         line_val = (0, 0, {
    #             'employee_id': line.employee_id.id,
    #             'payslip_input_type_id': input_type.id,
    #             'date': line.cost_plus_line_date,
    #             'type': 'allowance',
    #             'amount': line.amount,
    #         })
    #         line_list.append(line_val)
    #         line.write({'payroll_status': True})

    #     vals = {
    #         'start_date': datetime.now(),
    #         'amount': total_amt,
    #         'applied_to': 'emplopyee',
    #         'payslip_input_type_id': input_type.id,
    #         'type': 'allowance',
    #         'earnings_ids': line_list,
    #         'cost_reference': self.name,
    #     }
    #     self.env['other.earnings'].create(vals)


    def create_other_earning(self):
        # Get only payable lines that haven't been processed yet
        payable_lines = self.cost_line_ids.filtered(lambda x: x.payroll and not x.payroll_status)
        
        # Check if there are any unprocessed lines
        if not payable_lines:
            # Check if there are any processed lines to determine the error message
            if any(line.payroll_status for line in self.cost_line_ids):
                raise UserError(_("Other earnings already created for all payable lines. Please add new lines if needed."))
            else:
                raise UserError(_("No payable lines available for processing!"))
        
        # Process only the unprocessed lines
        line1 = payable_lines[0]
        input_type = self.env['hr.payslip.input.type'].search([('name', '=', line1.product_id.name)], limit=1)
        if not input_type:
            input_type = self.env['hr.payslip.input.type'].create({
                'name': line1.product_id.name,
                'code': line1.product_id.name,
                'type': 'allowance',
            })
        
        line_list = []
        total_amt = sum(payable_lines.mapped('amount'))
        
        for line in payable_lines:
            # Find or create input type for each product if different
            current_input_type = self.env['hr.payslip.input.type'].search([('name', '=', line.product_id.name)], limit=1)
            if not current_input_type:
                current_input_type = self.env['hr.payslip.input.type'].create({
                    'name': line.product_id.name,
                    'code': line.product_id.name,
                    'type': 'allowance',
                })
            
            line_val = (0, 0, {
                'employee_id': line.employee_id.id,
                'payslip_input_type_id': current_input_type.id,
                'date': line.cost_plus_line_date,
                'type': 'allowance',
                'amount': line.amount,
            })
            line_list.append(line_val)
            line.write({'payroll_status': True})

        vals = {
            'start_date': datetime.now(),
            'amount': total_amt,
            'applied_to': 'emplopyee',
            'payslip_input_type_id': input_type.id,
            'type': 'allowance',
            'earnings_ids': line_list,
            'cost_reference': self.name,
        }
        self.env['other.earnings'].create(vals)


class CostPlusLine(models.Model):
    _name = "cost.plus.line"
    _description = 'Cost Plus Line'

    cost_plus_id = fields.Many2one('cost.plus', string="Cost Plus")
    cost_plus_line_date = fields.Date(string="Date")
    product_id = fields.Many2one('product.product', string="Products/Service")
    employee_id = fields.Many2one('hr.employee', string="Employee No")
    amount = fields.Float(string="Amount")
    uom_id = fields.Many2one('uom.uom', string="UOM")
    partner_id = fields.Many2one('res.partner', string="Customer Name", related="task_id.partner_id")
    sale_order_id = fields.Many2one('sale.order', string="Sale Order No.", related="task_id.sale_order_id")
    task_id = fields.Many2one('project.task', string="Task")
    billing = fields.Boolean(string="Billing")
    payroll = fields.Boolean(string="Payroll")
    billing_status = fields.Boolean(string="Billing Status", readonly=True)
    payroll_status = fields.Boolean(string="Payroll Status", readonly=True)
    move_line_id = fields.Many2one('account.move.line', string="Move")

    def create_manager_notification(self, res):
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'cost.plus')], limit=1)
        activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Cost Plus To Be Assign')],
                                                                        limit=1)
        if not activity_type_id:
            activity_type_id = self.env['mail.activity.type'].create({
                'name': 'Cost Plus To Be Assign',
            })

        users = self.env.ref("sale_extended.cost_plus_approved_group").users
        for user in users:
            activity_vals = {
                'res_model_id': model_id.id,
                'res_model': 'cost.plus',
                'res_id': res.id,
                'res_name': 'Cost Plus To Be Assigned',
                'user_id': user.id,
                'activity_type_id': activity_type_id.id,
                'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')
            }
            self.env['mail.activity'].sudo().create(activity_vals)

    def create_cost_plus_batch(self):
        line_list = []
        cost_plus_line = self.filtered(lambda x: not x.cost_plus_id)
        for line in cost_plus_line:
            vals = (4, line.id)
            line_list.append(vals)
        if len(line_list) > 0:
            cost_plus = self.env['cost.plus'].create({'cost_line_ids': line_list})
            # self.create_manager_notification(cost_plus)


class CostApprovalsHistory(models.Model):
    _name = "cost.approval.history"
    _description = "Approval History"

    cost_approve_id = fields.Many2one('cost.plus', string="Cost Plus")
    user_id = fields.Many2one('res.users', string="Approver")
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approve', 'Approved'),
        ('reject', 'Rejected')], default='pending', copy=False, string="Approval Status")
    date_done = fields.Datetime(string="Approval Date")
    cost_line_ids = fields.One2many('cost.plus.line', 'cost_plus_id', string="Cost Line")


