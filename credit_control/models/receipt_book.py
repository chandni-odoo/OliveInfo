from odoo import models, fields, api
from odoo.exceptions import UserError


class ReceiptBook(models.Model):
    _name = 'receipt.book'
    _description = 'Receipt Book'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Book Serial No", required=True)
    employee_id = fields.Many2one('hr.employee', string="Driver")
    start_number = fields.Integer(string="Start Number", required=True)
    end_number = fields.Integer(string="End Number", required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed')
    ], default='draft')

    line_ids = fields.One2many('receipt.book.line', 'book_id', string="Receipt Details")

    # ----------------------
    # BUTTONS
    # ----------------------

    def action_draft(self):
        self.state = 'draft'

    def action_active(self):
        self.state = 'active'

    def action_closed(self):
        self.state = 'closed'

    # def action_generate(self):
    #     for rec in self:
    #         if rec.start_number > rec.end_number:
    #             raise UserError("Start number must be less than End number")

    #         rec.line_ids.unlink()

    #         lines = []
    #         for num in range(rec.start_number, rec.end_number + 1):
    #             receipt_str = str(num)

    #             payment = self.env['account.payment'].search([
    #                 ('receipt_number', '=', receipt_str)
    #             ], limit=1)

    #             status = 'available'
    #             voucher = False

    #             if payment:
    #                 status = 'used'
    #                 voucher = payment.receipt_number

    #             lines.append((0, 0, {
    #                 'receipt_no': receipt_str,
    #                 'payment_voucher': voucher,
    #                 'status': status,
    #             }))

    #         rec.line_ids = lines

    def action_generate(self):
        for rec in self:
            if rec.start_number > rec.end_number:
                raise UserError("Start number must be less than End number")

            existing_lines = {l.receipt_no: l for l in rec.line_ids}

            new_lines_commands = []

            for num in range(rec.start_number, rec.end_number + 1):
                receipt_str = str(num)

                payment = self.env['account.payment'].search([
                    ('receipt_number', '=', receipt_str)
                ], limit=1)

                line = existing_lines.get(receipt_str)

                # -------------------------
                # CASE 1: EXISTING LINE
                # -------------------------
                if line:
                    # 🔥 DO NOT TOUCH MANUALLY SET "missing"
                    if line.status == 'missing':
                        continue  # keep everything as-is

                    # otherwise update system fields only
                    status = 'used' if payment else 'available'
                    voucher = payment.receipt_number if payment else False

                    line.write({
                        'payment_voucher': voucher,
                        'status': status,
                    })

                # -------------------------
                # CASE 2: NEW LINE
                # -------------------------
                else:
                    status = 'used' if payment else 'available'
                    voucher = payment.receipt_number if payment else False

                    new_lines_commands.append((0, 0, {
                        'receipt_no': receipt_str,
                        'payment_voucher': voucher,
                        'status': status,
                    }))

            if new_lines_commands:
                rec.write({'line_ids': new_lines_commands})


class ReceiptBookLine(models.Model):
    _name = 'receipt.book.line'
    _description = 'Receipt Book Line'

    book_id = fields.Many2one('receipt.book', ondelete='cascade')

    receipt_no = fields.Char(string="Receipt No")

    # 🔥 STORE PAYMENT VOUCHER NUMBER ONLY
    payment_voucher = fields.Char(string="Payment Voucher")

    status = fields.Selection([
        ('used', 'Used'),
        ('available', 'Available'),
        ('missing', 'Missing')
    ], default='available')

    remark = fields.Char(string="Remarks")

    # 🔥 OPEN PAYMENT USING receipt_number
    def action_open_payment(self):
        self.ensure_one()

        payment = self.env['account.payment'].search([
            ('receipt_number', '=', self.receipt_no)
        ], limit=1)

        if payment:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'res_id': payment.id,
            }