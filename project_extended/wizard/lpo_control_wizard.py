from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class LpoControlWizard(models.Model):
    _name = "lpo.control.wizard"
    _description = "Lpo Control"

    name = fields.Char(required=True, string="Number")
    date = fields.Datetime(string="Date", default=fields.Datetime.now, required=True)
    attachment_id = fields.Binary(string="Attachment")
    lpo_control_ids = fields.One2many('lpo.control.line.wizard', 'lpo_control_id')
    sale_id = fields.Many2one('sale.order')
    branch_id = fields.Many2one('res.branch', string="Branch")

    def create_lpo_control(self):
        lpo_control_line_ids = []
        for line in self.lpo_control_ids:
            lpo_control_line_ids.append([0, 0,
                                         {
                                             'sale_order_line_id': line.sale_order_line_id and line.sale_order_line_id.id,
                                             'name': line.name,
                                             'quantity': line.quantity,
                                             'amount': line.amount,
                                             'no_of_hour': line.no_of_hour,
                                         }])
        if lpo_control_line_ids:
            vals = {
                'name': self.name,
                'date': self.date,
                'sale_id': self.sale_id and self.sale_id.id,
                'attachment_id': self.attachment_id,
                'lpo_control_line_ids': lpo_control_line_ids,
            }
            self.env['lpo.control'].create(vals)


class LpoControlLineWizard(models.Model):
    _name = "lpo.control.line.wizard"
    _description = "Lpo Control Line"

    lpo_control_id = fields.Many2one('lpo.control.wizard')
    name = fields.Char(required=True)
    no_of_hour = fields.Float('No. of hours')
    quantity = fields.Float(string="Quantity")
    amount = fields.Float(string="Amount")
    sale_order_line_id = fields.Many2one('sale.order.line')
