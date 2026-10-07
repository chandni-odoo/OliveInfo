from odoo import models, fields, api, _
import datetime
from datetime import timedelta, date
from datetime import datetime

class StatementOfAccountVersionWizard(models.TransientModel):
    _name = 'statement.account.version2.wizard'
    _description = "Statement Account Version 2 Wizard"

    customer_ids = fields.Many2many('res.partner')
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To", default=fields.Date.context_today)
    open_invoices = fields.Boolean(string="Show closed invoices")
    branch_id = fields.Many2one('res.branch', string="Branch")

    def button_generate_report(self):
        data = {
            'customer_id': self.customer_ids.ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'open_invoices': self.open_invoices,
            'branch_id': self.branch_id.id,
        }
        return self.env.ref('account_extended.action_wizard_report_details_v2').report_action(self, data=data)

class CustomerReportDetailsV2(models.AbstractModel):
    _name = 'report.account_extended.customer_report_details_templete_v2'

    # def _get_payment_values(self, payment_ids):
    #     for payment in payment_ids:
    #         invoice_id = payment.mapped('reconciled_invoice_ids')

    # def _get_reconciled_amount(self, payment):
    #     """Calculate the reconciled amount from payment's move lines"""
    #     reconciled_amount = 0.0
    #     for line in payment.move_id.line_ids:
    #         if line.account_id.internal_type == 'receivable':
    #             reconciled_amount += abs(line.amount_residual)
    #     return payment.amount - reconciled_amount
    

    def _get_invoice_residual_at_date(self, invoice, statement_date):
        """Calculate invoice residual amount as of statement date"""
        if not invoice:
            return 0.0
        
        # Get all payments applied to this invoice up to statement date
        total_paid = 0.0
        
        # Find all reconciled move lines for this invoice
        receivable_lines = invoice.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        
        for line in receivable_lines:
            # Get all reconciled items for this line
            for partial_rec in line.matched_debit_ids + line.matched_credit_ids:
                counterpart_line = partial_rec.debit_move_id if partial_rec.credit_move_id == line else partial_rec.credit_move_id
                
                # Check if the counterpart is a payment and within date range
                if counterpart_line.move_id.payment_id and counterpart_line.move_id.date <= statement_date:
                    total_paid += partial_rec.amount
                elif counterpart_line.move_id.move_type == 'out_refund' and counterpart_line.move_id.date <= statement_date:
                    # Credit note applied to invoice
                    total_paid += partial_rec.amount
        
        return max(0, invoice.amount_total - total_paid)

    def _get_credit_note_residual_at_date(self, credit_note, statement_date):
        """Calculate credit note residual amount as of statement date"""
        if not credit_note:
            return 0.0
        
        # Get all amounts applied from this credit note up to statement date
        total_applied = 0.0
        
        # Find all reconciled move lines for this credit note
        receivable_lines = credit_note.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        
        for line in receivable_lines:
            # Get all reconciled items for this line
            for partial_rec in line.matched_debit_ids + line.matched_credit_ids:
                counterpart_line = partial_rec.debit_move_id if partial_rec.credit_move_id == line else partial_rec.credit_move_id
                
                # Check if counterpart is an invoice or payment within date range
                if counterpart_line.move_id.date <= statement_date:
                    if counterpart_line.move_id.move_type == 'out_invoice':
                        # Credit note applied to invoice
                        total_applied += partial_rec.amount
                    elif counterpart_line.move_id.payment_id:
                        # Credit note refunded via payment
                        total_applied += partial_rec.amount
        
        return max(0, credit_note.amount_total - total_applied)

    def _get_payment_unreconciled_amount(self, payment, statement_date):
        """Calculate unreconciled amount of payment as of statement date"""
        if not payment or payment.date > statement_date:
            return 0.0
        
        total_reconciled = 0.0
        
        # Get payment move lines
        payment_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        
        for line in payment_lines:
            # Get all reconciled items for this line
            for partial_rec in line.matched_debit_ids + line.matched_credit_ids:
                counterpart_line = partial_rec.debit_move_id if partial_rec.credit_move_id == line else partial_rec.credit_move_id
                
                # Check if counterpart is an invoice or credit note within date range
                if counterpart_line.move_id.date <= statement_date:
                    if counterpart_line.move_id.move_type in ['out_invoice', 'out_refund']:
                        total_reconciled += partial_rec.amount
        
        return max(0, payment.amount - total_reconciled)

    def _calculate_aging_buckets(self, amount, due_date, statement_date):
        """Calculate aging bucket for given amount and due date"""
        if not due_date:
            return 'bucket_current'
        
        days_overdue = (statement_date - due_date).days
        
        if days_overdue <= 0:
            return 'bucket_current'
        elif 1 <= days_overdue <= 30:
            return 'bucket_1_30'
        elif 31 <= days_overdue <= 60:
            return 'bucket_31_60'
        elif 61 <= days_overdue <= 90:
            return 'bucket_61_90'
        elif 91 <= days_overdue <= 120:
            return 'bucket_91_120'
        elif 121 <= days_overdue <= 180:
            return 'bucket_121_180'
        elif 181 <= days_overdue <= 360:
            return 'bucket_181_360'
        else:
            return 'bucket_over_360'

    # @api.model
    # def _get_report_values(self, docids, data=None):
    #     model = self.env.context.get('active_model')
    #     docs = self.env[model].browse(self.env.context.get('active_id'))
    #     partner_id = data.get('customer_id')
    #     open_invoices = data.get('open_invoices')
    #     branch = data.get('branch_id')
    #     branch_id = self.env['res.branch'].browse(branch)
    #     customer_ids = self.env['res.partner'].browse(partner_id)
    #     lines = []
        
    #     # Ensure statement_date is a proper date object
    #     if data.get('date_to'):
    #         if isinstance(data.get('date_to'), str):
    #             from datetime import datetime
    #             statement_date = datetime.strptime(data.get('date_to'), '%Y-%m-%d').date()
    #         else:
    #             statement_date = data.get('date_to')
    #     else:
    #         statement_date = fields.Date.context_today(self)
        
    #     for customer in customer_ids:
    #         # Initialize aging buckets
    #         aging_buckets = {
    #             'bucket_current': 0,
    #             'bucket_1_30': 0,
    #             'bucket_31_60': 0,
    #             'bucket_61_90': 0,
    #             'bucket_91_120': 0,
    #             'bucket_121_180': 0,
    #             'bucket_181_360': 0,
    #             'bucket_over_360': 0
    #         }

    #         # Base domains - Include all records up to statement date
    #         invoice_domain = [
    #             ('partner_id', '=', customer.id),
    #             ('move_type', '=', 'out_invoice'),
    #             ('state', '=', 'posted'),
    #             ('invoice_date', '<=', statement_date)
    #         ]
            
    #         credit_note_domain = [
    #             ('partner_id', '=', customer.id),
    #             ('move_type', '=', 'out_refund'),
    #             ('state', '=', 'posted'),
    #             ('invoice_date', '<=', statement_date)
    #         ]
            
    #         payment_domain = [
    #             ('partner_id', '=', customer.id),
    #             ('payment_type', 'in', ['inbound']),
    #             ('state', '=', 'posted'),
    #             ('date', '<=', statement_date)
    #         ]

    #         # Apply date filters if provided
    #         if data.get('date_from'):
    #             invoice_domain.append(('invoice_date', '>=', data.get('date_from')))
    #             credit_note_domain.append(('invoice_date', '>=', data.get('date_from')))
    #             payment_domain.append(('date', '>=', data.get('date_from')))

    #         # Apply branch filter if provided
    #         if branch_id:
    #             invoice_domain.append(('branch_id', '=', branch_id.id))
    #             credit_note_domain.append(('branch_id', '=', branch_id.id))
    #             payment_domain.append(('branch_id', '=', branch_id.id))

    #         # Get all records
    #         all_invoices = self.env['account.move'].search(invoice_domain)
    #         all_credit_notes = self.env['account.move'].search(credit_note_domain)
    #         all_payments = self.env['account.payment'].search(payment_domain)

    #         # Initialize result sets
    #         invoice_ids = self.env['account.move']
    #         credit_note_ids = self.env['account.move']
    #         filtered_payments = self.env['account.payment']
            
    #         invoice_residuals = {}
    #         credit_note_residuals = {}
            
    #         # Process Invoices
    #         for invoice in all_invoices:
    #             residual = self._get_invoice_residual_at_date(invoice, statement_date)
    #             invoice_residuals[invoice.id] = residual
                
    #             # Include invoice based on criteria
    #             if open_invoices:
    #                 # Show all invoices if open_invoices is True
    #                 invoice_ids |= invoice
    #             else:
    #                 # Show only invoices with outstanding balance
    #                 if residual > 0.01:
    #                     invoice_ids |= invoice
                
    #             # Add to aging buckets if there's outstanding balance
    #             if residual > 0.01:
    #                 due_date = invoice.invoice_date_due or invoice.invoice_date
    #                 bucket_key = self._calculate_aging_buckets(residual, due_date, statement_date)
    #                 aging_buckets[bucket_key] += residual

    #         # Process Credit Notes
    #         for credit_note in all_credit_notes:
    #             residual = self._get_credit_note_residual_at_date(credit_note, statement_date)
    #             credit_note_residuals[credit_note.id] = residual
                
    #             # Include credit note based on criteria
    #             if open_invoices:
    #                 # Show all credit notes if open_invoices is True
    #                 credit_note_ids |= credit_note
    #             else:
    #                 # Show only credit notes with outstanding balance
    #                 if residual > 0.01:
    #                     credit_note_ids |= credit_note
                
    #             # Add to aging buckets if there's outstanding balance (negative for credit notes)
    #             if residual > 0.01:
    #                 due_date = credit_note.invoice_date_due or credit_note.invoice_date
    #                 bucket_key = self._calculate_aging_buckets(residual, due_date, statement_date)
    #                 aging_buckets[bucket_key] -= residual  # Subtract for credit notes

    #         # Process Payments - Only show payments if NOT showing closed invoices
    #         if not open_invoices:
    #             for payment in all_payments:
    #                 unreconciled_amount = self._get_payment_unreconciled_amount(payment, statement_date)
                    
    #                 # Show only payments with unreconciled amount
    #                 if unreconciled_amount > 0.01:
    #                     filtered_payments |= payment

    #         # Append customer data to lines
    #         lines.append({
    #             'customer_id': customer,
    #             'invoice_ids': invoice_ids,
    #             'payment_ids': filtered_payments,
    #             'credit_note_ids': credit_note_ids,
    #             'overdue': aging_buckets,
    #             'current_date': statement_date,
    #             'invoice_residuals': invoice_residuals,
    #             'credit_note_residuals': credit_note_residuals,
    #         })

    #     return {
    #         'docs': docs,
    #         'company': self.env.company,
    #         'lines': lines,
    #         'open_invoices': data.get('open_invoices', False),
    #     }

    def _get_payment_values(self, payment, statement_date):
        """Get payment values for report display"""
        residual_amount = 0.0
        if payment.reconciled_invoice_ids:
            residual_amount = payment.residual_amount
        else:
            residual_amount = payment.amount
        
        return {
            'name': payment.name,
            'date': payment.date,
            'amount': payment.amount,
            'residual_amount': residual_amount,
            'ref': payment.ref,
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        partner_id = data.get('customer_id')
        open_invoices = data.get('open_invoices')
        branch = data.get('branch_id')
        branch_id = self.env['res.branch'].browse(branch)
        customer_ids = self.env['res.partner'].browse(partner_id)
        lines = []
        
        # Ensure statement_date is a proper date object
        if data.get('date_to'):
            if isinstance(data.get('date_to'), str):
                from datetime import datetime
                statement_date = datetime.strptime(data.get('date_to'), '%Y-%m-%d').date()
            else:
                statement_date = data.get('date_to')
        else:
            statement_date = fields.Date.context_today(self)
        
        for customer in customer_ids:
            # Initialize aging buckets
            aging_buckets = {
                'bucket_current': 0,
                'bucket_1_30': 0,
                'bucket_31_60': 0,
                'bucket_61_90': 0,
                'bucket_91_120': 0,
                'bucket_121_180': 0,
                'bucket_181_360': 0,
                'bucket_over_360': 0
            }

            # Base domains
            invoice_domain = [
                ('partner_id', '=', customer.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '<=', statement_date)
            ]
            
            credit_note_domain = [
                ('partner_id', '=', customer.id),
                ('move_type', '=', 'out_refund'),
                ('state', '=', 'posted'),
                ('invoice_date', '<=', statement_date)
            ]
            
            payment_domain = [
                ('partner_id', '=', customer.id),
                ('payment_type', 'in', ['inbound']),
                ('state', '=', 'posted'),
                ('date', '<=', statement_date)
            ]

            # Apply date filters if provided
            if data.get('date_from'):
                invoice_domain.append(('invoice_date', '>=', data.get('date_from')))
                credit_note_domain.append(('invoice_date', '>=', data.get('date_from')))
                payment_domain.append(('date', '>=', data.get('date_from')))

            # Apply branch filter if provided
            if branch_id:
                invoice_domain.append(('branch_id', '=', branch_id.id))
                credit_note_domain.append(('branch_id', '=', branch_id.id))
                payment_domain.append(('branch_id', '=', branch_id.id))

            # Get all records
            invoice_ids = self.env['account.move'].search(invoice_domain)
            credit_note_ids = self.env['account.move'].search(credit_note_domain)
            payment_ids = self.env['account.payment'].search(payment_domain)

            # Initialize result sets
            filtered_invoices = self.env['account.move']
            filtered_credit_notes = self.env['account.move']
            filtered_payments = []
            
            invoice_residuals = {}
            credit_note_residuals = {}
            
            # Process Invoices
            for invoice in invoice_ids:
                residual = self._get_invoice_residual_at_date(invoice, statement_date)
                invoice_residuals[invoice.id] = residual
                
                if open_invoices or residual > 0.01:
                    filtered_invoices |= invoice
                
                if residual > 0.01:
                    due_date = invoice.invoice_date_due or invoice.invoice_date
                    bucket_key = self._calculate_aging_buckets(residual, due_date, statement_date)
                    aging_buckets[bucket_key] += residual

            # Process Credit Notes
            for credit_note in credit_note_ids:
                residual = self._get_credit_note_residual_at_date(credit_note, statement_date)
                credit_note_residuals[credit_note.id] = residual
                
                if open_invoices or residual > 0.01:
                    filtered_credit_notes |= credit_note
                
                if residual > 0.01:
                    due_date = credit_note.invoice_date_due or credit_note.invoice_date
                    bucket_key = self._calculate_aging_buckets(residual, due_date, statement_date)
                    aging_buckets[bucket_key] -= residual

            # Process Payments - Modified to match first report's behavior
            for payment in payment_ids:
                # Show payments that are either:
                # 1. Reconciled with invoices AND have residual_amount < 0
                # 2. Not reconciled with invoices AND residual_amount != 0
                if (payment.reconciled_invoice_ids and payment.residual_amount < 0) or \
                   (not payment.reconciled_invoice_ids and payment.residual_amount != 0):
                    filtered_payments.append(self._get_payment_values(payment, statement_date))

            # Append customer data to lines
            lines.append({
                'customer_id': customer,
                'invoice_ids': filtered_invoices,
                'payment_ids': filtered_payments,
                'credit_note_ids': filtered_credit_notes,
                'overdue': aging_buckets,
                'current_date': statement_date,
                'invoice_residuals': invoice_residuals,
                'credit_note_residuals': credit_note_residuals,
            })

        return {
            'docs': docs,
            'company': self.env.company,
            'lines': lines,
            'open_invoices': data.get('open_invoices', False),
        }
    



    # @api.model
    # def _get_report_values(self, docids, data=None):
    #     model = self.env.context.get('active_model')
    #     docs = self.env[model].browse(self.env.context.get('active_id'))
    #     partner_id = data.get('customer_id')
    #     open_invoices = data.get('open_invoices')
    #     branch = data.get('branch_id')
    #     branch_id = self.env['res.branch'].browse(branch)
    #     customer_ids = self.env['res.partner'].browse(partner_id)
    #     lines = []
    #     merge_je_ids = self.env['account.move.line']
    #     fil_payment_ids = self.env['account.payment']
        
    #     # Ensure statement_date is a proper date object
    #     if data.get('date_to'):
    #         if isinstance(data.get('date_to'), str):
    #             # Convert string to date if needed
    #             from datetime import datetime
    #             statement_date = datetime.strptime(data.get('date_to'), '%Y-%m-%d').date()
    #         else:
    #             statement_date = data.get('date_to')
    #     else:
    #         statement_date = fields.Date.context_today(self)
        
    #     for customer in customer_ids:
    #         # Initialize aging buckets
    #         bucket_current = 0
    #         bucket_1_30 = 0
    #         bucket_31_60 = 0
    #         bucket_61_90 = 0
    #         bucket_91_120 = 0
    #         bucket_121_180 = 0
    #         bucket_181_360 = 0
    #         bucket_over_360 = 0

    #         payment_domain = [('partner_id', '=', customer.id), ('payment_type', 'in', ['inbound']), ('state', '=', 'posted')]
    #         invoice_domain = [('partner_id', '=', customer.id), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('amount_residual', '>', 0)]
    #         credit_note_domain = [('partner_id', '=', customer.id), ('move_type', '=', 'out_refund'), ('state', '=', 'posted'), ('amount_residual', '>', 0)]

    #         if data.get('date_from'):
    #             invoice_domain.append(('invoice_date', '>=', data.get('date_from')))
    #             credit_note_domain.append(('invoice_date', '>=', data.get('date_from')))
    #             payment_domain.append(('date', '>=', data.get('date_from')))

    #         if data.get('date_to'):
    #             invoice_domain.append(('invoice_date', '<=', data.get('date_to')))
    #             credit_note_domain.append(('invoice_date', '<=', data.get('date_to')))
    #             payment_domain.append(('date', '<=', data.get('date_to')))

    #         if open_invoices:
    #             invoice_domain.remove(('amount_residual', '>', 0))
    #             credit_note_domain.remove(('amount_residual', '>', 0))

    #         if branch_id:
    #             invoice_domain.append(('branch_id', '=', branch_id.id))
    #             credit_note_domain.append(('branch_id', '=', branch_id.id))
    #             payment_domain.append(('branch_id', '=', branch_id.id))

    #         invoice_ids = self.env['account.move'].search(invoice_domain)
    #         invoice_je = invoice_ids.mapped('line_ids')
    #         merge_je_ids |= invoice_je

    #         credit_note_ids = self.env['account.move'].search(credit_note_domain)
    #         credit_note_je = credit_note_ids.mapped('line_ids')
    #         merge_je_ids |= credit_note_je

    #         payment_ids = self.env['account.payment'].search(payment_domain)
    #         fil_payment_ids |= payment_ids.filtered(lambda x: x.reconciled_invoice_ids and x.residual_amount < 0)
    #         fil_payment_ids |= payment_ids.filtered(lambda x: not x.reconciled_invoice_ids and x.residual_amount != 0)
    #         payment_je = fil_payment_ids.mapped('line_ids').filtered(lambda x: x.amount_residual > 0)
    #         merge_je_ids |= payment_je
            
    #         # Use statement_date for aging calculations
    #         for move_line in merge_je_ids.filtered(lambda x: x.date and x.partner_id.id == customer.id):
    #             # Ensure due_date is a date object
    #             if move_line.move_id.invoice_date_due:
    #                 move_line_due_date = move_line.move_id.invoice_date_due
    #             else:
    #                 move_line_due_date = move_line.date
                
    #             # Calculate days difference safely
    #             days_overdue = (statement_date - move_line_due_date).days
                
    #             amount = move_line.amount_residual
    #             if move_line.payment_id:
    #                 amount = move_line.payment_id.residual_amount
                
    #             # Bucket calculation based on days overdue
    #             if days_overdue < 1:  # Current (not due yet)
    #                 bucket_current += amount
    #             elif 1 <= days_overdue <= 30:
    #                 bucket_1_30 += amount
    #             elif 31 <= days_overdue <= 60:
    #                 bucket_31_60 += amount
    #             elif 61 <= days_overdue <= 90:
    #                 bucket_61_90 += amount
    #             elif 91 <= days_overdue <= 120:
    #                 bucket_91_120 += amount
    #             elif 121 <= days_overdue <= 180:
    #                 bucket_121_180 += amount
    #             elif 181 <= days_overdue <= 360:
    #                 bucket_181_360 += amount
    #             else:  # over 360 days
    #                 bucket_over_360 += amount
                    
    #         overdue = {
    #             'bucket_current': bucket_current,
    #             'bucket_1_30': bucket_1_30,
    #             'bucket_31_60': bucket_31_60,
    #             'bucket_61_90': bucket_61_90,
    #             'bucket_91_120': bucket_91_120,
    #             'bucket_121_180': bucket_121_180,
    #             'bucket_181_360': bucket_181_360,
    #             'bucket_over_360': bucket_over_360,
    #         }

    #         lines.append({
    #             'customer_id': customer,
    #             'invoice_ids': invoice_ids,
    #             'payment_ids': fil_payment_ids,
    #             'credit_note_ids': credit_note_ids,
    #             'overdue': overdue,
    #             'current_date': statement_date,  # This is now guaranteed to be a date object
    #         })

    #     return {
    #         'docs': docs,
    #         'company': self.env.company,
    #         'lines': lines,
    #     }