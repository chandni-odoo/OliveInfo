# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import time
import tempfile
import binascii
import xlrd
import io
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime
from odoo.exceptions import Warning
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, exceptions, api, _

import logging
_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': -1,
    'in_invoice': -1,
    'out_refund': 1,
}

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    multiple_payment_amount = fields.Float(string="Multiple Payment Amount")

class gen_inv_inherit(models.TransientModel):
    _inherit = "gen.invoice"

    stage = fields.Selection(
        [('draft', 'Import Draft Invoice'), ('confirm', 'Validate Invoice Automatically With Import'),('payment', 'Import Invoice with Payment')],
        string="Invoice Stage Option", default='draft')
    partial_payment = fields.Selection(
        [('keep','Keep Open'),('writeoff','Write-Off')],
        string="Partial Payment",default='keep')
    writeoff_account = fields.Many2one('account.account',string="Write-Off Account")
    allow_payment = fields.Boolean(string="Allow Payment Amount more then Invoice Amount")

    def find_invoice_date(self, date):
        DATETIME_FORMAT = "%d/%m/%Y"
        try:
            i_date = datetime.strptime(date, DATETIME_FORMAT).date()
        except Exception:
            raise ValidationError(_('Wrong Date Format. Date Should be in format YYYY-MM-DD.'))
        return i_date

    def find_branch_id(self, name):
        branch_id = self.env['res.branch']
        branch_search = branch_id.search([('name', '=', name)])
        if branch_search:
            return branch_search[0]
        else:
            raise ValidationError(_('Not Valid Branch Name "%s"') % name)

    def create_payment(self,payment):
        for res in payment: 
            if res.state in ['draft']:
                res.action_post()
            journal = self.env['account.journal'].search([('name','like',payment[res][0])],limit=1)
            if not journal:
                raise ValidationError(_('Journal %s does not exist.' %payment[res][0]))
                
            sign = res.move_type in ['in_refund', 'out_refund'] and -1 or 1
            date_payment = payment[res][2]
            date_payment = self.find_invoice_date(payment[res][2])
            branch_payment = self.find_branch_id(payment[res][3]) 

            if not self.allow_payment:
                if float(payment[res][1]) > res.amount_total:
                    raise UserError(_('Payment Amount is Bigger then Invoice "%s"!'%(res.name)))
            for lines in res.invoice_line_ids:
                if lines.multiple_payment_amount != 0.0:
                    payment_method = False
                    amount = float(lines.multiple_payment_amount) * MAP_INVOICE_TYPE_PAYMENT_SIGN[res.move_type] * sign
                    if MAP_INVOICE_TYPE_PARTNER_TYPE[res.move_type] == 'customer':
                        payment_method = journal.inbound_payment_method_line_ids and journal.inbound_payment_method_line_ids[0]
                    elif MAP_INVOICE_TYPE_PARTNER_TYPE[res.move_type] == 'supplier':
                        payment_method = journal.outbound_payment_method_line_ids and journal.outbound_payment_method_line_ids[0]
                    if payment_method:
                        payment_method = payment_method.payment_method_id
                    if res.amount_total != amount:
                        if self.partial_payment == 'keep':
                            pay_rec = self.env['account.payment'].with_context(Import=True).create({
                                'amount': abs(float(amount)),
                                'currency_id': res.currency_id.id,
                                'payment_type': amount > 0 and 'inbound' or 'outbound',
                                'partner_id': res.commercial_partner_id.id,
                                'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[res.move_type],
                                'move_type' : res.move_type,
                                'company_id' : res.company_id.id,
                                'ref': " ".join(i.payment_reference or i.ref or i.name for i in res),
                                'journal_id':journal.id,
                                'date': date_payment,
                                'payment_method_id': payment_method.id,
                                'branch_id':branch_payment.id,
                                })
                        elif self.partial_payment == 'writeoff':
                            payment_vals = {
                                'date': date_payment,
                                'amount': abs(amount),
                                'payment_type': amount > 0 and 'inbound' or 'outbound',
                                'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[res.move_type],
                                'ref':" ".join(i.payment_reference or i.ref or i.name for i in res),
                                'journal_id': journal.id,
                                'move_type' : res.move_type,
                                'currency_id': res.currency_id.id,
                                'partner_id': res.commercial_partner_id.id,
                                'company_id' : res.company_id.id,
                                'payment_method_id':payment_method.id,
                                'branch_id':branch_payment.id,
                            }
                            payment_difference = res.amount_residual - amount
                            if payment_difference > 0 :
                                payment_vals['write_off_line_vals'] = {
                                    'name': 'Write-Off',
                                    'amount': payment_difference,
                                    'account_id': self.writeoff_account.id,
                                }
                            pay_rec = self.env['account.payment'].with_context(Import=True).create(payment_vals)
                    else:
                        pay_rec = self.env['account.payment'].with_context(Import=True).create({
                                'amount': abs(float(amount)),
                                'currency_id': res.currency_id.id,
                                'payment_type': amount > 0 and 'inbound' or 'outbound',
                                'partner_id': res.commercial_partner_id.id,
                                'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[res.move_type],
                                'move_type' : res.move_type,
                                'company_id' : res.company_id.id,
                                'ref': " ".join(i.payment_reference or i.ref or i.name for i in res),
                                'journal_id':journal.id,
                                'date': date_payment,
                                'payment_method_id':payment_method.id,
                                })
                    pay_rec.action_post()
                    for record in pay_rec.move_id.line_ids:
                        if res.move_type in ['out_invoice','in_refund']:
                            if record.credit > 0:
                                lines = self.env['account.move.line'].browse(record.id) 
                        else:   
                            if record.debit > 0:
                                lines = self.env['account.move.line'].browse(record.id)
                    lines += res.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                        
    def import_csv(self):
        """Load Inventory data from the CSV file."""
        if self.stage == 'payment':
            if self.import_option == 'csv':

                keys = ['invoice', 'customer', 'currency', 'product','account', 'quantity', 'uom', 'description', 'price','discount','salesperson','tax','date','journal','amount','paymentdate', 'paymentbranch']
                
                try:
                    csv_data = base64.b64decode(self.file)
                    data_file = io.StringIO(csv_data.decode("utf-8"))
                    data_file.seek(0)
                    file_reader = []
                    csv_reader = csv.reader(data_file, delimiter=',')
                    file_reader.extend(csv_reader)
                except:
                    raise ValidationError(_("Please select an CSV/XLS file or You have selected invalid file"))

                values = {}
                invoice_ids=[]
                payment = {}
                for i in range(len(file_reader)):
                    field = list(map(str, file_reader[i]))
                    values = dict(zip(keys, field))
                    if values:
                        if i == 0:
                            continue
                        else:
                            values.update({'type':self.type,'option':self.import_option,'seq_opt':self.sequence_opt})
                            res = self.make_invoice(values)
                            res._recompute_dynamic_lines()
                            res._compute_amount()
                            invoice_ids.append(res)
                            if self.stage == 'payment':
                                if values.get('paymentdate') == '':
                                    raise UserError(_('Please assign a payment date'))  

                                if values.get('journal') and values.get('amount'):
                                    if res in payment:
                                        if payment[res][0] != values.get('journal'):
                                            raise UserError(_('Please Use same Journal for Invoice %s' %values.get('invoice')))   
                                        else:
                                            payment.update({res:[values.get('journal'),float(values.get('amount'))+float(payment[res][1]),values.get('paymentdate'),values.get('paymentbranch')]})
                                    else:
                                        payment.update({res:[values.get('journal'),values.get('amount'),values.get('paymentdate'), values.get('paymentbranch')]})
                                else:
                                    raise UserError(_('Please Specify Payment Journal and Amount for Invoice %s' %values.get('invoice')))

                if self.stage == 'confirm':
                    for res in invoice_ids: 
                        if res.state in ['draft']:
                            res.action_post()

                if self.stage == 'payment':
                    payment_id = self.create_payment(payment)
            else:
                try:
                    fp = tempfile.NamedTemporaryFile(delete= False,suffix=".xlsx")
                    fp.write(binascii.a2b_base64(self.file))
                    fp.seek(0)
                    values = {}
                    invoice_ids=[]
                    payment = {}
                    workbook = xlrd.open_workbook(fp.name)
                    sheet = workbook.sheet_by_index(0)
                except Exception:
                    raise UserError(_("Please select an CSV/XLS file or You have selected invalid file"))
                    
                for row_no in range(sheet.nrows):
                    val = {}
                    if row_no <= 0:
                        fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
                    else:
                        line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
                        if self.account_opt == 'default':
                            if line[12]:
                                if line[12] == '':
                                    raise UserError(_('Please assign a date'))
                                else:
                                    if line[12]:
                                        if line[12].split('/'):
                                            if len(line[12].split('/')) > 1:
                                                raise ValidationError(_('Wrong Date Format. Date Should be in format YYYY-MM-DD.'))
                                            if len(line[12]) > 8 or len(line[12]) < 5:
                                                raise ValidationError(_('Wrong Date Format. Date Should be in format YYYY-MM-DD.'))
                                    a1 = int(float(line[12]))
                                    a1_as_datetime = datetime(*xlrd.xldate_as_tuple(a1, workbook.datemode))
                                    date_string = a1_as_datetime.date().strftime('%Y-%m-%d')
                                values.update( {'invoice':line[0],
                                                'customer': line[1],
                                                'currency': line[2],
                                                'product': line[3].split('.')[0],
                                                'quantity': line[5],
                                                'uom': line[6],
                                                'description': line[7],
                                                'price': line[8],
                                                'discount':line[9],
                                                'salesperson': line[10],
                                                'tax': line[11],
                                                'date': date_string,
                                                'seq_opt':self.sequence_opt,
                                                })
                                if self.stage == 'payment':
                                    values.update({'amount' : line[14]})
                        else:
                            if line[12]:
                                if line[12] == '':
                                    raise UserError(_('Please assign a date'))
                                else:
                                    if line[12]:
                                        if line[12].split('/'):
                                            if len(line[12].split('/')) > 1:
                                                raise ValidationError(_('Wrong Date Format. Date Should be in format YYYY-MM-DD.'))
                                            if len(line[12]) > 8 or len(line[12]) < 5:
                                                raise ValidationError(_('Wrong Date Format. Date Should be in format YYYY-MM-DD.'))
                                    
                                    a1 = int(float(line[12]))
                                    a1_as_datetime = datetime(*xlrd.xldate_as_tuple(a1, workbook.datemode))
                                    date_string = a1_as_datetime.date().strftime('%Y-%m-%d')
                                values.update( {'invoice':line[0],
                                                'customer': line[1],
                                                'currency': line[2],
                                                'product': line[3].split('.')[0],
                                                'account': line[4],
                                                'quantity': line[5],
                                                'uom': line[6],
                                                'description': line[7],
                                                'price': line[8],
                                                'discount':line[9],
                                                'salesperson': line[10],
                                                'tax': line[11],
                                                'date': date_string,
                                                'seq_opt':self.sequence_opt,
                                                })
                                if self.stage == 'payment':
                                    values.update({'amount' : line[14]})

                        res = self.make_invoice(values)
                        res._recompute_dynamic_lines()
                        res._compute_amount()
                        invoice_ids.append(res)

                        if self.stage == 'payment':
                            if line[15] == '':
                                raise UserError(_('Please assign a payment date'))
                            else:
                                if line[15].split('/'):
                                    if len(line[15].split('/')) > 1:
                                        raise UserError(_('Wrong Date Format. Date Should be in format YYYY-MM-DD.'))
                                    if len(line[15]) > 8 or len(line[15]) < 5:
                                        raise UserError(_('Wrong Date Format. Date Should be in format YYYY-MM-DD.'))
                                a2 = int(float(line[15]))
                                a2_as_datetime = datetime(*xlrd.xldate_as_tuple(a2, workbook.datemode))
                                date_string2 = a2_as_datetime.date().strftime('%Y-%m-%d')

                                if line[13] and line[14]:
                                    if res in payment:
                                        if payment[res][0] != line[13]:
                                            raise UserError(_('Please Use same Journal for Invoice %s' %line[0]))   
                                        else:
                                            payment.update({res:[line[13],float(line[14])+float(payment[res][1]),date_string2 ]})
                                    else:
                                        payment.update({res:[line[13],line[14],date_string2 ]})
                                else:
                                    raise UserError(_('Please Specify Payment Journal and Amount for Invoice %s' %line[0]))

                if self.stage == 'confirm':
                    for res in invoice_ids: 
                        if res.state in ['draft']:
                            res.action_post()

                if self.stage == 'payment':
                    self.create_payment(payment)


                return res
        else:
            return super(gen_inv_inherit,self).import_csv()
    def download_auto(self):
        
        return {
             'type' : 'ir.actions.act_url',
             'url': '/web/binary/download_document_payment?model=gen.invoice&id=%s'%(self.id),
             'target': 'new',
             }

    def make_invoice_line(self, values, inv_id):
        product_obj = self.env['product.product']
        invoice_line_obj = self.env['account.move.line']

        if self.import_prod_option == 'barcode':
          product_search = product_obj.search([('barcode',  '=',values['product'])])
        elif self.import_prod_option == 'code':
            product_search = product_obj.search([('default_code', '=',values['product'])])
        else:
            product_search = product_obj.search([('name', '=',values['product'])])

        product_uom = self.env['uom.uom'].search([('name', '=', values.get('uom'))])
        if not product_uom:
            raise ValidationError(_(' "%s" Product UOM category is not available.') % values.get('uom'))

        if product_search:
            product_id = product_search[0]
        else:
            if self.import_prod_option == 'name':
                product_id = product_obj.create({
                                                    'name':values.get('product'),
                                                    'lst_price':values.get('price'),
                                                    'uom_id':product_uom.id,
                                                 })
            else:
                raise ValidationError(_('%s product is not found" .\n If you want to create product then first select Import Product By Name option .') % values.get('product'))

        tax_ids = []
        if inv_id.move_type == 'out_invoice':
            if values.get('tax'):
                if ';' in  values.get('tax'):
                    tax_names = values.get('tax').split(';')
                    for name in tax_names:
                        tax= self.env['account.tax'].search([('name', '=', name),('type_tax_use','=','sale')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_ids.append(tax.id)

                elif ',' in  values.get('tax'):
                    tax_names = values.get('tax').split(',')
                    for name in tax_names:
                        tax= self.env['account.tax'].search([('name', '=', name),('type_tax_use','=','sale')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_ids.append(tax.id)
                else:
                    tax_names = values.get('tax').split(',')
                    tax= self.env['account.tax'].search([('name', '=', tax_names),('type_tax_use','=','sale')])
                    if not tax:
                        raise ValidationError(_('"%s" Tax not in your system') % tax_names)
                    tax_ids.append(tax.id)
        elif inv_id.move_type == 'in_invoice':
            if values.get('tax'):
                if ';' in values.get('tax'):
                    tax_names = values.get('tax').split(';')
                    for name in tax_names:
                        tax = self.env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'purchase')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_ids.append(tax.id)

                elif ',' in values.get('tax'):
                    tax_names = values.get('tax').split(',')
                    for name in tax_names:
                        tax = self.env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'purchase')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_ids.append(tax.id)
                else:
                    tax_names = values.get('tax').split(',')
                    tax = self.env['account.tax'].search([('name', '=', tax_names), ('type_tax_use', '=', 'purchase')])
                    if not tax:
                        raise ValidationError(_('"%s" Tax not in your system') % tax_names)
                    tax_ids.append(tax.id)
        elif inv_id.move_type == 'out_refund':
            if values.get('tax'):
                if ';' in  values.get('tax'):
                    tax_names = values.get('tax').split(';')
                    for name in tax_names:
                        tax= self.env['account.tax'].search([('name', '=', name),('type_tax_use','=','sale')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_ids.append(tax.id)

                elif ',' in  values.get('tax'):
                    tax_names = values.get('tax').split(',')
                    for name in tax_names:
                        tax= self.env['account.tax'].search([('name', '=', name),('type_tax_use','=','sale')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_ids.append(tax.id)
                else:
                    tax_names = values.get('tax').split(',')
                    tax= self.env['account.tax'].search([('name', '=', tax_names),('type_tax_use','=','sale')])
                    if not tax:
                        raise ValidationError(_('"%s" Tax not in your system') % tax_names)
                    tax_ids.append(tax.id)
        else:
            if values.get('tax'):
                if ';' in values.get('tax'):
                    tax_names = values.get('tax').split(';')
                    for name in tax_names:
                        tax = self.env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'purchase')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_ids.append(tax.id)

                elif ',' in values.get('tax'):
                    tax_names = values.get('tax').split(',')
                    for name in tax_names:
                        tax = self.env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'purchase')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_ids.append(tax.id)
                else:
                    tax_names = values.get('tax').split(',')
                    tax = self.env['account.tax'].search([('name', '=', tax_names), ('type_tax_use', '=', 'purchase')])
                    if not tax:
                        raise ValidationError(_('"%s" Tax not in your system') % tax_names)
                    tax_ids.append(tax.id)

        if self.account_opt == 'default':
            if inv_id.move_type == 'out_invoice':
                if product_id.property_account_income_id:
                    account = product_id.property_account_income_id
                elif product_id.categ_id.property_account_income_categ_id:
                    account = product_id.categ_id.property_account_income_categ_id
                else:
                    account_search = self.env['ir.property'].search([('name', '=', 'property_account_income_categ_id')])
                    account = account_search.value_reference
                    account = account.split(",")[1]
                    account = self.env['account.account'].browse(account)
            if inv_id.move_type == 'in_invoice':
                if product_id.property_account_expense_id:
                    account = product_id.property_account_expense_id
                elif product_id.categ_id.property_account_expense_categ_id:
                    account = product_id.categ_id.property_account_expense_categ_id
                else:
                    account_search = self.env['ir.property'].search([('name', '=', 'property_account_expense_categ_id')])
                    account = account_search.value_reference
                    account = account.split(",")[1]
                    account = self.env['account.account'].browse(account)

            if inv_id.move_type == 'out_refund':
                if product_id.property_account_income_id:
                    account = product_id.property_account_income_id
                elif product_id.categ_id.property_account_income_categ_id:
                    account = product_id.categ_id.property_account_income_categ_id
                else:
                    account_search = self.env['ir.property'].search([('name', '=', 'property_account_income_categ_id')])
                    account = account_search.value_reference
                    account = account.split(",")[1]
                    account = self.env['account.account'].browse(account)
            if inv_id.move_type == 'in_refund':
                if product_id.property_account_expense_id:
                    account = product_id.property_account_expense_id
                elif product_id.categ_id.property_account_expense_categ_id:
                    account = product_id.categ_id.property_account_expense_categ_id
                else:
                    account_search = self.env['ir.property'].search([('name', '=', 'property_account_expense_categ_id')])
                    account = account_search.value_reference
                    account = account.split(",")[1]
                    account = self.env['account.account'].browse(account)

        else:
            if values.get('account') == '':
                raise ValidationError(_(' You can not left blank account field if you select Excel/CSV Account Option'))
            else:
                if self.import_option == 'csv':
                    account_id = self.env['account.account'].search([('code','=',values.get('account'))])
                else:
                    acc = values.get('account').split('.')
                    account_id = self.env['account.account'].search([('code','=',acc[0])])
                if account_id:
                    account = account_id
                else:
                    raise ValidationError(_(' "%s" Account is not available.') % values.get('account')) 

        vals = {
            'product_id' : product_id.id,
            'quantity' : values.get('quantity'),
            'price_unit' :values.get('price'),
            'discount':values.get('discount'),
            'name' : values.get('description'),
            'account_id' : account.id,
            'product_uom_id' : product_uom.id,
            'multiple_payment_amount': values.get('amount')
        }
        if tax_ids:
            vals.update({'tax_ids':([(6,0,tax_ids)])})

        inv_id.with_context(Import=True).write({'invoice_line_ids' :([(0,0,vals)]) })       
        
        return inv_id