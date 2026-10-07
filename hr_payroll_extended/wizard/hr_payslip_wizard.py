
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrPaySlipWizard(models.TransientModel):
    _name = "farmer.payment.summary.wizard"
    _description = "Farmer Payment Summary Wizard"


    def action_print_report(self):
        data = {}
        return self.env.ref('out_grower_extended.action_farmer_payment_summary_report').report_action(self, data=data)

class PaymentSummaryReport(models.AbstractModel):
    _name = 'report.out_grower_extended.farmer_payment_summary_report'

    def _get_group_by_partner(self, bill_ids):
        group_by_partner_id  = {}
        for bill in bill_ids:
            partner_id = bill.partner_id
            if partner_id not in group_by_partner_id:
                group_by_partner_id[partner_id] = bill
            else:
                group_by_partner_id[partner_id] |= bill
        return group_by_partner_id

    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        partner_ids = data.get('partner_ids')
        lines = []
        domain=[('partner_id.is_farmer', '=', True), ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid','partial']), ('invoice_date', '>=', date_from), ('invoice_date', '<=', date_to)]
        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))
        bill_ids = self.env['account.move'].search(domain)
        group_by_partner_id = self._get_group_by_partner(bill_ids)
        total_netwt = 0.0
        amount_total = 0.0
        total_netwt = 0.0
        total_amount = 0.0
        for partner_id, bill_ids in group_by_partner_id.items():
            line_ids = bill_ids.mapped('invoice_line_ids')
            netwt=  sum(line_ids.mapped('quantity'))
            amount = sum(bill_ids.mapped('amount_total'))
            total_netwt += netwt 
            total_amount += amount
            partner_bank_id  = partner_id.bank_ids and partner_id.bank_ids[0]
            lines.append({
                'farmer_code': partner_id.code,
                'farmer_name': partner_id.display_name,
                'national_id': partner_id.national_id,
                'contact_no': partner_id.mobile,
                'account_no': partner_bank_id.acc_number,
                'bank_id': partner_bank_id.bank_id.name,
                'branch_id': partner_bank_id.branch_id.branch_name,
                'bank_code': partner_bank_id.bank_id.bic,
                'branch_code': partner_bank_id.branch_id.branch_code,
                'netwt': netwt,
                'amount': amount,
            })
        return {
            'docs' : docs,
            'lines': lines,
            'total_netwt': total_netwt,
            'total_amount': total_amount,
        }
