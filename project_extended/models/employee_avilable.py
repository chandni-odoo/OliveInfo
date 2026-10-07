from odoo import api, fields, models, _


# from datetime import date, timedelta

class EmployeeAvilableReport(models.Model):
    _name = 'employee.avilable.report'
    _description = 'Employee Avilable Report'
    _rec_name = 'select_date'

    select_date = fields.Date(string="Date")
    branch_id = fields.Many2many('res.branch', string="Branch")
    company_id = fields.Many2many('res.company', string="Company")
    category_ids = fields.Many2many('hr.job', string="Category")

    def get_domain(self, data):
        domain = [('emp_status', '=', 'active'), ('billable', '=', True)]
        for record in self:
            if record.company_id:
                domain += [('company_id', 'in', record.company_id.ids)]
            if record.branch_id:
                domain += [('branch_id', 'in', record.branch_id.ids)]
            if record.category_ids:
                domain += [('job_id', 'in', record.category_ids.ids)]
        return domain

    def button_get_categ(self, data=None):
        domain = self.get_domain(data)
        for record in self:
            if domain:
                """ Employee Filtered """
                employees = self.env['hr.employee'].search(domain)
                print("Employe____", employees)

                """ Planning Filtered for selected date """
                # planning = self.env['planning.slot'].search([('employee_id', 'in', employees.ids),
                #                                         ('start_datetime','<=',record.select_date),
                #                                        ])

                # remove_ids = [plan.employee_id.id for plan in planning]
                # employees = employees.filtered(lambda x: x.id not in remove_ids)

                task_history_id = self.env['task.resource.history'].search([('employee_id', 'in', employees.ids),
                                                                            ('date_start', '<=', record.select_date),
                                                                            ('date_end', '>=', record.select_date)
                                                                            ])
                task_history_id = task_history_id.filtered(
                    lambda
                        sol: not sol.demobilize_date or sol.demobilize_date and sol.demobilize_date.date() > record.select_date)

                print("Task History_________", task_history_id)

                remove_ids = [task.employee_id.id for task in task_history_id]
                employees = employees.filtered(lambda x: x.id not in remove_ids)

                search_view_id = self.env.ref('project_extended.view_employee_availability_search').id
                tree_view_id = self.env.ref('project_extended.view_employee_availability_tree').ids
                form_view_id = self.env.ref('hr.view_employee_form').ids
                return {
                    'name': _('Employee Availability'),
                    'view_mode': 'tree',
                    'res_model': 'hr.employee',
                    'domain': str([('id', 'in', employees.ids)]),
                    'context': {'search_default_emp_status': 'active', 'search_default_billable': True,
                                'search_default_group_job_id': 1},
                    'search_view_id': search_view_id,
                    'views': [[tree_view_id, 'tree'], [form_view_id, 'form']],
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                }
