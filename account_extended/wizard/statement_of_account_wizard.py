from odoo import models, fields, api, _
import datetime
from datetime import timedelta, date


class StatementOfAccountWizard(models.TransientModel):
    _name = 'statement.account.wizard'
    _description = "statement account wizard"

    customer_ids = fields.Many2many('res.partner')
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
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
        return self.env.ref('account_extended.action_wizard_report_details').report_action(self, data=data)

class CustomerReportDetails(models.AbstractModel):
    _name = 'report.account_extended.customer_report_details_templete'

    def _get_payment_values(self, payment_ids):
        for payment in payment_ids:
            invoice_id = payment.mapped('reconciled_invoice_ids')
    
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
        overdue = []
        merge_je_ids = self.env['account.move.line']
        fil_payment_ids = self.env['account.payment']
        for customer in customer_ids:
            # current = 0
            # row_1 = 0
            # row_2 = 0
            # row_3 = 0
            # row_4 = 0
            # row_5 = 0

            bucket_0_30 = 0
            bucket_31_60 = 0
            bucket_61_90 = 0
            bucket_91_120 = 0
            bucket_121_180 = 0
            bucket_181_360 = 0
            bucket_over_360 = 0

            payment_domain = [('partner_id', '=', customer.id), ('payment_type', 'in', ['inbound']), ('state', '=', 'posted')]
            invoice_domain = [('partner_id', '=', customer.id), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('amount_residual', '>', 0)]
            credit_note_domain = [('partner_id', '=', customer.id), ('move_type', '=', 'out_refund'), ('state', '=', 'posted'), ('amount_residual', '>', 0)]

            if data.get('date_from'):
                invoice_domain.append(('invoice_date', '>=', data.get('date_from')))
                credit_note_domain.append(('invoice_date', '>=', data.get('date_from')))
                payment_domain.append(('date', '>=', data.get('date_from')))

            if data.get('date_to'):
                invoice_domain.append(('invoice_date', '<=', data.get('date_to')))
                credit_note_domain.append(('invoice_date', '<=', data.get('date_to')))
                payment_domain.append(('date', '<=', data.get('date_to')))

            if open_invoices:
                invoice_domain.remove(('amount_residual', '>', 0))
                credit_note_domain.remove(('amount_residual', '>', 0))

            if branch_id:
                invoice_domain.append(('branch_id', '=', branch_id.id))
                credit_note_domain.append(('branch_id', '=', branch_id.id))
                payment_domain.append(('branch_id', '=', branch_id.id))

            invoice_ids = self.env['account.move'].search(invoice_domain)
            invoice_je = invoice_ids.mapped('line_ids')
            merge_je_ids |= invoice_je

            credit_note_ids = self.env['account.move'].search(credit_note_domain)
            credit_note_je = credit_note_ids.mapped('line_ids')
            merge_je_ids |= credit_note_je

            payment_ids = self.env['account.payment'].search(payment_domain)
            fil_payment_ids |= payment_ids.filtered(lambda x: x.reconciled_invoice_ids and x.residual_amount < 0)
            fil_payment_ids |=  payment_ids.filtered(lambda x: not x.reconciled_invoice_ids and x.residual_amount != 0)
            payment_je = fil_payment_ids.mapped('line_ids').filtered(lambda x: x.amount_residual > 0)
            merge_je_ids |= payment_je
            today = datetime.date.today()
            for move_line in merge_je_ids.filtered(lambda x: x.date and x.partner_id.id == customer.id):
                move_line_date = move_line.move_id.invoice_date if move_line.move_id.invoice_date else move_line.date
                filter_days = abs(today - move_line_date).days
                amount = move_line.amount_residual
                if move_line.payment_id:
                    amount = move_line.payment_id.residual_amount
                # calculation
            #     if filter_days >= 0 and filter_days <= 60:
            #        current += amount
            #     if filter_days >= 61 and filter_days <= 90:
            #        row_1 += amount
            #     if filter_days >= 91 and filter_days <= 120:
            #        row_2 += amount
            #     if filter_days >= 121 and filter_days <= 180:
            #        row_3 += amount
            #     if filter_days >= 181 and filter_days <= 360:
            #        row_4 += amount
            #     if filter_days > 360:
            #        row_5 += amount
            # overdue = {
            #     'current': current,
            #     'row_1': row_1,
            #     'row_2': row_2,
            #     'row_3': row_3,
            #     'row_4': row_4,
            #     'row_5': row_5,
            # }
                if filter_days <= 30:
                    bucket_0_30 += amount
                elif 31 <= filter_days <= 60:
                    bucket_31_60 += amount
                elif 61 <= filter_days <= 90:
                    bucket_61_90 += amount
                elif 91 <= filter_days <= 120:
                    bucket_91_120 += amount
                elif 121 <= filter_days <= 180:
                    bucket_121_180 += amount
                elif 181 <= filter_days <= 360:
                    bucket_181_360 += amount
                else:  # over 360 days
                    bucket_over_360 += amount
                    
            overdue = {
                'bucket_0_30': bucket_0_30,
                'bucket_31_60': bucket_31_60,
                'bucket_61_90': bucket_61_90,
                'bucket_91_120': bucket_91_120,
                'bucket_121_180': bucket_121_180,
                'bucket_181_360': bucket_181_360,
                'bucket_over_360': bucket_over_360,
            }

            lines.append({
                'customer_id': customer,
                'invoice_ids': invoice_ids,
                'payment_ids': fil_payment_ids,
                'credit_note_ids': credit_note_ids,
                'overdue': overdue,
                'current_date': today,
            })

        return {
            'docs': docs,
            'company': self.env.company,
            'lines':lines,
        }
