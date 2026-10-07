from odoo.exceptions import UserError
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.tools import date_utils
from odoo.tools import format_date


class AccruedRevenueWizard(models.TransientModel):
    _name = 'accrued.revenue.wizard'
    _description = 'Accrued Revenue Entry Generation Details'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    journal_id = fields.Many2one(
        'account.journal', 
        string='Journal', 
        required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        default=lambda self: self.env['account.journal'].search([
            ('company_id', '=', self.env.company.id),
            ('type', '=', 'general')
        ], limit=1)
    )
    date = fields.Date(
        string='Date', 
        required=True, 
        default=lambda self: date_utils.get_month(fields.Date.context_today(self))[0] - relativedelta(days=1)
    )
    reversal_date = fields.Date(
        string='Reversal Date', 
        required=True,
        compute="_compute_reversal_date",
        readonly=False,
    )
    accrual_account_id = fields.Many2one(
        'account.account', 
        string='Accrual Account', 
        required=True,
        domain="[('user_type_id', '=', %(account.data_account_type_current_assets)d), ('company_id', '=', company_id)]"
    )
    
    sale_ids = fields.Many2many('sale.order', string='Sale Orders', required=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True)
    line_ids = fields.One2many('accrued.revenue.wizard.line', 'wizard_id', string='Lines')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
    debit_amount = fields.Float(string='Debit Amount', compute='_compute_total_amount', store=True)
    
    @api.depends('line_ids.credit_value', 'line_ids.final_credit_value')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(line.credit_value for line in record.line_ids if not line.is_debit_line)
            record.debit_amount = record.total_amount
    
    @api.depends('date')
    def _compute_reversal_date(self):
        for record in self:
            if not record.reversal_date or record.reversal_date <= record.date:
                record.reversal_date = record.date + relativedelta(days=1)
    
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        for record in self:
            if record.journal_id and record.journal_id.default_account_id:
                record.accrual_account_id = record.journal_id.default_account_id
    
    @api.onchange('sale_ids')
    def _onchange_sale_ids(self):
        self.ensure_one()
        if self.sale_ids:
            if not self.branch_id and self.sale_ids[0].branch_id:
                self.branch_id = self.sale_ids[0].branch_id
            self._update_wizard_lines()
    
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.branch_id and self.sale_ids:
            self.sale_ids = self.sale_ids.filtered(lambda so: so.branch_id == self.branch_id)
            self._update_wizard_lines()
    
    def _update_wizard_lines(self):
        self.ensure_one()
        if not self.sale_ids:
            self.line_ids = False
            return
            
        tasks = self.env['project.task'].search([
            ('sale_line_id', 'in', self.sale_ids.mapped('order_line').ids),
            ('branch_id', '=', self.branch_id.id)
        ])
        
        line_vals = []
        for task in tasks:
            sale_line = task.sale_line_id
            task_account_id = False
            
            if sale_line and sale_line.product_id and sale_line.product_id.property_account_income_id:
                task_account_id = sale_line.product_id.property_account_income_id.id
            elif sale_line and sale_line.product_id and sale_line.product_id.categ_id.property_account_income_categ_id:
                task_account_id = sale_line.product_id.categ_id.property_account_income_categ_id.id
            
            line_vals.append((0, 0, {
                'task_id': task.id,
                'account_id': task_account_id,
                'label': f"Accrued Revenue entry as of {fields.Date.today()}",
                'is_debit_line': False,
            }))
        
        self.line_ids = False  
        self.line_ids = line_vals  
    
    @api.model
    def default_get(self, fields_list):
        res = super(AccruedRevenueWizard, self).default_get(fields_list)
        
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids', [])
        
        if active_model == 'sale.order' and active_ids:
            sale_orders = self.env['sale.order'].browse(active_ids)
            res['sale_ids'] = [(6, 0, sale_orders.ids)]
            
            branches = sale_orders.mapped('branch_id')
            if len(branches) == 1:
                res['branch_id'] = branches.id
            
            tasks = self.env['project.task'].search([
                ('sale_line_id', 'in', sale_orders.mapped('order_line').ids),
                ('branch_id', 'in', branches.ids)
            ])
            
            line_vals = []
            for task in tasks:
                sale_line = task.sale_line_id
                task_account_id = False
                
                if sale_line and sale_line.product_id and sale_line.product_id.property_account_income_id:
                    task_account_id = sale_line.product_id.property_account_income_id.id
                elif sale_line and sale_line.product_id and sale_line.product_id.categ_id.property_account_income_categ_id:
                    task_account_id = sale_line.product_id.categ_id.property_account_income_categ_id.id
                
                line_vals.append((0, 0, {
                    'task_id': task.id,
                    'account_id': task_account_id,
                    'label': f"Accrued Revenue entry as of {fields.Date.today()}",
                    'is_debit_line': False,
                }))
            
            res['line_ids'] = line_vals
        
        journals = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', self.env.company.id)], limit=1)
        if journals:
            res['journal_id'] = journals[0].id
            
            if journals[0].default_account_id:
                res['accrual_account_id'] = journals[0].default_account_id.id
            else:
                accrual_accounts = self.env['account.account'].search([
                    ('name', 'ilike', 'accrued revenue'),
                    ('user_type_id', '=', self.env.ref('account.data_account_type_current_assets').id),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
                
                if not accrual_accounts:
                    accrual_accounts = self.env['account.account'].search([
                        ('name', 'ilike', 'outstanding revenue'),
                        ('user_type_id', '=', self.env.ref('account.data_account_type_current_assets').id),
                        ('company_id', '=', self.env.company.id)
                    ], limit=1)
                
                if accrual_accounts:
                    res['accrual_account_id'] = accrual_accounts[0].id
        
        return res
        
    @api.onchange('accrual_account_id', 'line_ids', 'line_ids.credit_value')
    def _onchange_update_debit_line(self):
        for wizard in self:
            if not wizard.accrual_account_id:
                continue
                
            total_credit = sum(line.credit_value for line in wizard.line_ids if not line.is_debit_line)
            
            for line in wizard.line_ids:
                if not line.is_debit_line:
                    line.final_credit_value = line.credit_value
            
            debit_line = wizard.line_ids.filtered(lambda l: l.is_debit_line)
            
            if total_credit > 0:
                if debit_line:
                    debit_line.debit_value = total_credit
                    debit_line.account_id = wizard.accrual_account_id
                    debit_line.label = f"Accrued Revenue Total as of {wizard.date}"
                else:
                    wizard.line_ids = [(0, 0, {
                        'is_debit_line': True,
                        'account_id': wizard.accrual_account_id.id,
                        'label': f"Accrued Revenue Total as of {wizard.date}",
                        'debit_value': total_credit,
                    })]
            elif debit_line:
                wizard.line_ids = [(2, debit_line.id, 0)]
    
    @api.onchange('date')
    def _onchange_date(self):
        for line in self.line_ids:
            if not line.is_debit_line:
                line.label = f"Accrued Revenue entry as of {self.date}"
            else:
                line.label = f"Accrued Revenue Total as of {self.date}"
            line._compute_unbilled_value()
            if not line.is_debit_line:
                line.final_credit_value = line.credit_value
        self._onchange_update_debit_line()
    
    def action_create_entry(self):
        self.ensure_one()
        
        for line in self.line_ids:
            if not line.is_debit_line:
                line.final_credit_value = line.credit_value
        
        total_credit = sum(line.final_credit_value for line in self.line_ids if not line.is_debit_line and line.final_credit_value > 0)
        
        if total_credit <= 0:
            raise UserError(_("No valid amounts to create journal entry. Please check your accrual values."))
            
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': f'Accrued Revenue entry as of {self.date} for {self.branch_id.name}',
            'branch_id': self.branch_id.id, 
            'line_ids': [],
        }
        
        for line in self.line_ids:
            if not line.is_debit_line and line.final_credit_value > 0:
                move_vals['line_ids'].append((0, 0, {
                    'name': line.label,
                    'account_id': line.account_id.id,
                    'debit': 0.0,
                    'credit': line.final_credit_value,
                    'analytic_account_id': line.task_id.project_id.analytic_account_id.id if line.task_id and line.task_id.project_id.analytic_account_id else False,
                    'branch_id': self.branch_id.id, 
                }))
        
        move_vals['line_ids'].append((0, 0, {
            'name': f"Accrued Revenue Total as of {self.date} for {self.branch_id.name}",
            'account_id': self.accrual_account_id.id,
            'debit': total_credit,
            'credit': 0.0,
            'analytic_account_id': False,
            'branch_id': self.branch_id.id,  
        }))
        
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()  
        
        if self.reversal_date:
            reversal = move._reverse_moves(
                default_values_list=[{
                    'date': self.reversal_date,
                    'ref': f'Reversal of: {move.name}',
                    'branch_id': self.branch_id.id,  
                }],
                cancel=False,
            )
           
            reversal.action_post()
        
        return {
            'name': 'Journal Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form,tree',
            'res_id': move.id,
            'target': 'current',
            'context': {'create': False},
        }


class AccruedRevenueWizardLine(models.TransientModel):
    _name = 'accrued.revenue.wizard.line'
    _description = 'Accrued Revenue Wizard Line'
    
    wizard_id = fields.Many2one('accrued.revenue.wizard', string='Wizard')
    task_id = fields.Many2one('project.task', string='Task')
    account_id = fields.Many2one(
        'account.account', 
        string='Account',
        domain="[('user_type_id', '=', %(account.data_account_type_current_assets)d), ('company_id', '=', context.get('company_id', parent.company_id))]"
    )
    label = fields.Char(string='Label', required=True)
    credit_value = fields.Float(string='Credit', compute='_compute_unbilled_value', store=True, readonly=False)
    final_credit_value = fields.Float(string='Final Credit', store=True)
    debit_value = fields.Float(string='Debit', default=0.0)

    is_debit_line = fields.Boolean(string='Is Debit Line', default=False)
    line_type = fields.Selection(
        [('credit', 'Credit'), ('debit', 'Debit')],
        string='Type',
        compute='_compute_line_type',
        store=True
    )
    
    @api.depends('is_debit_line')
    def _compute_line_type(self):
        for line in self:
            line.line_type = 'debit' if line.is_debit_line else 'credit'
    
    @api.onchange('task_id')
    def _onchange_task_id(self):
        for line in self:
            if line.task_id and line.task_id.sale_line_id:
                sale_line = line.task_id.sale_line_id
                if sale_line.product_id and sale_line.product_id.property_account_income_id:
                    line.account_id = sale_line.product_id.property_account_income_id
                elif sale_line.product_id and sale_line.product_id.categ_id.property_account_income_categ_id:
                    line.account_id = sale_line.product_id.categ_id.property_account_income_categ_id
    
    @api.depends('task_id', 'wizard_id.date')
    def _compute_unbilled_value(self):
        for line in self:
            if line.is_debit_line:
                continue
                
            task = line.task_id
            end_date = line.wizard_id.date if line.wizard_id else fields.Date.today()
            
            if not task or not task.last_invoice_date:
                line.credit_value = 0.0
                line.final_credit_value = 0.0
                continue
                
            if task.branch_for == 'es':
                # ES Branch Calculation
                valid_trips = task.trip_sheet_ids.filtered(
                    lambda t: t.date_from and 
                    fields.Datetime.to_datetime(t.date_from).date() > task.last_invoice_date and
                    fields.Datetime.to_datetime(t.date_from).date() <= end_date and
                    not t.non_billable
                )
                
                billable_amount = sum(trip.billable_qty * task.unit_price for trip in valid_trips)
                equipment_amount = sum(trip.equipment_qty * task.additional_rate for trip in valid_trips)
                line.credit_value = billable_amount + equipment_amount

            elif task.branch_for == 'hro':
                excluded_uoms = ['month', 'months', 'lumpsum', 'week', 'weeks', 'day', 'days']
                if task.task_uom and task.task_uom.name.lower() not in [u.lower() for u in excluded_uoms]:
                    regular_timesheets = task.timesheet_ids.filtered(
                        lambda t: t.date and 
                        fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(t.date).date() <= end_date
                    )
                    regular_hrs_amount = sum(t.unit_amount * task.unit_price for t in regular_timesheets)

                    normal_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
                        o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                    )
                    normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

                    special_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
                        o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                    )
                    special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)

                    line.credit_value = regular_hrs_amount + normal_ot_amount + special_ot_amount

                elif task.task_uom and task.task_uom.name.lower() in ['week', 'weeks']:
                    valid_timesheets = task.timesheet_ids.filtered(
                        lambda t: t.date and 
                        fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(t.date).date() <= end_date
                    )
                    
                    if not valid_timesheets:
                        line.credit_value = 0.0
                        continue
                        
                    max_date = min(end_date, max(valid_timesheets.mapped(lambda t: fields.Datetime.to_datetime(t.date).date())))

                    days_diff = (max_date - task.last_invoice_date).days
                    week_diff = days_diff / 7
                    
                    unbilled_period_amount = week_diff * task.unit_price
                    
                    agency_fee_amount = 0.0
                    if task.agency_fee == 'fix' and task.amount:
                        agency_fee_amount = task.amount * week_diff
                    elif task.agency_fee == 'percentage' and task.amount:
                        agency_fee_amount = (task.unit_price * task.amount / 100) * week_diff
                    
                    normal_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
                        o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                    )
                    normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

                    special_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
                        o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                    )
                    special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)
                    
                    line.credit_value = unbilled_period_amount + agency_fee_amount + normal_ot_amount + special_ot_amount

                elif task.task_uom and task.task_uom.name.lower() in ['day', 'days']:
                    valid_days = task.timesheet_ids.filtered(
                        lambda t: t.date and 
                        fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(t.date).date() <= end_date and
                        t.unit_amount > 0
                    ).mapped('date')
                    
                    day_count = len(set(valid_days))
                    regular_hrs_amount = day_count * task.unit_price

                    normal_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
                        o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                    )
                    normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

                    special_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
                        o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                    )
                    special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)

                    line.credit_value = regular_hrs_amount + normal_ot_amount + special_ot_amount

                else:
                    valid_timesheets = task.timesheet_ids.filtered(
                        lambda t: t.date and 
                        fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(t.date).date() <= end_date
                    )
                    
                    if not valid_timesheets:
                        line.credit_value = 0.0
                        continue
                        
                    max_date = min(end_date, max(valid_timesheets.mapped(lambda t: fields.Datetime.to_datetime(t.date).date())))

                    month_diff = (max_date.year - task.last_invoice_date.year) * 12 + (max_date.month - task.last_invoice_date.month)
                    
                    unbilled_month_amount = month_diff * task.unit_price
                    
                    agency_fee_amount = 0.0
                    if task.agency_fee == 'fix' and task.amount:
                        agency_fee_amount = task.amount * month_diff
                    elif task.agency_fee == 'percentage' and task.amount:
                        agency_fee_amount = (task.unit_price * task.amount / 100) * month_diff
                    
                    normal_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
                        o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
                    )
                    normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

                    special_ot_records = task.overtime_lines_ids.filtered(
                        lambda o: o.ot_date and 
                        fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
                        fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
                        o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
                    )
                    special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)
                    
                    line.credit_value = unbilled_month_amount + agency_fee_amount + normal_ot_amount + special_ot_amount
            else:
                line.credit_value = (task.delivered - task.invoiced) * task.unit_price if task.delivered > task.invoiced else 0.0




# class AccruedRevenueWizard(models.TransientModel):
#     _name = 'accrued.revenue.wizard'
#     _description = 'Accrued Revenue Entry Generation Details'

#     company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
#     journal_id = fields.Many2one(
#         'account.journal', 
#         string='Journal', 
#         required=True,
#         domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
#         default=lambda self: self.env['account.journal'].search([
#             ('company_id', '=', self.env.company.id),
#             ('type', '=', 'general')
#         ], limit=1)
#     )
#     date = fields.Date(
#         string='Date', 
#         required=True, 
#         default=lambda self: date_utils.get_month(fields.Date.context_today(self))[0] - relativedelta(days=1)
#     )
#     reversal_date = fields.Date(
#         string='Reversal Date', 
#         required=True,
#         compute="_compute_reversal_date",
#         readonly=False,
#     )
#     accrual_account_id = fields.Many2one(
#         'account.account', 
#         string='Accrual Account', 
#         required=True,
#         domain="[('user_type_id', '=', %(account.data_account_type_current_assets)d), ('company_id', '=', company_id)]"
#     )
    
#     sale_id = fields.Many2one('sale.order', string='Sale Order')
#     line_ids = fields.One2many('accrued.revenue.wizard.line', 'wizard_id', string='Lines')
#     total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
#     debit_amount = fields.Float(string='Debit Amount', compute='_compute_total_amount', store=True)
    
#     @api.depends('line_ids.credit_value', 'line_ids.final_credit_value')
#     def _compute_total_amount(self):
#         for record in self:
#             record.total_amount = sum(line.credit_value for line in record.line_ids if not line.is_debit_line)
#             record.debit_amount = record.total_amount
    
#     @api.depends('date')
#     def _compute_reversal_date(self):
#         for record in self:
#             if not record.reversal_date or record.reversal_date <= record.date:
#                 record.reversal_date = record.date + relativedelta(days=1)
    
#     @api.onchange('journal_id')
#     def _onchange_journal_id(self):
#         for record in self:
#             if record.journal_id and record.journal_id.default_account_id:
#                 record.accrual_account_id = record.journal_id.default_account_id
    
#     @api.model
#     def default_get(self, fields_list):
#         res = super(AccruedRevenueWizard, self).default_get(fields_list)
        
#         active_model = self.env.context.get('active_model')
#         active_ids = self.env.context.get('active_ids', [])
        
#         if active_model == 'sale.order' and active_ids and len(active_ids) == 1:
#             sale_order = self.env['sale.order'].browse(active_ids[0])
#             res['sale_id'] = sale_order.id
            
#             tasks = self.env['project.task'].search([
#                 ('sale_line_id', 'in', sale_order.order_line.ids)
#             ])
            
#             line_vals = []
#             for task in tasks:
#                 sale_line = task.sale_line_id
#                 task_account_id = False
                
#                 if sale_line and sale_line.product_id and sale_line.product_id.property_account_income_id:
#                     task_account_id = sale_line.product_id.property_account_income_id.id
#                 elif sale_line and sale_line.product_id and sale_line.product_id.categ_id.property_account_income_categ_id:
#                     task_account_id = sale_line.product_id.categ_id.property_account_income_categ_id.id
                
#                 line_vals.append((0, 0, {
#                     'task_id': task.id,
#                     'account_id': task_account_id,
#                     'label': f"Accrued Revenue entry as of {fields.Date.today()}",
#                     'is_debit_line': False,
#                 }))
            
#             res['line_ids'] = line_vals
        
#         journals = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', self.env.company.id)], limit=1)
#         if journals:
#             res['journal_id'] = journals[0].id
            
#             if journals[0].default_account_id:
#                 res['accrual_account_id'] = journals[0].default_account_id.id
#             else:
#                 accrual_accounts = self.env['account.account'].search([
#                     ('name', 'ilike', 'accrued revenue'),
#                     ('user_type_id', '=', self.env.ref('account.data_account_type_current_assets').id),
#                     ('company_id', '=', self.env.company.id)
#                 ], limit=1)
                
#                 if not accrual_accounts:
#                     accrual_accounts = self.env['account.account'].search([
#                         ('name', 'ilike', 'outstanding revenue'),
#                         ('user_type_id', '=', self.env.ref('account.data_account_type_current_assets').id),
#                         ('company_id', '=', self.env.company.id)
#                     ], limit=1)
                
#                 if accrual_accounts:
#                     res['accrual_account_id'] = accrual_accounts[0].id
        
#         return res
        
#     @api.onchange('accrual_account_id', 'line_ids', 'line_ids.credit_value')
#     def _onchange_update_debit_line(self):
#         for wizard in self:
#             if not wizard.accrual_account_id:
#                 continue
                
#             # Calculate total credit from non-debit lines
#             total_credit = sum(line.credit_value for line in wizard.line_ids if not line.is_debit_line)
            
#             # Update final_credit_value for each line
#             for line in wizard.line_ids:
#                 if not line.is_debit_line:
#                     line.final_credit_value = line.credit_value
            
#             # Find or create debit line
#             debit_line = wizard.line_ids.filtered(lambda l: l.is_debit_line)
            
#             if total_credit > 0:
#                 if debit_line:
#                     debit_line.debit_value = total_credit
#                     debit_line.account_id = wizard.accrual_account_id
#                     debit_line.label = f"Accrued Revenue Total as of {wizard.date}"
#                 else:
#                     wizard.line_ids = [(0, 0, {
#                         'is_debit_line': True,
#                         'account_id': wizard.accrual_account_id.id,
#                         'label': f"Accrued Revenue Total as of {wizard.date}",
#                         'debit_value': total_credit,
#                     })]
#             elif debit_line:
#                 # Remove debit line if no credit amounts
#                 wizard.line_ids = [(2, debit_line.id, 0)]
    
#     @api.onchange('date')
#     def _onchange_date(self):
#         for line in self.line_ids:
#             if not line.is_debit_line:
#                 line.label = f"Accrued Revenue entry as of {self.date}"
#             else:
#                 line.label = f"Accrued Revenue Total as of {self.date}"
#             line._compute_unbilled_value()
#             # Save the current credit value to final_credit_value
#             if not line.is_debit_line:
#                 line.final_credit_value = line.credit_value
#         self._onchange_update_debit_line()
    
#     def action_create_entry(self):
#         self.ensure_one()
        
#         # Save current credit values to final_credit_value for all lines
#         for line in self.line_ids:
#             if not line.is_debit_line:
#                 line.final_credit_value = line.credit_value
        
#         # Calculate total credit amount using the stored final_credit_value
#         total_credit = sum(line.final_credit_value for line in self.line_ids if not line.is_debit_line and line.final_credit_value > 0)
        
#         # Check if we have amounts to create journal entry
#         if total_credit <= 0:
#             raise UserError(_("No valid amounts to create journal entry. Please check your accrual values."))
            
#         # Create move with proper line_ids
#         move_vals = {
#             'journal_id': self.journal_id.id,
#             'date': self.date,
#             'ref': f'Accrued Revenue entry as of {self.date}',
#             'line_ids': [],
#         }
        
#         # Add credit lines from each task using the saved final_credit_value
#         for line in self.line_ids:
#             if not line.is_debit_line and line.final_credit_value > 0:
#                 move_vals['line_ids'].append((0, 0, {
#                     'name': line.label,
#                     'account_id': line.account_id.id,
#                     'debit': 0.0,
#                     'credit': line.final_credit_value,
#                     'analytic_account_id': line.task_id.project_id.analytic_account_id.id if line.task_id and line.task_id.project_id.analytic_account_id else False,
#                 }))
        
#         # Add debit line for total amount
#         move_vals['line_ids'].append((0, 0, {
#             'name': f"Accrued Revenue Total as of {self.date}",
#             'account_id': self.accrual_account_id.id,
#             'debit': total_credit,
#             'credit': 0.0,
#             'analytic_account_id': False,
#         }))
        
#         # Create the move
#         move = self.env['account.move'].create(move_vals)
#         move.action_post()  # Post the journal entry immediately
        
#         # Create reversal if a reversal date is set
#         if self.reversal_date:
#             reversal = move._reverse_moves(
#                 default_values_list=[{
#                     'date': self.reversal_date,
#                     'ref': f'Reversal of: {move.name}',
#                 }],
#                 cancel=False,
#             )
#             # Post the reversal entry as well
#             reversal.action_post()
        
#         return {
#             'name': 'Journal Entry',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'form,tree',
#             'res_id': move.id,
#             'target': 'current',
#             'context': {'create': False},
#         }


# class AccruedRevenueWizardLine(models.TransientModel):
#     _name = 'accrued.revenue.wizard.line'
#     _description = 'Accrued Revenue Wizard Line'
    
#     wizard_id = fields.Many2one('accrued.revenue.wizard', string='Wizard')
#     task_id = fields.Many2one('project.task', string='Task')
#     account_id = fields.Many2one(
#         'account.account', 
#         string='Account',
#         domain="[('user_type_id', '=', %(account.data_account_type_current_assets)d), ('company_id', '=', context.get('company_id', parent.company_id))]"
#     )
#     label = fields.Char(string='Label', required=True)
#     credit_value = fields.Float(string='Credit', compute='_compute_unbilled_value', store=True, readonly=False)
#     final_credit_value = fields.Float(string='Final Credit', store=True)
#     debit_value = fields.Float(string='Debit', default=0.0)

#     is_debit_line = fields.Boolean(string='Is Debit Line', default=False)
#     line_type = fields.Selection(
#         [('credit', 'Credit'), ('debit', 'Debit')],
#         string='Type',
#         compute='_compute_line_type',
#         store=True
#     )
    
#     @api.depends('is_debit_line')
#     def _compute_line_type(self):
#         for line in self:
#             line.line_type = 'debit' if line.is_debit_line else 'credit'
    
#     @api.onchange('task_id')
#     def _onchange_task_id(self):
#         for line in self:
#             if line.task_id and line.task_id.sale_line_id:
#                 sale_line = line.task_id.sale_line_id
#                 if sale_line.product_id and sale_line.product_id.property_account_income_id:
#                     line.account_id = sale_line.product_id.property_account_income_id
#                 elif sale_line.product_id and sale_line.product_id.categ_id.property_account_income_categ_id:
#                     line.account_id = sale_line.product_id.categ_id.property_account_income_categ_id
    
#     @api.depends('task_id', 'wizard_id.date')
#     def _compute_unbilled_value(self):
#         for line in self:
#             if line.is_debit_line:
#                 continue
                
#             task = line.task_id
#             end_date = line.wizard_id.date if line.wizard_id else fields.Date.today()
            
#             if not task or not task.last_invoice_date:
#                 line.credit_value = 0.0
#                 line.final_credit_value = 0.0
#                 continue
                
#             if task.branch_for == 'es':
#                 # ES Branch Calculation
#                 valid_trips = task.trip_sheet_ids.filtered(
#                     lambda t: t.date_from and 
#                     fields.Datetime.to_datetime(t.date_from).date() > task.last_invoice_date and
#                     fields.Datetime.to_datetime(t.date_from).date() <= end_date and
#                     not t.non_billable
#                 )
                
#                 billable_amount = sum(trip.billable_qty * task.unit_price for trip in valid_trips)
#                 equipment_amount = sum(trip.equipment_qty * task.additional_rate for trip in valid_trips)
#                 line.credit_value = billable_amount + equipment_amount

#             elif task.branch_for == 'hro':
#                 excluded_uoms = ['month', 'months', 'lumpsum', 'week', 'weeks', 'day', 'days']
#                 if task.task_uom and task.task_uom.name.lower() not in [u.lower() for u in excluded_uoms]:
#                     regular_timesheets = task.timesheet_ids.filtered(
#                         lambda t: t.date and 
#                         fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(t.date).date() <= end_date
#                     )
#                     regular_hrs_amount = sum(t.unit_amount * task.unit_price for t in regular_timesheets)

#                     normal_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
#                     )
#                     normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

#                     special_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
#                     )
#                     special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)

#                     line.credit_value = regular_hrs_amount + normal_ot_amount + special_ot_amount

#                 elif task.task_uom and task.task_uom.name.lower() in ['week', 'weeks']:
#                     valid_timesheets = task.timesheet_ids.filtered(
#                         lambda t: t.date and 
#                         fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(t.date).date() <= end_date
#                     )
                    
#                     if not valid_timesheets:
#                         line.credit_value = 0.0
#                         continue
                        
#                     max_date = min(end_date, max(valid_timesheets.mapped(lambda t: fields.Datetime.to_datetime(t.date).date())))

#                     days_diff = (max_date - task.last_invoice_date).days
#                     week_diff = days_diff / 7
                    
#                     unbilled_period_amount = week_diff * task.unit_price
                    
#                     agency_fee_amount = 0.0
#                     if task.agency_fee == 'fix' and task.amount:
#                         agency_fee_amount = task.amount * week_diff
#                     elif task.agency_fee == 'percentage' and task.amount:
#                         agency_fee_amount = (task.unit_price * task.amount / 100) * week_diff
                    
#                     normal_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
#                     )
#                     normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

#                     special_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
#                     )
#                     special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)
                    
#                     line.credit_value = unbilled_period_amount + agency_fee_amount + normal_ot_amount + special_ot_amount

#                 elif task.task_uom and task.task_uom.name.lower() in ['day', 'days']:
#                     valid_days = task.timesheet_ids.filtered(
#                         lambda t: t.date and 
#                         fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(t.date).date() <= end_date and
#                         t.unit_amount > 0
#                     ).mapped('date')
                    
#                     day_count = len(set(valid_days))
#                     regular_hrs_amount = day_count * task.unit_price

#                     normal_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
#                     )
#                     normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

#                     special_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
#                     )
#                     special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)

#                     line.credit_value = regular_hrs_amount + normal_ot_amount + special_ot_amount

#                 else:
#                     valid_timesheets = task.timesheet_ids.filtered(
#                         lambda t: t.date and 
#                         fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(t.date).date() <= end_date
#                     )
                    
#                     if not valid_timesheets:
#                         line.credit_value = 0.0
#                         continue
                        
#                     max_date = min(end_date, max(valid_timesheets.mapped(lambda t: fields.Datetime.to_datetime(t.date).date())))

#                     month_diff = (max_date.year - task.last_invoice_date.year) * 12 + (max_date.month - task.last_invoice_date.month)
                    
#                     unbilled_month_amount = month_diff * task.unit_price
                    
#                     agency_fee_amount = 0.0
#                     if task.agency_fee == 'fix' and task.amount:
#                         agency_fee_amount = task.amount * month_diff
#                     elif task.agency_fee == 'percentage' and task.amount:
#                         agency_fee_amount = (task.unit_price * task.amount / 100) * month_diff
                    
#                     normal_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
#                     )
#                     normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

#                     special_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
#                     )
#                     special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)
                    
#                     line.credit_value = unbilled_month_amount + agency_fee_amount + normal_ot_amount + special_ot_amount
#             else:
#                 line.credit_value = (task.delivered - task.invoiced) * task.unit_price if task.delivered > task.invoiced else 0.0




# class AccruedRevenueWizard(models.TransientModel):
#     _name = 'accrued.revenue.wizard'
#     _description = 'Accrued Revenue Entry Generation Details'

#     company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
#     journal_id = fields.Many2one(
#         'account.journal', 
#         string='Journal', 
#         required=True,
#         domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
#         default=lambda self: self.env['account.journal'].search([
#             ('company_id', '=', self.env.company.id),
#             ('type', '=', 'general')
#         ], limit=1)
#     )
#     date = fields.Date(
#         string='Date', 
#         required=True, 
#         default=lambda self: date_utils.get_month(fields.Date.context_today(self))[0] - relativedelta(days=1)
#     )
#     reversal_date = fields.Date(
#         string='Reversal Date', 
#         required=True,
#         compute="_compute_reversal_date",
#         readonly=False,
#     )
#     accrual_account_id = fields.Many2one(
#         'account.account', 
#         string='Accrual Account', 
#         required=True,
#         domain="[('user_type_id', '=', %(account.data_account_type_current_assets)d), ('company_id', '=', company_id)]"
#     )
    
#     sale_id = fields.Many2one('sale.order', string='Sale Order')
#     line_ids = fields.One2many('accrued.revenue.wizard.line', 'wizard_id', string='Lines')
    
#     @api.depends('date')
#     def _compute_reversal_date(self):
#         for record in self:
#             if not record.reversal_date or record.reversal_date <= record.date:
#                 record.reversal_date = record.date + relativedelta(days=1)
    
#     @api.onchange('journal_id')
#     def _onchange_journal_id(self):
#         for record in self:
#             if record.journal_id and record.journal_id.default_account_id:
#                 record.accrual_account_id = record.journal_id.default_account_id
    
#     @api.model
#     def default_get(self, fields_list):
#         res = super(AccruedRevenueWizard, self).default_get(fields_list)
        
#         active_model = self.env.context.get('active_model')
#         active_ids = self.env.context.get('active_ids', [])
        
#         if active_model == 'sale.order' and active_ids and len(active_ids) == 1:
#             sale_order = self.env['sale.order'].browse(active_ids[0])
#             res['sale_id'] = sale_order.id
            
#             tasks = self.env['project.task'].search([
#                 ('sale_line_id', 'in', sale_order.order_line.ids)
#             ])
            
#             line_vals = []
#             for task in tasks:
#                 sale_line = task.sale_line_id
#                 task_account_id = False
                
#                 if sale_line and sale_line.product_id and sale_line.product_id.property_account_income_id:
#                     task_account_id = sale_line.product_id.property_account_income_id.id
#                 elif sale_line and sale_line.product_id and sale_line.product_id.categ_id.property_account_income_categ_id:
#                     task_account_id = sale_line.product_id.categ_id.property_account_income_categ_id.id
                
#                 line_vals.append((0, 0, {
#                     'task_id': task.id,
#                     'account_id': task_account_id,
#                     'label': f"Accrued Revenue entry as of {fields.Date.today()}",
#                     'is_debit_line': False,
#                 }))
            
#             res['line_ids'] = line_vals
        
#         journals = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', self.env.company.id)], limit=1)
#         if journals:
#             res['journal_id'] = journals[0].id
            
#             if journals[0].default_account_id:
#                 res['accrual_account_id'] = journals[0].default_account_id.id
#             else:
#                 accrual_accounts = self.env['account.account'].search([
#                     ('name', 'ilike', 'accrued revenue'),
#                     ('user_type_id', '=', self.env.ref('account.data_account_type_current_assets').id),
#                     ('company_id', '=', self.env.company.id)
#                 ], limit=1)
                
#                 if not accrual_accounts:
#                     accrual_accounts = self.env['account.account'].search([
#                         ('name', 'ilike', 'outstanding revenue'),
#                         ('user_type_id', '=', self.env.ref('account.data_account_type_current_assets').id),
#                         ('company_id', '=', self.env.company.id)
#                     ], limit=1)
                
#                 if accrual_accounts:
#                     res['accrual_account_id'] = accrual_accounts[0].id
        
#         return res
        
#     @api.onchange('accrual_account_id', 'line_ids')
#     def _onchange_update_debit_line(self):
#         for wizard in self:
#             if not wizard.accrual_account_id:
#                 continue
                
#             # Calculate total credit
#             total_credit = sum(line.credit_value for line in wizard.line_ids if not line.is_debit_line)
            
#             # Find or create debit line
#             debit_line = wizard.line_ids.filtered(lambda l: l.is_debit_line)
#             if debit_line:
#                 debit_line.debit_value = total_credit
#                 debit_line.account_id = wizard.accrual_account_id
#                 debit_line.label = f"Accrued Revenue Total as of {wizard.date}"
#             else:
#                 wizard.write({
#                     'line_ids': [(0, 0, {
#                         'is_debit_line': True,
#                         'account_id': wizard.accrual_account_id.id,
#                         'label': f"Accrued Revenue Total as of {wizard.date}",
#                         'debit_value': total_credit,
#                     })]
#                 })
    
#     @api.onchange('date')
#     def _onchange_date(self):
#         for line in self.line_ids:
#             if not line.is_debit_line:
#                 line.label = f"Accrued Revenue entry as of {self.date}"
#             else:
#                 line.label = f"Accrued Revenue Total as of {self.date}"
#             line._compute_unbilled_value()
#         self._onchange_update_debit_line()
    
    
#     def action_create_entry(self):
#         self.ensure_one()
        
#         # Force recompute all values before creating the entry
#         for line in self.line_ids:
#             if not line.is_debit_line:
#                 line._compute_unbilled_value()
        
#         # Update the debit line with the latest credit values
#         self._onchange_update_debit_line()
        
#         move_vals = {
#             'journal_id': self.journal_id.id,
#             'date': self.date,
#             'ref': f'Accrued Revenue entry as of {self.date}',
#             'line_ids': [],
#         }
        
#         # Add credit lines (task-related lines)
#         credit_lines = []
#         for line in self.line_ids:
#             if not line.is_debit_line:
#                 # Skip lines with zero or negative credit
#                 if line.credit_value <= 0:
#                     continue
                    
#                 credit_lines.append((0, 0, {
#                     'name': line.label,
#                     'account_id': line.account_id.id,
#                     'debit': 0.0,
#                     'credit': line.credit_value,
#                     'analytic_account_id': line.task_id.project_id.analytic_account_id.id if line.task_id and line.task_id.project_id.analytic_account_id else False,
#                 }))
        
#         # Calculate total credits from our credit lines
#         total_credit = sum(line[2]['credit'] for line in credit_lines)
        
#         # Add all credit lines to move
#         move_vals['line_ids'].extend(credit_lines)
        
#         # Find the debit line or use the accrual account
#         debit_line = self.line_ids.filtered(lambda l: l.is_debit_line)
#         if debit_line:
#             move_vals['line_ids'].append((0, 0, {
#                 'name': debit_line[0].label,
#                 'account_id': debit_line[0].account_id.id,
#                 'debit': total_credit,  # Use total_credit to ensure balance
#                 'credit': 0.0,
#                 'analytic_account_id': False,
#             }))
#         else:
#             # If no debit line exists, create one using the accrual account
#             move_vals['line_ids'].append((0, 0, {
#                 'name': f"Accrued Revenue Total as of {self.date}",
#                 'account_id': self.accrual_account_id.id,
#                 'debit': total_credit,  # Use total_credit to ensure balance
#                 'credit': 0.0,
#                 'analytic_account_id': False,
#             }))
        
#         # Create the move with the balanced lines
#         move = self.env['account.move'].create(move_vals)
        
#         # Create reversal if a reversal date is set
#         if self.reversal_date:
#             reversal = move._reverse_moves(
#                 default_values_list=[{
#                     'date': self.reversal_date,
#                     'ref': f'Reversal of: {move.name}',
#                 }]
#             )
        
#         return {
#             'name': 'Journal Entry',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'tree,form',
#             'res_id': move.id,
#         }


# class AccruedRevenueWizardLine(models.TransientModel):
#     _name = 'accrued.revenue.wizard.line'
#     _description = 'Accrued Revenue Wizard Line'
    
#     wizard_id = fields.Many2one('accrued.revenue.wizard', string='Wizard')
#     task_id = fields.Many2one('project.task', string='Task')
#     account_id = fields.Many2one(
#         'account.account', 
#         string='Account',
#         domain="[('user_type_id', '=', %(account.data_account_type_current_assets)d), ('company_id', '=', context.get('company_id', parent.company_id))]"
#     )
#     label = fields.Char(string='Label', required=True)
#     credit_value = fields.Float(string='Credit', compute='_compute_unbilled_value', store=True)
#     debit_value = fields.Float(string='Debit', default=0.0)

#     is_debit_line = fields.Boolean(string='Is Debit Line', default=False)
#     line_type = fields.Selection(
#         [('credit', 'Credit'), ('debit', 'Debit')],
#         string='Type',
#         compute='_compute_line_type',
#         store=True
#     )
    
#     @api.depends('is_debit_line')
#     def _compute_line_type(self):
#         for line in self:
#             line.line_type = 'debit' if line.is_debit_line else 'credit'
    
#     @api.onchange('task_id')
#     def _onchange_task_id(self):
#         for line in self:
#             if line.task_id and line.task_id.sale_line_id:
#                 sale_line = line.task_id.sale_line_id
#                 if sale_line.product_id and sale_line.product_id.property_account_income_id:
#                     line.account_id = sale_line.product_id.property_account_income_id
#                 elif sale_line.product_id and sale_line.product_id.categ_id.property_account_income_categ_id:
#                     line.account_id = sale_line.product_id.categ_id.property_account_income_categ_id
    
#     @api.depends('task_id', 'wizard_id.date')
#     def _compute_unbilled_value(self):
#         for line in self:
#             if line.is_debit_line:
#                 continue
                
#             task = line.task_id
#             end_date = line.wizard_id.date if line.wizard_id else fields.Date.today()
            
#             if not task or not task.last_invoice_date:
#                 line.credit_value = 0.0
#                 continue
                
#             if task.branch_for == 'es':
#                 # ES Branch Calculation
#                 valid_trips = task.trip_sheet_ids.filtered(
#                     lambda t: t.date_from and 
#                     fields.Datetime.to_datetime(t.date_from).date() > task.last_invoice_date and
#                     fields.Datetime.to_datetime(t.date_from).date() <= end_date and
#                     not t.non_billable
#                 )
                
#                 billable_amount = sum(trip.billable_qty * task.unit_price for trip in valid_trips)
#                 equipment_amount = sum(trip.equipment_qty * task.additional_rate for trip in valid_trips)
#                 line.credit_value = billable_amount + equipment_amount

#             elif task.branch_for == 'hro':
                
#                 excluded_uoms = ['month', 'months', 'lumpsum', 'week', 'weeks', 'day', 'days']
#                 if task.task_uom and task.task_uom.name.lower() not in [u.lower() for u in excluded_uoms]:
                   
#                     regular_timesheets = task.timesheet_ids.filtered(
#                         lambda t: t.date and 
#                         fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(t.date).date() <= end_date
#                     )
#                     regular_hrs_amount = sum(t.unit_amount * task.unit_price for t in regular_timesheets)

#                     normal_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
#                     )
#                     normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

#                     special_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
#                     )
#                     special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)

#                     line.credit_value = regular_hrs_amount + normal_ot_amount + special_ot_amount

#                 elif task.task_uom and task.task_uom.name.lower() in ['week', 'weeks']:
#                     valid_timesheets = task.timesheet_ids.filtered(
#                         lambda t: t.date and 
#                         fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(t.date).date() <= end_date
#                     )
                    
#                     if not valid_timesheets:
#                         line.credit_value = 0.0
#                         continue
                        
#                     max_date = min(end_date, max(valid_timesheets.mapped(lambda t: fields.Datetime.to_datetime(t.date).date())))

#                     days_diff = (max_date - task.last_invoice_date).days
#                     week_diff = days_diff / 7
                    
#                     unbilled_period_amount = week_diff * task.unit_price
                    
#                     agency_fee_amount = 0.0
#                     if task.agency_fee == 'fix' and task.amount:
#                         agency_fee_amount = task.amount * week_diff
#                     elif task.agency_fee == 'percentage' and task.amount:
#                         agency_fee_amount = (task.unit_price * task.amount / 100) * week_diff
                    
#                     normal_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
#                     )
#                     normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

#                     special_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
#                     )
#                     special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)
                    
#                     line.credit_value = unbilled_period_amount + agency_fee_amount + normal_ot_amount + special_ot_amount

#                 elif task.task_uom and task.task_uom.name.lower() in ['day', 'days']:
#                     valid_days = task.timesheet_ids.filtered(
#                         lambda t: t.date and 
#                         fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(t.date).date() <= end_date and
#                         t.unit_amount > 0
#                     ).mapped('date')
                    
#                     day_count = len(set(valid_days))
#                     regular_hrs_amount = day_count * task.unit_price

#                     normal_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
#                     )
#                     normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

#                     special_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
#                     )
#                     special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)

#                     line.credit_value = regular_hrs_amount + normal_ot_amount + special_ot_amount

#                 else:
#                     valid_timesheets = task.timesheet_ids.filtered(
#                         lambda t: t.date and 
#                         fields.Datetime.to_datetime(t.date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(t.date).date() <= end_date
#                     )
                    
#                     if not valid_timesheets:
#                         line.credit_value = 0.0
#                         continue
                        
#                     max_date = min(end_date, max(valid_timesheets.mapped(lambda t: fields.Datetime.to_datetime(t.date).date())))

#                     month_diff = (max_date.year - task.last_invoice_date.year) * 12 + (max_date.month - task.last_invoice_date.month)
                    
#                     unbilled_month_amount = month_diff * task.unit_price
                    
#                     agency_fee_amount = 0.0
#                     if task.agency_fee == 'fix' and task.amount:
#                         agency_fee_amount = task.amount * month_diff
#                     elif task.agency_fee == 'percentage' and task.amount:
#                         agency_fee_amount = (task.unit_price * task.amount / 100) * month_diff
                    
#                     normal_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code in ('NOD', 'RAMD')
#                     )
#                     normal_ot_amount = sum(ot.ot_hour * task.new_overtime for ot in normal_ot_records)

#                     special_ot_records = task.overtime_lines_ids.filtered(
#                         lambda o: o.ot_date and 
#                         fields.Datetime.to_datetime(o.ot_date).date() > task.last_invoice_date and
#                         fields.Datetime.to_datetime(o.ot_date).date() <= end_date and
#                         o.ot_type and o.ot_type.code not in ('NOD', 'RAMD')
#                     )
#                     special_ot_amount = sum(ot.ot_hour * task.spe_overtime for ot in special_ot_records)
                    
#                     line.credit_value = unbilled_month_amount + agency_fee_amount + normal_ot_amount + special_ot_amount
#             else:
#                 line.credit_value = (task.delivered - task.invoiced) * task.unit_price if task.delivered > task.invoiced else 0.0





