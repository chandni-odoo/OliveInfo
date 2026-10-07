# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrWorkEntryRegenerationWizard(models.TransientModel):
    _inherit = 'hr.work.entry.regeneration.wizard'
    _description = 'Regenerate Employee Work Entries'

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_hr_work_entry_regeneration_wizard_rel', string='Employees')
    employee_id = fields.Many2one('hr.employee', 'Employee', required=False)
    
    def get_filter_work_entry(self, employee_ids):
        search_domain = [('employee_id', 'in', employee_ids.ids),('state', '!=', 'validated')]
        work_entry_ids = self.env['hr.work.entry'].search(search_domain, order="date_start")
        return work_entry_ids

    @api.depends('employee_id', 'employee_ids')
    def _compute_earliest_available_date(self):
        for wizard in self:
            fil_employee_ids = wizard.employee_ids | wizard.employee_id
            fil_hr_work_entry_ids = self.get_filter_work_entry(fil_employee_ids)
            employee_ids = fil_employee_ids - fil_hr_work_entry_ids.mapped('employee_id')
            dates = employee_ids.mapped('contract_ids.date_generated_from')
            wizard.earliest_available_date = min(dates) if dates else None

    @api.depends('employee_id', 'employee_ids')
    def _compute_latest_available_date(self):
        for wizard in self:
            fil_employee_ids = wizard.employee_ids | wizard.employee_id
            fil_hr_work_entry_ids = self.get_filter_work_entry(fil_employee_ids)
            employee_ids = fil_employee_ids - fil_hr_work_entry_ids.mapped('employee_id')
            dates = employee_ids.mapped('contract_ids.date_generated_to')
            wizard.latest_available_date = max(dates) if dates else None

    @api.depends('date_from', 'date_to', 'employee_id', 'employee_ids')
    def _compute_validated_work_entry_ids(self):
        for wizard in self:
            validated_work_entry_ids = self.env['hr.work.entry']
            if wizard.search_criteria_completed:
                fil_employees = wizard.employee_ids | wizard.employee_id 
                fil_hr_work_entry_ids = self.get_filter_work_entry(fil_employees)
                employees = fil_employees - fil_hr_work_entry_ids.mapped('employee_id')
                search_domain = [
                                ('employee_id', 'in', employees.ids),
                                ('date_start', '>=', self.date_from),
                                ('date_stop', '<=', self.date_to),
                                ('state', '=', 'validated')]
                validated_work_entry_ids = self.env['hr.work.entry'].search(search_domain, order="date_start")
            wizard.validated_work_entry_ids = validated_work_entry_ids


    @api.depends('validated_work_entry_ids')
    def _compute_valid(self):
        for wizard in self:
            wizard.valid = wizard.search_criteria_completed and len(wizard.validated_work_entry_ids) == 0

    @api.depends('date_from', 'date_to', 'employee_id', 'employee_ids')
    def _compute_search_criteria_completed(self):
        for wizard in self:
            fil_employees =  wizard.employee_ids | wizard.employee_id
            fil_hr_work_entry_ids = self.get_filter_work_entry(fil_employees)
            employees  = fil_employees - fil_hr_work_entry_ids.mapped('employee_id')
            wizard.search_criteria_completed = wizard.date_from and wizard.date_to and employees and wizard.earliest_available_date and wizard.latest_available_date

    @api.onchange('date_from', 'date_to', 'employee_id', 'employee_ids')
    def _check_dates(self):
        for wizard in self:
            wizard.earliest_available_date_message = ''
            wizard.latest_available_date_message = ''
            if wizard.search_criteria_completed:
                if wizard.date_from > wizard.date_to:
                    date_from = wizard.date_from
                    wizard.date_from = wizard.date_to
                    wizard.date_to = date_from
                if wizard.earliest_available_date and wizard.date_from < wizard.earliest_available_date:
                    wizard.date_from = wizard.earliest_available_date
                    wizard.earliest_available_date_message = 'The earliest available date is {date}' \
                        .format(date=self._date_to_string(wizard.earliest_available_date))
                if wizard.latest_available_date and wizard.date_to > wizard.latest_available_date:
                    wizard.date_to = wizard.latest_available_date
                    wizard.latest_available_date_message = 'The latest available date is {date}' \
                        .format(date=self._date_to_string(wizard.latest_available_date))


    def regenerate_work_entries(self):
        self.ensure_one()
        if not self.env.context.get('work_entry_skip_validation'):
            if not self.valid:
                raise ValidationError(_("In order to regenerate the work entries, you need to provide the wizard with an employee_id, a date_from and a date_to. In addition to that, the time interval defined by date_from and date_to must not contain any validated work entries."))

            if self.date_from < self.earliest_available_date or self.date_to > self.latest_available_date:
                raise ValidationError(_("The from date must be >= '%(earliest_available_date)s' and the to date must be <= '%(latest_available_date)s', which correspond to the generated work entries time interval.", earliest_available_date=self._date_to_string(self.earliest_available_date), latest_available_date=self._date_to_string(self.latest_available_date)))

        date_from = max(self.date_from, self.earliest_available_date) if self.earliest_available_date else self.date_from
        date_to = min(self.date_to, self.latest_available_date) if self.latest_available_date else self.date_to
        fil_employee_ids = self.employee_ids | self.employee_id 
        fil_hr_work_entry_ids = self.get_filter_work_entry(fil_employee_ids)
        employees = fil_employee_ids - fil_hr_work_entry_ids.mapped('employee_id')
        for employee_id in employees:
            work_entries = self.env['hr.work.entry'].search([
                ('employee_id', '=', employee_id.id),
                ('date_stop', '>=', date_from),
                ('date_start', '<=', date_to),
                ('state', '!=', 'validated')])

            work_entries.write({'active': False})
            employee_id.generate_work_entries(date_from, date_to, True)
        action = self.env["ir.actions.actions"]._for_xml_id('hr_work_entry.hr_work_entry_action')
        return action