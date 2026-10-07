# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone, UTC
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta

import logging
import re
from io import BytesIO

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    emp_no = fields.Char()
    pay_frequency = fields.Selection(
        [('hourly', 'Hourly'), ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')], default='daily')
    emp_status = fields.Selection(
        [('active', 'Active'), ('off_hire', 'Off Hire'), ('leave', 'Leave'), ('deceased,', 'Deceased'),
         ('retired', 'Retired'), ('absconded', 'Absconded'), ('resigned', 'Resigned'), ('terminated', 'Terminated'),
         ('layoff', 'Layoff'), ('long_leave', 'Long Leave Absconder'), ('onboarding', 'Onboarding'),
         ('employer_change', 'Employer Change')], default='onboarding', string='Employee Status')
    mentor_id = fields.Many2one('res.partner', string="Mentor/Sponsor", tracking=True)
    date_cur_positon = fields.Date('Date In Current Position')
    visa_profession_id = fields.Many2one('visa.profession')
    country_of_emp_id = fields.Many2one('res.country', 'Country Of Employement')
    confirmation_date = fields.Date(tracking=True)
    original_hire_date = fields.Date(tracking=True)
    date_started = fields.Date()
    date_pay_start = fields.Date('Salary Start Date', tracking=True)
    terminattion_date = fields.Date('Seperation Date', tracking=True)
    pay_stop_date = fields.Date(tracking=True)
    overtime_eligibility = fields.Selection([('yes', 'Yes'), ('no', 'No')], default='no', required='1', tracking=True)
    pay_class = fields.Selection([('salaried', 'Salaried'), ('commission', 'Commission')], default='salaried')
    hourly_rate = fields.Float()
    salutation = fields.Selection(
        [('mr', 'Mr.'), ('mrs', 'Mrs.'), ('miss', 'Miss.'), ('dr', 'Dr.'), ('other', 'Other.')], default='mr')
    ethinic_code_id = fields.Many2one('ethinic.code')
    first_nationality_id = fields.Many2one('res.country')
    second_nationality_id = fields.Many2one('res.country')
    bank_account_number = fields.Char()
    bank_id = fields.Many2one('res.bank', string="Bank Name")
    account_no = fields.Char()
    bank_code = fields.Char()
    branch_name = fields.Char()
    disability = fields.Selection([('yes', 'Yes.'), ('no', 'No.')], default='no')
    camp_info = fields.Char(string='Camp Information')
    employee_group_id = fields.Many2one('emplopyee.group', tracking=True)
    employee_sub_group_id = fields.Many2one('emplopyee.sub.group')
    emplopyee_category_id = fields.Many2one('emp.category', 'Employee Categories')

    # status = fields.Many2one('emplopyee.status', string='Status')
    status = fields.Selection([('family', 'Family'), ('single', 'Singe')], string='Status')

    family_status = fields.Many2one('family.status', string='Family Status', tracking=True)
    visa_type_id = fields.Many2one('visa.type', 'Visa Type')
    travel_sector_id = fields.Many2one('travel.sector', 'Travel Sector')
    travel_benefit = fields.Many2one('travel.benefit', string='Travel Benefit')
    passport_clearance = fields.Selection([('fidelity', 'Fidelity'), ('yes', 'Yes'), ('no', 'No')], default='no')
    recruitment_sources = fields.Selection([('locally', 'Locally'), ('india', 'India'), ('internal', 'Internal')],
                                           default='internal')
    recruitment_agent_id = fields.Many2one('res.partner')
    recruitment_country_id = fields.Many2one('res.country')
    who_line_ids = fields.One2many('hr.employee.line', 'employee_id')
    ducument_line_ids = fields.One2many('hr.document.line', 'employee_id')
    passport_control_line_ids = fields.One2many('passport.control.line', 'employee_id', string="Passport", tracking=True)
    insurance_line_ids = fields.One2many('hr.insurance.line', 'employee_id')
    driving_licence_line_ids = fields.One2many('driving.licence.line', 'employee_id')
    training_line_ids = fields.One2many('hr.training', 'employee_id')
    certification_ids = fields.One2many('hr.certification', 'employee_id')
    disciplinary_line_ids = fields.One2many('disciplinary.action.line', 'employee_id')
    status_data = fields.Selection([('in', 'In'), ('out', 'Out')], compute='_compute_status_data', store=True)
    hr_employee_type = fields.Selection([('own', 'Own'), ('subcontractor', 'Subcontractor')], default='own',
                                        required=True)
    vendor_employee_id = fields.Char(string="Vendor Employee Id")
    # trade = fields.Many2one('product.product', string="Trade")
    # trade_ids = fields.Many2many('product.product', string="Trade")
    qid_no = fields.Char(string="QID No.")
    qid_validity = fields.Date(string="QIDValidity", tracking=True)
    vendor_name = fields.Many2one('res.partner', string="Vendor Name")
    sponsor_name = fields.Many2one('res.partner', string="Sponsor Name", domain="[('is_mentor','=', True)]")
    employee_trade = fields.Many2many('hr.skill')
    metrash_register_no = fields.Char(string="Metrash Registered Mobile")
    billable = fields.Boolean(string="Billable")
    is_resource = fields.Boolean(string="Resource", compute='_compute_is_resource')

    bank_ids = fields.One2many('res.partner.bank', 'employee_id', tracking=True)
    passport_expiry_date = fields.Date()
    product_ids = fields.Many2many('product.product', string='Product/Service Category')
    working_hours = fields.Float(string='Working Hours', tracking=True)
    driving_licence_issue_date = fields.Date(string="Driving Licence Issue Date")
    camp_information = fields.Text(string='Address')
    hr_employee_attendance = fields.Selection(
        [('reported', 'Reported'), ('not_reported', 'Not Reported'), ('leave', 'Leave')],
        compute='_compute_hr_employee_attendance', string="Status")
    gratuity_unproductive_days = fields.Float(string="Unproductive Days Opening Balance")
    task_id = fields.Many2one('project.task', string="Project Task")
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    partner_id = fields.Many2one('res.partner', string="Customer")
    public_holiday_eligible = fields.Boolean(string="Public Holiday Eligible")

    @api.constrains('qid_no')
    def _check_qid_no(self):
        for rec in self:
            if rec.qid_no:
                domain = [('qid_no', '=', rec.qid_no)]
                duplicate_records = self.sudo().search(domain)

                if len(duplicate_records) > 1:
                    employee_name = duplicate_records[0].name
                    raise ValidationError(
                        _("QID Number '%s' is already assigned to employee: %s") % (rec.qid_no, employee_name))
            else:
                pass

    def name_get(self):
        res_list = []
        for rec in self:
            if rec.name and rec.emp_no:
                res_list.append((rec.id, rec.name + ' - ' + rec.emp_no))
            else:
                res_list.append((rec.id, rec.name))
        return res_list

    def action_off_hire(self):
        for emp in self:
            #Chandni@globalteckz
            if self.env['email.notification.management'].search([]):
                search_ids = self.env['email.notification.management'].search([])[-1].id
                email_mgmt_id = self.env['email.notification.management'].browse(search_ids)

                if email_mgmt_id:
                    accommodation_email = email_mgmt_id.accommodation_email
                    procurement_email = email_mgmt_id.procurement_email

                    mail_temp = self.env.ref('pways_sale_approval.sending_mail_template')

                    if mail_temp:
                        emp_name = emp.name
                        emp_no = emp.emp_no
                        substarcor_name = emp.hr_employee_type
                        subject = f"Off-Hire Notification for {emp_name} for {emp_no}"
                        """ Customer Service Email """
                        if accommodation_email:
                            body = """
                            <div> 
                                <p>Dear Recipient  """ + str(accommodation_email) + """,
                                    <br/><br/>
                                    Inform you that """+str(emp_name)+""" (Employee Number: """+str(emp_no)+""") of sub-contractor """+str(substarcor_name)+""" is presently off-hired, effective immediately.
                                    Please coordinate his/her departure and ensure the return of any company property.
                                <br></br>
                                Thank you.
                            <br/>
                            <br/>
                            <div>"""
                            mail_temp.send_mail(self.id, email_values={
                                'email_to': accommodation_email,
                                'subject': subject,
                                'body_html': body,
                                }, force_send=True)
                    """ Scheduler Email """
                    if procurement_email:
                        body = """
                            <div> 
                                <p>Dear Recipient  """ + str(procurement_email) + """,
                                <br/><br/>
                                Inform you that """+str(emp_name)+""" (Employee Number: """+str(emp_no)+""") of sub-contractor """+str(substarcor_name)+""" is presently off-hired, effective immediately.
                                Please coordinate his/her departure and ensure the return of any company property.
                            <br></br>
                            Thank you.
                            <br/>
                            <br/>
                        <div>"""
                        mail_temp.send_mail(self.id, email_values={
                            'email_to': procurement_email,
                            'subject': subject,
                            'body_html': body,
                            }, force_send=True)
            emp.write({'emp_status': 'off_hire'})


    def action_active_emp(self):
        for emp in self:
            emp.write({'emp_status': 'active'})

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('emp_no', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def _compute_is_resource(self):
        for employee in self:
            min_time = datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()), "%Y-%m-%d 00:00:00")
            max_time = datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()), "%Y-%m-%d 23:59:59")
            resource_line = self.env['resource.reporting'].search(
                [('date', '>', min_time), ('date', '<', max_time), ('emp_id', '=', employee.id)])
            leave_line = self.env['hr.leave'].search(
                [('date_to', '>=', min_time), ('date_from', '<=', max_time), ('employee_id', '=', employee.id)])
            if resource_line or leave_line:
                employee.is_resource = True
            else:
                employee.is_resource = False

    def _compute_hr_employee_attendance(self):
        for employee in self:
            now = fields.Date.today()
            attendances = employee.attendance_ids.filtered(
                lambda x: x.check_in and x.check_in.date() == now or x.check_out and x.check_out.date() == now)
            if attendances:
                employee.hr_employee_attendance = 'reported'
            else:
                employee.hr_employee_attendance = 'not_reported'

    def action_create_attendance(self):
        print("@@@@@@@")
        contract_id = self.env['hr.contract'].search([('employee_id', '=', self.id), ('state', '=', 'open')], limit=1)
        if not contract_id and self.hr_employee_type == 'own':
            raise ValidationError(
                ("Employee %s does not have any running contract . Please create on employee.") % (self.name))
        # task_id = self.env['project.task'].search([('resource_ids', 'in', self.id)])
        print('yas++++++++++++++', self.group_by_task_shift)

        date_start_day = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) + " 00:00:00"
        _logger.info("\n<<date_start_day>>-----------%s", date_start_day)
        if date_start_day:
            print('self.group_by_task_shift+++++++++++++', self.group_by_task_shift)
            if self.group_by_task_shift:
                for task_id in self.group_by_task_shift:
                    print('\n\n\n\n\n\n\n\n\n\n\n\nSTARTED LOOP FOR TASK ID+++++++++++++++++++++++-------------', task_id)
                    date = fields.Date.today()
                    shift_allocation = self.env['shift.allocation'].search(
                        [('employee_id', '=', self.id), ('task_id', '=', task_id.id), ('state', '=', 'in_progress'),
                         ('date_from', '<=', date),
                         ('date_to', '>=', date)], limit=1)
                    print('shift_allocation+++++++before+++++', shift_allocation)
                    if not shift_allocation and not shift_allocation.shift_id:
                        raise ValidationError(
                            ("Employee %s does not have any shift for today. Please create today's shift") % (
                                self.name))
                    if not shift_allocation.shift_id.hours_from:
                        raise ValidationError(
                            ("Employee %s does not have start time in shift. Please set shift start time.") % (
                                self.name))
                    if not shift_allocation.shift_id.hours_to:
                        raise ValidationError(
                            ("Employee %s does not have end time in shift. Please set shift end time.") % (self.name))

                    hours_from_hr = str(shift_allocation.shift_id.hours_from).split('.')
                    print('hours_from_hr++++++++++++++++++++', hours_from_hr)

                    value_to_check = int(hours_from_hr[0])
                    value_to_check_min = hours_from_hr[1][:2]
                    if int(value_to_check_min) == 5:
                        value_to_check_min = str(value_to_check_min) + '0'
                    minutes = (int(value_to_check_min) / 100) * 60 / 100
                    round_minutes = round(minutes, 2)
                    start_final_value = int(value_to_check) + round_minutes
                    print('start_final_value+++++++++++++++', start_final_value, type(start_final_value))

                    # start_hours = int(shift_allocation.shift_id.hours_from) - 3
                    # start_hours = int(shift_allocation.shift_id.hours_from)
                    start_hours = start_final_value


                    hours_end_hr = str(shift_allocation.shift_id.hours_to).split('.')
                    print('hours_end_hr++++++++++++++++++++', hours_end_hr)

                    value_to_check = int(hours_end_hr[0])
                    value_to_check_min = hours_end_hr[1][:2]
                    if int(value_to_check_min) == 5:
                        value_to_check_min = str(value_to_check_min) + '0'
                    minutes = (int(value_to_check_min) / 100) * 60 / 100
                    round_minutes = round(minutes, 2)
                    end_final_value = int(value_to_check) + round_minutes
                    print('end_final_value+++++++++++++++', end_final_value, type(end_final_value))

                    hours_meals_hr = str(shift_allocation.shift_id.meal_hours).split('.')
                    print('hours_meals_hr++++++++++++++++++++', hours_meals_hr)

                    value_to_check = int(hours_meals_hr[0])
                    value_to_check_min = hours_meals_hr[1][:2]
                    if int(value_to_check_min) == 5:
                        value_to_check_min = str(value_to_check_min) + '0'
                    minutes = (int(value_to_check_min) / 100) * 60 / 100
                    round_minutes = round(minutes, 2)
                    meals_final_value = int(value_to_check) + round_minutes
                    print('meals_final_value+++++++++++++++', meals_final_value, type(meals_final_value))

                    # end_hours = int(shift_allocation.shift_id.hours_to - shift_allocation.shift_id.meal_hours) - 3
                    end_hours = end_final_value - meals_final_value - 3

                    print('start_hours+++++++++++++++', start_hours)
                    start_hr = str(start_hours).split('.')[0]
                    start_minutes = str(start_hours).split('.')[1][:2]
                    if len(start_minutes) == 1:
                        start_minutes = str(start_minutes) + '0'
                    start_hr = fields.Datetime.from_string(date_start_day).replace(hour=int(start_hr))
                    final_start = start_hr + timedelta(minutes=int(start_minutes))

                    print('end_hours+++++++++++++++', end_hours)
                    end_hr = str(end_hours).split('.')[0]
                    end_minutes = str(end_hours).split('.')[1][:2]
                    if len(end_minutes) == 1:
                        end_minutes = str(end_minutes) + '0'
                    end_hr = fields.Datetime.from_string(date_start_day).replace(hour=int(end_hr))
                    final_end = end_hr + timedelta(minutes=int(end_minutes))

                    # date_start = fields.Datetime.from_string(date_start_day) + timedelta(hours=start_hours)
                    date_start = final_start
                    # date_end = fields.Datetime.from_string(date_start_day) + timedelta(hours=end_hours)
                    date_end = final_end

                    self.env['resource.reporting'].create({
                        'emp_name': self.name,
                        'emp_id': self.id,
                        'emp_code': self.emp_no,
                        'task_id': task_id.id if task_id else False,
                        'project_id': task_id.project_id.id if task_id else False,
                        'branch_id': task_id.branch_id.id,
                        'billable': self.billable,
                        'date': datetime.now()
                    })

                    print('\n\n\n\n\n\n\n\n\n\n\n\n\ndate_start++++++++++++', date_start)
                    print('date_end++++++++++++', date_end)

                    self.env['hr.attendance'].with_context({'deduct_3': True}).create({
                        'employee_id': self.id,
                        'task_id': task_id.id if task_id else False,
                        'check_in': date_start,
                        'check_out': date_end,
                        'branch_id': contract_id.branch_id and contract_id.branch_id.id,
                        'status': self.employee_status_new,
                    })

            elif self.hr_employee_type == 'subcontractor':
                start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(hours=5)

                self.env['resource.reporting'].create({
                    'emp_name': self.name,
                    'emp_id': self.id,
                    'emp_code': self.emp_no,
                    'task_id': False,
                    'project_id': False,
                    'branch_id': False,
                    'billable': self.billable,
                    'date': datetime.now()
                })

                self.env['hr.attendance'].with_context({'deduct_3': True}).create({
                    'employee_id': self.id,
                    'task_id': False,
                    'check_in': start_time,
                    'check_out': end_time,
                    'branch_id': False,
                    'status': self.employee_status_new,
                })

            else:
                date_check = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) + " 08:00:00"
                start_time = date_check
                print('start_date++++++++++', start_time)

                contract = self.env['hr.contract'].search([('employee_id', '=', self.id), ('state', '=', 'open')], limit=1)
                work_hrs = contract.work_hours
                hr = str(work_hrs).split('.')[0]
                min = str(work_hrs).split('.')[1]
                end_date = date_start_day
                start_hr = fields.Datetime.from_string(end_date).replace(hour=int(hr))
                end_time = start_hr + timedelta(minutes=int(min)) + timedelta(hours=5)
                print('end_time++++++++++++++++', end_time)

                # start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
                # end_time = start_time + timedelta(hours=5)

                self.env['resource.reporting'].create({
                    'emp_name': self.name,
                    'emp_id': self.id,
                    'emp_code': self.emp_no,
                    'task_id': False,
                    'project_id': False,
                    'branch_id': False,
                    'billable': self.billable,
                    'date': datetime.now()
                })

                self.env['hr.attendance'].with_context({'deduct_3': True}).create({
                    'employee_id': self.id,
                    'task_id': False,
                    'check_in': start_time,
                    'check_out': end_time,
                    'branch_id': False,
                    'status': self.employee_status_new,
                })

        return True

    @api.depends('passport_control_line_ids')
    def _compute_status_data(self):
        for employee in self:
            last_rec = employee.passport_control_line_ids and employee.passport_control_line_ids[-1:]
            if last_rec and last_rec.status:
                employee.status_data = 'in' if not last_rec.status or last_rec.status == 'out' else 'out'
            # if employee.task_id and employee.task_id.sale_order_id:
            # employee.write({'sale_order_id': employee.task_id.sale_order_id.id})
            # if employee.task_id and employee.task_id.partner_id:
            # employee.write({'partner_id': employee.task_id.partner_id.id})

    # @api.model
    # def create(self, vals):
    #     vals['emp_no'] = self.env['ir.sequence'].next_by_code('hr.employee') or 'New'
    #     return super(HrEmployee, self).create(vals)


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    parent_id = fields.Many2one('hr.employee', 'Manager', domain="", compute="_compute_parent_id", store=True,
                                readonly=False)


class ActionReason(models.Model):
    _name = 'emplopyee.status'
    _description = 'Employee Status'

    name = fields.Char('Status', required=True, copy=False)


class FamilyStatus(models.Model):
    _name = 'family.status'
    _description = 'Family Status'

    name = fields.Char('Family Status', required=True, copy=False)


class TravelBenefit(models.Model):
    _name = 'travel.benefit'
    _description = 'Traven Benefit'

    name = fields.Char('Travel Benefit', required=True, copy=False)
    month = fields.Float(string="Month", required=True)
    tickets = fields.Float(string="Tickets", required=True)

    @api.model
    def _update_null_fields(self):
        # Update existing records to ensure 'month' and 'tickets' are not NULL
        self.env.cr.execute("""
            UPDATE travel_benefit
            SET month = 0
            WHERE month IS NULL
        """)
        self.env.cr.execute("""
            UPDATE travel_benefit
            SET tickets = 0
            WHERE tickets IS NULL
        """)

    @api.model
    def init(self):
        super(TravelBenefit, self).init()
        self._update_null_fields()


class HrEmployeeLine(models.Model):
    _name = 'hr.employee.line'
    _description = 'hr.employee.line'

    employee_id = fields.Many2one('hr.employee')
    relation_type = fields.Selection(
        [('father', 'Father'), ('mother', 'Mother'), ('spouse', 'Spouse'), ('husband', 'Husband'),
         ('daughter', 'Daughter'), ('son', 'Son'), ('other', 'Other')], default='other', string="Relation")
    name = fields.Char()
    date_of_birth = fields.Date('Date Of Birth')
    visa_no = fields.Char('Visa No')
    pass_no = fields.Char('Passport No')
    pass_exp_date = fields.Date('Passport Expiry Date')
    visa_expiry_date = fields.Date()
    address = fields.Char()
    next_of_kin = fields.Selection([('yes', 'Yes.'), ('no', 'No.')], default='no', string='Next of Kin')
    contact_no = fields.Char('Contact No')
    next_kin_data = fields.Char('Next of Kin Info')
    attachment = fields.Binary('Attachment')


class HrDocumentLine(models.Model):
    _name = 'hr.document.line'
    _description = "Hr Document Line"

    employee_id = fields.Many2one('hr.employee')
    document_line_id = fields.Many2one('hr.document', 'Document Type')
    document_number = fields.Char('Document No')
    valid_from = fields.Date()
    valid_to = fields.Date()
    doc_issue_place = fields.Char('Document Place ')
    status = fields.Selection([('active', 'Active'), ('history', 'History')], default='active')
    receipt_no = fields.Char('Receipt No')
    receipt_date = fields.Date()
    remarks = fields.Char()
    attachment = fields.Binary('Attachment')

    @api.model
    def create(self, vals):
        if isinstance(vals, dict) and vals.get('status'):
            status = self.search([('status', '=', 'active'), ('document_line_id', '=', vals.get('document_line_id'))])
            for rec in status:
                rec.update({'status': 'history'})
        return super(HrDocumentLine, self).create(vals)


class PassportControlLine(models.Model):
    _name = 'passport.control.line'
    _description = "Passport Control Line"

    employee_id = fields.Many2one('hr.employee')
    passport_control_id = fields.Many2one('hr.passport.control', 'Passport Transaction Code')
    # status = fields.Selection([('in', 'In'), ('out', 'Out'), ], related="passport_control_id.status", )
    status = fields.Selection(string='status', related="passport_control_id.status")
    date_of_trans = fields.Date('Date of Transaction')
    remarks = fields.Char()
    exp_return_date = fields.Date('Expected Return Date')


class HrInsuranceLine(models.Model):
    _name = 'hr.insurance.line'
    _description = "Hr Insurance Line"

    employee_id = fields.Many2one('hr.employee')
    insurance_type_id = fields.Many2one('hr.insurance', 'Insurance Type')
    plan_amount = fields.Float(string='Plan Amount')
    premium = fields.Float()
    benefits = fields.Char()
    start_date = fields.Date()
    end_date = fields.Date()
    insurance_company_id = fields.Many2one('res.partner', 'Insurance Company')
    attachment = fields.Binary('Attachment')


class DrivingLicenceLine(models.Model):
    _name = 'driving.licence.line'
    _description = 'Driving Licence Details'

    employee_id = fields.Many2one('hr.employee')
    driving_licence_id = fields.Many2one('driving.licence', "Licence Name")
    licence_no = fields.Char()
    validity_date = fields.Date(string='Validity Date')
    issuing_country = fields.Many2one('res.country', string='Issuing Country')
    attachment = fields.Binary('Attachment')
    driving_licence_issue_date = fields.Date(string="Driving Licence Issue Date")


class HrTraining(models.Model):
    _name = 'hr.training'
    _description = 'Hr Training'

    employee_id = fields.Many2one('hr.employee')
    training_name = fields.Char()
    training_date = fields.Date()
    location = fields.Char(string="Institution")
    attachment = fields.Binary('Attachment')
    trainer = fields.Char(string="Trainer")
    validity_date = fields.Date(string='Validity Date')


class HrTraining(models.Model):
    _name = 'hr.certification'
    _description = 'Hr Certification'

    employee_id = fields.Many2one('hr.employee')
    remark = fields.Char(string="Remark")
    certificate_date = fields.Date()
    certificate_type = fields.Many2one('certificate.type', 'Certification Name')
    institution = fields.Char(string='Institution')
    specialization = fields.Char(string='Specialization')
    trainer = fields.Char(string="Trainer")
    validity_date = fields.Date(string='Validity Date')
    attachment = fields.Binary('Attachment')


class ActionReason(models.Model):
    _name = 'action.reason'
    _description = 'Action Reason'

    name = fields.Char('Reason Name', required=True, copy=False)


class DisciplinaryActionLine(models.Model):
    _name = 'disciplinary.action.line'
    _description = 'Disciplinary Action Line'

    employee_id = fields.Many2one('hr.employee')
    action_type_id = fields.Many2one('disciplinary.action', 'Action Type')
    action = fields.Many2one('action.reason', string="Reason")
    date = fields.Date()
    action_amount = fields.Float(string='Fine Amount')
    remarks = fields.Char()
    severity = fields.Selection([('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], default='low')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_default_contact_type(self):
        contact_id = self.env['contact.type'].search([('contact_name', '=', 'contact')], limit=1)
        if contact_id:
            return contact_id.id
        return False

    is_mentor = fields.Boolean("Mentor/Sponsor")
    is_agent = fields.Boolean("Is Agent")
    insurance_company = fields.Boolean('Insurance Ccmpany')
    contract_type_id = fields.Many2one('contact.type', string='Contact', default=_get_default_contact_type)
    is_supplier = fields.Boolean("Is Vendor")


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    employee_id = fields.Many2one('hr.employee')


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    is_paid = fields.Boolean('Is Paid')


class Contract(models.Model):
    _inherit = 'hr.contract'

    has_payslip = fields.Boolean('Has Payslip', compute="_compute_has_payslip", store=True)
    payslip_ids = fields.One2many('hr.payslip', 'contract_id', string="payslips")

    @api.depends('payslip_ids', 'payslip_ids.state')
    def _compute_has_payslip(self):
        for rec in self:
            payslip_ids = rec.payslip_ids.filtered(
                lambda x: x.state in ['draft', 'verify'] and x.contract_id and x.contract_id.state == 'open')
            if payslip_ids:
                rec.has_payslip = True
            else:
                rec.has_payslip = False
