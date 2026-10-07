from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta

class ShiftType(models.Model):
    _name = "shift.type"
    _description = "shift.type"

    name = fields.Char(required=True)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    shift_id = fields.Many2one("hr.shift", compute='_compute_shift_id', search='_search_shift_id', store=True)
    dayofweek_ids = fields.One2many('hr.day.of.week', 'employee_id', string="Days Of Weeks")

    def _compute_shift_id(self):
        today = date.today()
        for emp in self:
            allocation_id = self.env['shift.allocation'].search([
                ('employee_id', '=', emp.id),
                ('date_from','<=', today), ('date_to', '>=', today),
                ('state', '=', 'in_progress'),
            ], limit=1) 
            emp.shift_id = allocation_id and allocation_id.shift_id.id or False

    def _search_shift_id(self, operator, value):
        today = date.today()
        domain = [('date_from','<=', today), ('date_to', '>=', today)]
        if operator in ('ilike', 'not ilike'):
            domain.append(('shift_id.name', operator, value))
        if operator in ('=', '!=', 'in', 'not in'):
            domain.append(('shift_id', operator, value))

        allocation_ids = self.env['shift.allocation'].search(domain)
        set_employee = allocation_ids.mapped('employee_id')
        not_set_employee = self.env['hr.employee'].search([('id', 'not in', set_employee.ids)])
        if set_employee and operator in ('!=', '=', 'ilike', 'not ilike', 'in', 'not on'):
            return [('id', 'in', set_employee.ids)]

        if not allocation_ids and not set_employee:
            allocation_ids = self.env['shift.allocation'].search([('date_from','<=', today), ('date_to', '>=', today)])
            set_employee = allocation_ids.mapped('employee_id')
            not_set_employee = self.env['hr.employee'].search([('id', 'not in', set_employee.ids)]) 
            return [('id', 'in', not_set_employee.ids)]
        return []

class ShiftAllocation(models.Model):
    _name = "shift.allocation"
    _description = "Shift Allocation"
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', required=True, index=True, readonly=True, copy=False, default='New')
    date_from = fields.Datetime()
    date_to = fields.Datetime()
    shift_id = fields.Many2one("hr.shift")
    employee_id = fields.Many2one("hr.employee")
    state = fields.Selection([('draft', 'Draft'),('in_progress', 'Done'),('cancel','Cancel')], default='draft')
    description = fields.Text()
    shift_type_id = fields.Many2one('shift.type')
    dayofweek_ids = fields.One2many('hr.day.of.week', 'shift_allocation_id', string="Lines")

    # @chandni ...comment for multi shift task allocation
    # print ("_____________-CHANDNI GLOBALTECKZ")
    # @api.constrains('employee_id','date_from','date_to')
    # def check_validation(self):
    #     # Overlapping Not working
    #     for rec in self:
    #         match_shift = self.env['shift.allocation'].search([
    #             ('id', '!=', rec.id),
    #             ('employee_id', '=', rec.employee_id.id),
    #             ('date_from', '<=', rec.date_from), ('date_to', '>=', rec.date_to)
    #         ])
    #         if match_shift:
    #             raise ValidationError(_('Shift allocation are already defined for these dates'))

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.shift.allocation') or '/'
        return super(ShiftAllocation, self).create(vals)

    def name_get(self):
        res = []
        for rec in self:
            name = rec.name
            if rec.employee_id and rec.shift_id:
                name = "%s - %s" % (rec.employee_id.name, rec.shift_id.name)
            res += [(rec.id, name)]
        return res

    # def button_in_progress(self):
    #     self.write({'state' :'in_progress'})

    def button_in_progress(self):
        for allocation in self:
            # Update all related dayofweek records with the employee_id
            allocation.dayofweek_ids.write({'employee_id': allocation.employee_id.id})
        self.write({'state': 'in_progress'})

    def button_closed(self):
        self.write({'state': 'cancel'})

class HrShift(models.Model):
    _name = 'hr.shift'
    _description = "hr.shift"

    name = fields.Char(required=True)
    shift_type_id = fields.Many2one('shift.type')
    hours_from = fields.Float(string="Hours From")
    hours_to = fields.Float(string="Hours To")
    meal_hours = fields.Float(string="Meal Hours")

    @api.constrains('shift_type_id','hours_from','hours_from')
    def check_validation(self):
        for rec in self:
            shift = self.env['hr.shift'].search([
                ('id', '!=', rec.id),
                ('shift_type_id', '=', rec.shift_type_id.id),
                ('hours_from', '<=', rec.hours_from), ('hours_to', '>=', rec.hours_to)
            ])
            if shift: 
                raise ValidationError(_('Shift allocation are already defined for these house'))

    def name_get(self):
        res = []
        for rec in self:
            name = rec.name
            if rec.hours_from and rec.hours_to:
                name = "%s - %s - %s" % (rec.name, rec.hours_from, rec.hours_to)
            res += [(rec.id, name)]
        return res



class HrShiftDayofWeek(models.Model):
    _name = 'hr.day.of.week'
    _description = "Hr day of weeks"

    employee_id = fields.Many2one('hr.employee', string="Employee")
    date = fields.Date(string="Date of week")
    shift_allocation_id = fields.Many2one('shift.allocation', string="Shift Allocation")
    week_id = fields.Many2one('week.week', string="Day of Week")
    types = fields.Selection([('first_half', 'First Half'), ('second_half', 'Second Half')])
    week_selection_ids = fields.Many2many('week.selection', string="WeekSelection")

    @api.model
    def create(self, vals):
        if 'shift_allocation_id' in vals and not vals.get('employee_id'):
            allocation = self.env['shift.allocation'].browse(vals['shift_allocation_id'])
            if allocation.employee_id:
                vals['employee_id'] = allocation.employee_id.id
        return super(HrShiftDayofWeek, self).create(vals)
    
    @api.constrains('employee_id', 'date')
    def _check_duplicate_employee_date(self):
        for record in self:
            if record.employee_id and record.date:
                existing = self.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('date', '=', record.date),
                    ('id', '!=', record.id)
                ], limit=1)

                if existing:
                    raise ValidationError(_(
                        "Duplicate entry! Employee already has a shift on this date."
                    ))

    # @api.constrains('date')
    # def _check_duplicate_date(self):
    #     for days in self:
    #         date_ids = self.env['hr.day.of.week'].search_count([('date', '=', days.date),('employee_id', '=', days.employee_id.id),('types', '=', days.types)])
    #         if date_ids > 1:
    #             raise ValidationError(("Employee %s has duplicate weekend entry for date %s and type %s .") % (days.employee_id.name, days.date, days.types))

class HrWeek(models.Model):
    _name = "week.week"
    _description = "Hr Weeks"

    name = fields.Char(string="Name")
    code = fields.Char(string="Day No")
    l_code = fields.Char(string="Leave Code")
    types = fields.Selection([('first_half', 'First Half'), ('second_half', 'Second Half')])

class WeekSelection(models.Model):
    _name = 'week.selection'
    _description = "Week Selection"

    name = fields.Char(string="Name")
    code = fields.Char(string="No")
