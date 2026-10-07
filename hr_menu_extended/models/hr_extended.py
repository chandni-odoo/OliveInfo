from odoo import api, fields, models, _
from datetime import date
from datetime import timedelta

class HrInsuranceLine(models.Model):
    _inherit = 'hr.insurance.line'

    employee_job_title = fields.Char(related='employee_id.job_title', string='Job Title', readonly=True, store=True)
    employee_branch = fields.Many2one(related='employee_id.branch_id', string='Branch/Department', readonly=True, store=True)
    employee_manager = fields.Many2one(related='employee_id.parent_id', string='Manager', readonly=True, store=True)
    employee_status = fields.Selection(related='employee_id.emp_status', string='Status', readonly=True)
    days_to_expire = fields.Integer(
        string='Days to Expire',
        compute='_compute_days_to_expire',
        store=True,
    )

    expiry_status = fields.Selection([
        ('expired', 'Expired'),
        ('soon', 'Expiring Soon (1-30 days)'),
        ('medium', 'Expiring in 31-90 Days'),
        ('valid', 'Valid (>90 days)'),
    ], string='Expiry Status', compute='_compute_days_to_expire', store=True)
    
    @api.depends('end_date')
    def _compute_days_to_expire(self):
        today = date.today()
        for record in self:
            if record.end_date:
                delta = record.end_date - today
                record.days_to_expire = delta.days
                
                if delta.days < 0:
                    record.expiry_status = 'expired'
                elif delta.days <= 30:
                    record.expiry_status = 'soon'
                elif delta.days <= 90:
                    record.expiry_status = 'medium'
                else:
                    record.expiry_status = 'valid'
            else:
                record.days_to_expire = 0
                record.expiry_status = 'expired'
    

class HrTraining(models.Model):
    _inherit = 'hr.training'

    employee_job_title = fields.Char(related='employee_id.job_title', string='Job Title', readonly=True, store=True)
    employee_branch = fields.Many2one(related='employee_id.branch_id', string='Branch/Department', readonly=True, store=True)
    employee_manager = fields.Many2one(related='employee_id.parent_id', string='Manager', readonly=True, store=True)
    employee_status = fields.Selection(related='employee_id.emp_status', string='Status', readonly=True)
    days_to_expire = fields.Integer(
        string='Days to Expire',
        compute='_compute_days_to_expire',
        store=True,
    )
    expiry_status = fields.Selection([
        ('expired', 'Expired'),
        ('soon', 'Expiring Soon (1-30 days)'),
        ('medium', 'Expiring in 31-90 Days'),
        ('valid', 'Valid (>90 days)'),
    ], string='Expiry Status', compute='_compute_days_to_expire', store=True)
    
    @api.depends('validity_date')
    def _compute_days_to_expire(self):
        today = date.today()
        for record in self:
            if record.validity_date:
                delta = record.validity_date - today
                record.days_to_expire = delta.days
                if delta.days < 0:
                    record.expiry_status = 'expired'
                elif delta.days <= 30:
                    record.expiry_status = 'soon'
                elif delta.days <= 90:
                    record.expiry_status = 'medium'
                else:
                    record.expiry_status = 'valid'
            else:
                record.days_to_expire = 0
                record.expiry_status = 'expired'

class DisciplinaryActionLine(models.Model):
    _inherit = 'disciplinary.action.line'

    employee_id = fields.Many2one('hr.employee')
    employee_job_title = fields.Char(related='employee_id.job_title', string='Job Title', readonly=True, store=True)
    employee_branch = fields.Many2one(related='employee_id.branch_id', string='Branch/Department', readonly=True, store=True)
    employee_manager = fields.Many2one(related='employee_id.parent_id', string='Manager', readonly=True, store=True)
    employee_status = fields.Selection(related='employee_id.emp_status', string='Status', readonly=True)
                

class HrTraining(models.Model):
    _inherit = 'hr.certification'

    employee_job_title = fields.Char(related='employee_id.job_title', string='Job Title', readonly=True, store=True)
    employee_branch = fields.Many2one(related='employee_id.branch_id', string='Branch/Department', readonly=True, store=True)
    employee_manager = fields.Many2one(related='employee_id.parent_id', string='Manager', readonly=True, store=True)
    employee_status = fields.Selection(related='employee_id.emp_status', string='Status', readonly=True)
    days_to_expire = fields.Integer(
        string='Days to Expire',
        compute='_compute_days_to_expire',
        store=True,
    )

    expiry_status = fields.Selection([
        ('expired', 'Expired'),
        ('soon', 'Expiring Soon (1-30 days)'),
        ('medium', 'Expiring in 31-90 Days'),
        ('valid', 'Valid (>90 days)'),
    ], string='Expiry Status', compute='_compute_days_to_expire', store=True)

    @api.depends('validity_date')
    def _compute_days_to_expire(self):
        today = date.today()
        for record in self:
            if record.validity_date:
                delta = record.validity_date - today
                record.days_to_expire = delta.days
                if delta.days < 0:
                    record.expiry_status = 'expired'
                elif delta.days <= 30:
                    record.expiry_status = 'soon'
                elif delta.days <= 90:
                    record.expiry_status = 'medium'
                else:
                    record.expiry_status = 'valid'
            else:
                record.days_to_expire = 0
                record.expiry_status = 'expired'

class HolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    employee_job_title = fields.Char(related='employee_id.job_title', string='Job Title', readonly=True, store=True)
    employee_branch = fields.Many2one(related='employee_id.branch_id', string='Branch/Department', readonly=True, store=True)
    employee_status = fields.Selection(related='employee_id.emp_status', string='Status', readonly=True)
    employee_joining_date = fields.Date(related='employee_id.original_hire_date', string='Joining Date', readonly=True)


    leaves_taken = fields.Float(
        string="Leave Availed",
        compute='_compute_leaves_taken',
        store=True
    )
    
    remaining_leaves = fields.Float(
        string="Accrued Balance",
        compute='_compute_remaining_leaves',
        store=True
    )
    
    @api.depends('employee_id', 'holiday_status_id')
    def _compute_remaining_leaves(self):
        for allocation in self:
            if allocation.employee_id and allocation.holiday_status_id:
                leaves = allocation.holiday_status_id.get_employees_days([allocation.employee_id.id])[allocation.employee_id.id]
                allocation.remaining_leaves = leaves[allocation.holiday_status_id.id]['remaining_leaves']
            else:
                allocation.remaining_leaves = 0
    
    @api.depends('number_of_days', 'remaining_leaves')
    def _compute_leaves_taken(self):
        for allocation in self:
            allocation.leaves_taken = allocation.number_of_days - allocation.remaining_leaves


class ProjectTask(models.Model):
    _inherit = 'project.task'
    
    last_planned_date = fields.Date(
        string='Last Planned Date',
        compute='_compute_last_planned_date',
        store=True,
        help='Latest end date from related shift schedules'
    )
    
    @api.depends('schedule_id.end_date')
    def _compute_last_planned_date(self):
        for task in self:
            if task.schedule_id and task.schedule_id.end_date:
                task.last_planned_date = task.schedule_id.end_date
            else:
                schedules = self.env['shift.schedule'].search([
                    ('task_id', '=', task.id)
                ], order='end_date desc', limit=1)
                task.last_planned_date = schedules.end_date if schedules else False
        

class ShiftSchedule(models.Model):
    _inherit = 'shift.schedule'
    
    task_id = fields.Many2one(
        'project.task',
        string='Project Task',
        help='Related project task'
    )
    
    @api.model
    def create(self, vals):
        schedule = super(ShiftSchedule, self).create(vals)
        
        if schedule.task_id:
            schedule.task_id.schedule_id = schedule.id
            
        return schedule
    
    def write(self, vals):
        result = super(ShiftSchedule, self).write(vals)
        
        if 'end_date' in vals:
            for schedule in self:
                if schedule.task_id:
                    schedule.task_id._compute_last_planned_date()
                    
        return result
    
