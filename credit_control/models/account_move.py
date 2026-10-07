from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def _move_dict_to_preview_vals(self, move_vals, currency=None):
        preview_vals = super()._move_dict_to_preview_vals(move_vals, currency)
        
        for idx, line in enumerate(move_vals.get('line_ids', [])):
            if isinstance(line, tuple) and line[0] == 0:
                line_dict = line[2]
                if 'unbilled_value' in line_dict:
                    if idx < len(preview_vals['items_vals']):
                        preview_vals['items_vals'][idx]['unbilled_value'] = line_dict['unbilled_value']
        return preview_vals
    


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    _description = 'Analytic Line'

    unbilled_yes_no = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        default='yes',
        string='Unbilled'
    )

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    receipt_number = fields.Char("Receipt Number")    

