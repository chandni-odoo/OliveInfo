import binascii
import json
import math

from odoo import fields, http, SUPERUSER_ID, _
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.fields import Command
from odoo.http import request
from datetime import datetime

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.payment import utils as payment_utils
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager, get_records_pager
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
from datetime import datetime, timedelta
import operator
from odoo.tools import float_compare, float_round
import pytz
import logging

_logger = logging.getLogger(__name__)

class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        employee_id = request.env.user.partner_id
        if 'attendance_count' in counters:
            attendance_count = request.env['hr.attendance'].sudo().search_count(
                [('employee_id.peoplesolve_emp_partner_id', '=', employee_id.id)])
            print("=============attendance_count===============", attendance_count)
            # if request.env['hr.attendance'].check_access_rights('read', raise_exception=False) else 0
            values['attendance_count'] = attendance_count
        if 'leave_count' in counters:
            leave_count = request.env['hr.leave'].sudo().search_count(
                [('employee_id.peoplesolve_emp_partner_id', '=', employee_id.id)])
            # if request.env['hr.leave'].check_access_rights('read', raise_exception=False) else 0
            values['leave_count'] = leave_count
        if 'duty_count' in counters:
            duty_count = request.env['duty.resumption'].sudo().search_count(
                [('employee_id.peoplesolve_emp_partner_id', '=', employee_id.id)]) \
                if request.env['duty.resumption'].check_access_rights('read', raise_exception=False) else 0
            values['duty_count'] = duty_count
            print("=============employee_id============", employee_id.id, request.env.user.partner_id.id, values,
                  counters, duty_count)

        return values

    def _get_utc_time(self, sync_time):
        from datetime import datetime
        date = sync_time.strftime('%Y-%m-%d %H:%M:%S')
        if date:
            user_tz = request.env.user.tz or self.env.context.get('tz') or 'UTC'
            local = pytz.timezone(user_tz)
            date = datetime.strptime(datetime.strftime(
                local.localize(datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(pytz.utc),
                DEFAULT_SERVER_DATETIME_FORMAT), DEFAULT_SERVER_DATETIME_FORMAT)
        return date

    # Have added the functionality in the PY function of create_attendance()
    # @http.route('/add/attendance', type='json', auth='public')
    # def create_attendance(self, data):
    #     check_in_date, check_out_date, = operator.itemgetter('check_in_date', 'check_out_date', )(
    #         {f['name']: f['value'] for f in data})
    #     employee_id = request.env.user.employee_id
    #     from_date = self._get_utc_time(datetime.strptime(check_in_date, '%m/%d/%Y %H:%M:%S'))
    #     to_date = self._get_utc_time(datetime.strptime(check_out_date, '%m/%d/%Y %H:%M:%S'))
    #     employee_id = employee_id.id if employee_id else False
    #     vals = {'employee_id': employee_id, 'check_in': from_date, 'check_out': to_date}
    #     try:
    #         attendance_id = request.env['hr.attendance'].sudo().create(vals)
    #     except ValidationError as e:
    #         request.env.cr.rollback()
    #         data = {'title': _('Send info'), 'msg': e.args[0]}
    #         return data
    #     return True

    # Not used therefore commented
    # @http.route('/find/holiday_status_id', type='json', auth='public')
    # def find_holiday_status_id(self, data):
    #     leave_type = request.env['hr.leave.type'].sudo().browse(int(data))
    #     print("============data ==============", self, data, leave_type)
    #     return leave_type.request_unit

    # Not used therefore commented
    # def get_types(self, types):
    #     if types == 'Half Day':
    #         return {'request_unit_half': True}
    #     if types == 'Custom Hours':
    #         return {'request_unit_hours': True}

    # Have added the functionality in the PY function of create_leave() and JS function of _onSubmit
    # @http.route('/add/myduty', type='json', auth='public')
    # def create_duty(self, data):
    #     types = False
    #     employee_id = request.env.user.partner_id
    #     leave_type_id, reporting_date, duty_resumption_date, reason, state = \
    #         operator.itemgetter('duty_id', 'reporting_date', 'duty_resumption_date', 'reason', 'state')(
    #             {f['name']: f['value'] for f in data})
    #     date_to = fields.Date.from_string(reporting_date)
    #     date_form = fields.Date.from_string(duty_resumption_date)
    #     if leave_type_id:
    #         leave_type = request.env['hr.leave.type'].sudo().browse(int(leave_type_id))
    #         if leave_type.request_unit == 'day':
    #             if not date_from or not date_to:
    #                 return {'title': _('Send info'), 'msg': 'Please Enter Valid Date'}
    #             if fields.Date.from_string(date_to) < fields.Date.from_string(date_from):
    #                 return {'title': _('Send info'),
    #                         'msg': 'Please Enter Valid Date. enddate should not be greater than start date.'}
    #         if leave_type.request_unit == 'hour':
    #             if not from_time or not to_time or not shift_type_ma and not holidays_status_half_costome:
    #                 return {'title': _('Send info'), 'msg': 'Please Enter All Valid Date'}
    #     vals = [{
    #         'employee_id': employee_id.id if employee_id else False,
    #         'leave_type_id': int(leave_type_id),
    #         'reporting_date': date_from,
    #         'duty_resumption_date': date_to,
    #         'reason': reason,
    #         'state': state
    #     }]
    #     try:
    #         duty = request.env['duty.resumption'].sudo().create(vals)
    #     except ValidationError as e:
    #         request.env.cr.rollback()
    #         data = {'title': _('Send info'), 'msg': e.args[0]}
    #         return data
    #     return True

    # Have added the functionality in the PY function of create_leave() and JS function of _onSubmit
    # @http.route('/add/mytimeoff', type='json', auth='public')
    # def get_information(self, data):
    #
    #     print('****get_information****')
    #     print('data+_+_+_+_', data)
    #
    #     types = False
    #     employee_id = request.env.user.employee_id
    #     print('employee_id+_+_+_+_', employee_id)
    #     holiday_status_id, date_from, date_to, holidays_status_half_costome, shift_type_ma, from_time, to_time, name, emergency_contact_number, address, air_ticket = \
    #         operator.itemgetter('employee_id', 'start_date_leave', 'end_date_leave', 'shift_type_type', 'shift_type',
    #                             'from_time', 'to_time', 'description_leave', 'emergency_contact_number', 'address',
    #                             'air_ticket')({f['name']: f['value'] for f in data})
    #     date_to = fields.Date.from_string(date_to)
    #     date_from = fields.Date.from_string(date_from)
    #     if holiday_status_id:
    #         leave_type = request.env['hr.leave.type'].sudo().browse(int(holiday_status_id))
    #         if leave_type.request_unit == 'day':
    #             if not date_from or not date_to:
    #                 return {'title': _('Send info'), 'msg': 'Please Enter Valid Date'}
    #             if fields.Date.from_string(date_to) < fields.Date.from_string(date_from):
    #                 return {'title': _('Send info'),
    #                         'msg': 'Please Enter Valid Date. enddate should not be greater than start date.'}
    #         if leave_type.request_unit == 'hour':
    #             if not from_time or not to_time or not shift_type_ma and not holidays_status_half_costome:
    #                 return {'title': _('Send info'), 'msg': 'Please Enter All Valid Date'}
    #     vals = {
    #         'employee_id': employee_id.id if employee_id else False,
    #         'holiday_status_id': int(holiday_status_id),
    #         'request_date_from': date_from,
    #         'request_date_to': date_to,
    #         'date_from': date_from,
    #         'date_to': date_to,
    #         'request_date_from_period': shift_type_ma,
    #         'request_unit_half': True if holidays_status_half_costome == 'request_unit_half' else False,
    #         'request_unit_hours': True if holidays_status_half_costome == 'request_unit_hours' else False,
    #         'name': name,
    #         'state': 'draft',
    #         'emergency_contact_number': emergency_contact_number,
    #         'address': address,
    #         'air_ticket': air_ticket,
    #     }
    #     if holidays_status_half_costome == 'request_unit_hours':
    #         vals.update({'request_hour_from': from_time if from_time else None,
    #                      'request_hour_to': to_time if to_time else None, })
    #     try:
    #         lead = request.env['hr.leave'].sudo().create(vals)
    #         print('lead+_+_+_+_', lead)
    #     except ValidationError as e:
    #         request.env.cr.rollback()
    #         data = {'title': _('Send info'), 'msg': e.args[0]}
    #         return data
    #     return True

    # Not used therefore commented
    # @http.route(['/add/timeoff'], type='http', auth="public", website=True)
    # def create_timeoff(self, **post):
    #     data = post
    #     return request.redirect('/my/home')

    
    # @http.route(['/my/attendance', '/my/attendance/page/<int:page>'], type='http', auth="user", website=True)
    # def portal_my_delivery(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
    #     values = self._prepare_portal_layout_values()
    #     employee_id = request.env.user.employee_id
    #     hr_attendance_obj = request.env['hr.attendance']
    #     emp_obj = request.env['hr.employee']
    #     payroll_batch = request.env['payroll.batch'].sudo().search([])

    #     emp_domain = [
    #         ('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)
    #     ]
    #     domain = [
    #         ('employee_id.peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)
    #     ]
    #     searchbar_sortings = {
    #         'check_in': {'label': _('Check In'), 'order': 'check_in desc'},
    #         'check_out': {'label': _('Check Out'), 'order': 'check_in'},

    #     }
    #     # default sortby order
    #     if not sortby:
    #         sortby = 'check_in'
    #     sort_order = searchbar_sortings[sortby]['order']

    #     if date_begin and date_end:
    #         domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
    #     # count for pager
    #     attendance_ids = hr_attendance_obj.sudo().search(domain)

    #     attendance_count = attendance_ids.sudo().search_count(domain)
    #     employee_id = emp_obj.sudo().search(emp_domain)

    #     # picking_ids = order_ids.mapped('picking_ids')
    #     # pager
    #     pager = portal_pager(
    #         url="/my/attendance",
    #         url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
    #         total=len(attendance_ids),
    #         page=page,
    #         step=self._items_per_page
    #     )
    #     # content according to pager and archive selected
    #     attendances = hr_attendance_obj.sudo().search(domain, order=sort_order, limit=self._items_per_page,
    #                                                   offset=pager['offset'])
    #     request.session['my_attendance_history'] = attendance_ids.ids[:100]
    #     values.update({
    #         'date': date_begin,
    #         'attendance_ids': attendance_ids.sudo(),
    #         'page_name': 'attendance_list_view',
    #         'employee_id': employee_id,
    #         'x_studio_payroll_batch': payroll_batch,
    #         'pager': pager,
    #         'default_url': '/my/attendance',
    #         'searchbar_sortings': searchbar_sortings,
    #         'create_attendance': True,
    #         'sortby': sortby,
    #     })
    #     print("\n================kw=============", kw)
    #     print("\n================value=============", values)
    #     return request.render("hr_employee_portal.portal_my_attendance", values)
    
    
    # @http.route('/my/create/attendance/n_page', type='http', method=["POST", "GET"], auth="user", website=True, csrf=False)
    # def create_attendance(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
    #     values = self._prepare_portal_layout_values()
    #     employee_id = request.env.user.employee_id
    #     hr_attendance_obj = request.env['hr.attendance']
    #     emp_obj = request.env['hr.employee']
    #     payroll_batch = request.env['payroll.batch'].sudo().search([])
    #     task_list = request.env['project.task'].search([])

    #     emp_domain = [
    #         ('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)
    #     ]
    #     domain = [
    #         ('employee_id.peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)
    #     ]
    #     searchbar_sortings = {
    #         'check_in': {'label': _('Check In'), 'order': 'check_in desc'},
    #         'check_out': {'label': _('Check Out'), 'order': 'check_in'},

    #     }
    #     # default sortby order
    #     if not sortby:
    #         sortby = 'check_in'
    #     sort_order = searchbar_sortings[sortby]['order']

    #     if date_begin and date_end:
    #         domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
    #     # count for pager
    #     attendance_ids = hr_attendance_obj.sudo().search(domain)

    #     attendance_count = attendance_ids.sudo().search_count(domain)
    #     employee_id = emp_obj.sudo().search(emp_domain)

    #     employee_dict = self.get_employee_details(employee_id)

    #     # picking_ids = order_ids.mapped('picking_ids')
    #     # pager
    #     pager = portal_pager(
    #         url="/my/attendance",
    #         url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
    #         total=len(attendance_ids),
    #         page=page,
    #         step=self._items_per_page
    #     )
    #     # content according to pager and archive selected
    #     attendances = hr_attendance_obj.sudo().search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
    #     request.session['my_attendance_history'] = attendance_ids.ids[:100]
    #     values.update({
    #         'date': date_begin,
    #         'attendance_ids': attendance_ids.sudo(),
    #         'page_name': 'attendance_list_view',
    #         'employee_ids': employee_id,
    #         'employee_dict': employee_dict,
    #         'x_studio_payroll_batch': payroll_batch,
    #         'pager': pager,
    #         'default_url': '/my/attendance',
    #         'searchbar_sortings': searchbar_sortings,
    #         'create_attendance': True,
    #         'task_list': task_list,
    #         'sortby': sortby,
    #     })
    #     print("\n================kw=============", kw)
    #     print("\n================value=============", values)
    #     return request.render("hr_employee_portal.create_attendance", values)


    @http.route(['/my/attendance', '/my/attendance/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_attendance(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        hr_attendance_obj = request.env['hr.attendance']
        emp_obj = request.env['hr.employee']
        
        emp_domain = [('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)]
        domain = [('employee_id.peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)]
        
        searchbar_sortings = {
            'check_in': {'label': 'Check In', 'order': 'check_in desc'},
            'check_out': {'label': 'Check Out', 'order': 'check_in'},
        }
        
        if not sortby:
            sortby = 'check_in'
        sort_order = searchbar_sortings[sortby]['order']
        
        if date_begin and date_end:
            domain += [('check_in', '>=', date_begin), ('check_in', '<=', date_end)]
        
        attendance_count = hr_attendance_obj.sudo().search_count(domain)
        employee_id = emp_obj.sudo().search(emp_domain)

        attendances = hr_attendance_obj.sudo().search(
            domain, 
            order='check_in desc',  
            limit=60  
        )
        
        pager = portal_pager(
            url="/my/attendance",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=attendance_count,
            page=page,
            step=self._items_per_page
        )

        paged_attendances = attendances[(page-1)*self._items_per_page : page*self._items_per_page]
        
        # attendances = hr_attendance_obj.sudo().search(domain, order=sort_order, 
        #                                       limit=self._items_per_page,
        #                                       offset=pager['offset'])
        
        values.update({
            'date': date_begin,
            # 'attendance_ids': attendances,
            'attendance_ids': paged_attendances,
            'page_name': 'attendance',
            'employee_id': employee_id,
            'pager': pager,
            'default_url': '/my/attendance',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("hr_employee_portal.portal_my_attendance", values)


    @http.route('/my/create/attendance/n_page', type='http', auth="user", website=True)
    def create_attendance(self, page=1, date_begin=None, date_end=None, sortby=None, attendance_id=None, **kw):
        values = self._prepare_portal_layout_values()
        hr_attendance_obj = request.env['hr.attendance']
        emp_obj = request.env['hr.employee']
        
        attendance = None
        employee_data = {'job_title': '', 'hr_employee_type': ''}
        
        if attendance_id:
            attendance = hr_attendance_obj.sudo().browse(int(attendance_id))
            if not attendance or attendance.employee_id.peoplesolve_emp_partner_id != request.env.user.partner_id:
                return request.redirect('/my/attendance')
            emp_data = self.get_employee_details(attendance.employee_id.id)
            employee_data = emp_data['employee_data']
        else:
            employee_ids = emp_obj.sudo().search([('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)])
            if employee_ids:
                emp_data = self.get_employee_details(employee_ids[0].id)
                employee_data = emp_data['employee_data']

        current_datetime = datetime.now().strftime('%Y-%m-%dT%H:%M')
        
        values.update({
            'page_name': 'attendance_form',
            'employee_ids': emp_obj.sudo().search([('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)]),
            'edit_attendance': attendance is not None,
            'attendance': attendance,
            'job_title': employee_data.get('job_title', ''),
            'employee_type_display': employee_data.get('employee_type', ''), 
            'hr_employee_type': employee_data.get('hr_employee_type', ''),
            'current_datetime': current_datetime,
            # 'hr_employee_type': employee_data.get('employee_type', ''),  # Display value
        })
        return request.render("hr_employee_portal.create_attendance", values)

    @http.route(['/my/edit/attendance/<int:attendance_id>'], type='http', auth="user", website=True)
    def redirect_to_edit_attendance(self, attendance_id, **kw):
        return request.redirect(f'/my/create/attendance/n_page?attendance_id={attendance_id}')

    @http.route(['/create/attendance'], type='http', auth="user", website=True, csrf=True)
    def create_attendance_portal(self, **kw):
        hr_attendance_obj = request.env['hr.attendance']
        
        attendance_id = kw.get('attendance_id')
        if attendance_id:
            attendance = hr_attendance_obj.sudo().browse(int(attendance_id))
            if attendance.employee_id.peoplesolve_emp_partner_id != request.env.user.partner_id:
                return request.redirect('/my/attendance')
            
            if kw.get("check_out_date"):
                try:
                    check_out = datetime.strptime(kw.get("check_out_date"), '%Y-%m-%dT%H:%M')
                    if check_out < attendance.check_in:
                        return request.redirect('/my/attendance?error=invalid_date_range')
                    attendance.sudo().write({'check_out': check_out})
                except ValueError:
                    return request.redirect('/my/attendance?error=invalid_date_format')
        else:
            try:
                vals = {
                    'employee_id': int(kw.get('employee_ids')),
                    'check_in': datetime.strptime(kw.get("check_in_date"), '%Y-%m-%dT%H:%M'),
                }
                
                if kw.get("check_out_date"):
                    check_out = datetime.strptime(kw.get("check_out_date"), '%Y-%m-%dT%H:%M')
                    if check_out < vals['check_in']:
                        return request.redirect('/my/attendance?error=invalid_date_range')
                    vals['check_out'] = check_out
                
                hr_attendance_obj.sudo().create(vals)
            except (ValueError, KeyError) as e:
                return request.redirect('/my/attendance?error=creation_error')
        
        return request.redirect('/my/attendance')

    @http.route('/hr/employee/get_data', type='json', auth="user", website=True)
    def get_employee_data_json(self, employee_id, **kw):
        return self.get_employee_details(employee_id)
            
    
    # @http.route(['/create/attendance', ], type='http', website=True)
    # def create_attendance_portal(self, **kw):
    #     hr_attendance_obj = request.env['hr.attendance']
    #     print("=============got leave call===========", kw, kw.get('employee_ids'), hr_attendance_obj)
    #     vals = {
    #             'employee_id': int(kw.get('employee_ids')),
    #             # 'x_studio_payroll_batch': kw.get("x_studio_payroll_batch"),
    #             # 'x_studio_emplyoee_type': 'own',
    #             'check_in': datetime.strptime(kw.get("check_in_date"), '%m/%d/%Y %H:%M:%S'),
    #             'check_out': datetime.strptime(kw.get("check_out_date"), '%m/%d/%Y %H:%M:%S'),
    #             }
    #     hr_attendance = hr_attendance_obj.sudo().create(vals)

    #     print('hr_attendance+_+_+_+_', hr_attendance)

    # def get_holidays_status(self, holidays_status):
    #     name_list = []
    #     for record in holidays_status:
    #         name = record.name
    #         if record.requires_allocation in ["yes", "no"]:
    #             name = "%(name)s (%(count)s)" % {
    #                 'name': name,
    #                 'count': _('%g remaining out of %g') % (
    #                     float_round(record.virtual_remaining_leaves, precision_digits=2) or 0.0,
    #                     float_round(record.max_leaves, precision_digits=2) or 0.0,
    #                 ) + (_(' hours') if record.request_unit == 'hour' else _(' days'))
    #             }
    #         name_list.append({'id': record.id, 'name': name})
    #     return name_list
    

    # def get_employee_details(self, employee_ids):
    #     name_list = []
    #     emp_list = []
    #     for rec in employee_ids:
    #         emp_list.append({'id': rec.id, 'name': rec.name, 'emp_no': rec.emp_no, 'branch': rec.branch_id.name,
    #                          'job_title': rec.job_title, 'coach_id': rec.coach_id.name,
    #                          'joining_date': rec.joining_date, 'company_id': rec.company_id.name,
    #                          'status': rec.hr_employee_attendance})
    #         name = rec.name
    #         name = "%(code)s - %(name)s" % {
    #             'code': _(' %s') % rec.emp_no,
    #             'name': name,
    #         }
    #         name_list.append({'id': rec.id, 'name': name})
    #     print("============emp_list=============", emp_list, len(employee_ids))
    #     return name_list


    def get_employee_details(self, employee_ids):
        if not isinstance(employee_ids, list):
            employee_ids = [employee_ids]
        
        name_list = []
        emp_list = []
        for rec in request.env['hr.employee'].sudo().browse(employee_ids):
            # Get both raw and display values
            employee_type_raw = rec.hr_employee_type or ''
            employee_type_display = dict(rec._fields['hr_employee_type'].selection).get(rec.hr_employee_type) or ''
            
            emp_list.append({
                'id': rec.id,
                'name': rec.name,
                'emp_no': rec.emp_no,
                'branch': rec.branch_id.name if rec.branch_id else '',
                'job_title': rec.job_id.name if rec.job_id else '',
                'coach_id': rec.coach_id.name if rec.coach_id else '',
                'joining_date': rec.joining_date or '',
                'company_id': rec.company_id.name if rec.company_id else '',
                'status': rec.hr_employee_attendance or '',
                'employee_type': employee_type_display,  
                'hr_employee_type': employee_type_raw,   
                'employee_type_display': employee_type_display  
            })
            
            name = "%(code)s - %(name)s" % {
                'code': (' %s') % (rec.emp_no or ''),
                'name': rec.name,
            }
            name_list.append({'id': rec.id, 'name': name})
        
        return {
            'employee_data': emp_list[0] if emp_list else {},
            'name_list': name_list
        }

    
    def get_employee_info(self, employees):
        employee_dict = []
        for rec in employees:
            employee_type_display = dict(rec._fields['hr_employee_type'].selection).get(rec.hr_employee_type) if rec.hr_employee_type else ''
            employee_dict.append({
                'id': rec.id,
                'name': rec.name,
                'job_title': rec.job_title or rec.job_id.name,
                'parent_id': rec.parent_id.name if rec.parent_id else '',
                'coach_id': rec.coach_id.name if rec.coach_id else '',
                'joining_date': rec.joining_date.strftime('%d/%m/%Y') if rec.joining_date else '',
                'company_id': rec.company_id.id if rec.company_id else '',
                'branch_id': rec.branch_id.id if rec.branch_id else '',
                'hr_employee_type': rec.hr_employee_type or '',
                'employee_type_display': employee_type_display,
            })
        return employee_dict

    def get_holidays_status(self, records):
        status_list = []
        for rec in records:
            status_list.append({
                'id': rec.id,
                'name': rec.name,
                'requires_allocation': rec.requires_allocation
            })
        return status_list


            
    
    # @http.route(['/my/leave', '/my/leave/page/<int:page>'], type='http', auth="user", website=True)
    # def portal_my_timeoff(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
    #     values = self._prepare_portal_layout_values()
    #     employee_id = request.env.user.partner_id
    #     leave_obj = request.env['hr.leave']
    #     emp_obj = request.env['hr.employee']
    #     duty_obj = request.env['duty.resumption']
    #     branch_list = request.env['res.branch'].search([])

    #     emp_domain = ['|', ('coach_id.peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id),
    #                   ('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)]
    #     domain = [
    #         ('employee_id.peoplesolve_emp_partner_id', '=', employee_id.id if employee_id else False)
    #     ]
    #     searchbar_sortings = {
    #         'state': {'label': _('state'), 'order': 'state desc'},

    #     }
    #     # default sortby order
    #     if not sortby:
    #         sortby = 'state'
    #     sort_order = searchbar_sortings[sortby]['order']

    #     if date_begin and date_end:
    #         domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
    #     # count for pager
    #     leave_ids = leave_obj.sudo().search(domain)
    #     for leave in leave_ids:
    #         leave.check_leave_view = leave.state == 'validate'

    #     # leave_count = leave_ids.sudo().search_count(domain)
    #     employee_ids = emp_obj.sudo().search(emp_domain)
    #     print("==================portal_my_timeoff===============", len(leave_ids), employee_ids, request.env.user,
    #           request.env.user.employee_id, kw)
    #     # pager
    #     pager = portal_pager(
    #         url="/my/leave",
    #         url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
    #         total=len(leave_ids),
    #         page=page,
    #         step=self._items_per_page
    #     )
    #     # content according to pager and archive selected
    #     leaves = leave_obj.sudo().search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
    #     request.session['my_leave_history'] = leave_ids.ids[:100]
    #     partner_id = request.env.user.partner_id
    #     employee_id = request.env['hr.employee'].sudo().search([('peoplesolve_emp_partner_id', '=', partner_id.id)],
    #                                                            limit=1)
    #     allocation_ids = request.env['hr.leave.allocation'].sudo().search([('employee_id', '=', employee_id.id)])
    #     holidays_status_require_allocation_ids = request.env['hr.leave.type'].sudo().search(
    #         [('requires_allocation', '=', 'no')])
    #     holidays_status_ids = request.env['hr.leave.type'].sudo().search(['|', (
    #         'id', 'in', allocation_ids.mapped('holiday_status_id').ids + holidays_status_require_allocation_ids.ids),
    #                                                                       ('is_service_portal', '=', 'True')])
    #     status_dict = self.get_holidays_status(holidays_status_ids)
    #     employee_dict = self.get_employee_details(employee_ids)

    #     duty_resumption_ids = duty_obj.sudo().search([('leave_id', 'in', leave_ids.ids)])
    #     duty_exists_map = {duty.leave_id.id: True for duty in duty_resumption_ids}

    #     print('employee_ids+++++++++++++++++', employee_ids)
    #     print('status_dict+++++++++++++++++', status_dict)

    #     print('branch_list+++++++++++++++++', branch_list)

    #     values.update({
    #         'date': date_begin,
    #         'leave_ids': leave_ids.sudo(),
    #         'employee_ids': employee_ids,
    #         'page_name': 'leave_list_view',
    #         'pager': pager,
    #         'default_url': '/my/leave',
    #         'searchbar_sortings': searchbar_sortings,
    #         'create_leaves': True,
    #         'holidays_status_ids': holidays_status_ids,
    #         'status_dict': status_dict,
    #         'employee_dict': employee_dict,
    #         'branch_list': branch_list,
    #         'sortby': sortby,
    #         'duty_exists_map': duty_exists_map,
    #     })
    #     print("================values==============", kw)
    #     # leave_obj.sudo().create({'employee_ids':kw.get("employee_ids"),
    #     #     'leave_type_id':kw.get('holidays_status_id'),
    #     #     'request_date_from':kw.get('start_date_leave'),
    #     #     'request_date_to':kw.get('end_date_leave')})
    #     return request.render("hr_employee_portal.portal_my_leave", values)

    
    # @http.route(['/my/leave/n_page'], type='http', website=True, method=["POST", "GET"], auth="user", csrf=False)
    # def leave_page(self, date_begin=None, date_end=None, sortby=None, **kw):
    #     print("+++++++++++++kw+++++++++++++++", kw)

    #     values = self._prepare_portal_layout_values()
    #     employee_id = request.env.user.partner_id
    #     leave_obj = request.env['hr.leave']
    #     emp_obj = request.env['hr.employee']
    #     branch_list = request.env['res.branch'].search([])
    #     company_list = request.env['res.company'].search([])

    #     emp_domain = ['|', ('coach_id.peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id), ('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)]
    #     domain = [
    #         ('employee_id.peoplesolve_emp_partner_id', '=', employee_id.id if employee_id else False)
    #     ]
    #     searchbar_sortings = {
    #         'state': {'label': _('state'), 'order': 'state desc'},

    #     }
    #     # default sortby order
    #     if not sortby:
    #         sortby = 'state'
    #     sort_order = searchbar_sortings[sortby]['order']

    #     if date_begin and date_end:
    #         domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
    #     # count for pager
    #     leave_ids = leave_obj.sudo().search(domain)

    #     leave_count = leave_ids.sudo().search_count(domain)
    #     employee_ids = emp_obj.sudo().search(emp_domain)
    #     print("==================portal_my_timeoff===============", len(leave_ids), employee_ids, request.env.user, request.env.user.employee_id, kw)
    #     # pager

    #     # content according to pager and archive selected
    #     leaves = leave_obj.sudo().search(domain)
    #     request.session['my_leave_history'] = leave_ids.ids[:100]
    #     partner_id = request.env.user.partner_id
    #     employee_id = request.env['hr.employee'].sudo().search([('peoplesolve_emp_partner_id', '=', partner_id.id)], limit=1)
    #     allocation_ids = request.env['hr.leave.allocation'].sudo().search([('employee_id', '=', employee_id.id)])
    #     holidays_status_require_allocation_ids = request.env['hr.leave.type'].sudo().search([('requires_allocation', '=', 'no')])
    #     holidays_status_ids = request.env['hr.leave.type'].sudo().search(['|', (
    #         'id', 'in', allocation_ids.mapped('holiday_status_id').ids + holidays_status_require_allocation_ids.ids), ('is_service_portal', '=', 'True')])
    #     status_dict = self.get_holidays_status(holidays_status_ids)
    #     employee_dict = self.get_employee_details(employee_ids)

    #     print('employee_ids+++++++++++++++++', employee_ids)
    #     print('status_dict+++++++++++++++++', status_dict)

    #     print('branch_list+++++++++++++++++', branch_list)

    #     values.update({
    #         'date': date_begin,
    #         'leave_ids': leave_ids.sudo(),
    #         'employee_ids': employee_ids,
    #         'employee_id': request.env['hr.employee'].sudo().search([('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)], limit=1).id,
    #         # 'all_employee_dict': self.get_employee_details(emp_obj.sudo().search([])),
    #         'page_name': 'leave_list_view',
    #         'default_url': '/my/leave/n_page',
    #         'searchbar_sortings': searchbar_sortings,
    #         'create_leaves': True,
    #         'holidays_status_ids': holidays_status_ids,
    #         'status_dict': status_dict,
    #         'employee_dict': employee_dict,
    #         'branch_list': branch_list,
    #         'company_list': company_list,
    #         'sortby': sortby,
    #     })
    #     print("================values==============", kw, values)

    #     return request.render("hr_employee_portal.create_leave_page", values)

    @http.route(['/my/leave', '/my/leave/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_timeoff(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        employee_id = request.env.user.partner_id
        leave_obj = request.env['hr.leave']
        emp_obj = request.env['hr.employee']
        duty_obj = request.env['duty.resumption']
        branch_list = request.env['res.branch'].search([])

        emp_domain = ['|', ('coach_id.peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id),
                    ('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)]
        employee_ids = emp_obj.sudo().search(emp_domain)
    
        domain = ['|',
                ('employee_id.peoplesolve_emp_partner_id', '=', employee_id.id if employee_id else False),
                ('create_uid', '=', request.env.user.id)]
        
        searchbar_sortings = {
            'state': {'label': _('state'), 'order': 'state desc'},
        }
        
        if not sortby:
            sortby = 'state'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        
        leave_ids = leave_obj.sudo().search(domain)
        for leave in leave_ids:
            leave.check_leave_view = leave.state == 'validate'

        employee_ids = emp_obj.sudo().search(emp_domain)
        
        current_employee = request.env['hr.employee'].sudo().search(
            [('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)], limit=1)
        subordinates = []
        if current_employee:
            subordinates = request.env['hr.employee'].sudo().search(
                ['|', ('parent_id', '=', current_employee.id), ('coach_id', '=', current_employee.id)])
        
        pager = portal_pager(
            url="/my/leave",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=len(leave_ids),
            page=page,
            step=self._items_per_page
        )
        
        leaves = leave_obj.sudo().search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_leave_history'] = leave_ids.ids[:100]
        partner_id = request.env.user.partner_id
        employee_id = request.env['hr.employee'].sudo().search([('peoplesolve_emp_partner_id', '=', partner_id.id)], limit=1)
        allocation_ids = request.env['hr.leave.allocation'].sudo().search([('employee_id', '=', employee_id.id)])
        holidays_status_require_allocation_ids = request.env['hr.leave.type'].sudo().search(
            [('requires_allocation', '=', 'no')])
        holidays_status_ids = request.env['hr.leave.type'].sudo().search(['|', (
            'id', 'in', allocation_ids.mapped('holiday_status_id').ids + holidays_status_require_allocation_ids.ids),
                                                                        ('is_service_portal', '=', 'True')])
        status_dict = self.get_holidays_status(holidays_status_ids)
        employee_dict = self.get_employee_info(employee_ids)
        subordinate_dict = self.get_employee_info(subordinates)

        duty_resumption_ids = duty_obj.sudo().search([('leave_id', 'in', leave_ids.ids)])
        duty_exists_map = {duty.leave_id.id: True for duty in duty_resumption_ids}

        values.update({
            'date': date_begin,
            'leave_ids': leaves,
            'employee_ids': employee_ids,
            'subordinates': subordinates,
            'subordinate_dict': subordinate_dict,
            'page_name': 'leave_list_view',
            'pager': pager,
            'default_url': '/my/leave',
            'searchbar_sortings': searchbar_sortings,
            'create_leaves': True,
            'holidays_status_ids': holidays_status_ids,
            'status_dict': status_dict,
            'employee_dict': employee_dict,
            'branch_list': branch_list,
            'sortby': sortby,
            'duty_exists_map': duty_exists_map,
            'is_manager': len(subordinates) > 0,  
        })
        return request.render("hr_employee_portal.portal_my_leave", values)

    

    @http.route(['/my/leave/n_page'], type='http', website=True, method=["POST", "GET"], auth="user", csrf=False)
    def leave_page(self, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        employee_id = request.env.user.partner_id
        leave_obj = request.env['hr.leave']
        emp_obj = request.env['hr.employee']
        branch_list = request.env['res.branch'].search([])
        company_list = request.env['res.company'].search([])

        current_employee = request.env['hr.employee'].sudo().search(
            [('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)], limit=1)
        
        emp_domain = ['|', ('coach_id.peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id),
                    ('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)]
        
        subordinates = []
        if current_employee:
            subordinates = request.env['hr.employee'].sudo().search(
                ['|', ('parent_id', '=', current_employee.id), ('coach_id', '=', current_employee.id)])
        
        employee_ids = emp_obj.sudo().search(emp_domain)
        
        all_employees = employee_ids | subordinates
        
        partner_id = request.env.user.partner_id
        employee_id = request.env['hr.employee'].sudo().search([('peoplesolve_emp_partner_id', '=', partner_id.id)], limit=1)
        
        allocation_ids = request.env['hr.leave.allocation'].sudo().search([('employee_id', '=', employee_id.id)])
        holidays_status_require_allocation_ids = request.env['hr.leave.type'].sudo().search([('requires_allocation', '=', 'no')])
        holidays_status_ids = request.env['hr.leave.type'].sudo().search(['|', (
            'id', 'in', allocation_ids.mapped('holiday_status_id').ids + holidays_status_require_allocation_ids.ids),
                                                                        ('is_service_portal', '=', 'True')])
        
        status_dict = self.get_holidays_status(holidays_status_ids)
        employee_dict = self.get_employee_info(employee_ids)
        
        subordinate_dict = self.get_employee_info(subordinates)
        
        all_employees_dict = self.get_employee_info(all_employees)

        values.update({
            'date': date_begin,
            'employee_ids': employee_ids,
            'employee_id': employee_id.id,
            'page_name': 'leave_list_view',
            'default_url': '/my/leave/n_page',
            'searchbar_sortings': {
                'state': {'label': _('state'), 'order': 'state desc'},
            },
            'create_leaves': True,
            'holidays_status_ids': holidays_status_ids,
            'status_dict': status_dict,
            'employee_dict': employee_dict,
            'subordinate_dict': subordinate_dict,
            'all_employees_dict': all_employees_dict,
            'branch_list': branch_list,
            'company_list': company_list,
            'sortby': sortby,
            'is_manager': len(subordinates) > 0,
            'current_employee_id': employee_id.id if employee_id else False,
        })
        return request.render("hr_employee_portal.create_leave_page", values)
    
    @http.route(['/create/leave'], type='http', website=True)
    def create_leave(self, **kw):
        leave_obj = request.env['hr.leave']
            
        date_from = datetime.strptime(kw.get("start_date_leave"), '%Y-%m-%d').strftime('%Y-%m-%d %H:%M')
        date_to = datetime.strptime(kw.get("end_date_leave"), '%Y-%m-%d').strftime('%Y-%m-%d %H:%M')

        employee_id = int(kw.get("on_behalf_of")) if kw.get("on_behalf_of") else int(kw.get("employee_ids"))
        
        vals = {
            'employee_ids': [(6, 0, [employee_id])],
            'holiday_status_id': int(kw.get("holidays_status_ids")),
            'request_date_from': date_from,
            'request_date_to': date_to,
            'date_from': date_from,
            'date_to': date_to,
            'name': kw.get("description_leave"),
            'emergency_contact_number': kw.get("emergency_contact_number"),
            'address': kw.get("address"),
            'air_ticket': kw.get("air_ticket"),
            'holiday_type': 'employee',
            'multi_employee': True
        }

        leave = leave_obj.sudo().create(vals)
        return request.redirect('/my/home/')

    

    # @http.route(['/login/employee/'], type='json', auth='public', website=True)
    # def return_login_employee(self, **kw):

    #     print('***return_login_employee***')

    #     print('partner_id+_+_+_+_', request.env.user.partner_id)

    #     if request.env.user.partner_id:
    #         hr_employee = request.env['hr.employee'].sudo().search([('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)], limit=1)
    #         print('hr_employee+_+_+_+_', hr_employee)
    #         if hr_employee:
    #             employee_data = {'employee_id': hr_employee.id, 'job_title': hr_employee.job_title, 'parent_id': hr_employee.parent_id.name, 'coach_id': hr_employee.coach_id.name,
    #                              'joining_date': hr_employee.joining_date, 'company_id': str(hr_employee.company_id.id), 'branch_id': str(hr_employee.branch_id.id),
    #                              'hr_employee_type': hr_employee.hr_employee_type}

    #             print('current_leave_id+_+_+_+_', hr_employee.current_leave_id)
    #             if hr_employee.current_leave_id:
    #                 print('virtual_remaining_leaves+_+_+_+_', ('%.2f' % hr_employee.current_leave_id.virtual_remaining_leaves).rstrip('0').rstrip('.'))
    #                 employee_data.update({'virtual_remaining_leaves': str(('%.2f' % hr_employee.current_leave_id.virtual_remaining_leaves).rstrip('0').rstrip('.'))})

    #             if kw.get('params').get('attendance'):
    #                 print('task_id+_+_+_', hr_employee.task_id)
    #                 if hr_employee.task_id:
    #                     print('name+_+_+_', hr_employee.task_id.name)
    #                     print('partner_id+_+_+_', hr_employee.task_id.partner_id)
    #                     print('partner_location_id+_+_+_', hr_employee.task_id.partner_location_id)
    #                     print('emp_id+_+_+_', hr_employee.task_id.emp_id)
    #                     print('shift_allocation_ids+_+_+_', hr_employee.task_id.shift_allocation_ids)
    #                     for shift_allocation_id in hr_employee.task_id.shift_allocation_ids:
    #                         print('name+_+_+_', shift_allocation_id.name)
    #                         print('name+_+_+_', shift_allocation_id.shift_id.name)
    #                     # errrr
    #                     employee_data.update(
    #                         {'task_id': hr_employee.task_id, 'name': hr_employee.task_id.name, 'partner_id': hr_employee.task_id.partner_id.name,
    #                          'partner_location_id': hr_employee.task_id.partner_location_id.name})

    #             return employee_data
    #         else:
    #             return False
            

    # @http.route(['/employee/data'], type='json', auth='public', website=True)
    # def return_employee_data(self, **kw):

    #     print('***return_employee_data***')

    #     print('kw+_+_+_+_', kw)

    #     if kw.get('params').get('employee_id'):
    #         print('Going in IFF')
    #         hr_employee = request.env['hr.employee'].sudo().browse(int(kw.get('params').get('employee_id')))
    #         print('hr_employee+_+_+_+_', hr_employee)
    #         print('job_title+_+_+_+_', hr_employee.job_title)
    #         print('parent_id+_+_+_+_', hr_employee.parent_id)
    #         print('coach_id+_+_+_+_', hr_employee.coach_id)
    #         print('joining_date+_+_+_+_', hr_employee.joining_date)
    #         print('company_id+_+_+_+_', hr_employee.company_id)
    #         print('branch_id+_+_+_+_', hr_employee.branch_id.id)
    #         print('employee_type+_+_+_+_', hr_employee.hr_employee_type)

    #         employee_data = {'job_title': hr_employee.job_title, 'parent_id': hr_employee.parent_id.name, 'coach_id': hr_employee.coach_id.name,
    #                          'joining_date': hr_employee.joining_date, 'company_id': str(hr_employee.company_id.id), 'branch_id': str(hr_employee.branch_id.id),
    #                          'hr_employee_type': hr_employee.hr_employee_type}

    #         print('current_leave_id+_+_+_+_', hr_employee.current_leave_id)
    #         if hr_employee.current_leave_id:
    #             print('virtual_remaining_leaves+_+_+_+_', ('%.2f' % hr_employee.current_leave_id.virtual_remaining_leaves).rstrip('0').rstrip('.'))
    #             employee_data.update({'virtual_remaining_leaves': str(('%.2f' % hr_employee.current_leave_id.virtual_remaining_leaves).rstrip('0').rstrip('.'))})

    #         if kw.get('params').get('attendance'):
    #             print('task_id+_+_+_', hr_employee.task_id)
    #             if hr_employee.task_id:
    #                 print('name+_+_+_', hr_employee.task_id.name)
    #                 print('partner_id+_+_+_', hr_employee.task_id.partner_id)
    #                 print('partner_location_id+_+_+_', hr_employee.task_id.partner_location_id)
    #                 print('emp_id+_+_+_', hr_employee.task_id.emp_id)
    #                 print('shift_allocation_ids+_+_+_', hr_employee.task_id.shift_allocation_ids)
    #                 for shift_allocation_id in hr_employee.task_id.shift_allocation_ids:
    #                     print('name+_+_+_', shift_allocation_id.name)
    #                     print('name+_+_+_', shift_allocation_id.shift_id.name)
    #                 # errrr
    #                 employee_data.update(
    #                     {'task_id': hr_employee.task_id, 'name': hr_employee.task_id.name, 'partner_id': hr_employee.task_id.partner_id.name,
    #                      'partner_location_id': hr_employee.task_id.partner_location_id.name})

    #         return employee_data
    #     else:
    #         return False

    @http.route(['/employee/data'], type='json', auth='public', website=True)
    def return_employee_data(self, **kw):
        print('***return_employee_data***')
        print('kw+_+_+_+_', kw)
        
        employee_id = None
        if kw.get('params') and kw.get('params').get('employee_id'):
            employee_id = int(kw.get('params').get('employee_id'))
        elif kw.get('employee_id'):
            employee_id = int(kw.get('employee_id'))
        
        if employee_id:
            hr_employee = request.env['hr.employee'].sudo().browse(employee_id)
            
            if not hr_employee:
                return False
            
            employee_type_display = dict(hr_employee._fields['hr_employee_type'].selection).get(hr_employee.hr_employee_type) if hasattr(hr_employee, 'hr_employee_type') else ''
                
            employee_data = {
                'employee_id': hr_employee.id,
                'job_title': hr_employee.job_title if hasattr(hr_employee, 'job_title') else hr_employee.job_id.name,
                'parent_id': hr_employee.parent_id.name if hr_employee.parent_id else '',
                'coach_id': hr_employee.coach_id.name if hr_employee.coach_id else '',
                'joining_date': hr_employee.original_hire_date.strftime('%Y-%m-%d') if hasattr(hr_employee, 'original_hire_date') and hr_employee.original_hire_date else False,
                'company_id': str(hr_employee.company_id.id) if hr_employee.company_id else '',
                'branch_id': str(hr_employee.branch_id.id) if hr_employee.branch_id else '',
                'hr_employee_type': hr_employee.hr_employee_type if hasattr(hr_employee, 'hr_employee_type') else '',
                'employee_type_display': employee_type_display,
                'employee_name': hr_employee.name
            }
            
            # Get all leave allocations and calculate remaining leaves
            leave_allocations = request.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', hr_employee.id),
                ('state', '=', 'validate'),
                ('holiday_status_id.active', '=', True)
            ])
            
            total_available = 0
            
            for allocation in leave_allocations:
                total_available += allocation.number_of_days_display
            
            if leave_allocations:
                leaves_taken = request.env['hr.leave'].sudo().search([
                    ('employee_id', '=', hr_employee.id),
                    ('state', '=', 'validate'),
                    ('holiday_status_id', 'in', leave_allocations.mapped('holiday_status_id').ids)
                ])
                
                for leave in leaves_taken:
                    total_available -= leave.number_of_days
            
            # Add any accrual plan balances if applicable
            if hasattr(hr_employee, 'leave_accrual_plan_ids') and hr_employee.leave_accrual_plan_ids:
                for accrual_plan in hr_employee.leave_accrual_plan_ids:
                    if accrual_plan.balance > 0:
                        total_available += accrual_plan.balance
            
            # Format the total available leaves
            if total_available > 0:
                formatted_available = str(('%.2f' % total_available).rstrip('0').rstrip('.'))
                employee_data.update({'virtual_remaining_leaves': formatted_available})
            else:
                employee_data.update({'virtual_remaining_leaves': '0'})
            
            # Get all available leave types for this specific employee
            allocation_ids = request.env['hr.leave.allocation'].sudo().search([('employee_id', '=', hr_employee.id)])
            holidays_status_require_allocation_ids = request.env['hr.leave.type'].sudo().search([('requires_allocation', '=', 'no')])
            holidays_status_ids = request.env['hr.leave.type'].sudo().search(['|', (
                'id', 'in', allocation_ids.mapped('holiday_status_id').ids + holidays_status_require_allocation_ids.ids),
                                                                            ('is_service_portal', '=', 'True')])
            
            status_list = []
            for rec in holidays_status_ids:
                status_list.append({
                    'id': rec.id,
                    'name': rec.name,
                    'requires_allocation': rec.requires_allocation
                })
            
            employee_data.update({'holidays_status': status_list})
            
            # Check if employee is a subordinate of the current user
            current_employee = request.env['hr.employee'].sudo().search(
                [('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)], limit=1)
            
            is_subordinate = False
            if current_employee:
                subordinates = request.env['hr.employee'].sudo().search(
                    ['|', ('parent_id', '=', current_employee.id), ('coach_id', '=', current_employee.id)])
                is_subordinate = hr_employee.id in subordinates.ids
            
            employee_data.update({'is_subordinate': is_subordinate})
            
            # Add task information if available
            if hasattr(hr_employee, 'task_id') and hr_employee.task_id:
                task = hr_employee.task_id
            
                employee_data.update({
                    'task_id': task.id,
                    'task_name': task.name,
                    'customer': task.partner_id.name if task.partner_id else '',
                    'location': task.partner_location_id.name if hasattr(task, 'partner_location_id') and task.partner_location_id else ''
                })
                
                # Add shift information if available
                if hasattr(task, 'shift_allocation_ids') and task.shift_allocation_ids:
                    shift_allocation = task.shift_allocation_ids[0]
                    employee_data.update({
                        'shift': shift_allocation.shift_id.name if shift_allocation.shift_id else '',
                        'shift_id': shift_allocation.shift_id.id if shift_allocation.shift_id else False
                    })
            
            return employee_data
        else:
            return False

        
    @http.route(['/login/employee/'], type='json', auth='public', website=True)
    def return_login_employee(self, **kw):
        partner_id = request.env.user.partner_id
        
        if not partner_id:
            return False
            
        hr_employee = request.env['hr.employee'].sudo().search([
            ('peoplesolve_emp_partner_id', '=', partner_id.id)
        ], limit=1)
        
        if not hr_employee:
            return False
        
        employee_type_display = dict(hr_employee._fields['hr_employee_type'].selection).get(hr_employee.hr_employee_type) if hasattr(hr_employee, 'hr_employee_type') else ''
            
        employee_data = {
            'employee_id': hr_employee.id,
            'job_title': hr_employee.job_title if hasattr(hr_employee, 'job_title') else hr_employee.job_id.name,
            'parent_id': hr_employee.parent_id.name if hr_employee.parent_id else '',
            'coach_id': hr_employee.coach_id.name if hr_employee.coach_id else '',
            'joining_date': hr_employee.original_hire_date.strftime('%Y-%m-%d') if hasattr(hr_employee, 'original_hire_date') and hr_employee.original_hire_date else False,
            'company_id': str(hr_employee.company_id.id) if hr_employee.company_id else '',
            'branch_id': str(hr_employee.branch_id.id) if hr_employee.branch_id else '',
            'hr_employee_type': hr_employee.hr_employee_type if hasattr(hr_employee, 'hr_employee_type') else '',
            'employee_type_display': employee_type_display
        }
        
        # Get all leave allocations and calculate remaining leaves
        leave_allocations = request.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', hr_employee.id),
            ('state', '=', 'validate'),
            ('holiday_status_id.active', '=', True)
        ])
        
        total_available = 0
        for allocation in leave_allocations:
            total_available += allocation.number_of_days_display
        
        if leave_allocations:
            leaves_taken = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', hr_employee.id),
                ('state', '=', 'validate'),
                ('holiday_status_id', 'in', leave_allocations.mapped('holiday_status_id').ids)
            ])
            
            for leave in leaves_taken:
                total_available -= leave.number_of_days
        
        # Add any accrual plan balances if applicable
        if hasattr(hr_employee, 'leave_accrual_plan_ids') and hr_employee.leave_accrual_plan_ids:
            for accrual_plan in hr_employee.leave_accrual_plan_ids:
                if accrual_plan.balance > 0:
                    total_available += accrual_plan.balance
        
        if total_available > 0:
            formatted_available = str(('%.2f' % total_available).rstrip('0').rstrip('.'))
            employee_data.update({'virtual_remaining_leaves': formatted_available})
        else:
            employee_data.update({'virtual_remaining_leaves': '0'})
        
        # Add task information if available
        if hasattr(hr_employee, 'task_id') and hr_employee.task_id:
            task = hr_employee.task_id
            
            employee_data.update({
                'task_id': task.id,
                'task_name': task.name,  
                'customer': task.partner_id.name if task.partner_id else '',
                'location': task.partner_location_id.name if hasattr(task, 'partner_location_id') and task.partner_location_id else ''
            })
            
            # Add shift information if available
            if hasattr(task, 'shift_allocation_ids') and task.shift_allocation_ids:
                shift_allocation = task.shift_allocation_ids[0]
                employee_data.update({
                    'shift': shift_allocation.shift_id.name if shift_allocation.shift_id else '',
                    'shift_id': shift_allocation.shift_id.id if shift_allocation.shift_id else False
                })
        
        return employee_data

    

    @http.route(['/my/duty', '/my/duty/page/<int:page>'], type='http', method=["POST", "GET"], auth="user", website=True)
    def portal_my_duty(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        employee_id = request.env.user.partner_id
        duty_obj = request.env['duty.resumption']
        emp_obj = request.env['hr.employee']

        
        domain = ['|',
                ('employee_id.peoplesolve_emp_partner_id', '=', employee_id.id if employee_id else False),
                ('create_uid', '=', request.env.user.id)]

        searchbar_sortings = {
            'state': {'label': _('state'), 'order': 'state desc'},
        }
        
        if not sortby:
            sortby = 'state'
        sort_order = searchbar_sortings[sortby]['order']

        emp_domain = ['|', ('coach_id.peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id),
                    ('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)]
        employee_ids = emp_obj.sudo().search(emp_domain)

        current_employee = request.env['hr.employee'].sudo().search(
            [('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)], limit=1)
        subordinates = []
        if current_employee:
            subordinates = request.env['hr.employee'].sudo().search(
                ['|', ('parent_id', '=', current_employee.id), ('coach_id', '=', current_employee.id)])

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        duty_ids = duty_obj.sudo().search(domain)
        
        duty_exists_map = {duty.leave_id.id: duty.id for duty in duty_ids}

        employee_id = request.env['hr.employee'].sudo().search(
            [('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)], limit=1)
        allocation_ids = request.env['hr.leave.allocation'].sudo().search([('employee_id', '=', employee_id.id)])
        holidays_status_require_allocation_ids = request.env['hr.leave.type'].sudo().search(
            [('requires_allocation', '=', 'no')])

        holidays_status_ids = request.env['hr.leave.type'].sudo().search(['|', (
            'id', 'in', allocation_ids.mapped('holiday_status_id').ids + holidays_status_require_allocation_ids.ids),
                                                                        ('is_service_portal', '=', 'True')])

        status_dict = self.get_holidays_status(holidays_status_ids)
        employee_dict = self.get_employee_info(employee_ids)
        subordinate_dict = self.get_employee_info(subordinates)

        pager = portal_pager(
            url="/my/duty",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=len(duty_ids),
            page=page,
            step=self._items_per_page
        )

        values.update({
            'date': date_begin,
            'duty_ids': duty_ids.sudo(),
            'employee_ids': employee_ids,
            'subordinates': subordinates,
            'subordinate_dict': subordinate_dict,
            'employee_names': employee_dict,
            'page_name': 'duty_list_view',
            'pager': pager,
            'default_url': '/my/duty',
            'searchbar_sortings': searchbar_sortings,
            'create_duty': True,
            'holidays_status_ids': holidays_status_ids,
            'status_dict': status_dict,
            'sortby': sortby,
            'duty_exists_map': duty_exists_map,
            'is_manager': len(subordinates) > 0,
        })
        return request.render("hr_employee_portal.portal_my_duty", values)


    @http.route('/my/create/duty/n_page', type='http', method=["POST", "GET"], auth="user", website=True, csrf=False)
    def create_duty_resumption(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        employee_id = request.env.user.partner_id
        duty_obj = request.env['duty.resumption']
        emp_obj = request.env['hr.employee']
        branch_list = request.env['res.branch'].search([])

        domain = [
            ('employee_id.peoplesolve_emp_partner_id', '=', employee_id.id if employee_id else False)
        ]

        emp_domain = ['|', ('coach_id.peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id),
                    ('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)]
        employee_ids = emp_obj.sudo().search(emp_domain)

        current_employee = request.env['hr.employee'].sudo().search(
            [('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)], limit=1)
        subordinates = []
        if current_employee:
            subordinates = request.env['hr.employee'].sudo().search(
                ['|', ('parent_id', '=', current_employee.id), ('coach_id', '=', current_employee.id)])

        employee_id = current_employee
        
        leave_domain = [
            ('duty_resumption_leave', '=', False), 
            ('employee_id', '=', current_employee.id if current_employee else False),
            ('state', '=', 'validate'),
            ('holiday_status_id.allow_duty_resumption', '=', True)
        ]
        leave_ids = request.env['hr.leave'].sudo().search(leave_domain)

        leave_data = []
        for leave in leave_ids:
            leave_data.append({
                'id': leave.id,
                'name': f"{leave.holiday_status_id.name}: {leave.request_date_from.strftime('%Y-%m-%d')} to {leave.request_date_to.strftime('%Y-%m-%d')}"
            })

        allocation_ids = request.env['hr.leave.allocation'].sudo().search([('employee_id', '=', current_employee.id if current_employee else False)])
        holidays_status_require_allocation_ids = request.env['hr.leave.type'].sudo().search(
            [('requires_allocation', '=', 'no')])

        holidays_status_ids = request.env['hr.leave.type'].sudo().search(['|', (
            'id', 'in', allocation_ids.mapped('holiday_status_id').ids + holidays_status_require_allocation_ids.ids),
                                                                        ('is_service_portal', '=', 'True')])

        status_dict = self.get_holidays_status(holidays_status_ids)
        employee_dict = self.get_employee_info(employee_ids)
        subordinate_dict = self.get_employee_info(subordinates)

        values.update({
            'date': date_begin,
            'employee_ids': employee_ids,
            'subordinates': subordinates,
            'subordinate_dict': subordinate_dict,
            'employee_dict': employee_dict,
            'page_name': 'duty_list_view',
            'default_url': '/my/create/duty/n_page',
            'searchbar_sortings': {
                'state': {'label': _('state'), 'order': 'state desc'},
            },
            'create_duty': True,
            'leave_ids': leave_data,  
            'leave_records': leave_ids,  
            'holidays_status_ids': holidays_status_ids,
            'status_dict': status_dict,
            'branch_list': branch_list,
            'sortby': sortby,
            'is_manager': len(subordinates) > 0,
            'current_employee_id': current_employee.id if current_employee else False,
            'current_employee_name': current_employee.name if current_employee else '',
        })
        return request.render("hr_employee_portal.create_duty_resumption", values)
    
    @http.route(['/create/duty'], type='http', website=True, auth='public')
    def create_dutyres(self, **kw):
        duty_obj = request.env['duty.resumption']
        leave_id = int(kw.get("emp_leaves"))

        employee_id = int(kw.get("on_behalf_of")) if kw.get("on_behalf_of") else int(kw.get("employee_ids"))
        existing_duty = duty_obj.sudo().search([('leave_id', '=', leave_id)], limit=1)
        
        # Safely handle holidays_status_ids
        holidays_status_id = kw.get("holidays_status_ids")
        holidays_status_id = int(holidays_status_id) if holidays_status_id and holidays_status_id.strip() else False
        
        if existing_duty:
            existing_duty.write({
                'employee_id': employee_id,
                'reporting_date': kw.get("reporting_date"),
                'leave_type_id': holidays_status_id,
                'duty_resumption_date': kw.get("duty_resumption_date"),
                'reason': kw.get("reason")
            })
            duty = existing_duty
        else:
            vals = {
                'employee_id': employee_id,
                'reporting_date': kw.get("reporting_date"),
                'leave_id': leave_id,
                'leave_type_id': holidays_status_id,
                'duty_resumption_date': kw.get("duty_resumption_date"),
                'reason': kw.get("reason")
            }
            duty = duty_obj.sudo().create(vals)

        return request.redirect('/my/home/')

    # @http.route(['/create/duty'], type='http', website=True, auth='public')
    # def create_dutyres(self, **kw):
    #     duty_obj = request.env['duty.resumption']
    #     leave_id = int(kw.get("emp_leaves"))

    #     employee_id = int(kw.get("on_behalf_of")) if kw.get("on_behalf_of") else int(kw.get("employee_ids"))
    #     existing_duty = duty_obj.sudo().search([('leave_id', '=', leave_id)], limit=1)

    #     if existing_duty:
    #         existing_duty.write({
    #             'employee_id': employee_id,
    #             'reporting_date': kw.get("reporting_date"),
    #             'leave_type_id': int(kw.get("holidays_status_ids")),
    #             'duty_resumption_date': kw.get("duty_resumption_date"),
    #             'reason': kw.get("reason")
    #         })
    #         duty = existing_duty
    #     else:
    #         vals = {
    #             'employee_id': employee_id,
    #             'reporting_date': kw.get("reporting_date"),
    #             'leave_id': leave_id,
    #             'leave_type_id': int(kw.get("holidays_status_ids")),
    #             'duty_resumption_date': kw.get("duty_resumption_date"),
    #             'reason': kw.get("reason")
    #         }
    #         duty = duty_obj.sudo().create(vals)

    #     return request.redirect('/my/home/')

    
    
    # @http.route(['/create/leave'], type='http', website=True)
    # def create_leave(self, **kw):

    #     print('****create_leave****')

    #     leave_obj = request.env['hr.leave']

    #     print('kw+_+_+_+_+_+_', kw)

    #     date_from = datetime.strptime(kw.get("start_date_leave"), '%Y-%m-%d').strftime('%Y-%m-%d %H:%M')
    #     date_to = datetime.strptime(kw.get("end_date_leave"), '%Y-%m-%d').strftime('%Y-%m-%d %H:%M')
    #     vals = {
    #         'employee_ids': [(6, 0, [int(kw.get("employee_ids"))])],
    #         'holiday_status_id': int(kw.get("holidays_status_ids")),
    #         'request_date_from': date_from,
    #         'request_date_to': date_to,
    #         'date_from': date_from,
    #         'date_to': date_to,
    #         'name': kw.get("description_leave"),
    #         # 'state': 'draft',
    #         'emergency_contact_number': kw.get("emergency_contact_number"),
    #         'address': kw.get("address"),
    #         'air_ticket': kw.get("air_ticket"),
    #         'holiday_type': 'employee',
    #         'multi_employee': True
    #     }

    #     # try:
    #     leave = leave_obj.sudo().create(vals)
    #     print('leave+_+_+_+_', leave)
    #     # except ValidationError as e:
    #     #     request.env.cr.rollback()
    #     #     data = {'title': _('Send info'), 'msg': e.args[0]}
    #     #     return data

    #     return request.redirect('/my/home/')


    # @http.route(['/my/duty', '/my/duty/page/<int:page>'], type='http', method=["POST", "GET"], auth="user", website=True)
    # def portal_my_duty(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
    #     values = self._prepare_portal_layout_values()
    #     employee_id = request.env.user.partner_id
    #     duty_obj = request.env['duty.resumption']
    #     emp_obj = request.env['hr.employee']

    #     domain = [
    #         ('employee_id.peoplesolve_emp_partner_id', '=', employee_id.id if employee_id else False)
    #     ]

    #     searchbar_sortings = {
    #         'state': {'label': _('state'), 'order': 'state desc'},

    #     }
    #     # default sortby order
    #     if not sortby:
    #         sortby = 'state'
    #     sort_order = searchbar_sortings[sortby]['order']

    #     print('request.env.user.partner_id.id++++++++++', request.env.user.partner_id.id)
    #     emp_domain = ['|', ('coach_id.peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id),
    #                   ('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)]
    #     print('emp_domain++++++++++++++++', emp_domain)
    #     employee_ids = emp_obj.sudo().search(emp_domain)

    #     if date_begin and date_end:
    #         domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

    #     duty_ids = duty_obj.sudo().search(domain)

    #     employee_id = request.env['hr.employee'].sudo().search(
    #         [('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)], limit=1)
    #     allocation_ids = request.env['hr.leave.allocation'].sudo().search([('employee_id', '=', employee_id.id)])
    #     holidays_status_require_allocation_ids = request.env['hr.leave.type'].sudo().search(
    #         [('requires_allocation', '=', 'no')])

    #     holidays_status_ids = request.env['hr.leave.type'].sudo().search(['|', (
    #         'id', 'in', allocation_ids.mapped('holiday_status_id').ids + holidays_status_require_allocation_ids.ids),
    #                                                                       ('is_service_portal', '=', 'True')])

    #     status_dict = self.get_holidays_status(holidays_status_ids)
    #     print("=============duty employee==============", employee_ids)

    #     employee_dict = self.get_employee_details(employee_ids)

    #     # pager
    #     pager = portal_pager(
    #         url="/my/duty",
    #         url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
    #         total=len(duty_ids),
    #         page=page,
    #         step=self._items_per_page
    #     )

    #     values.update({
    #         'date': date_begin,
    #         'duty_ids': duty_ids.sudo(),
    #         'employee_ids': employee_ids,
    #         'employee_names': employee_dict,
    #         'page_name': 'duty_list_view',
    #         'pager': pager,
    #         'default_url': '/my/duty',
    #         'searchbar_sortings': searchbar_sortings,
    #         'create_duty': True,
    #         'holidays_status_ids': holidays_status_ids,
    #         'status_dict': status_dict,
    #         'sortby': sortby,
    #     })
    #     print("============kw value=================", kw.get("leaves_types"), kw.get("start_date"), kw)

    #     return request.render("hr_employee_portal.portal_my_duty", values)

    # @http.route('/my/create/duty/n_page', type='http', method=["POST", "GET"], auth="user", website=True, csrf=False)
    # def create_duty_resumption(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):

    #     print('***/my/create/duty/n_page***')

    #     values = self._prepare_portal_layout_values()
    #     employee_id = request.env.user.partner_id
    #     duty_obj = request.env['duty.resumption']
    #     emp_obj = request.env['hr.employee']
    #     branch_list = request.env['res.branch'].search([])

    #     domain = [
    #         ('employee_id.peoplesolve_emp_partner_id', '=', employee_id.id if employee_id else False)
    #     ]

    #     searchbar_sortings = {
    #         'state': {'label': _('state'), 'order': 'state desc'},

    #     }
    #     # default sortby order
    #     if not sortby:
    #         sortby = 'state'
    #     sort_order = searchbar_sortings[sortby]['order']

    #     print('request.env.user.partner_id.id++++++++++', request.env.user.partner_id.id)
    #     emp_domain = ['|', ('coach_id.peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id), ('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)]
    #     print('emp_domain++++++++++++++++', emp_domain)
    #     employee_ids = emp_obj.sudo().search(emp_domain)

    #     if date_begin and date_end:
    #         domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

    #     duty_ids = duty_obj.sudo().search(domain)

    #     employee_id = request.env['hr.employee'].sudo().search(
    #         [('peoplesolve_emp_partner_id', '=', request.env.user.partner_id.id)], limit=1)
    #     allocation_ids = request.env['hr.leave.allocation'].sudo().search([('employee_id', '=', employee_id.id)])
    #     holidays_status_require_allocation_ids = request.env['hr.leave.type'].sudo().search(
    #         [('requires_allocation', '=', 'no')])

    #     print('employee_id+_+_+_', employee_id.id)
    #     leave_ids = request.env['hr.leave'].sudo().search([('employee_id', '=', employee_id.id), ('duty_resumption_leave', '=', False)])
    #     print('leave_ids+_+_+_+_', leave_ids)

    #     holidays_status_ids = request.env['hr.leave.type'].sudo().search(['|', (
    #         'id', 'in', allocation_ids.mapped('holiday_status_id').ids + holidays_status_require_allocation_ids.ids),
    #                                                                       ('is_service_portal', '=', 'True')])

    #     status_dict = self.get_holidays_status(holidays_status_ids)
    #     print("=============duty employee==============", employee_ids)

    #     employee_dict = self.get_employee_details(employee_ids)
    #     print('employee_dict+_+_+_+_', employee_dict)

    #     # pager
    #     pager = portal_pager(
    #         url="/my/create/duty/n_page",
    #         url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
    #         total=len(duty_ids),
    #         page=page,
    #         step=self._items_per_page
    #     )

    #     values.update({
    #         'date': date_begin,
    #         'duty_ids': duty_ids.sudo(),
    #         'employee_ids': employee_ids,
    #         'employee_dict': employee_dict,
    #         # 'all_employee_dict': self.get_employee_details(emp_obj.sudo().search([])),
    #         'page_name': 'duty_list_view',
    #         'pager': pager,
    #         'default_url': '/my/create/duty/n_page',
    #         'searchbar_sortings': searchbar_sortings,
    #         'create_duty': True,
    #         'leave_ids': leave_ids,
    #         'holidays_status_ids': holidays_status_ids,
    #         'status_dict': status_dict,
    #         'branch_list': branch_list,
    #         'sortby': sortby,
    #     })
    #     print("============kw value=================", kw.get("leaves_types"), kw.get("start_date"), kw)

    #     print('values+_+_+_', values)

    #     return request.render("hr_employee_portal.create_duty_resumption", values)

    # @http.route(['/create/duty'], type='http', website=True)
    # def create_dutyres(self, **kw):

    #     print('***/create/duty***')

    #     print("+++++++++++++kw+++++++++++++++", kw)
    #     print('holidays_status_ids', kw.get("holidays_status_ids"))

    #     duty_obj = request.env['duty.resumption']
    #     vals = {
    #         'employee_id': int(kw.get("employee_ids")),
    #         "reporting_date": kw.get("reporting_date"),
    #         "leave_id": int(kw.get("emp_leaves")),
    #         "leave_type_id": int(kw.get("holidays_status_ids")),
    #         "duty_resumption_date": kw.get("duty_resumption_date"),
    #         "reason": kw.get("reason")
    #     }

    #     print('vals+_+_+_+_', vals)
    #     # errrrr

    #     duty = duty_obj.sudo().create(vals)

    #     print('duty+_+_+_+_', duty)

    #     return request.redirect('/my/home/')

    # @http.route(['/create/duty'], type='http', website=True, auth='public')
    # def create_dutyres(self, **kw):
    #     print('***/create/duty***')
    #     print("+++++++++++++kw+++++++++++++++", kw)
    #     print('holidays_status_ids', kw.get("holidays_status_ids"))

    #     duty_obj = request.env['duty.resumption']
    #     leave_id = int(kw.get("emp_leaves"))

    #     # Check if a duty resumption already exists for this leave
    #     existing_duty = duty_obj.sudo().search([('leave_id', '=', leave_id)], limit=1)

    #     if existing_duty:
    #         # If a record already exists, you can either update it or return an error
    #         # Here, we are updating the existing record
    #         existing_duty.write({
    #             'employee_id': int(kw.get("employee_ids")),
    #             'reporting_date': kw.get("reporting_date"),
    #             'leave_type_id': int(kw.get("holidays_status_ids")),
    #             'duty_resumption_date': kw.get("duty_resumption_date"),
    #             'reason': kw.get("reason")
    #         })
    #         duty = existing_duty
    #     else:
    #         # If no record exists, create a new one
    #         vals = {
    #             'employee_id': int(kw.get("employee_ids")),
    #             'reporting_date': kw.get("reporting_date"),
    #             'leave_id': leave_id,
    #             'leave_type_id': int(kw.get("holidays_status_ids")),
    #             'duty_resumption_date': kw.get("duty_resumption_date"),
    #             'reason': kw.get("reason")
    #         }
    #         duty = duty_obj.sudo().create(vals)

    #     print('duty+_+_+_+_', duty)
    #     return request.redirect('/my/home/')

    @http.route(['/leave/data'], type='json', auth='public', website=True)
    def return_leave_data(self, **kw):

        print('***return_leave_data***')

        print('kw+_+_+_+_', kw)

        if kw.get('params').get('leave_id'):
            hr_leave = request.env['hr.leave'].sudo().browse(int(kw.get('params').get('leave_id')))
            print('hr_employee+_+_+_+_', hr_leave)
            if kw.get('params').get('date'):
                print('hr_leave.request_date_to+_+_+_', hr_leave.request_date_to)
                return hr_leave.request_date_to
            return hr_leave.holiday_status_id.id
        else:
            return False
        

    @http.route('/employee/leaves', type='json', auth='user', website=True)
    def return_employee_leaves(self, **kw):
        employee_id = None
        
        if kw.get('params') and kw.get('params').get('employee_id'):
            employee_id = int(kw.get('params').get('employee_id'))
        elif kw.get('employee_id'):
            employee_id = int(kw.get('employee_id'))
        
        if not employee_id:
            return False
        
        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if not employee:
            return False
        
        leave_domain = [
            ('duty_resumption_leave', '=', False), 
            ('employee_id', '=', employee_id),
            ('state', '=', 'validate'),
            ('holiday_status_id.allow_duty_resumption', '=', True)
        ]
        leave_ids = request.env['hr.leave'].sudo().search(leave_domain)
        
        leave_data = []
        for leave in leave_ids:
            leave_data.append({
                'id': leave.id,
                'name': f"{leave.holiday_status_id.name}: {leave.request_date_from.strftime('%Y-%m-%d')} to {leave.request_date_to.strftime('%Y-%m-%d')}"
            })
        
        return leave_data
