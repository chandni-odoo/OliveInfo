# -*- coding: utf-8 -*-
from odoo import models
from datetime import date, datetime, timedelta
from pytz import timezone, UTC
import pytz
import datetime


class AgedXlsx(models.AbstractModel):
    _name = 'report.pways_custom_ar_ap.aged_xlsx'
    _inherit = 'report.report_xlsx.abstract'


    def generate_xlsx_report(self, workbook, data, products):
        if data.get('active_record'):
            active_id = data.get('active_record')
            vals = []
            # bank_details = []
            aged_id = self.env['custom.ap.ar'].browse(int(active_id))
            sheet = workbook.add_worksheet("AR/AP Report")
            format1 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True, 'bg_color': '#D3D3D3'})
            format2 = workbook.add_format({'font_size': 10, 'bold': True, 'bg_color': '#D3D3D3'})
            format3 = workbook.add_format({'font_size': 10, 'align': 'left'})
            format4 = workbook.add_format({'font_size': 10, 'align': 'left'})
            format5 = workbook.add_format({'font_size': 10, 'bold': True})
            format1.set_align('center')

            name = ''
            if aged_id.aged_state == "ap":
                name = "Aged Payable"
            if aged_id.aged_state == "ar":
                name = "Aged Receivable"
            sheet.merge_range('A1:K1', 'Aged Details :- ' + name, format1)
            
            # Add new row for As on and Based on information
            based_on_text = dict(aged_id._fields['based_on'].selection).get(aged_id.based_on)
            sheet.merge_range('A2:K2', f'As on: {aged_id.as_on_date.strftime("%d/%m/%Y")} | Based on: {based_on_text}', format1)
            
            # Add customer/vendor and branch information if available
            customer_info = ""
            if aged_id.aged_state == "ar" and aged_id.customer_ids:
                customer_names = ", ".join(aged_id.customer_ids.mapped('name'))
                customer_info = f"Customers: {customer_names}"
            elif aged_id.aged_state == "ap" and aged_id.vendors_ids:
                vendor_names = ", ".join(aged_id.vendors_ids.mapped('name'))
                customer_info = f"Vendors: {vendor_names}"
                
            branch_info = ""
            if aged_id.branch_ids:
                branch_names = ", ".join(aged_id.branch_ids.mapped('name'))
                branch_info = f"Branches: {branch_names}"
            
            if customer_info or branch_info:
                info_text = " | ".join(filter(None, [customer_info, branch_info]))
                sheet.merge_range('A3:K3', info_text, format1)
                row_offset = 3
            else:
                row_offset = 2
            
            sheet.merge_range(f'A{row_offset+1}:B{row_offset+1}', 'Partner Name', format3)

            due_range_ids = aged_id.due_range_ids
            row = row_offset
            col = 1
            sheet.write(row, col+1, 'Credit Limit', format3)
            col += 1
            sheet.write(row, col+1, 'Payment Terms', format3)
            col += 1
            sheet.write(row, col+1, 'Branch', format3)
            col += 1
            sheet.write(row, col+1, 'Responsible Person', format3)
            col += 1
            for due_range in due_range_ids:
                sheet.write(row, col+1, due_range.name, format3)
                col += 1
            sheet.write(row, col+1, "Other", format3)
            col += 1
            sheet.write(row, col+1, "Total", format3)

            invoice_domain = [('reconciled', '=', False), ('move_id.state', '=', 'posted')]
            if aged_id.based_on == 'due_date':
                invoice_domain.append(('date_maturity', '<=', aged_id.as_on_date))
            elif aged_id.based_on == 'invoice_date':
                invoice_domain.append(('date', '<=', aged_id.as_on_date))
            elif aged_id.based_on == 'received_date':
                # For received date, we'll need to check the custom_invoice_date field in account.move
                invoice_domain.append(('date', '<=', aged_id.as_on_date))
                
            if aged_id.aged_state == "ar":
                invoice_domain.append(('account_id.internal_type', '=', 'receivable'))
            if aged_id.aged_state == "ap":
                invoice_domain.append(('account_id.internal_type', '=', 'payable'))
            if aged_id.customer_ids:
                invoice_domain.append(('partner_id', 'in', aged_id.customer_ids.ids))
            if aged_id.vendors_ids:
                invoice_domain.append(('partner_id', 'in', aged_id.vendors_ids.ids))
            if aged_id.branch_ids:
                invoice_domain.append(('branch_id', 'in', aged_id.branch_ids.ids))
            
            fil_move_line_ids = self.env['account.move.line'].search(invoice_domain)
            
            # filter partner
            partner_dict = {}
            for line in fil_move_line_ids:
                if line.partner_id not in partner_dict:
                    partner_dict[line.partner_id] = line
                else:
                    partner_dict[line.partner_id] |= line
            recs = {}
            for partner, values in partner_dict.items():
                branch_id = self.env['res.branch']
                if aged_id.branch_ids:
                    branch_ids = values.mapped('branch_id')
                    branch_id = branch_ids[0] if branch_ids else branch_id
                # recs.update({partner.name: {}})
                # recs[partner.name].update({
                #     'credit_limit': "{:,.2f}".format(partner.credit_limit), 
                #     'credit_days': "{:,.2f}".format(partner.credit_days), 
                #     'branch_id': branch_id.name if aged_id.branch_ids and branch_id else '', 
                #     'collection_manager': partner.collection_manager.name if partner.collection_manager else ''
                # })

                payment_terms = ""
                if aged_id.aged_state == "ar":
                    payment_terms = partner.property_payment_term_id.name if partner.property_payment_term_id else ""
                elif aged_id.aged_state == "ap":
                    payment_terms = partner.property_supplier_payment_term_id.name if partner.property_supplier_payment_term_id else ""
                
                recs.update({partner.name: {}})
                recs[partner.name].update({
                    'credit_limit': "{:,.2f}".format(partner.credit_limit), 
                    'payment_terms': payment_terms,  # Changed from credit_days
                    'branch_id': branch_id.name if aged_id.branch_ids and branch_id else '', 
                    'collection_manager': partner.collection_manager.name if partner.collection_manager else ''
                })
    
                fil_values = self.env['account.move.line']
                max_range = 0
                total_values = 0
                if aged_id.due_range_ids:
                    max_range = max(aged_id.due_range_ids.mapped('to_range'))
                for due_range in aged_id.due_range_ids:
                    amount = 0
                    start_day = due_range.from_range
                    end_day = due_range.to_range
                    start_date = aged_id.as_on_date - timedelta(days=int(start_day))
                    end_date = aged_id.as_on_date - timedelta(days=int(end_day))
                    
                    if aged_id.based_on == "due_date":
                        fil_values = values.filtered(lambda x: x.date_maturity and x.date_maturity <= start_date and x.date_maturity >= end_date)
                    elif aged_id.based_on == "invoice_date":
                        fil_values = values.filtered(lambda x: x.move_id.invoice_date and x.move_id.invoice_date <= start_date and x.move_id.invoice_date >= end_date)
                        fil_values |= values.filtered(lambda x: x.date and x.date <= start_date and x.date >= end_date and not x.move_id.invoice_date)
                    elif aged_id.based_on == "received_date" and aged_id.aged_state == "ap":
                        # For AP with received date (using custom_invoice_date)
                        fil_values = values.filtered(lambda x: x.move_id.custom_invoice_date and x.move_id.custom_invoice_date <= start_date and x.move_id.custom_invoice_date >= end_date)
                        # Fallback to invoice_date if custom_invoice_date is not set
                        no_received_date = values.filtered(lambda x: not x.move_id.custom_invoice_date)
                        fil_values |= no_received_date.filtered(lambda x: x.move_id.invoice_date and x.move_id.invoice_date <= start_date and x.move_id.invoice_date >= end_date)
                        fil_values |= no_received_date.filtered(lambda x: x.date and x.date <= start_date and x.date >= end_date and not x.move_id.invoice_date)
                    else:
                        # If receivable with received_date selected, fallback to invoice_date
                        fil_values = values.filtered(lambda x: x.move_id.invoice_date and x.move_id.invoice_date <= start_date and x.move_id.invoice_date >= end_date)
                        fil_values |= values.filtered(lambda x: x.date and x.date <= start_date and x.date >= end_date and not x.move_id.invoice_date)
                    
                    for item in fil_values:
                        days = -1
                        if aged_id.based_on == "due_date":
                            days = (aged_id.as_on_date - (item.date_maturity if item.date_maturity else date.today())).days
                        elif aged_id.based_on == "invoice_date":
                            invoice_date = item.move_id.invoice_date if item.move_id.invoice_date else item.date
                            days = (aged_id.as_on_date - invoice_date).days
                        elif aged_id.based_on == "received_date" and aged_id.aged_state == "ap":
                            if item.move_id.custom_invoice_date:
                                days = (aged_id.as_on_date - item.move_id.custom_invoice_date).days
                            else:
                                # Fallback to invoice date if received date not available
                                invoice_date = item.move_id.invoice_date if item.move_id.invoice_date else item.date
                                days = (aged_id.as_on_date - invoice_date).days
                        else:
                            # Default for AR when received_date is selected
                            invoice_date = item.move_id.invoice_date if item.move_id.invoice_date else item.date
                            days = (aged_id.as_on_date - invoice_date).days
                        
                        if days >= start_day and days <= end_day:
                            if aged_id.aged_state == "ap":
                                total = 0
                                partial_payment_ids = item.matched_credit_ids.filtered(lambda a: a.credit_move_id.id == item.id and a.max_date <= start_date)
                                total = item.amount_residual - sum(partial_payment_ids.mapped('amount'))
                                if item.move_id.move_type == "in_refund":
                                    total = abs(total)
                                amount += total
                            if aged_id.aged_state == "ar":
                                rec_total = 0
                                partial_payment_ids = item.matched_debit_ids.filtered(lambda a: a.debit_move_id.id == item.id and a.max_date <= start_date)
                                rec_total = item.amount_residual - sum(partial_payment_ids.mapped('amount'))
                                if item.move_id.move_type == "out_refund":
                                    rec_total = -abs(rec_total)
                                amount += rec_total
                        amount = round(amount, 2)
                    if aged_id.aged_state == "ap":
                        if amount <= 0:
                            amount = abs(amount)
                        else:
                            amount = -abs(amount)
                    total_values += amount
                    recs[partner.name].update({due_range.name: "{:,.2f}".format(amount)})

                # Other
                fil_values = self.env['account.move.line']
                total_amount = 0
                start_date = aged_id.as_on_date - timedelta(days=int(max_range))
                if aged_id.based_on == "due_date":
                    fil_values = values.filtered(lambda x: x.date_maturity and x.date_maturity <= start_date)
                elif aged_id.based_on == "invoice_date":
                    fil_values = values.filtered(lambda x: x.move_id.invoice_date and x.move_id.invoice_date <= start_date)
                    fil_values |= values.filtered(lambda x: x.date and x.date <= start_date and not x.move_id.invoice_date)
                elif aged_id.based_on == "received_date" and aged_id.aged_state == "ap":
                    fil_values = values.filtered(lambda x: x.move_id.custom_invoice_date and x.move_id.custom_invoice_date <= start_date)
                    # Fallback to invoice_date if custom_invoice_date is not set
                    no_received_date = values.filtered(lambda x: not x.move_id.custom_invoice_date)
                    fil_values |= no_received_date.filtered(lambda x: x.move_id.invoice_date and x.move_id.invoice_date <= start_date)
                    fil_values |= no_received_date.filtered(lambda x: x.date and x.date <= start_date and not x.move_id.invoice_date)
                else:
                    # Default for AR when received_date is selected
                    fil_values = values.filtered(lambda x: x.move_id.invoice_date and x.move_id.invoice_date <= start_date)
                    fil_values |= values.filtered(lambda x: x.date and x.date <= start_date and not x.move_id.invoice_date)
                
                for item in fil_values:
                    days = -1
                    if aged_id.based_on == "due_date":
                        days = (aged_id.as_on_date - (item.date_maturity if item.date_maturity else date.today())).days
                    elif aged_id.based_on == "invoice_date":
                        invoice_date = item.move_id.invoice_date if item.move_id.invoice_date else item.date
                        days = (aged_id.as_on_date - invoice_date).days
                    elif aged_id.based_on == "received_date" and aged_id.aged_state == "ap":
                        if item.move_id.custom_invoice_date:
                            days = (aged_id.as_on_date - item.move_id.custom_invoice_date).days
                        else:
                            # Fallback to invoice date if received date not available
                            invoice_date = item.move_id.invoice_date if item.move_id.invoice_date else item.date
                            days = (aged_id.as_on_date - invoice_date).days
                    else:
                        # Default for AR when received_date is selected
                        invoice_date = item.move_id.invoice_date if item.move_id.invoice_date else item.date
                        days = (aged_id.as_on_date - invoice_date).days
                    
                    if days > max_range:
                        if aged_id.aged_state == "ap":
                            total = 0
                            partial_payment_ids = item.matched_credit_ids.filtered(lambda a: a.credit_move_id.id == item.id and a.max_date <= start_date)
                            total = item.amount_residual - sum(partial_payment_ids.mapped('amount'))
                            if item.move_id.move_type == "in_refund":
                                total = abs(total)
                            total_amount += total
                        if aged_id.aged_state == "ar":
                            rec_total = 0
                            partial_payment_ids = item.matched_debit_ids.filtered(lambda a: a.debit_move_id.id == item.id and a.max_date <= start_date)
                            rec_total = item.amount_residual - sum(partial_payment_ids.mapped('amount'))
                            if item.move_id.move_type == "out_refund":
                                rec_total = -abs(rec_total)
                            total_amount += rec_total
                    total_amount = round(total_amount, 2)
                if aged_id.aged_state == "ap":
                    if total_amount <= 0:
                        total_amount = abs(total_amount)
                    else:
                        total_amount = -abs(total_amount)
                total_values += total_amount
                recs[partner.name].update({'other': "{:,.2f}".format(total_amount), 'total_values': "{:,.2f}".format(total_values)})
            vals.append(recs)

            row_number = row_offset + 1
            column_number = 0
            col = 1
            row = row_offset + 1
            for value in vals:
                for key, values in value.items():
                    sheet.merge_range(row_number, column_number, row_number, column_number+1, key, format4)
                    row_number += 1
                    col = 1
                    for v1, values in values.items():
                        sheet.write(row, col+1, values, format3)
                        col += 1
                    row += 1


    # def generate_xlsx_report(self, workbook, data, products):
    #     if data.get('active_record'):
    #         active_id = data.get('active_record')
    #         vals = []
    #         # bank_details = []
    #         aged_id = self.env['custom.ap.ar'].browse(int(active_id))
    #         sheet = workbook.add_worksheet("AR/AP Report")
    #         format1 = workbook.add_format({'font_size': 10, 'align': 'center' , 'bold': True, 'bg_color': '#D3D3D3'})
    #         format2 = workbook.add_format({'font_size': 10, 'bold': True, 'bg_color': '#D3D3D3'})
    #         format3 = workbook.add_format({'font_size': 10, 'align': 'left'})
    #         format4 = workbook.add_format({'font_size': 10, 'align': 'left'})
    #         format1.set_align('center')

    #         name = ''
    #         if aged_id.aged_state == "ap":
    #             name = "Aged Payable"
    #         if aged_id.aged_state == "ar":
    #             name = "Aged Receivable"
    #         sheet.merge_range('A1:K1', 'Aged Details :- ' + name, format1)
    #         sheet.merge_range('A2:B2', 'Partner Name', format3)

    #         due_range_ids = aged_id.due_range_ids
    #         row = 1
    #         col = 1
    #         sheet.write(row, col+1, 'Credit Limit', format3)
    #         col += 1
    #         sheet.write(row, col+1, 'Credit Period', format3)
    #         col += 1
    #         sheet.write(row, col+1, 'Branch', format3)
    #         col += 1
    #         sheet.write(row, col+1, 'Responsible Person', format3)
    #         col += 1
    #         for due_range in due_range_ids:
    #             sheet.write(row, col+1, due_range.name , format3)
    #             col += 1
    #         sheet.write(row, col+1, "Other" , format3)
    #         col += 1
    #         sheet.write(row, col+1, "Total" , format3)

    #         invoice_domain = [('reconciled', '=', False), ('move_id.state', '=', 'posted')]
    #         if aged_id.based_on == 'due_date':
    #             invoice_domain.append(('date_maturity','<=', aged_id.as_on_date))
    #         if aged_id.based_on == 'invoice_date':
    #             invoice_domain.append(('date', '<=' , aged_id.as_on_date))                
    #         if aged_id.aged_state == "ar":
    #             invoice_domain.append(('account_id.internal_type', '=' , 'receivable'))
    #         if aged_id.aged_state == "ap":
    #             invoice_domain.append(('account_id.internal_type', '=', 'payable'))
    #         if aged_id.customer_ids:
    #             invoice_domain.append(('partner_id', 'in', aged_id.customer_ids.ids))
    #         if aged_id.vendors_ids:
    #             invoice_domain.append(('partner_id', 'in' , aged_id.vendors_ids.ids))
    #         if aged_id.branch_ids:
    #             invoice_domain.append(('branch_id', 'in' , aged_id.branch_ids.ids))
           
    #         fil_move_line_ids = self.env['account.move.line'].search(invoice_domain)
    #         # filter partner
    #         partner_dict = {}
    #         for line in fil_move_line_ids:
    #             if line.partner_id not in partner_dict:
    #                 partner_dict[line.partner_id] = line
    #             else:
    #                 partner_dict[line.partner_id] |= line
    #         recs = {}
    #         for partner, values in partner_dict.items():
    #             branch_id = self.env['res.branch']
    #             if aged_id.branch_ids:
    #                 branch_ids = values.mapped('branch_id')
    #                 branch_id = branch_ids[0]
    #             recs.update({partner.name: {}})
    #             recs[partner.name].update({'credit_limit': "{:,.2f}".format(partner.credit_limit), 'credit_days': "{:,.2f}".format(partner.credit_days), 'branch_id': branch_id.name if aged_id.branch_ids else '', 'collection_manager': partner.collection_manager.name if partner.collection_manager else ''})
    #             fil_values = self.env['account.move.line']
    #             max_range = 0
    #             total_values = 0
    #             if aged_id.due_range_ids:
    #                 max_range =  max(aged_id.due_range_ids.mapped('to_range'))
    #             for due_range in aged_id.due_range_ids:
    #                 amount = 0
    #                 start_day = due_range.from_range
    #                 end_day = due_range.to_range
    #                 start_date = aged_id.as_on_date - timedelta(days=int(start_day))
    #                 end_date = aged_id.as_on_date - timedelta(days=int(end_day))
    #                 if aged_id.based_on == "due_date":
    #                     fil_values = values.filtered(lambda x: x.date_maturity and x.date_maturity <= start_date and x.date_maturity >= end_date)
    #                 if aged_id.based_on == "invoice_date":
    #                     fil_values |= values.filtered(lambda x: x.move_id.invoice_date and x.move_id.invoice_date <= start_date and x.move_id.invoice_date >= end_date)
    #                     fil_values |= values.filtered(lambda x: x.date and x.date <= start_date and x.date >= end_date)
    #                 for item in fil_values:
    #                     days = -1
    #                     if aged_id.based_on == "due_date":
    #                         days = (aged_id.as_on_date - item.date_maturity if item.date_maturity else  date.today()).days
    #                     if aged_id.based_on == "invoice_date":
    #                         invoice_date = item.move_id.invoice_date if item.move_id.invoice_date else item.date
    #                         days = (aged_id.as_on_date - invoice_date).days
    #                     if days >= start_day and days <= end_day:
    #                         if aged_id.aged_state == "ap":
    #                             total = 0
    #                             partial_payment_ids = item.matched_credit_ids.filtered(lambda a: a.credit_move_id.id == item.id and a.max_date <= start_date)
    #                             total = item.amount_residual - sum(partial_payment_ids.mapped('amount'))
    #                             if item.move_id.move_type == "in_refund":
    #                                 total = abs(total)
    #                             amount += total
    #                         if aged_id.aged_state == "ar":
    #                             rec_total = 0
    #                             partial_payment_ids = item.matched_debit_ids.filtered(lambda a: a.debit_move_id.id == item.id and a.max_date <= start_date)
    #                             rec_total = item.amount_residual - sum(partial_payment_ids.mapped('amount'))
    #                             if item.move_id.move_type == "out_refund":
    #                                 rec_total = -abs(rec_total)
    #                             amount += rec_total
    #                     amount = round(amount,2)
    #                 if aged_id.aged_state == "ap":
    #                     if amount <= 0:
    #                         amount = abs(amount)
    #                     else:
    #                         amount = -abs(amount)
    #                 total_values += amount
    #                 recs[partner.name].update({due_range.name: "{:,.2f}".format(amount)})

    #             # Other
    #             fil_values = self.env['account.move.line']
    #             total_amount = 0
    #             start_date = aged_id.as_on_date - timedelta(days=int(max_range))
    #             if aged_id.based_on == "due_date":
    #                 fil_values = values.filtered(lambda x: x.date_maturity and x.date_maturity <= start_date)
    #             if aged_id.based_on == "invoice_date":
    #                 fil_values |= values.filtered(lambda x: x.move_id.invoice_date and x.move_id.invoice_date <= start_date)
    #                 fil_values |= values.filtered(lambda x: x.date and x.date <= start_date)
    #             for item in fil_values:
    #                 days = -1
    #                 if aged_id.based_on == "due_date":
    #                     days = (aged_id.as_on_date - item.date_maturity if item.date_maturity else  date.today()).days
    #                 if aged_id.based_on == "invoice_date":
    #                     invoice_date = item.move_id.invoice_date if item.move_id.invoice_date else item.date
    #                     days = (aged_id.as_on_date - invoice_date).days
    #                 if days > max_range:
    #                     if aged_id.aged_state == "ap":
    #                         total = 0
    #                         partial_payment_ids = item.matched_credit_ids.filtered(lambda a: a.credit_move_id.id == item.id and a.max_date <= start_date)
    #                         total = item.amount_residual - sum(partial_payment_ids.mapped('amount'))
    #                         if item.move_id.move_type == "in_refund":
    #                             total = abs(total)
    #                         total_amount += total
    #                     if aged_id.aged_state == "ar":
    #                         rec_total = 0
    #                         partial_payment_ids = item.matched_debit_ids.filtered(lambda a: a.debit_move_id.id == item.id and a.max_date <= start_date)
    #                         rec_total = item.amount_residual - sum(partial_payment_ids.mapped('amount'))
    #                         if item.move_id.move_type == "out_refund":
    #                             rec_total = -abs(rec_total)
    #                         total_amount += rec_total
    #                 total_amount = round(total_amount,2)
    #             if aged_id.aged_state == "ap":
    #                 if total_amount <= 0:
    #                     total_amount = abs(total_amount)
    #                 else:
    #                     total_amount = -abs(total_amount)
    #             total_values += total_amount
    #             recs[partner.name].update({'other': "{:,.2f}".format(total_amount), 'total_values': "{:,.2f}".format(total_values)})
    #         vals.append(recs)

    #         row_number = 2
    #         column_number = 0
    #         col = 1
    #         row = 2
    #         for value in vals:
    #             for key, values in value.items():
    #                 sheet.merge_range(row_number, column_number, row_number, column_number+1, key, format4)
    #                 row_number += 1
    #                 col = 1
    #                 for v1, values in values.items():
    #                     sheet.write(row, col+1, values , format3)
    #                     col += 1
    #                 row += 1


