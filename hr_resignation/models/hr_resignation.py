# -*- coding: utf-8 -*-
import datetime
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
date_format = "%Y-%m-%d"

class HrResignation(models.Model):
    _name = 'hr.resignation'
    _description = "Hr Resignation"
    _inherit = ['mail.thread','mail.activity.mixin']
    _rec_name = 'employee_id'

    def _get_employee_id(self):
        # assigning the related employee of the logged in user
        employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee_rec.id

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string="Employee", help='Name of the employee for whom the request is creating')
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id', help='Department of the employee')
    joined_date = fields.Date(string="Join Date", required=True, help='Joining date of the employee')
    expected_revealing_date = fields.Date(string="Releaving Date", required=True, default=fields.Date.today(), help='Date on which he is revealing from the company')
    resign_confirm_date = fields.Date(string="Resign confirm date", help='Date on which the request is confirmed')
    approved_revealing_date = fields.Date(string="Approved Date", help='The date approved for the releaving')
    reason = fields.Text(string="Reason", help='Specify reason for leaving the company')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('approved', 'Approved'), ('cancel', 'Cancel')], string='Status', default='draft')
    type = fields.Selection([('one', '1 Year'), ('one2five', '1 to 5 Year'), ('morethen5year', 'More Then 5 Year')], string='Duration', compute="_compute_type", store=True)
    notice_id = fields.Many2one('notice.period', string="Notice Period", related="employee_id.notice_id")
    sepration_type = fields.Selection([('resign', 'Resignation'), ('terminate', 'Terminate'), ('retirement', 'Retirement')], default="retirement", string="Type of Sepration", required="True")
    attachment_ids = fields.Many2many("ir.attachment")

    @api.onchange('employee_id')
    def set_join_date(self):
        if self.employee_id and not self.employee_id.date_started:
            raise ValidationError(_('Please set started date on employee'))
        self.joined_date = self.employee_id.date_started

    @api.depends('joined_date')
    def _compute_type(self):
        difference = relativedelta(fields.Date.today(), self.joined_date).years
        if difference <= 1:
            self.type = 'one'
        if difference > 1 and difference <=5:
            self.type = 'one2five'
        if difference > 5:
            self.type = 'morethen5year'

    @api.model
    def create(self, vals):
        # assigning the sequence for the record
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.resignation') or _('New')
        res = super(HrResignation, self).create(vals)
        return res

    @api.constrains('employee_id')
    def check_employee(self):
        # Checking whether the user is creating leave request of his/her own
        for rec in self:
            if not self.env.user.has_group('hr.group_hr_user'):
                if rec.employee_id.user_id.id and rec.employee_id.user_id.id != self.env.uid:
                    raise ValidationError(_('You cannot create request for other employees'))

    # @api.onchange('employee_id')
    # @api.depends('employee_id')
    # def check_request_existence(self):
    #     # Check whether any resignation request already exists
    #     for rec in self:
    #         if rec.employee_id:
    #             resignation_request = self.env['hr.resignation'].search([('employee_id', '=', rec.employee_id.id), ('state', 'in', ['confirm', 'approved'])])
    #             if resignation_request:
    #                 raise ValidationError(_('There is a resignation request in confirmed or approved state for this employee'))

    # @api.depends('notice_period') 
    # def compute_notice_period(self):
    #     # calculating the notice period for the employee
    #     for rec in self:
    #         notice_days = 0
    #         if rec.approved_revealing_date and rec.resign_confirm_date:
    #             approved_date = datetime.strptime(rec.approved_revealing_date, date_format)
    #             confirmed_date = datetime.strptime(rec.resign_confirm_date, date_format)
    #             notice_period = approved_date - confirmed_date
    #             notice_days= notice_period.days
    #         rec.notice_period = notice_days

    @api.constrains('joined_date')
    def _check_dates(self):
        # validating the entered dates
        resignation_request = self.env['hr.resignation'].search([('employee_id', '=', self.employee_id.id), ('state', 'in', ['confirm', 'approved'])])
        for rec in self:
            if resignation_request:
                raise ValidationError(_('There is a resignation request in confirmed or'
                                        ' approved state for this employee'))
            if rec.joined_date >= fields.Date.today():
                raise ValidationError(_('Releaving date must be anterior to joining date'))

    def confirm_resignation(self):
        for rec in self:
            rec.state = 'confirm'
            # rec.expected_revealing_date = datetime.now() + timedelta(days= rec.notice_id.days)
            rec.resign_confirm_date = datetime.now()
            rec.approved_revealing_date = datetime.now()

    def cancel_resignation(self):
        for rec in self:
            rec.state = 'cancel'

    def reject_resignation(self):
        for rec in self:
            rec.state = 'cancel'

    def approve_resignation(self):
        for rec in self:
            if not rec.approved_revealing_date:
                raise ValidationError(_('Enter Approved Releaving Date'))
            if rec.approved_revealing_date and rec.expected_revealing_date:
                # if rec.approved_revealing_date <= rec.resign_confirm_date:
                #     raise ValidationError(_('Approved releaving date must be anterior to confirmed date'))
                rec.employee_id.write({'resign_date': self.expected_revealing_date})

            """Employee Separation set Task Demoblization based on approved Resignation """
            for demobilize in rec.employee_id.task_ids.filtered(lambda sol: not sol.demobilize_date):

                if demobilize.filtered(lambda sol: sol.date_start.date() <= rec.expected_revealing_date <= sol.date_end.date()):

                    demobilize.write({'demobilize_date': rec.expected_revealing_date,
                                'remarks': 'Employee Separation Approved ' + rec.sepration_type,
                                'is_demobilize': True})
                    demobilize.planning_id.write({'end_datetime':rec.expected_revealing_date})
                if demobilize.filtered(lambda sol: 
                    sol.date_start.date() <= rec.expected_revealing_date and
                    sol.date_end.date() >= rec.expected_revealing_date):

                    demobilize.write({'demobilize_date': rec.expected_revealing_date,
                                'remarks': 'Employee Separation Approved ' + rec.sepration_type,
                                'is_demobilize': True})
                    demobilize.planning_id.write({'end_datetime':rec.expected_revealing_date})

            rec.state = 'approved'

    def update_employee_status(self):
        resignation = self.env['hr.resignation'].search([('state', '=', 'approved')])
        for rec in resignation:
            if rec.approved_revealing_date <= fields.Date.today() and rec.employee_id.active:
                rec.employee_id.resign_date = rec.approved_revealing_date


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    resign_date = fields.Date('Resign Date')
    joining_date = fields.Date(string="Join Date", help='Joining date of the employee')

    @api.onchange('date_started')
    def _onchange_joining_date(self):
        if self.date_started:
            self.joining_date = self.date_started
