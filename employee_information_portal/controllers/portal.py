from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64

class EmployeeInformationPortal(CustomerPortal):
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

    @http.route(['/my/employee-information'], type='http', auth='user', website=True)
    def portal_my_employee_information(self):
        user = request.env.user
        employee = self._get_current_employee(user)
        
        if not employee:
            return request.render('employee_information_portal.employee_information_not_found')
        
        vals = {
            'employee': employee,
            'page_name': 'employee_information',
            'user': user,
        }
        return request.render('employee_information_portal.employee_information_template', vals)
    
    @http.route(['/download/employee_document/<int:document_id>'], type='http', auth='user', website=True)
    def download_employee_document(self, document_id, **post):
        try:
            document = request.env['hr.document.line'].sudo().browse(document_id)
            
            if not document.exists():
                return request.not_found()
            
            if not document.attachment:
                return request.not_found()
            
            filename = f"{document.document_line_id.name or 'document'}_{document.document_number or 'file'}.pdf"
            return request.make_response(
                base64.b64decode(document.attachment),
                headers=[
                    ('Content-Type', 'application/octet-stream'),
                    ('Content-Disposition', 
                     f'attachment; filename={filename}')
                ]
            )
        
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'Document Download Error',
                'type': 'server',
                'dbname': request.env.cr.dbname,
                'level': 'error',
                'message': str(e),
                'path': '/download/employee_document',
                'func': 'download_employee_document',
                'line': 15
            })
            return request.not_found()