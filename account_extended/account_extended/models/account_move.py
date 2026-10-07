from odoo import api, fields, models, _
from datetime import datetime, date
from num2words import num2words
from odoo.addons.account_check_printing.models.account_payment import AccountPayment as AccountPaymentx
from odoo.exceptions import ValidationError, UserError

class AccountAsset(models.Model):
    _inherit = 'account.move'

    code = fields.Char(string="Code", related="partner_id.address_no")
    comment = fields.Text(string="Comment")
    bill_terms_id = fields.Many2one('terms.condition', string="Terms and Conditions")
    invoice_terms_id = fields.Many2one('terms.condition', string="Terms and Conditions")

    check_history = fields.Boolean(string="Historical Check", default=False)


    @api.onchange('bill_terms_id', 'invoice_terms_id')
    def onchange_terms_id(self):
        if self.move_type == 'in_invoice':
            self.narration = self.bill_terms_id.description
        if self.move_type == 'out_invoice':
            self.narration = self.invoice_terms_id.description

    def convert_num_to_word(self):
        amount = sum(self.invoice_line_ids.mapped('price_subtotal'))
        amount_in_words = self.currency_id.with_context(lang=self.partner_id.lang or 'es_ES').amount_to_text(
            amount).title()
        return amount_in_words

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        if self.move_type in ['out_invoice', 'out_refund']:
            self.journal_id = self.env['account.journal'].search([('branch_id', '=', self.branch_id.id), ('type','=', 'sale')], limit=1).id


    def action_post(self):
        target_branch_id = 10

        for move in self:
            # Only for posted customer invoices of the target branch
            if move.move_type == 'out_invoice' and move.branch_id.id == target_branch_id:
                # Assign sequence if name is '/' or 'Draft'
                if move.name in ('/', 'Draft'):
                    seq = self.env['ir.sequence'].sudo().search([
                        ('name', '=', 'HRO Invoice Sequence'),
                        ('code', '=', 'account.move.custom_invoice'),
                        ('company_id', '=', move.company_id.id)
                    ], limit=1)
                    if seq:
                        move.name = seq.next_by_id()

        res = super(AccountAsset, self).action_post()
        line_ids = self.line_ids.filtered(lambda x: x.type_id and x.type_id.is_invoice)
        for partner in line_ids.mapped('partner_id'):
            invoice_line_list = []
            for line in line_ids.filtered(lambda x: x.debit > 0 and x.partner_id == partner):
                vals = (0, 0, {
                    'name': line.name,
                    'branch_id': line.branch_id.id or False,
                    'account_id': line.account_id.id or False,
                    'employee_id': line.employee_id.id or False,
                    'type_id': line.type_id.id or False,
                    'price_unit': line.debit or False,
                })
                invoice_line_list.append(vals)
            journal_domain = [
                    ('type', '=', 'sale'),
                    ('company_id', '=', self.env.user.company_id.id),
                ]
            journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            if not journal_id:
                raise ValidationError(_('Sale type journal is not found'))
            partner_invoice = self.env['account.move'].search([('partner_id', '=', partner.id), ('move_type', '=', 'out_invoice'), ('state', '=', 'draft')], limit=1)
            if partner_invoice:
                partner_invoice.write({'invoice_line_ids': invoice_line_list or False})
            else:
                invoice = self.env['account.move'].create({
                                'move_type': 'out_invoice',
                                'partner_id': partner or False,
                                'journal_id': journal_id.id or False,
                                'invoice_line_ids': invoice_line_list or False,
                                'invoice_date': date.today(),
                            })
                
        return res
    
class Product(models.Model):
    _inherit = 'product.product'

    unit_type_id = fields.Many2one('unit.type', string="Type")

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    type_id = fields.Many2one('unit.type', string="Type", related="product_id.unit_type_id", readonly="1")
    extra_charge_product_id = fields.Many2one('product.product',string="Extra Charge Ref")
    project_id = fields.Many2one('project.project', string='Project',compute='_compute_project_id')
    task_id = fields.Many2one('project.task', string='Task')

    @api.depends('task_id')
    def _compute_project_id(self):
        for rec in self:
            # Make sure task_id is set
            if rec.task_id:
                rec.project_id = rec.task_id.project_id
            else:
                rec.project_id = False


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_processed = fields.Boolean()

    def action_post(self):
        res = super(AccountPaymentx, self).action_post()
        payment_method_check = self.env.ref('account_check_printing.account_payment_method_check')
        for payment in self.filtered(lambda p: p.payment_method_id == payment_method_check and p.check_manual_sequencing and not p.is_processed):
            sequence = payment.journal_id.check_sequence_id
            payment.check_number = sequence.next_by_id()
            payment.is_processed = True
        return res
    
