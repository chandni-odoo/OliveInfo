import binascii
import json

from odoo import fields, http, SUPERUSER_ID, _
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.fields import Command
from odoo.http import request

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.payment import utils as payment_utils
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager, get_records_pager
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
import operator
from odoo.tools import float_compare, float_round
import pytz
import base64
import logging

_logger = logging.getLogger(__name__)


class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner_id = request.env.user.partner_id
        
        if 'request_count' in counters:
            request_count = request.env['request.request'].sudo().search_count([
                ('employee_id.peoplesolve_emp_partner_id', '=', partner_id.id)
            ])
            values['request_count'] = request_count
            print("=============request_count===============", request_count)
            
        return values


    def get_request_types(self):
        return request.env['hr.request.type'].sudo().search([])
    
    def get_leaving_reasons(self):
        return request.env['hr.leaving.reason'].sudo().search([])
    
    def get_employee_subordinates(self):
        """Fetch employees based on the current user's manager status"""
        user = request.env.user
        current_employee = user.employee_id
        
        if not current_employee:
            
            employee_obj = request.env['hr.employee'].sudo()
            current_employee = employee_obj.search([('work_email', '=', user.email)], limit=1)
            
        if not current_employee:
            
            current_employee = employee_obj.search([('peoplesolve_emp_partner_id', '=', user.partner_id.id)], limit=1)
            
        if not current_employee:
            return request.env['hr.employee'].sudo().browse([])
            
        subordinates = request.env['hr.employee'].sudo().search([
            ('parent_id', '=', current_employee.id)
        ])
        
        if subordinates:
            return current_employee + subordinates
        else:
            return current_employee


    @http.route(['/my/request', '/my/request/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_request(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        
        current_employee = self._get_current_employee(user)
        request_obj = request.env['request.request'] 
        domain = [
            ('state', 'in', ['draft', 'confirm', 'approve', 'submit'])
        ]
        
        if current_employee:
            employees = self.get_employee_subordinates()
            employee_ids = employees.ids if employees else []
            if current_employee.id not in employee_ids:
                employee_ids.append(current_employee.id)
                
            domain.append(('employee_id', 'in', employee_ids))
        
        searchbar_sortings = {
            'state': {'label': _('state'), 'order': 'state desc'},
            'date': {'label': _('Newest'), 'order': 'request_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']
        
       
        request_ids = request_obj.sudo().search(domain, order=sort_order)
        request_count = len(request_ids)
        
       
        pager = portal_pager(
            url="/my/request",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=request_count,
            page=page,
            step=self._items_per_page
        )
        
        requests = request_ids[pager['offset']:pager['offset'] + self._items_per_page]
        
        request.session['my_request_history'] = request_ids.ids[:100]
        
        employees = self.get_employee_subordinates()
        
        values.update({
            'date': date_begin,
            'requests': requests,
            'requests_ids': requests,  
            'page_name': 'request',
            'pager': pager,
            'default_url': '/my/request',
            'searchbar_sortings': searchbar_sortings,
            'create_request': True,
            'requests_type_ids': self.get_request_types(),
            'leaving_reasons': self.get_leaving_reasons(),
            'sortby': sortby,
            'employees': employees,
            'current_employee': current_employee,
            'employee_name': current_employee.name if current_employee else '',
        })
        requests = requests.sudo()  
    
        values.update({
            'show_final_document': True,  
        })
        
        return request.render("hr_request_portal.portal_my_request", values)


    @http.route('/add/request', type='http', auth="user", website=True, csrf=True, methods=['POST'])
    def create_request(self, **post):
        try:
            request_selection = post.get('request_selection')
            request_date = post.get('request_date')
            description_request = post.get('description_request')
            relieving_date = post.get('relieving_date')
            languages = post.get('languages')
            requirements = post.get('requirements')
            on_behalf_of = post.get('on_behalf_of')
            reason_for_leaving_id = post.get('reason_for_leaving_id')
            attachments = request.httprequest.files.get('attachments')
            resignation_date = post.get('resignation_date')
            
           
            if not request_selection:
                return request.make_response(json.dumps({
                    'success': False,
                    'title': 'Send info',
                    'msg': "Please select request type"
                }), headers=[('Content-Type', 'application/json')])
                
            if not request_date:
                return request.make_response(json.dumps({
                    'success': False,
                    'title': 'Send info',
                    'msg': "Please select request date"
                }), headers=[('Content-Type', 'application/json')])
                
            if not description_request:
                return request.make_response(json.dumps({
                    'success': False,
                    'title': 'Send info',
                    'msg': "Please enter request description"
                }), headers=[('Content-Type', 'application/json')])

            try:
                request_date = fields.Date.from_string(request_date)
                relieving_date = fields.Date.from_string(relieving_date) if relieving_date else False
            except ValueError:
                return request.make_response(json.dumps({
                    'success': False,
                    'title': 'Send info',
                    'msg': "Invalid date format"
                }), headers=[('Content-Type', 'application/json')])
            

            # Get request type record to check if it's resignation or termination
            request_type = request.env['hr.request.type'].sudo().browse(int(request_selection))
            is_resignation_or_termination = False
            if request_type and ('termination' in request_type.name.lower() or 'resignation' in request_type.name.lower()):
                is_resignation_or_termination = True
                
                # Additional validation for resignation/termination
                if not relieving_date:
                    return request.make_response(json.dumps({
                        'success': False,
                        'title': 'Send info',
                        'msg': "Please select relieving date"
                    }), headers=[('Content-Type', 'application/json')])

           
            employee_id = int(on_behalf_of) if on_behalf_of else request.env.user.employee_id.id
            if not employee_id:
                return request.make_response(json.dumps({
                    'success': False,
                    'title': 'Send info',
                    'msg': "Employee not found"
                }), headers=[('Content-Type', 'application/json')])
                
            employee = request.env['hr.employee'].sudo().browse(employee_id)
            
            vals = {
                'employee_id': employee_id,
                'branch_id': employee.branch_id.id if employee.branch_id else False,
                'job_id': employee.job_id.id if employee.job_id else False,
                'request_date': request_date,
                'type_id': int(request_selection),
                'state': 'draft',
                'description': description_request,
                'relieving_date': relieving_date,
                'resignation_date': fields.Date.from_string(resignation_date) if resignation_date else False,
                'reason_for_leaving_id': int(reason_for_leaving_id) if reason_for_leaving_id else False,
                # 'languages': languages,
                'languages': languages if not is_resignation_or_termination else 'na',
                'requirements': requirements,
            }

            try:
                request_id = request.env['request.request'].sudo().create(vals)
                
                if attachments:
                    attachment_data = attachments.read()
                    request_id.write({
                        'attachments': base64.b64encode(attachment_data),
                        'attachments_filename': attachments.filename
                    })
                    
                return request.make_response(json.dumps({
                    'success': True,
                    'request_id': request_id.id,
                    'redirect_url': '/my/request'
                }), headers=[('Content-Type', 'application/json')])
            except Exception as e:
                request.env.cr.rollback()
                return request.make_response(json.dumps({
                    'success': False,
                    'title': 'Send info',
                    'msg': str(e)
                }), headers=[('Content-Type', 'application/json')])
                
        except Exception as e:
            return request.make_response(json.dumps({
                'success': False,
                'title': 'Error',
                'msg': str(e)
            }), headers=[('Content-Type', 'application/json')])

        
    def _get_current_employee(self, user):
        current_employee = user.employee_id
        
        if not current_employee:
            current_employee = request.env['hr.employee'].sudo().search([
                ('work_email', '=', user.email)
            ], limit=1)
        
        
        if not current_employee:
            current_employee = request.env['hr.employee'].sudo().search([
                ('peoplesolve_emp_partner_id', '=', user.partner_id.id)
            ], limit=1)
        
        
        if not current_employee:
            current_employee = request.env['hr.employee'].sudo().search([
                ('user_id', '=', user.id)
            ], limit=1)
        
        return current_employee
    
    @http.route(['/download/final_document/<int:request_id>'], type='http', auth='user', website=True)
    def download_final_document(self, request_id, **post):
        try:
            
            request_record = request.env['request.request'].sudo().browse(request_id)
            
            if not request_record.exists():
                return request.not_found()
            
            if not request_record.final_document:
                return request.not_found()
            
           
            return request.make_response(
                base64.b64decode(request_record.final_document),
                headers=[
                    ('Content-Type', 'application/octet-stream'),
                    ('Content-Disposition', 
                     'attachment; filename=%s' % (request_record.final_document_filename or 'document.pdf'))
                ]
            )
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'Document Download Error',
                'type': 'server',
                'dbname': request.env.cr.dbname,
                'level': 'error',
                'message': str(e),
                'path': '/download/final_document',
                'func': 'download_final_document',
                'line': 15
            })
            return request.not_found()
        
    @http.route('/get/employee/notice_period', type='json', auth="user", website=True)
    def get_employee_notice_period(self, employee_id=None, **kw):
        employee = request.env['hr.employee'].sudo().browse(int(employee_id))
        return {
            'notice_period': employee.notice_id.name if employee.notice_id else "Not specified"
        }
