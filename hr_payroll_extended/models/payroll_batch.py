from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict


class HrPayslip(models.Model):
    _name = 'payroll.batch'
    _rec_name= "payroll_batch"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    payroll_batch = fields.Char()

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    payroll_batch_id = fields.Many2one('payroll.batch', string="Payroll Batch")
    notice_id = fields.Many2one('notice.period', string="Notice Period",tracking=True)
    per_based_on = fields.Selection([('basic', 'BASIC'), ('gross', 'GROSS'), ('net', 'NET')],tracking=True, string="Leave Settlement Based On", default="basic")

    def get_passport_data(self):
        doc_line = self.env['hr.document.line'].search([('document_line_id.is_passport', '=', True), ('employee_id', '=', self.id)], limit=1)
        return {
            'passport_no': doc_line and doc_line.document_number or '',
            'exp_date': doc_line and doc_line.valid_to and doc_line.valid_to.strftime('%m/%d/%Y') or ''
        }


class HrPayslip(models.Model):
    _name = 'notice.period'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    days = fields.Float('Days', default=0.0)

class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    payroll_batch_id = fields.Many2one('payroll.batch', string="Payroll Batch")
    name = fields.Char(required=False, readonly=True, states={'draft': [('readonly', False)]})

    @api.onchange('payroll_batch_id')
    def _get_payroll_batch_id(self):
        if self.payroll_batch_id:
            self.name = self.payroll_batch_id.payroll_batch

class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    payroll_batch_id = fields.Many2one('payroll.batch', string="Payroll Batch", readonly=True)
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees', 
        default=None, required=True, compute=False, store=True, readonly=False)

    def _filter_contracts(self, contracts):
        contracts = super(HrPayslipEmployees, self)._filter_contracts(contracts)
        # Could be overriden to avoid having 2 'end of the year bonus' payslips, etc.
        for contract in contracts:
            if not self.structure_id and not contract.structure_type_id.default_struct_id.id:
                raise ValidationError(_('You need to set default structure on contract . (Contract Name: %s)', contract.name))
        return contracts

    def default_get(self, fields):
        vals = super(HrPayslipEmployees, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        payslips = self.env[active_model].browse(self.env.context.get('active_id'))
        vals['payroll_batch_id'] = payslips.payroll_batch_id.id
        employee_ids =  self.env['hr.employee'].search([('payroll_batch_id', '=', payslips.payroll_batch_id.id)])
        vals['employee_ids'] = [(6, 0, employee_ids.ids)]
        return vals

    def compute_sheet(self):
        #Override Compute sheet
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            today = fields.date.today()
            first_day = today + relativedelta(day=1)
            last_day = today + relativedelta(day=31)
            if from_date == first_day and end_date == last_day:
                batch_name = from_date.strftime('%B %Y')
            else:
                batch_name = _('From %s to %s', format_date(self.env, from_date), format_date(self.env, end_date))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': batch_name,
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        employees = self.with_context(active_test=False).employee_ids
        if not employees:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        #Prevent a payslip_run from having multiple payslips for the same employee
        employees -= payslip_run.slip_ids.employee_id
        success_result = {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }
        if not employees:
            return success_result

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']

        contracts = employees._get_contracts(payslip_run.date_start, payslip_run.date_end, states=['open', 'close']).filtered(lambda c: c.active)
        contracts._generate_work_entries(payslip_run.date_start, payslip_run.date_end)
        work_entries = self.env['hr.work.entry'].search([
            ('date_start', '<=', payslip_run.date_end),
            ('date_stop', '>=', payslip_run.date_start),
            ('employee_id', 'in', employees.ids),
        ])
        self._check_undefined_slots(work_entries, payslip_run)

        if(self.structure_id.type_id.default_struct_id == self.structure_id):
            work_entries = work_entries.filtered(lambda work_entry: work_entry.state != 'validated')
            if work_entries._check_if_error():
                work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])

                for work_entry in work_entries.filtered(lambda w: w.state == 'conflict'):
                    work_entries_by_contract[work_entry.contract_id] |= work_entry

                for contract, work_entries in work_entries_by_contract.items():
                    conflicts = work_entries._to_intervals()
                    time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in conflicts._items]])
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Some work entries could not be validated.'),
                        'message': _('Time intervals to look for:%s', time_intervals_str),
                        'sticky': False,
                    }
                }

        default_values = Payslip.default_get(Payslip.fields_get())
        payslips_vals = []
        for contract in self._filter_contracts(contracts):
            values = dict(default_values, **{
                'name': _('New Payslip'),
                'employee_id': contract.employee_id.id,
                'credit_note': payslip_run.credit_note,
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'contract_id': contract.id,
                'branch_id': contract.employee_id.branch_id.id,
                'struct_id': self.structure_id.id or contract.structure_type_id.default_struct_id.id,
            })
            payslips_vals.append(values)
        payslips = Payslip.with_context(tracking_disable=True).create(payslips_vals)
        payslips._compute_name()
        payslips.compute_sheet()
        payslip_run.state = 'verify'
        return success_result
