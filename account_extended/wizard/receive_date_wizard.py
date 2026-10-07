from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ReceiveDateWizard(models.TransientModel):
    _name = 'receive.date.wizard'
    _description = "Set Received Date"

    date_line_ids = fields.One2many('receive.date.line', 'line_id')
    receive_date = fields.Date(default=fields.Date.context_today)

    @api.onchange('receive_date')
    def _onchange_receive_date(self):
        if self.receive_date:
            self.date_line_ids.receive_date = self.receive_date

    @api.model
    def default_get(self, fields):
        line = []
        vals = super(ReceiveDateWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        move_ids = self.env['account.move'].browse(active_ids).filtered(lambda x:x.custom_invoice_date == False)
        if not move_ids:
            raise ValidationError("Receive Date Already Set")
        for rec in move_ids:
            line.append((0, 0, {'move_id': rec.id}))
        vals['date_line_ids'] = line
        return vals

    def action_set_date(self):
        for rec in self.date_line_ids:
            rec.move_id.write({'custom_invoice_date': rec.receive_date})

class ReceiveDateLineWizard(models.TransientModel):
    _name = 'receive.date.line'
    _description = "Receive Date Line"

    line_id = fields.Many2one('receive.date.wizard')
    move_id = fields.Many2one('account.move')
    receive_date = fields.Date()
