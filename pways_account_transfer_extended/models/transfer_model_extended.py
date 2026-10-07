from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero
from datetime import date, timedelta


class TransferModel(models.Model):
    _inherit = "account.transfer.model"

    def _create_or_update_move_for_period(self, start_date, end_date):
        result = super(TransferModel, self)._create_or_update_move_for_period(start_date, end_date)
        result.update({
            'branch_id' : self.branch_id.id,
        })
        return result

    def _get_move_lines_base_domain(self, start_date, end_date):
        """
        Determine the domain to get all account move lines posted in a given period, for an account in origin accounts
        :param start_date: the start date of the period
        :param end_date: the end date of the period
        :return: the computed domain
        :rtype: list
        """
        self.ensure_one()
        return [
            ('account_id', 'in', self.account_ids.ids),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('move_id.state', '=', 'posted')
        ]

    def action_perform_auto_transfer(self):
        """ Perform the automatic transfer for the current recordset of models  """
        for record in self:
            # If no account to ventilate or no account to ventilate into : nothing to do
            if record.account_ids and record.line_ids:
                today = date.today()
                max_date = record.date_stop and min(today, record.date_stop) or today
                start_date = record._determine_start_date()
                next_move_date = record._get_next_move_date(start_date)

                # (Re)Generate moves in draft untill today
                # Journal entries will be recomputed everyday untill posted.
                while next_move_date <= max_date:
                    record._create_or_update_move_for_period(start_date, next_move_date - timedelta(days=1))
                    start_date = next_move_date
                    next_move_date = record._get_next_move_date(start_date)

                # (Re)Generate move for one more period if needed
                if not record.date_stop:
                    record._create_or_update_move_for_period(start_date, next_move_date)
                elif today < record.date_stop:
                    record._create_or_update_move_for_period(start_date, min(next_move_date - timedelta(days=1), record.date_stop))
                elif today > start_date and today > max_date :
                    record._create_or_update_move_for_period(start_date, min(next_move_date, record.date_stop))
        return False

    def _get_auto_transfer_move_line_values(self, start_date, end_date):
        """ Get all the transfer move lines values for a given period
        :param start_date: the start date of the period
        :param end_date: the end date of the period
        :return: a list of dict representing the values of lines to create
        :rtype: list
        """
        self.ensure_one()
        values = []
        # Get the balance of all moves from all selected accounts, grouped by accounts
        filtered_lines = self.line_ids.filtered(lambda x: x.analytic_account_ids or x.partner_ids)
        if filtered_lines:
            values += filtered_lines._get_transfer_move_lines_values(start_date, end_date)

        non_filtered_lines = self.line_ids - filtered_lines
        if non_filtered_lines:
            for account_rec in non_filtered_lines:
                values += self._get_non_filtered_auto_transfer_move_line_values(account_rec, start_date, end_date)
        return values

    def _get_non_filtered_auto_transfer_move_line_values(self, lines, start_date, end_date):
        """
        Get all values to create move lines corresponding to the transfers needed by all lines without analytic
        account or partner for a given period. It contains the move lines concerning destination accounts and
        the ones concerning the origin accounts. This process all the origin accounts one after one.
        :param lines: the move model lines to handle
        :param start_date: the start date of the period
        :param end_date: the end date of the period
        :return: a list of dict representing the values to use to create the needed move lines
        :rtype: list
        """
        self.ensure_one()
        domain = self._get_move_lines_base_domain(start_date, end_date)
        domain = expression.AND([domain, [
            ('analytic_account_id', 'not in', self.line_ids.analytic_account_ids.ids),
            ('partner_id', 'not in', self.line_ids.partner_ids.ids),
            ('branch_id', '=', self.branch_id.id)
        ]])
        total_balance_by_accounts = self.env['account.move.line'].read_group(domain, ['balance', 'account_id'],
                                                                             ['account_id'])
        # balance = debit - credit
        # --> balance > 0 means a debit so it should be credited on the source account
        # --> balance < 0 means a credit so it should be debited on the source account
        values_list = []
        for total_balance_account in total_balance_by_accounts:
            initial_amount = abs(total_balance_account['balance'])
            source_account_is_debit = total_balance_account['balance'] >= 0
            account_id = total_balance_account['account_id'][0]
            account = self.env['account.account'].browse(account_id)
            if account != lines.account_id:
                continue
            if not float_is_zero(initial_amount, precision_digits=9):
                move_lines_values, amount_left = self._get_non_analytic_transfer_values(account, lines, end_date,
                                                                                        initial_amount,
                                                                                        source_account_is_debit, start_date, end_date)

                # the line which credit/debit the source account
                substracted_amount = initial_amount - amount_left
                source_move_line = {
                    'name': _('Automatic Transfer (-%s%%)', self.total_percent),
                    'account_id': account_id,
                    'date_maturity': end_date,
                    'branch_id': self.branch_id and self.branch_id.id,
                    'credit' if source_account_is_debit else 'debit': substracted_amount
                }
                values_list += move_lines_values
                values_list.append(source_move_line)
        return values_list

    def _get_non_analytic_transfer_values(self, account, lines, write_date, amount, is_debit, start_date, end_date):
        """
        Get all values to create destination account move lines corresponding to the transfers needed by all lines
        without analytic account for a given account.
        :param account: the origin account to handle
        :param write_date: the write date of the move lines
        :param amount: the total amount to take care on the origin account
        :type amount: float
        :param is_debit: True if origin account has a debit balance, False if it's a credit
        :type is_debit: bool
        :return: a tuple containing the move lines values in a list and the amount left on the origin account after
        processing as a float
        :rtype: tuple
        """
        # if total ventilated is 100%
        #   then the last line should not compute in % but take the rest
        # else
        #   it should compute in % (as the rest will stay on the source account)
        self.ensure_one()
        amount_left = amount

        take_the_rest = self.total_percent == 100.0
        amount_of_lines = len(lines)
        values_list = []

        move_ids = self.env['account.move.line'].search([
            ('account_id', '=', account.id),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('move_id.state', '=', 'posted'),
            ('move_id.transfer_model_id', '!=', False),
        ])

        amount_debit = sum(move_ids.mapped('debit'))
        left_amount = amount - amount_debit
        for i, line in enumerate(lines): 
            if take_the_rest and i == amount_of_lines - 1:
                line_amount = amount_left
                amount_left = 0
            else:
                line_amount = (line.percent / 100.0) * left_amount
                amount_left -= line_amount

            move_line = line._get_destination_account_transfer_move_line_values(account, line_amount, is_debit,
                                                                                write_date)
            values_list.append(move_line)

        return values_list, amount_left
