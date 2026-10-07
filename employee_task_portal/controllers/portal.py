from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class EmployeeTaskPortal(CustomerPortal):
    def _get_current_employee(self, user):
        current_employee = user.employee_id
        
        if not current_employee:
            current_employee = request.env['hr.employee'].sudo().search([
                ('work_email', '=', user.email)
            ], limit=1)
        
        if not current_employee:
            current_employee = request.env['hr.employee'].sudo().search([
                ('user_id', '=', user.id)
            ], limit=1)
        
        return current_employee

    @http.route(['/my/employee-tasks'], type='http', auth='user', website=True)
    def portal_my_employee_tasks(self):
        user = request.env.user
        employee = self._get_current_employee(user)
        
        if not employee:
            return request.render('employee_task_portal.employee_tasks_not_found')
        task_history = request.env['task.resource.history'].sudo().search([
            ('employee_id', '=', employee.id)
        ], order='date_start desc', limit=5)
        
        vals = {
            'employee': employee,
            'task_history': task_history,
            'page_name': 'employee_tasks',
            'user': user,
        }
        
        return request.render('employee_task_portal.employee_tasks_template', vals)