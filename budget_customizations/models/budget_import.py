import datetime as dt
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class BudgetImport(models.Model):
    _name = 'budget.import'
    _description = 'Budget Import'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Budget Name', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    branch_id = fields.Many2one('res.branch', string='Branch', tracking=True)
    responsible_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)
    year = fields.Selection(lambda self: [(str(year), str(year)) for year in range(dt.datetime.now().year - 2, dt.datetime.now().year + 5)], 
                          string='Year', default=lambda self: str(dt.datetime.now().year), tracking=True)
    
    # Used for direct entry in the tree view
    # budget_position_id = fields.Many2one('account.budget.post', string='Budget Position')
    budget_position_id = fields.Many2one(
        'account.budget.post', 
        string='Budget Position',
        domain="[('branch_id', '=', branch_id)]"
    )
    budget_position_branch_id = fields.Many2one(
        related='budget_position_id.branch_id', 
        string='Position Branch', 
        store=True,
        readonly=True
    )
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytical Account')
    
    jan = fields.Float(string='Jan')
    feb = fields.Float(string='Feb')
    mar = fields.Float(string='Mar')
    apr = fields.Float(string='Apr')
    may = fields.Float(string='May')
    jun = fields.Float(string='Jun')
    jul = fields.Float(string='Jul')
    aug = fields.Float(string='Aug')
    sep = fields.Float(string='Sep')
    oct = fields.Float(string='Oct')
    nov = fields.Float(string='Nov')
    dec = fields.Float(string='Dec')
    
    active = fields.Boolean(string="Active", default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ], default='draft', string='Status', tracking=True)
    
    budget_line_ids = fields.One2many('budget.import.line', 'budget_import_id', string='Budget Lines')

    
    @api.model
    def create(self, vals):
        # If direct entry in the list view, create a budget line
        if any(month in vals for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
            if 'budget_position_id' in vals and 'analytic_account_id' in vals:
                line_vals = {
                    'budget_position_id': vals.pop('budget_position_id'),
                    'analytic_account_id': vals.pop('analytic_account_id'),
                }
                
                # Add monthly values to line
                for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
                    if month in vals:
                        line_vals[month] = vals.pop(month)
                
                if 'budget_line_ids' not in vals:
                    vals['budget_line_ids'] = []
                vals['budget_line_ids'].append((0, 0, line_vals))
        
        record = super(BudgetImport, self).create(vals)
        return record
    
    
    def post_action(self):
        """Post budget entries and create crossovered budget - grouping by budget name, branch and year"""
        # First, validate that no record is already posted
        already_posted = self.filtered(lambda r: r.state == 'posted')
        if already_posted:
            if len(already_posted) == 1:
                raise ValidationError(_("Budget '%s' is already posted and cannot be posted again.") % already_posted[0].name)
            else:
                posted_names = ', '.join(already_posted.mapped('name'))
                raise ValidationError(_("The following budgets are already posted and cannot be posted again: %s") % posted_names)
        
        # Additional validation: Check if records have data to post
        for record in self:
            has_direct_entries = any(record[f] for f in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                                        'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])
            has_line_entries = bool(record.budget_line_ids)
            
            if not (has_direct_entries or has_line_entries):
                raise ValidationError(_("Budget '%s' has no budget entries to post!") % record.name)
            
            # If has direct entries, validate required fields
            if has_direct_entries and not record.budget_position_id:
                raise ValidationError(_("Budget Position is required for budget '%s' when posting direct entries!") % record.name)
        
        posted_budgets = self.env['budget.import']
        error_records = []
        
        # Group records by budget name, branch and year
        budget_groups = {}
        for record in self:
            if record.state != 'draft':
                continue  # Skip already posted budgets
                
            # Create a unique key for grouping (include company_id for better grouping)
            group_key = (record.name, record.branch_id.id if record.branch_id else False, record.year, record.company_id.id)
            
            if group_key not in budget_groups:
                budget_groups[group_key] = self.env['budget.import']
            budget_groups[group_key] += record
        
        for group_key, records in budget_groups.items():
            budget_name, branch_id, year, company_id = group_key
            try:
                if not year:
                    raise UserError(_("Please set a valid year before posting for budget %s!") % budget_name)
                
                try:
                    year_int = int(year)
                except ValueError:
                    raise UserError(_("Invalid year format! Please enter a valid year for budget %s.") % budget_name)
                
                # Check if crossovered budget already exists with same name, branch, year, and company
                domain = [
                    ('name', '=', budget_name),
                    ('date_from', '=', f"{year_int}-01-01"),
                    ('date_to', '=', f"{year_int}-12-31"),
                    ('company_id', '=', company_id),
                ]
                
                # Add branch condition if branch exists
                if branch_id:
                    domain.append(('branch_id', '=', branch_id))
                else:
                    domain.append(('branch_id', '=', False))
                
                existing_budget = self.env['crossovered.budget'].search(domain, limit=1)
                
                if existing_budget:
                    # Use existing budget
                    budget_id = existing_budget
                else:
                    # Create new crossovered budget for this group
                    first_record = records[0]
                    budget_vals = {
                        'name': budget_name,
                        'user_id': first_record.responsible_id.id,
                        'date_from': f"{year_int}-01-01",
                        'date_to': f"{year_int}-12-31",
                        'company_id': company_id,
                    }
                    
                    # Include branch if it exists
                    if branch_id:
                        budget_vals['branch_id'] = branch_id
                    
                    budget_id = self.env['crossovered.budget'].create(budget_vals)
                
                # Process all records in this group
                for record in records:
                    # Check if we have either direct entries or line entries
                    has_direct_entries = any(record[f] for f in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                                                'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])
                    has_line_entries = bool(record.budget_line_ids)
                    
                    if not (has_direct_entries or has_line_entries):
                        raise UserError(_("No budget entries to post for record %s!") % record.name)
                    
                    # Create budget lines from direct entries if they exist
                    if has_direct_entries and record.budget_position_id:
                        self._create_budget_lines_from_direct_entry(record, budget_id, year_int)
                    
                    # Create budget lines from line entries if they exist
                    if has_line_entries:
                        self._create_budget_lines_from_line_entries(record, budget_id, year_int)
                    
                    record.write({
                        'state': 'posted',
                        'active': False,
                    })
                    
                    record.message_post(body=_(
                        "Budget has been posted successfully and automatically archived. "
                        "Created/Updated crossovered budget: %s") % budget_id.name)
                    
                    posted_budgets += record
                
            except Exception as e:
                for record in records:
                    error_records.append((record.name, str(e)))
        
        # Show notification for errors
        if error_records:
            error_message = _("The following budgets could not be posted:\n")
            for name, error in error_records:
                error_message += f"- {name}: {error}\n"
            raise UserError(error_message)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('%s budget(s) have been posted.') % len(posted_budgets),
                'sticky': False,
            }
        }

    def _create_budget_lines_from_direct_entry(self, record, budget_id, year_int):
        """Create budget lines from direct monthly entries"""
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        month_nums = list(range(1, 13))
        
        for month, month_num in zip(months, month_nums):
            amount = record[month]
            # if amount > 0:
            if amount != 0 or amount == 0: 
                # Check if budget line already exists for this combination
                existing_line = self._find_existing_budget_line(
                    budget_id, record.budget_position_id, record.analytic_account_id, month_num, year_int
                )
                
                if existing_line:
                    # Update existing line by adding the amount
                    existing_line.planned_amount += amount
                else:
                    # Create new budget line
                    start_date, end_date = self._get_month_date_range(month_num, year_int)
                    line_vals = {
                        'crossovered_budget_id': budget_id.id,
                        'general_budget_id': record.budget_position_id.id,
                        'date_from': start_date,
                        'date_to': end_date,
                        'planned_amount': amount,
                    }
                    # Only add analytic account if it exists
                    if record.analytic_account_id:
                        line_vals['analytic_account_id'] = record.analytic_account_id.id
                    self.env['crossovered.budget.lines'].create(line_vals)

    def _create_budget_lines_from_line_entries(self, record, budget_id, year_int):
        """Create budget lines from line entries"""
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        month_nums = list(range(1, 13))
        
        for line in record.budget_line_ids:
            if not line.budget_position_id:
                continue
                
            for month, month_num in zip(months, month_nums):
                amount = getattr(line, month)
                # if amount > 0:
                if amount != 0 or amount == 0: 
                    # Check if budget line already exists for this combination
                    existing_line = self._find_existing_budget_line(
                        budget_id, line.budget_position_id, line.analytic_account_id, month_num, year_int
                    )
                    
                    if existing_line:
                        # Update existing line by adding the amount
                        existing_line.planned_amount += amount
                    else:
                        # Create new budget line
                        start_date, end_date = self._get_month_date_range(month_num, year_int)
                        line_vals = {
                            'crossovered_budget_id': budget_id.id,
                            'general_budget_id': line.budget_position_id.id,
                            'date_from': start_date,
                            'date_to': end_date,
                            'planned_amount': amount,
                        }
                        # Only add analytic account if it exists
                        if line.analytic_account_id:
                            line_vals['analytic_account_id'] = line.analytic_account_id.id
                        self.env['crossovered.budget.lines'].create(line_vals)

    def _find_existing_budget_line(self, budget_id, budget_position, analytic_account, month_num, year_int):
        """Find existing budget line for the same combination"""
        start_date, end_date = self._get_month_date_range(month_num, year_int)
        
        domain = [
            ('crossovered_budget_id', '=', budget_id.id),
            ('general_budget_id', '=', budget_position.id),
            ('date_from', '=', start_date),
            ('date_to', '=', end_date),
        ]
        
        # Handle analytic account condition
        if analytic_account:
            domain.append(('analytic_account_id', '=', analytic_account.id))
        else:
            domain.append(('analytic_account_id', '=', False))
        
        return self.env['crossovered.budget.lines'].search(domain, limit=1)

    def _get_month_date_range(self, month_num, year_int):
        """Get start and end date for a given month"""
        start_date = f"{year_int}-{month_num:02d}-01"
        if month_num == 12:
            end_date = f"{year_int}-12-31"
        else:
            next_month = month_num + 1
            next_year = year_int
            if next_month > 12:
                next_month = 1
                next_year += 1
            end_date = f"{next_year}-{next_month:02d}-01"
            end_date = (dt.datetime.strptime(end_date, '%Y-%m-%d') - dt.timedelta(days=1)).strftime('%Y-%m-%d')
        
        return start_date, end_date

    def reset_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            record.message_post(body=_("Budget has been reset to draft."))

    def action_archive(self):
        for record in self:
            record.write({'active': False})
            record.message_post(body=_("Budget has been archived."))
    
    def action_unarchive(self):
        for record in self:
            record.write({'active': True})
            record.message_post(body=_("Budget has been unarchived."))

    @api.constrains('state')
    def _check_state_change(self):
        """Additional constraint to prevent state manipulation"""
        for record in self:
            if record.state == 'posted':
                # You can add additional validations here if needed
                pass

    def action_update_budget_position_by_branch(self):
        """Switch to the Budget Position with the same name but matching branch"""
        updated_count = 0
        skipped_records = []

        for record in self:
            if not record.branch_id:
                skipped_records.append(_("%s (no branch set)") % record.name)
                continue
            if not record.budget_position_id:
                skipped_records.append(_("%s (no budget position selected)") % record.name)
                continue

            matching_position = self.env['account.budget.post'].search([
                ('name', '=', record.budget_position_id.name),
                ('branch_id', '=', record.branch_id.id),
            ], limit=1)

            if matching_position:
                if matching_position.id != record.budget_position_id.id:
                    record.budget_position_id = matching_position.id
                    updated_count += 1
            else:
                skipped_records.append(_("%s (no Budget Position named '%s' exists for branch %s)") % (
                    record.name, record.budget_position_id.name, record.branch_id.name))

        message = _("%s record(s) updated.") % updated_count
        if skipped_records:
            message += _("\nSkipped:\n") + "\n".join(skipped_records)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Budget Position Update'),
                'message': message,
                'sticky': bool(skipped_records),
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }


class BudgetImportLine(models.Model):
    _name = 'budget.import.line'
    _description = 'Budget Import Line'
    
    budget_import_id = fields.Many2one('budget.import', string='Budget Import')
    branch_id = fields.Many2one(related='budget_import_id.branch_id', string='Branch', store=True)
    budget_position_id = fields.Many2one(
        'account.budget.post', 
        string='Budget Position', 
        required=True,
        domain="[('branch_id', '=', branch_id)]"
    )
    budget_position_branch_id = fields.Many2one(
        related='budget_position_id.branch_id', 
        string='Position Branch', 
        store=True,
        readonly=True
    )
    # budget_position_id = fields.Many2one('account.budget.post', string='Budget Position', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytical Account')
    
    jan = fields.Float(string='Jan')
    feb = fields.Float(string='Feb')
    mar = fields.Float(string='Mar')
    apr = fields.Float(string='Apr')
    may = fields.Float(string='May')
    jun = fields.Float(string='Jun')
    jul = fields.Float(string='Jul')
    aug = fields.Float(string='Aug')
    sep = fields.Float(string='Sep')
    oct = fields.Float(string='Oct')
    nov = fields.Float(string='Nov')
    dec = fields.Float(string='Dec')
    
    total = fields.Float(string='Total', compute='_compute_total')
    
    @api.depends('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
    def _compute_total(self):
        for record in self:
            record.total = sum([
                record.jan, record.feb, record.mar, record.apr, record.may, record.jun,
                record.jul, record.aug, record.sep, record.oct, record.nov, record.dec
            ])
            
