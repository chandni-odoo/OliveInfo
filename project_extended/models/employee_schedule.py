from odoo import api, fields, models, _


class EmployeeScheduleReport(models.Model):
    _name = 'employee.schedule.report'
    _description = 'Employee Schedule Report'
    _rec_name = 'select_date'


    select_date = fields.Date(string="Date", default=fields.Date.today)
    branch_ids = fields.Many2many('res.branch', string="Branch")
    company_ids = fields.Many2many('res.company', string="Company")
    category_ids = fields.Many2many('product.product', string="Category")

    
    hr_employee_type = fields.Selection([('own', 'Own'),('subcontractor','Subcontractor'),('both','Both')], default='both', required=True)
    
    employees_schedule_ids = fields.Many2many('hr.employee', string="Employees Schdule")

    task_ids = fields.Many2many('project.task', string="Project Task")
    partner_ids = fields.Many2many('res.partner', string="Customer")
    sale_order_ids = fields.Many2many('sale.order', string="Sale Order")
    supervisor_user_ids = fields.Many2many('res.users', string="Supervisor")#not Used
    supervisors_ids = fields.Many2many('hr.employee', 'employee_supervisors_rel', 'employee_id', 'supervisor_id', string="Task Supervisors")
 
    customer_location_ids = fields.Many2many('contact.location', string="Customer Location")

    def get_domain(self, data):
        domain = [('emp_status', '=', 'active'), ('billable', '=', True)]
        for record in self:
            if record.company_ids:
                domain += [('company_id', 'in', record.company_ids.ids)]
            if record.branch_ids:
                domain += [('branch_id', 'in', record.branch_ids.ids)]
            if record.category_ids:
                domain += [('product_ids', 'in', record.category_ids.ids)]
            if record.hr_employee_type == 'own':
                domain += [('hr_employee_type', '=', 'own')]
            if record.hr_employee_type == 'subcontractor':
                domain += [('hr_employee_type', '=', 'subcontractor')]
            if record.hr_employee_type == 'both':
                domain += [('hr_employee_type', 'in', ('own','subcontractor'))]
        return domain

    def button_get_categ(self, data=None):
        domain = self.get_domain(data)
        for record in self:
            if domain:
                partners = []
                supervisor = []
                # """ Employee Filtered """
                employees = self.env['hr.employee'].search(domain)
                print ("Employe____",employees)

                # """ Planning Filtered for selected date """
                # planning = self.env['planning.slot'].search([('employee_id', 'in', employees.ids),
                #                                         ('start_datetime','>=',record.select_date),
                #                                        ])

                # remove_ids = [plan.employee_id.id for plan in planning]
                # employees = employees.filtered(lambda x: x.id not in remove_ids)

                # task_ids = employees.mapped('task_ids')
                # task_history_id = task_ids.filtered(
                # lambda sol: not sol.demobilize_date or sol.demobilize_date and sol.demobilize_date.date() > record.select_date)

                task_history_id = self.env['task.resource.history'].search([('employee_id', 'in', employees.ids),
                                                        ('date_start','<=',record.select_date),('date_end','>=',record.select_date)
                                                       ])
                
                task_history_id = task_history_id.filtered(
                lambda sol: not sol.demobilize_date or sol.demobilize_date and sol.demobilize_date.date() > record.select_date)

                
                search_view_id = self.env.ref('project_extended.view_employee_task_schedule_history_search').id
                tree_view_id = self.env.ref('project_extended.view_employee_task_schedule_history_tree').ids
                form_view_id = self.env.ref('project_extended.view_employee_task_schedule_history_form').ids
                return {
                        'name': _('Employee Deployed'),
                        'view_mode': 'tree',
                        'res_model': 'task.resource.history',
                        'domain': str([('id', 'in', task_history_id.ids)]),
                        'context': {
                                'search_default_group_customer_id':1,
                        },
                        'search_view_id': search_view_id,
                        'views': [[tree_view_id, 'tree'], [form_view_id, 'form']],
                        'type': 'ir.actions.act_window',
                        'target': 'current',
                    }

class EmployeeScheduleDeployed(models.Model):
    _name = 'employee.schedule.deployed'
    _description = 'Employee Schedule Deployed'

    emp_no = fields.Char(string='Employee No')
    employee_id = fields.Char(string='Employee Name')
    hr_employee_type = fields.Selection([('own', 'Own'),('subcontractor','Subcontractor'),('both','Both')], default='own', required=True)
    product_ids = fields.Many2many('product.product', 'employee_product_category_rel', 'emp_id', 'product_id', string="Skill/Category")

    branch_id = fields.Many2one('res.branch', string="Branch")
    company_id = fields.Many2one('res.company', string="Company")
    category_id = fields.Many2one('hr.job', string="Category")

    task_id = fields.Many2one('project.task', string="Project Task")
    partner_id = fields.Many2one('res.partner', string="Customer")
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    supervisor_emp_id = fields.Many2one('hr.employee', string="Supervisor")
 
    partner_location_id = fields.Many2many('contact.location', string="Customer Location")

class TaskResourceHistory(models.Model):
    _inherit = 'task.resource.history'
    _description = 'Employee Deployed'
    _rec_name = 'emp_no'

    #Employee
    emp_no = fields.Char(string="Employee No", related="employee_id.emp_no")
    hr_employee_type = fields.Selection(related="employee_id.hr_employee_type")

    product_ids = fields.Many2many('product.product', 'employee_product_category_rel', 'emp_id', 'product_id', string="Skill/Category", related="employee_id.product_ids", store=True)
    branch_id = fields.Many2one('res.branch', string="Branch", related="employee_id.branch_id", store=True)
    company_id = fields.Many2one('res.company', related="employee_id.company_id")
    #Partner
    
    customer_id = fields.Many2one('res.partner', string="Customer", related="task_id.partner_id", store=True)
    emp_id = fields.Many2one('hr.employee', string="Supervisor", related="task_id.emp_id", store=True)

    sale_order_id = fields.Many2one('sale.order', string="Sale Order", compute='task_sale_and_partner_location', store=True)
    partner_location_id = fields.Many2one('contact.location', string="Customer Location",compute='task_sale_and_partner_location', store=True)

    @api.depends('task_id')
    def task_sale_and_partner_location(self):
        for rec in self:
            if rec.task_id:
                if rec.task_id.sale_order_id:
                    rec.sale_order_id = rec.task_id.sale_order_id.id
                if rec.task_id.partner_location_id:
                    rec.partner_location_id = rec.task_id.partner_location_id.id
