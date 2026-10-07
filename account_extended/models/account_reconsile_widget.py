from odoo import api, fields, models
from datetime import datetime, date
from num2words import num2words
from odoo.addons.account_check_printing.models.account_payment import AccountPayment as AccountPaymentx
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import formatLang, format_date, parse_date

class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    @api.model
    def get_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, search_str=False, offset=0, limit=None, target_currency_id=False):
        res = super(AccountReconciliation, self).get_move_lines_for_manual_reconciliation(account_id, partner_id, excluded_ids, search_str, offset, limit, target_currency_id)
        for line in res:
            line.update({'invoice_date': format_date(self.env, self.env['account.move.line'].browse(line['id']).move_id.date)}) 
        return res
    def _prepare_js_reconciliation_widget_move_line(self, statement_line, line, recs_count=0):
        res = super(AccountReconciliation, self)._prepare_js_reconciliation_widget_move_line(statement_line, line, recs_count)
        res.update({'invoice_date': format_date(self.env, self.env['account.move.line'].browse(line['id']).move_id.date)})
        return res

    def _get_statement_line(self, st_line):
        res = super(AccountReconciliation, self)._get_statement_line(st_line)
        res.update({'invoice_date': format_date(self.env, st_line.move_id.date)})
        return res