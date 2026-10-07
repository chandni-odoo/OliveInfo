# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError
from datetime import datetime

class PaymentDistribution(models.TransientModel):
    _name = 'payment.distribution'
    _description = 'Payment Distribution'

    @api.model
    def _default_journal(self):
        journal = self.env['account.journal'].search([('type', 'in', ['bank', 'cash'])], limit=1)
        return journal.id if journal else False

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain=[('type', 'in', ['cash', 'bank'])], default=_default_journal)
    payment_date = fields.Date("Payment Date", default=fields.Date.context_today)
    reference = fields.Char('Memo') 
    payment_amount = fields.Monetary(string='Payment Amount', required=True)
    payment_type = fields.Many2one('account.payment.method.line', string='Payment Method', domain="[('journal_id', '=', journal_id),('payment_method_id.payment_type', '=', 'outbound')]")
    invoice_type = fields.Selection([('invoice', 'Customer Invoices'), ('bills','Vendor Bills'),
    ('credit_note', 'Vendor Credit Notes'), ('debit_note', 'Customer Credit Notes')], required=True, string='Invoice Type', default='invoice')
    distribution_line_ids = fields.One2many('payment.distribution.line', 'distribution_id', string='Partial Inovice Line')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    cheque_no = fields.Char('Cheque Number')
    receipt_date = fields.Date('Receipt Date', default=fields.Date.context_today)
    is_cheque = fields.Boolean()
    is_bank = fields.Boolean()

    @api.onchange('payment_type')
    def _assign_cheque_number(self):
        self.cheque_no = False
        if self.payment_type.name == "Checks":
            sequence = self.journal_id.check_sequence_id
            self.cheque_no = sequence.get_next_char(sequence.number_next_actual)

    @api.onchange('journal_id')
    def _assign_payment_type(self):
        if self.journal_id and self.journal_id.outbound_payment_method_line_ids:
            self.payment_type = self.journal_id.outbound_payment_method_line_ids[0].id

    @api.onchange('invoice_type')
    def _onchange_is_cheque(self):
        self.is_cheque = False
        self.is_bank = False
        if self.invoice_type == "bills" and self.journal_id.type == "bank":
            self.is_cheque = True
        if self.invoice_type == "bills":
            self.is_bank = True

    def get_partner_invoices(self):
        invoices = []
        res = {'invoice': 'out_invoice', 'bills': 'in_invoice', 'credit_note': 'in_refund', 'debit_note': 'out_refund'}
        domain = [('move_type', '=', res[self.invoice_type]), ('state', '=', 'posted'), ('partner_id', '=', self.partner_id.id), ('amount_residual', '>', '0')]
        invoice_ids = self.env['account.move'].search(domain)
        for inv in invoice_ids:
            invoices.append({
                'partner_id': inv.partner_id.id,
                'date_invoice': inv.invoice_date,
                'residual': inv.amount_residual,
                'invoice_total' : inv.amount_total,
                'invoice_id': inv.id,
                'currency_id': inv.currency_id and inv.currency_id.id or False
            })
        return invoices

    def select_invoices(self):
        self.distribution_line_ids = [(5,0,0)]
        invoices = self.get_partner_invoices()
        view_id = self.env.ref('pways_payment_distribution.select_invoice_line_tree_view').id
        return{
                'type': 'ir.actions.act_window',
                'name': "Select Invoice",
                'res_model': 'select.invoice.line',
                'target' : 'new',
                'view_mode': 'form',
                'view' : [[view_id, 'form']],
                'context': {'default_select_invoice_ids': [(0, 0, inv) for inv in invoices],
                            'default_partner_id': self.partner_id.id,
                            'default_payment_amount': self.payment_amount,
                            'default_invoice_type': self.invoice_type,
                            'default_currency_id': self.currency_id.id,
                            'default_journal_id': self.journal_id.id,
                            'default_payment_type': self.payment_type.id,
                            'default_cheque_no': self.cheque_no,
                            'default_receipt_date': self.receipt_date,
                            'default_reference': self.reference,
                },
        }

    def _check_valid_payment(self):
        currency_id = self.journal_id.currency_id
        if self.payment_amount < sum(self.distribution_line_ids.mapped('amount_to_pay')):
            raise UserError(_("Total amount of lines can't be greater than payment amount !"))
        if self.distribution_line_ids.filtered(lambda x: x.residual < x.amount_to_pay):
            raise UserError(_("allocated amount must be less than or equal to amount to pay !"))
        if self.distribution_line_ids.filtered(lambda x: currency_id and x.currency_id and x.currency_id != currency_id):
            raise UserError(_("Journal and invoices must have same currency !"))        

    def make_payment_distribution(self):
        self.ensure_one()
        payment_vals = {}
        move_lines = self.env['account.move.line']
        ref = ''
        if self.reference:
            ref = self.reference
        if self.cheque_no:
            ref = self.cheque_no
        if self.reference and self.cheque_no:
            ref = "%s / %s" %(self.reference, self.cheque_no)

        self._check_valid_payment()
        vals = {'invoice': {'payment_type': 'inbound', 'partner_type': 'customer'},
                'bills': {'payment_type': 'outbound', 'partner_type': 'supplier'},
                'credit_note':{'payment_type': 'inbound', 'partner_type': 'supplier'},
                'debit_note': {'payment_type': 'outbound', 'partner_type': 'customer'}}
        payment_vals.update(vals[self.invoice_type])
        payment_vals.update({
            'partner_id': self.partner_id and self.partner_id.id or False,
            'journal_id': self.journal_id and self.journal_id.id or False,
            'check_number': self.cheque_no,
            'payment_method_line_id': self.payment_type.id,
            'create_date': self.payment_date or self.Date.context_today(self),
            'ref': ref,
            'amount': self.payment_amount,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in') and self.env.ref('account.account_payment_method_manual_in').id
             if self.invoice_type in ['invoice', 'credit_note'] else self.env.ref('account.account_payment_method_manual_out') and self.env.ref('account.account_payment_method_manual_out').id,
            'receipt_date': self.receipt_date if self.receipt_date else datetime.today(),
        })
        payment = self.env['account.payment'].create(payment_vals)
        if payment:
            self.distribution_line_ids.write({'payment_id': payment.id})
            payment.action_post()
        lines_to_reconcile = self.distribution_line_ids.filtered(lambda x: x.payment_id)
        if not lines_to_reconcile or payment.state != 'posted':
            raise UserError(_("Either payment not created or confirmed !"))
        for line in lines_to_reconcile.filtered(lambda x:x.amount_to_pay > 0):
            invoice_move = line.invoice_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
            payment_move = line.payment_id.move_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
            move_lines |= (invoice_move + payment_move)
            if line.currency_id and invoice_move and payment_move:
                rate = line.currency_id.with_context(date=invoice_move.date).rate
                amount_reconcile_currency = line.currency_id.round(line.amount_to_pay * rate)
                if self.invoice_type in ['invoice', 'credit_note']:
                    self.env['account.partial.reconcile'].create({
                        'debit_move_id': invoice_move.id,
                        'credit_move_id': payment_move.id,
                        'amount': line.amount_to_pay,
                        'credit_amount_currency': amount_reconcile_currency,
                        'credit_currency_id': line.currency_id.id,
                        'debit_amount_currency': amount_reconcile_currency,
                        'debit_currency_id': line.currency_id.id,
                    })
                elif self.invoice_type in ['bills', 'debit_note']:
                    self.env['account.partial.reconcile'].create({
                        'credit_move_id': invoice_move.id,
                        'debit_move_id': payment_move.id,
                        'amount': line.amount_to_pay,
                        'credit_amount_currency': amount_reconcile_currency,
                        'credit_currency_id': line.currency_id.id,
                        'debit_amount_currency': amount_reconcile_currency,
                        'debit_currency_id': line.currency_id.id,
                    })

class PaymentDistributionLine(models.TransientModel):
    _name = 'payment.distribution.line'
    _description = 'Payment Distribution Line'

    select_invoice_id = fields.Many2one('select.invoice.line')
    distribution_id = fields.Many2one('payment.distribution', 'Distribution Wizard')
    check = fields.Boolean("Select", default=False)
    amount_to_pay = fields.Monetary(string='Amount', required=True, default=0.0)
    date_invoice = fields.Date(string='Invoice Date', readonly=True)
    invoice_total = fields.Monetary(string='Invoice Total', readonly=True)
    residual = fields.Monetary(string='Amount Due', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    payment_id = fields.Many2one('account.payment', string="Payment", readonly=True)
    invoice_id = fields.Many2one('account.move', string="Invoice", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)

class SelectInvoiceLines(models.TransientModel):
    _name = 'select.invoice.line'
    _description = 'Select Invoice Lines'

    select_all = fields.Boolean('Select All')
    select_invoice_ids = fields.One2many('payment.distribution.line', 'select_invoice_id', string='Select Invoices')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    payment_amount = fields.Monetary(string='Payment Amount', required=True)
    invoice_type = fields.Selection([('invoice', 'Customer Invoices'), ('bills','Vendor Bills'),
    ('credit_note', 'Vendor Credit Notes'), ('debit_note', 'Customer Credit Notes')], required=True, string='Invoice Type', default='invoice')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain=[('type', 'in', ['cash', 'bank'])])
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    payment_type = fields.Many2one('account.payment.method.line')
    cheque_no = fields.Char('Cheque Number')
    receipt_date = fields.Date('Receipt Date')
    reference = fields.Char('Memo')

    @api.onchange('select_all')
    def select_all_invoices(self):
        if self.select_all == True:
            for line in self.select_invoice_ids:
                line.check = True
        if self.select_all == False:
            for line in self.select_invoice_ids:
                line.check = False

    def confirm_invoice(self):
        invoices = []
        for invoice in self.select_invoice_ids.filtered(lambda x: x.check):
            invoices.append({
                'partner_id': invoice.partner_id.id,
                'date_invoice': invoice.date_invoice,
                'residual': invoice.residual,
                'invoice_total' : invoice.invoice_total,
                'invoice_id': invoice.invoice_id.id,
                'currency_id': invoice.currency_id and invoice.currency_id.id or False
            })
        
        view_id = self.env.ref('pways_payment_distribution.payment_distribution_form_view').id
        return{
                'type': 'ir.actions.act_window',
                'name': "Payment Distribution",
                'res_model': 'payment.distribution',
                'target' : 'new',
                'view_mode': 'form',
                'view' : [[view_id, 'form']],
                'context': {'default_distribution_line_ids': [(0, 0, inv) for inv in invoices],
                            'default_partner_id': self.partner_id.id,
                            'default_payment_amount': self.payment_amount,
                            'default_invoice_type': self.invoice_type,
                            'default_currency_id': self.currency_id.id,
                            'default_journal_id': self.journal_id.id,
                            'default_payment_type': self.payment_type.id,
                            'default_cheque_no': self.cheque_no,
                            'default_receipt_date': self.receipt_date,
                            'default_reference': self.reference,
                },
        }

    def cancel_wizard(self):
        view_id = self.env.ref('pways_payment_distribution.payment_distribution_form_view').id
        return{
                'type': 'ir.actions.act_window',
                'name': "Payment Distribution",
                'res_model': 'payment.distribution',
                'target' : 'new',
                'view_mode': 'form',
                'view' : [[view_id, 'form']],
                'context': {'default_partner_id': self.partner_id.id,
                            'default_payment_amount': self.payment_amount,
                            'default_invoice_type': self.invoice_type,
                            'default_currency_id': self.currency_id.id,
                            'default_journal_id': self.journal_id.id,
                            'default_payment_type': self.payment_type.id,
                            'default_cheque_no': self.cheque_no,
                            'default_receipt_date': self.receipt_date,
                            'default_reference': self.reference,
                },
        }