from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
import base64

class PortalPayslips(http.Controller):
    # def _prepare_home_portal_values(self, counters):
    #     values = super()._prepare_home_portal_values(counters)
    #     partner_id = request.env.user.partner_id
        
    #     if 'payslip_count' in counters:
    #         payslip_count = request.env['hr.payslip'].sudo().search_count([
    #             ('employee_id.peoplesolve_emp_partner_id', '=', partner_id.id)
    #         ])
    #         values['payslip_count'] = payslip_count
    #         print("=============payslip_count===============", payslip_count)
            
    #     return values


    @http.route(['/my/payslips'], type='http', auth="user", website=True)
    def my_payslips(self, **kw):
        try:
            
            employee = self._get_current_employee(request.env.user)
            
            if not employee:
                return request.render('portal.portal_my_home', {
                    'error_message': "No employee found for the current user."
                })
            
            payslips = request.env['hr.payslip'].sudo().search([
                ('employee_id', '=', employee.id)
            ], order='date_from desc', limit=12)
            
            payslip_data = []
            for payslip in payslips:
                
                attachments = request.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'hr.payslip'),
                    ('res_id', '=', payslip.id),
                    ('type', '=', 'binary'),
                    ('mimetype', 'in', ['application/pdf', 'application/octet-stream'])
                ])
                
                payslip_data.append({
                    'payslip': payslip,
                    'attachments': attachments
                })
            
            return request.render('hr_payslip_portal.my_payslips_list', {
                'payslip_data': payslip_data,
                'payslip_count': len(payslip_data),
                'page_name': 'payslip_list_view'
            })
        
        except AccessError:
            return request.render('portal.portal_my_home', {
                'error_message': "You do not have permission to view payslips."
            })
    
    # @http.route(['/my/payslip/download/<int:attachment_id>'], type='http', auth="user")
    # def download_payslip(self, attachment_id, **kw):
    #     try:
           
    #         attachment = request.env['ir.attachment'].sudo().search([
    #             ('id', '=', attachment_id),
    #             ('type', '=', 'binary'),
    #             ('mimetype', 'in', ['application/pdf', 'application/octet-stream'])
    #         ], limit=1)
            
           
    #         if not attachment or attachment.res_model != 'hr.payslip':
    #             return request.not_found()
            
            
    #         current_employee = self._get_current_employee(request.env.user)
            
            
    #         payslip = request.env['hr.payslip'].sudo().browse(attachment.res_id)
    #         if payslip.employee_id != current_employee:
    #             return request.not_found()
            
            
    #         file_content = base64.b64decode(attachment.datas)
            
            
    #         return request.make_response(
    #             file_content,
    #             headers=[
    #                 ('Content-Type', 'application/pdf'),
    #                 ('Content-Disposition', f'inline; filename={attachment.name}')
    #             ]
    #         )
    #     except Exception as e:
            
    #         request.env['ir.logging'].sudo().create({
    #             'name': 'Payslip Download Error',
    #             'type': 'server',
    #             'dbname': request.env.cr.dbname,
    #             'level': 'error',
    #             'message': str(e),
    #             'path': '',
    #             'func': 'download_payslip',
    #             'line': '0'
    #         })
    #         return request.not_found()

    @http.route(['/my/payslip/download/<int:attachment_id>'], type='http', auth="user")
    def download_payslip(self, attachment_id, **kw):
        try:
            attachment = request.env['ir.attachment'].sudo().search([
                ('id', '=', attachment_id),
                ('type', '=', 'binary'),
                ('mimetype', 'in', ['application/pdf', 'application/octet-stream'])
            ], limit=1)
            
            if not attachment or attachment.res_model != 'hr.payslip':
                return request.not_found()
            
            current_employee = self._get_current_employee(request.env.user)
            payslip = request.env['hr.payslip'].sudo().browse(attachment.res_id)
            
            if payslip.employee_id != current_employee:
                return request.not_found()
            
            file_content = base64.b64decode(attachment.datas)
            
            # Get the file extension from the attachment name or default to .pdf
            filename = attachment.name
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            return request.make_response(
                file_content,
                headers=[
                    ('Content-Type', 'application/octet-stream'),  # Changed from 'application/pdf'
                    ('Content-Disposition', f'attachment; filename={filename}')  # Changed from 'inline'
                ]
            )
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'Payslip Download Error',
                'type': 'server',
                'dbname': request.env.cr.dbname,
                'level': 'error',
                'message': str(e),
                'path': '',
                'func': 'download_payslip',
                'line': '0'
            })
            return request.not_found()
    
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