# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import pycompat
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, Warning
from datetime import datetime, date, timedelta


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model
    def default_get(self, flds):
        result = super(HrDepartment, self).default_get(flds)
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id.id
        result['branch_id'] = branch_id
        return result


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model
    def default_get(self, flds):
        result = super(HrApplicant, self).default_get(flds)
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id.id
        result['branch_id'] = branch_id
        return result

    @api.onchange('job_id')
    def onchange_job_id(self):
        """ Override to get branch from department """

        department = self.env['hr.department'].browse(self.department_id.id)
        if department.branch_id:
            self.branch_id = department.branch_id

    def create_employee_from_applicant(self):
        """ Create an hr.employee from the hr.applicants """
        employee = False
        for applicant in self:
            contact_name = False
            if applicant.partner_id:
                address_id = applicant.partner_id.address_get(['contact'])['contact']
                contact_name = applicant.partner_id.display_name
            else:
                new_partner_id = self.env['res.partner'].create({
                    'is_company': False,
                    'name': applicant.partner_name,
                    'email': applicant.email_from,
                    'phone': applicant.partner_phone,
                    'mobile': applicant.partner_mobile
                })
                address_id = new_partner_id.address_get(['contact'])['contact']
            if applicant.job_id and (applicant.partner_name or contact_name):
                applicant.job_id.write({'no_of_hired_employee': applicant.job_id.no_of_hired_employee + 1})
                employee = self.env['hr.employee'].create({
                    'name': applicant.partner_name or contact_name,
                    'job_id': applicant.job_id.id,
                    'address_home_id': address_id,
                    'department_id': applicant.department_id.id or False,
                    'branch_id': applicant.branch_id.id or False,
                    'address_id': applicant.company_id and applicant.company_id.partner_id
                                  and applicant.company_id.partner_id.id or False,
                    'work_email': applicant.department_id and applicant.department_id.company_id
                                  and applicant.department_id.company_id.email or False,
                    'work_phone': applicant.department_id and applicant.department_id.company_id
                                  and applicant.department_id.company_id.phone or False})
                applicant.write({'emp_id': employee.id})

            else:
                raise UserError(_('You must define an Applied Job and a Contact Name for this applicant.'))

        employee_action = self.env.ref('hr.open_view_employee_list')
        dict_act_window = employee_action.sudo().read([])[0]
        dict_act_window['context'] = {'form_view_initial_mode': 'edit'}
        dict_act_window['res_id'] = employee.id
        return dict_act_window


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model
    def default_get(self, flds):
        result = super(HrEmployee, self).default_get(flds)
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id.id
        result['branch_id'] = branch_id
        return result

    # @api.onchange('branch_id')
    # def _onchange_branch_id(self):
    #     selected_brach = self.branch_id
    #     if selected_brach:
    #         user_id = self.env['res.users'].browse(self.env.uid)
    #         user_branch = user_id.sudo().branch_id
    #         if user_branch and user_branch.id != selected_brach.id:
    #             raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    branch_id = fields.Many2one('res.branch', string='Branch', compute='_compute_branch',store=True)
    actual_hours = fields.Float(string="Actual Hours")

    # def _compute_active_task(self):
    #     for attendance in self:
    #         attendance.write({
    #             'task_name':attendance.employee_id.task_name,
    #             })

    # def _compute_task_id(self):
    #     sale_order_id = False
    #     task_id = False
    #     partner_id = False
    #     for attendance in self:
    #         if attendance and attendance.employee_id and attendance.employee_id.task_id:
    #             task_id = attendance.employee_id.task_id.id
    #         attendance.write({
    #             'task_id':task_id,
    #             })

    # def _compute_sale_order_id(self):
    #     sale_order_id = False
    #     for attendance in self:
    #         if attendance and attendance.employee_id and attendance.employee_id.task_id and attendance.employee_id.task_id.sale_order_id:
    #             sale_order_id = attendance.employee_id.task_id.sale_order_id.id
    #         attendance.write({
    #             'sale_order_id':sale_order_id,
    #             })

    # def _compute_partner_id(self):
    #     partner_id = False
    #     for attendance in self:
    #         if attendance and attendance.employee_id and attendance.employee_id.task_id and attendance.employee_id.task_id.partner_id:
    #             partner_id = attendance.employee_id.partner_id.id
    #         attendance.write({
    #             'partner_id':partner_id,
    #             })

    task_name = fields.Char(string="Task")
    task_id = fields.Many2one('project.task', string='Task')
    partner_id = fields.Many2one('res.partner', string='Customer')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    task_record_id = fields.Char(string="Task ID")

    # @api.onchange('worked_hours')
    # def change_worked_hour(self):
    #     if self.worked_hours:
    #         self.write({'actual_hours': actual_hours})

    @api.onchange('actual_hours')
    def change_actual_hours(self):
        if self.check_out and self.actual_hours:
            print('self+++++++++++++++++++', self._origin)
            existing_attendance = self._origin
            total_sub_time = round(self.actual_hours, 2)
            print('total_sub_time+++++++++++++++', total_sub_time)
            only_min = str(total_sub_time).split('.')[1]
            print('only_min++++++++++++++++++', only_min)
            if int(only_min) == 5:
                only_min = str(only_min) + '0'
            minutes = (int(only_min) * 60 / 100)
            print('minutes+++++++++++++++', minutes)
            # if len(str(int(minutes))) == 1:
            #     minutes = str(int(minutes)) + '0'
            # with_hours = self.check_in + timedelta(hours=int(total_sub_time))
            print('self.check_in+++++++++++++++', self.check_in)
            with_hours = self.check_in + timedelta(hours=int(total_sub_time))
            print('with_hours++++++++++++++++', with_hours)
            with_hr_min = with_hours + timedelta(minutes=int(minutes))

            print('with_hr_min++++++++++++++', with_hr_min)

            # start_hr = self.check_in.replace(hour=int(total_sub_time))
            # final_start = start_hr + timedelta(minutes=int(minutes))
            # check_out = self.check_out + timedelta(hours=int(self.actual_hours - self.worked_hours))

            check_out = with_hr_min
            print('check_out+++++++++++++++++++++++', check_out)
            existing_attendance.write({'check_out': check_out})

    # @api.model
    # def default_get(self, flds):
    #     """ Override to get default branch from employee """
    #     result = super(HrAttendance, self).default_get(flds)
    #     employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    #     if employee_id:
    #         if employee_id.branch_id:
    #             result['branch_id'] = employee_id.branch_id.id
    #     return result

    # @api.onchange('employee_id')
    # def get_branch(self):
    #     if self.employee_id:
    #         if self.employee_id.branch_id:
    #             self.update({'branch_id': self.employee_id.branch_id})
    #         else:
    #             self.update({'branch_id': False})

    @api.depends('employee_id')
    def _compute_branch(self):
        for rec in self:
            rec.branch_id = rec.employee_id.branch_id


class HrContract(models.Model):
    _inherit = 'hr.contract'

    branch_id = fields.Many2one('res.branch', string='Branch', related="employee_id.branch_id")

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.branch_id = self.employee_id.branch_id


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model
    def default_get(self, flds):
        """ Override to get default branch from employee """
        result = super(HrPayslip, self).default_get(flds)
        if self._context.get("active_model") == 'hr.employee':
            employee_id = self.env['hr.employee'].browse(self._context.get("active_id"))
            result['branch_id'] = employee_id.branch_id.id
        return result

    @api.onchange('employee_id')
    def get_branch(self):
        if self.employee_id:
            if self.employee_id.branch_id:
                self.update({'branch_id': self.employee_id.branch_id})
            else:
                self.update({'branch_id': False})


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model
    def default_get(self, flds):
        """ Override to get default branch from employee """
        result = super(HrExpenseSheet, self).default_get(flds)
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

        if employee_id:
            if employee_id.branch_id:
                result['branch_id'] = employee_id.branch_id.id
        return result

    @api.onchange('employee_id')
    def get_branch(self):
        if self.employee_id:
            if self.employee_id.branch_id:
                self.update({'branch_id': self.employee_id.branch_id})
            else:
                self.update({'branch_id': False})


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model
    def default_get(self, flds):
        """ Override to get default branch from employee """
        result = super(HrExpense, self).default_get(flds)

        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

        if employee_id:
            if employee_id.branch_id:
                result['branch_id'] = employee_id.branch_id.id
        return result

    @api.onchange('employee_id')
    def get_branch(self):
        if self.employee_id:
            if self.employee_id.branch_id:
                self.update({'branch_id': self.employee_id.branch_id})
            else:
                self.update({'branch_id': False})

    def _create_sheet_from_expenses(self):
        if any(expense.state != 'draft' or expense.sheet_id for expense in self):
            raise UserError(_("You cannot report twice the same line!"))
        if len(self.mapped('employee_id')) != 1:
            raise UserError(_("You cannot report expenses for different employees in the same report."))
        if any(not expense.product_id for expense in self):
            raise UserError(_("You can not create report without product."))

        todo = self.filtered(lambda x: x.payment_mode == 'own_account') or self.filtered(
            lambda x: x.payment_mode == 'company_account')
        sheet = self.env['hr.expense.sheet'].create({
            'company_id': self.company_id.id,
            'employee_id': self[0].employee_id.id,
            'name': todo[0].name if len(todo) == 1 else '',
            'expense_line_ids': [(6, 0, todo.ids)],
            'branch_id': self.branch_id.id or False,
        })
        return sheet

    def _prepare_move_values(self):
        """
        This function prepares move values related to an expense
        """
        self.ensure_one()
        journal = self.sheet_id.bank_journal_id if self.payment_mode == 'company_account' else self.sheet_id.journal_id
        account_date = self.sheet_id.accounting_date or self.date
        move_values = {
            'journal_id': journal.id,
            'company_id': self.sheet_id.company_id.id,
            'date': account_date,
            'ref': self.sheet_id.name,
            # force the name to the default value, to avoid an eventual 'default_name' in the context
            # to set it to '' which cause no number to be given to the account.move when posted.
            'name': '/',
            'branch_id': self.sheet_id.branch_id.id,
        }
        return move_values

