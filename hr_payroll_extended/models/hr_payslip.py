# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
import pytz
from collections import defaultdict
from odoo.tools import float_compare, float_is_zero, plaintext2html
from markupsafe import Markup
from datetime import timedelta, date



class ContractHistory(models.Model):
    _inherit = 'hr.contract.history'

    # state = fields.Selection(selection_add=[('approval', 'Approval')])
    state = fields.Selection(selection_add=[('approval', 'Approval'),('open',),('rejects','Rejected')])


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    is_sick_leave = fields.Boolean('Sick Leave')


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    salary_days = fields.Float('Salary Days', compute='_compute_salary_total_days', store=True)
    attendance_days = fields.Float('Paid Days', compute='_compute_attendance_total_days', store=True)
    shift_days = fields.Float('Shift Days', compute='_compute_shift_days', store=True)
    public_holidays = fields.Float('Public Holidays', compute='_compute_public_holidays', store=True)
    leave_day = fields.Float('Leave Days', compute='_compute_leave_day', store=True)
    code = fields.Char(string="Code", related="employee_id.emp_no")
    present_day = fields.Float('Present Days', compute='_compute_present_day', store=True)
    absent_day = fields.Float('Absent Days', compute="_get_absent_leaves_days", store=True)
    unpaid_day = fields.Float('Unpaid Leaves', compute="_compute_unpaid_leaves", store=True)

    def _prepare_line_values(self, line, account_id, date, debit, credit):
        return {
            'name': line.name,
            'partner_id': line.partner_id.id,
            'account_id': account_id,
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'employee_id': line.employee_id.id,
            'branch_id': line.employee_id.branch_id.id,
            'date': date,
            'debit': debit,
            'credit': credit,
            'analytic_account_id': line.salary_rule_id.analytic_account_id.id or line.slip_id.contract_id.analytic_account_id.id,
        }

    def _get_existing_lines(self, line_ids, line, account_id, debit, credit):
        existing_lines = (
            line_id for line_id in line_ids if
            line_id['name'] == line.name
            and line_id['employee_id'] == line.employee_id.id
            and line_id['branch_id'] == line.employee_id.branch_id.id
            and line_id['account_id'] == account_id
            and line_id['analytic_account_id'] == (
                        line.salary_rule_id.analytic_account_id.id or line.slip_id.contract_id.analytic_account_id.id)
            and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0)))
        return next(existing_lines, False)

    def _prepare_line_net_values(self, line, account_id, date, debit, credit):
        print("line.name+_+_+_+_+_+", line.name)
        return {
            'name': line.name,
            'partner_id': line.partner_id.id,
            'account_id': account_id[0],
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'branch_id': account_id[1],
            'date': date,
            'debit': debit,
            'credit': credit,
            'analytic_account_id': line.salary_rule_id.analytic_account_id.id or line.slip_id.contract_id.analytic_account_id.id,
        }

    def _get_existing_net_lines(self, line_ids, line, account_id, debit, credit):
        existing_lines = (
            line_id for line_id in line_ids if
            line_id['name'] == line.name
            and line_id['account_id'] == account_id[0]
            and line_id['branch_id'] == account_id[1]
            and line_id['analytic_account_id'] == (
                        line.salary_rule_id.analytic_account_id.id or line.slip_id.contract_id.analytic_account_id.id)
            and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0)))
        print("existing_lines+_+_+_+_+", existing_lines)
        return next(existing_lines, False)

    # def _action_create_account_move(self):
    #     precision = self.env['decimal.precision'].precision_get('Payroll')
    #     # Add payslip without run
    #     payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)
    #
    #     # Adding pay slips from a batch and deleting pay slips with a batch that is not ready for validation.
    #     payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
    #     for run in payslip_runs:
    #         if run._are_payslips_ready():
    #             payslips_to_post |= run.slip_ids
    #
    #     # A payslip need to have a done state and not an accounting move.
    #     payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.move_id)
    #
    #     # Check that a journal exists on all the structures
    #     if any(not payslip.struct_id for payslip in payslips_to_post):
    #         raise ValidationError(_('One of the contract for these payslips has no structure type.'))
    #     if any(not structure.journal_id for structure in payslips_to_post.mapped('struct_id')):
    #         raise ValidationError(_('One of the payroll structures has no account journal defined on it.'))
    #
    #     # Map all payslips by structure journal and pay slips month.
    #     # {'journal_id': {'month': [slip_ids]}}
    #     slip_mapped_data = defaultdict(lambda: defaultdict(lambda: self.env['hr.payslip']))
    #     for slip in payslips_to_post:
    #         slip_mapped_data[slip.struct_id.journal_id.id][fields.Date().end_of(slip.date_to, 'month')] |= slip
    #     for journal_id in slip_mapped_data: # For each journal_id.
    #         for slip_date in slip_mapped_data[journal_id]: # For each month.
    #             line_ids = []
    #             match_slip_ids = []
    #             account_debit = {}
    #             account_credit = {}
    #             debit_sum = 0.0
    #             credit_sum = 0.0
    #             date = slip_date
    #             move_dict = {
    #                 'narration': '',
    #                 'ref': date.strftime('%B %Y'),
    #                 'journal_id': journal_id,
    #                 'date': date,
    #             }
    #
    #             payslip_ids = slip_mapped_data[journal_id][slip_date].mapped('line_ids').filtered(lambda line: line.category_id and line.code == 'NET')
    #             #print ("payslip_ids+_+_+_+_+_+_+_+_+",payslip_ids)
    #             debit_payslip_ids = payslip_ids.mapped('salary_rule_id.account_debit')
    #             #print ("debit_payslip_ids+_+_+_+_+_+_",debit_payslip_ids)
    #             credit_payslip_ids = payslip_ids.mapped('salary_rule_id.account_credit')
    #             #print ("credit_payslip_ids+_+_+_+_+_++,",credit_payslip_ids)
    #             payslip_branch_ids = payslip_ids.mapped('employee_id.branch_id')
    #             #print ("payslip_branch_ids+_+_+_+_+_+",payslip_branch_ids)
    #             # print("\n<<<<<<NET>>DATA>>>", debit_payslip_ids, credit_payslip_ids, payslip_branch_ids)
    #             for slip in slip_mapped_data[journal_id][slip_date]:
    #                 move_dict['narration'] += plaintext2html(slip.number or '' + ' - ' + slip.employee_id.name or '')
    #                 move_dict['narration'] += Markup('<br/>')
    #                 for line in slip.line_ids.filtered(lambda line: line.category_id):
    #                     #print ("slip.line_ids+_+_+_+_+_+",slip.line_ids)
    #                     amount = line.total
    #                     #print ('amount+_+_+_+_+',amount)
    #                     if line.code == 'NET':
    #                         for tmp_line in slip.line_ids.filtered(lambda line: line.category_id):
    #                             if tmp_line.salary_rule_id.not_computed_in_net:
    #                                 print ("tmp_line.salary_rule_id+_+_+_+_+",tmp_line.salary_rule_id,tmp_line.salary_rule_id.not_computed_in_net)
    #                                 if amount > 0:
    #                                     amount -= abs(tmp_line.total)
    #                                 elif amount < 0:
    #                                     amount += abs(tmp_line.total)
    #                     print ("amount+_+_+_+__+_+",amount)
    #                     if float_is_zero(amount, precision_digits=precision):
    #                         continue
    #
    #                     debit_account_id = line.salary_rule_id.account_debit
    #                     #print ("debit_account_id_)_))___)_)",debit_account_id,debit_account_id.name)
    #                     credit_account_id = line.salary_rule_id.account_credit
    #                     #print ("credit_account_id+_+_+_+_+_+",credit_account_id,credit_account_id.name)
    #
    #                     if (debit_account_id in debit_payslip_ids):
    #                         #print("\n\n<<<<<<<<DEBIT>>>>", line.code, amount, debit_account_id)
    #                         match_slip_ids.append(line)
    #                         continue
    #                     else:
    #                         if debit_account_id: # If the rule has a debit account.
    #                             #print("\n<<>>>REST DEBIT>>>>>>>>>>",line.code, line.total, debit_account_id, credit_account_id)
    #                             debit = amount if amount > 0.0 else 0.0
    #                             credit = -amount if amount < 0.0 else 0.0
    #                             #print("\n<<>>>REST DEBIT>>>>>>>>>>",line.code, line.total, debit_account_id, credit_account_id)
    #                             debit_line = self._get_existing_lines(line_ids, line, debit_account_id.id, debit, credit)
    #                             #print ("debit_line__+_+________",debit_line)
    #                             if not debit_line:
    #                                 debit_line = self._prepare_line_values(line, debit_account_id.id, date, debit, credit)
    #                                # print ("debit_line+_+_+_+_+_+_+_+",debit_line)
    #                                 line_ids.append(debit_line)
    #                             else:
    #                                 debit_line['debit'] += debit
    #                                 debit_line['credit'] += credit
    #
    #
    #                     if (credit_account_id in credit_payslip_ids):
    #                         #print("\n\n<<<<<<<<CREDIT>>>>", line.code, line.total, credit_account_id)
    #                         match_slip_ids.append(line)
    #                         continue
    #                     else:
    #                         if credit_account_id: # If the rule has a credit account.
    #                             #print("\n<<>>>REST CREDIT>>>>>>>>>>",line.code, line.total, debit_account_id, credit_account_id)
    #                             debit = -amount if amount < 0.0 else 0.0
    #                             credit = amount if amount > 0.0 else 0.0
    #                             credit_line = self._get_existing_lines(line_ids, line, credit_account_id.id, debit, credit)
    #
    #                             if not credit_line:
    #                                 credit_line = self._prepare_line_values(line, credit_account_id.id, date, debit, credit)
    #                                 #print ("credit_line+_+_+_+_+_+_+",credit_line)
    #                                 line_ids.append(credit_line)
    #                             else:
    #                                 credit_line['debit'] += debit
    #                                 credit_line['credit'] += credit
    #                     # print ("debit_+_+_+_+",debit)
    #                     # print ("credit+_+_+_+_",credit)
    #             #print ("match_slip_ids+_+_+_+_+_+",match_slip_ids)
    #             for line in match_slip_ids:
    #                 #print ("line++_+_+_+_+_++_",line)
    #                 credit_account_id = line.salary_rule_id.account_credit
    #                 #print ("credit_account_id+_+_+_+_+",credit_account_id)
    #                 debit_account_id = line.salary_rule_id.account_debit
    #                 #print ("debit_account_id+_+_+_+_+_",debit_account_id)
    #                 branch_id = line.employee_id.branch_id
    #                 #print ("branch_id_+_)_)_____",branch_id)
    #                 if credit_account_id and branch_id: # If the rule has a credit account.
    #                     if (credit_account_id.id,branch_id.id) not in account_credit:
    #                         account_credit[credit_account_id.id, branch_id.id] = line
    #                         #print ("line_)+_+going in credit if ",line)
    #                     else:
    #                         account_credit[credit_account_id.id, branch_id.id] |= line
    #                         #print ("linelinein going in credit else",line)
    #                     #print ("credit_account_id+_+_+_+_+",account_credit)
    #                 if debit_account_id and branch_id: # If the rule has a debit account.
    #                     if (debit_account_id.id,branch_id.id) not in account_debit:
    #                         account_debit[debit_account_id.id, branch_id.id] = line
    #                        # print ("going in if debit",line)
    #                     else:
    #                         account_debit[debit_account_id.id, branch_id.id] |= line
    #                        # print ("going in else debit",line)
    #                 #print ("account_debit+_+_+_+_+",account_debit)
    #             print ("account_debit.items()+_+_+_+_++",account_debit.items())
    #             for d_key, d_values in account_debit.items():
    #                 print ("d_key+_+_+_+_+_+_+",d_key)
    #                 print ("d_values+_+_+_+__+",d_values)
    #                 f_total = 0.0
    #                 not_total = 0.0
    #                 d_total = sum(d_values.mapped('total')) - not_total
    #                 print ("d_total+_+__+_+_+_+sumedup",d_total)
    #                 if float_is_zero(d_total, precision_digits=precision):
    #                     continue
    #                 d_debit = d_total if d_total > 0.0 else 0.0
    #                 d_credit = -d_total if d_total < 0.0 else 0.0
    #                 debit_line = self._get_existing_net_lines(line_ids, d_values[-1], d_key, d_debit, d_credit)
    #                 if not debit_line:
    #                     f_total = 0.0
    #                     net = 0.0
    #                     allowance = 0.0
    #                     deduction =0.0
    #                     for d_lines in d_values:
    #                         for liness in d_lines.slip_id.line_ids:
    #                             print ("liness.category_id.name+__+_+_+_",liness.category_id.name,liness.total)
    #                             if liness.category_id.name == 'Net':
    #                                 net += liness.total
    #                             if liness.salary_rule_id.not_computed_in_net:
    #                                 if liness.category_id.name == 'Allowance':
    #                                     allowance += liness.total
    #                                 if liness.category_id.name == 'Deduction':
    #                                     deduction += liness.total
    #                             print ("net allowance deduction FIRST",net,deduction,allowance)
    #                         print ("net allowance deduction THIRD",net,deduction,allowance,)
    #                     print ("net allowance deduction",net,deduction,allowance)
    #                     print ("print _+_+_+_+_+_+_+_+", net + deduction)
    #                     fs_total = net + deduction
    #                     f_total = fs_total - allowance
    #                     print ("f_total___)_)_)_)_)_",f_total)
    #                     if d_values[0].category_id.name == 'Net':
    #                         d_debit = f_total if f_total > 0.0 else 0.0
    #                         print ("d_debit+_+_+_+_+_",d_debit)
    #                         d_credit = -f_total if f_total < 0.0 else 0.0
    #                     else:
    #                         d_debit = d_total if d_total > 0.0 else 0.0
    #                         print ("d_debit+_+_+_+_+_",d_debit)
    #                         d_credit = -d_total if d_total < 0.0 else 0.0
    #                         print ("d_credit+_+_+_++",d_credit)
    #                     print (d_debit,d_credit)
    #                     debit_line = self._prepare_line_net_values(d_values[-1], d_key, date, d_debit, d_credit)
    #                     line_ids.append(debit_line)
    #                 print ("debit_line+_+_+_+_+_+_+ if not",debit_line)
    #             print ("account_credit.items()+_+_+_+_+_+_+_",account_credit.items())
    #             for c_key, c_values in account_credit.items():
    #                 print ("c_key+_+_+_+_+_+_+",c_key)
    #                 print ("c_values+_+_+_+__+",c_values)
    #                 not_total = 0.0
    #                 print ("not_total+_+_+_+_+_+",not_total)
    #                 for total in d_values:
    #                     print ("d_values.total+_+_+_+_+",total.total)
    #                 # for c_val in c_values:
    #                 #     not_compute_rule_id = c_val.salary_rule_id.not_computed_in_net
    #                 #     if not_compute_rule_id:
    #                 #         not_total += c_val.total
    #                 print ("c_values.mapped('total')+_+_+_+_+_+",c_values.mapped('total'))
    #                 c_total = sum(c_values.mapped('total')) - not_total
    #                 print ("c_total+_+_+_+_+_+sumed up",c_total)
    #                 if float_is_zero(c_total, precision_digits=precision):
    #                     continue
    #
    #                 c_debit = -c_total if c_total < 0.0 else 0.0
    #                 print ("c_debit+_+_+_+_+",c_debit)
    #                 c_credit = c_total if c_total > 0.0 else 0.0
    #                 print ("c_credit__+_+_+_+_+_+",c_credit)
    #                 credit_line = self._get_existing_net_lines(line_ids, c_values[-1], c_key, c_debit, c_credit)
    #                 print ("credit_line+_+_+_+_+_+",credit_line)
    #                 if not credit_line:
    #                     f_total = 0.0
    #                     net = 0.0
    #                     print ("d_values[0].category_id.name+_+_+_+_+",c_values[0].category_id.name)
    #                     for c_lines in c_values:
    #                         if c_lines.category_id.name == 'Net':
    #                             for liner in c_lines.slip_id.line_ids:
    #                                 if liner.category_id.name == 'Net':
    #                                     print ("CREDIT SIDE +_+_+_+_+_+_+_",liner.total)
    #                                     f_total += liner.total
    #                         print ("net allowance deduction",f_total)
    #                         print ("f_total___)_)_)_)_)_",f_total)
    #                     if d_values[0].category_id.name == 'Net':
    #                         c_debit = -f_total if f_total < 0.0 else 0.0
    #                         print ("c_debit+_+_+_+_+",c_debit)
    #                         c_credit = f_total if f_total > 0.0 else 0.0
    #                         print ("c_credit__+_+_+_+_+_+",c_credit)
    #                     else:
    #                         c_debit = -c_total if c_total < 0.0 else 0.0
    #                         print ("c_debit+_+_+_+_+",c_debit)
    #                         c_credit = c_total if c_total > 0.0 else 0.0
    #                         print ("c_credit__+_+_+_+_+_+",c_credit)
    #                     credit_line = self._prepare_line_net_values(c_values[-1], c_key, date, c_debit, c_credit)
    #                     print ("credit_line+_+_+_+_ if not",credit_line)
    #                     line_ids.append(credit_line)
    #             #print ("line_ids+_+_+_+__+_+_+_++_+",line_ids)
    #             for line_id in line_ids: # Get the debit and credit sum.
    #                 debit_sum += line_id['debit']
    #                 credit_sum += line_id['credit']
    #             print ("debit_sum+_+_+_",debit_sum)
    #             print ("credit_sum+_+_+_",credit_sum)
    #             #print (error)
    #             # The code below is called if there is an error in the balance between credit and debit sum.
    #             acc_id = slip.sudo().journal_id.default_account_id.id
    #             if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
    #                 if not acc_id:
    #                     raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (slip.journal_id.name))
    #                 existing_adjustment_line = (
    #                     line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
    #                 )
    #                 adjust_credit = next(existing_adjustment_line, False)
    #
    #                 if not adjust_credit:
    #                     adjust_credit = {
    #                         'name': _('Adjustment Entry'),
    #                         'partner_id': False,
    #                         'account_id': acc_id,
    #                         'journal_id': slip.journal_id.id,
    #                         'date': date,
    #                         'debit': 0.0,
    #                         'credit': debit_sum - credit_sum,
    #                     }
    #                     line_ids.append(adjust_credit)
    #                 else:
    #                     adjust_credit['credit'] = debit_sum - credit_sum
    #
    #             elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
    #                 if not acc_id:
    #                     raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (slip.journal_id.name))
    #                 existing_adjustment_line = (
    #                     line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
    #                 )
    #                 adjust_debit = next(existing_adjustment_line, False)
    #
    #                 if not adjust_debit:
    #                     adjust_debit = {
    #                         'name': _('Adjustment Entry'),
    #                         'partner_id': False,
    #                         'account_id': acc_id,
    #                         'journal_id': slip.journal_id.id,
    #                         'date': date,
    #                         'debit': credit_sum - debit_sum,
    #                         'credit': 0.0,
    #                     }
    #                     line_ids.append(adjust_debit)
    #                 else:
    #                     adjust_debit['debit'] = credit_sum - debit_sum
    #
    #
    #             # Add accounting lines in the move
    #             print ("line_ids+_+)_+_+_+_+_+_+",line_ids)
    #             move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
    #             print ("move_dict+_+_+_+_+_+",move_dict)
    #             move = self.env['account.move'].sudo().create(move_dict)
    #             for slip in slip_mapped_data[journal_id][slip_date]:
    #                 slip.write({'move_id': move.id, 'date': date})
    #     return True

    # New Function Created by GT to fix the issue of JV creation and calculation branch wise

    def _action_create_account_move(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')

        # Add payslip without run
        payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)

        # Adding pay slips from a batch and deleting pay slips with a batch that is not ready for validation.
        payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
        for run in payslip_runs:
            if run._are_payslips_ready():
                payslips_to_post |= run.slip_ids

        # A payslip need to have a done state and not an accounting move.
        payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.move_id)

        # Check that a journal exists on all the structures
        if any(not payslip.struct_id for payslip in payslips_to_post):
            raise ValidationError(_('One of the contract for these payslips has no structure type.'))
        if any(not structure.journal_id for structure in payslips_to_post.mapped('struct_id')):
            raise ValidationError(_('One of the payroll structures has no account journal defined on it.'))

        slip_mapped_data = defaultdict(lambda: defaultdict(lambda: self.env['hr.payslip']))
        for slip in payslips_to_post:
            slip_mapped_data[slip.struct_id.journal_id.id][fields.Date().end_of(slip.date_to, 'month')] |= slip
        for journal_id in slip_mapped_data:  # For each journal_id.
            for slip_date in slip_mapped_data[journal_id]:  # For each month.
                branch_list = []
                for slip in slip_mapped_data[journal_id][slip_date]:
                    if slip.branch_id.id not in branch_list:
                        branch_list.append(slip.branch_id.id)
                for branch in branch_list:
                    slips = []
                    line_ids = []
                    debit_sum = 0.0
                    credit_sum = 0.0
                    c_net = 0.0
                    c_allowance = 0.0
                    c_deduction = 0.0
                    c_net_amount = 0.0
                    c_f_amount = 0.0
                    net_credit_account_id = []
                    for sliper in slip_mapped_data[journal_id][slip_date]:
                        if branch == sliper.branch_id.id:
                            slips.append(sliper)
                    print("slips+_+_+_+_+_+", slips)
                    structure_list = []
                    for st_slip in slips:
                        if st_slip.struct_id.id not in structure_list:
                            structure_list.append(st_slip.struct_id.id)
                    # print ("structure_list++",structure_list)
                    # print ("slips+_+_+_+_+_+",slips)
                    date = slip_date
                    move_dict = {
                        'narration': '',
                        'ref': date.strftime('%B %Y'),
                        'journal_id': journal_id,
                        'date': date,
                        'branch_id': branch,
                        'company_id': self.env['res.branch'].browse(branch).company_id.id
                    }
                    for structure in structure_list:
                        print("Final structure_list+_+_+_+_+_+", structure)
                        final_l_slips = []
                        for final_slips in slips:
                            if structure == final_slips.struct_id.id:
                                final_l_slips.append(final_slips)
                        print("final_l_slips+_+_+_+_+_+FINAL", final_l_slips)
                        net = 0.0
                        allowance = 0.0
                        deduction = 0.0
                        net_amount = 0.0
                        f_amount = 0.0
                        for slip in final_l_slips:
                            move_dict['narration'] += plaintext2html(
                                slip.number or '' + ' - ' + slip.employee_id.name or '')
                            move_dict['narration'] += Markup('<br/>')
                            for t_line in slip.line_ids:
                                # print ("line_ids+_+_+_+-+line_ids+_+_+_+_+_+_+_+line_ids",line_ids)
                                if t_line.category_id.name == 'Net':
                                    net += t_line.total  # adding total of NET lines
                                    c_net += t_line.total
                                    net_credit_account_id = t_line.salary_rule_id.account_credit.id  #
                                    net_debit_account_id = t_line.salary_rule_id.account_debit.id
                                if t_line.salary_rule_id.not_computed_in_net:
                                    if t_line.category_id.name == 'Allowance':
                                        allowance += t_line.total
                                        c_allowance += t_line.total
                                        if t_line.salary_rule_id.account_debit.id:  # If the rule has a debit account.
                                            debit = t_line.total if t_line.total > 0.0 else 0.0
                                            credit = -t_line.total if t_line.total < 0.0 else 0.0
                                            if debit or credit != 0.0:
                                                debit_line = self._get_existing_lines(
                                                    line_ids, t_line, t_line.salary_rule_id.account_debit.id, debit,
                                                    credit)
                                                if not debit_line:
                                                    debit_line = self._prepare_line_values(t_line,
                                                                                           t_line.salary_rule_id.account_debit.id,
                                                                                           date, debit, credit)
                                                    line_ids.append(debit_line)
                                                else:
                                                    debit_line['debit'] += debit
                                                    debit_line['credit'] += credit
                                    if t_line.category_id.name == 'Deduction':
                                        deduction += t_line.total * -1
                                        c_deduction += t_line.total * -1
                                        if t_line.salary_rule_id.account_debit.id:  # If the rule has a credit account.
                                            debit = 0.0
                                            credit = t_line.total * -1
                                            if debit or credit != 0.0:
                                                credit_line = self._get_existing_lines(
                                                    line_ids, t_line, t_line.salary_rule_id.account_debit.id, debit,
                                                    credit)
                                                if not credit_line:
                                                    credit_line = self._prepare_line_values(t_line,
                                                                                            t_line.salary_rule_id.account_debit.id,
                                                                                            date, debit, credit)
                                                    line_ids.append(credit_line)
                                                else:
                                                    credit_line['debit'] += debit
                                                    credit_line['credit'] += credit
                        # preparing NET amount Entry for all slips in a single branch
                        if net_debit_account_id:
                            net_amount = net + deduction - allowance
                            debit = net_amount if net_amount > 0.0 else 0.0
                            credit = -net_amount if net_amount < 0.0 else 0.0
                            if debit or credit != 0.0:
                                debit_line = self._prepare_net_values(branch, journal_id, net_debit_account_id, date,
                                                                      debit, credit)
                                line_ids.append(debit_line)
                    if net_credit_account_id:
                        c_net_amount = c_net + c_deduction - c_allowance
                        c_f_amount = c_net_amount - c_deduction + c_allowance
                        debit = -c_f_amount if c_f_amount < 0.0 else 0.0
                        credit = c_f_amount if c_f_amount > 0.0 else 0.0
                        if debit or credit != 0.0:
                            credit_line = self._prepare_net_values(branch, journal_id, net_credit_account_id, date,
                                                                   debit, credit)
                            print("credit_line+_+_+_+_+", credit_line)
                            line_ids.append(credit_line)

                    print("line_ids+_+_+_+_+_+_+AFTER NET", line_ids)
                    for line_id in line_ids:  # Get the debit and credit sum.
                        debit_sum += line_id['debit']
                        credit_sum += line_id['credit']
                    print("debit_sum+_+_+_+_+_+", debit_sum)
                    print("credit_sum+_+_+_+_+_+", credit_sum)
                    # The code below is called if there is an error in the balance between credit and debit sum.
                    acc_id = slip.sudo().journal_id.default_account_id.id
                    if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                        if not acc_id:
                            raise UserError(
                                _('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                                    slip.journal_id.name))
                        existing_adjustment_line = (
                            line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                        )
                        adjust_credit = next(existing_adjustment_line, False)

                        if not adjust_credit:
                            adjust_credit = {
                                'name': _('Adjustment Entry'),
                                'partner_id': False,
                                'account_id': acc_id,
                                'journal_id': slip.journal_id.id,
                                'date': date,
                                'debit': 0.0,
                                'credit': debit_sum - credit_sum,
                            }
                            line_ids.append(adjust_credit)
                        else:
                            adjust_credit['credit'] = debit_sum - credit_sum

                    elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                        if not acc_id:
                            raise UserError(
                                _('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                                    slip.journal_id.name))
                        existing_adjustment_line = (
                            line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                        )
                        adjust_debit = next(existing_adjustment_line, False)

                        if not adjust_debit:
                            adjust_debit = {
                                'name': _('Adjustment Entry'),
                                'partner_id': False,
                                'account_id': acc_id,
                                'journal_id': slip.journal_id.id,
                                'date': date,
                                'debit': credit_sum - debit_sum,
                                'credit': 0.0,
                            }
                            line_ids.append(adjust_debit)
                        else:
                            adjust_debit['debit'] = credit_sum - debit_sum
                    print("line_ids+_+_+_+_+_++", line_ids)
                    # Add accounting lines in the move
                    if line_ids:
                        move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
                        move = self.env['account.move'].sudo().create(move_dict)
                        for slip in slips:
                            slip.write({'move_id': move.id, 'date': date})
        return True

    def _prepare_net_values(self, branch, journal_id, account_id, date, debit, credit):
        print("debit+_+_+_+_+_+_+__+ in prepare net values", debit)
        print("credit_+_+_+_+_+_++_+_+ in prepare net valu", credit)
        return {
            'name': 'Net Salary',
            'account_id': account_id,
            'journal_id': journal_id,
            'branch_id': branch,
            'date': date,
            'debit': debit,
            'credit': credit,
            # 'analytic_account_id': line.salary_rule_id.analytic_account_id.id or line.slip_id.contract_id.analytic_account_id.id,
        }

    @api.constrains('contract_id')
    def check_contract_values(self):
        for rec in self.filtered(lambda x: x.contract_id):
            if not rec.contract_id.work_hours:
                raise ValidationError(_("Please set work hours for '%s' !") % rec.contract_id.name)
            if not rec.contract_id.wage:
                raise ValidationError(_("Please set structure type for '%s' !") % rec.contract_id.name)
            if not rec.contract_id.structure_type_id:
                raise ValidationError(_("Please set wage for '%s' !") % rec.contract_id.name)
            if not rec.contract_id.structure_id:
                raise ValidationError(_("Please set Salary Structure for '%s' !") % rec.contract_id.name)
            if not rec.contract_id.allowance_ids:
                raise ValidationError(_("Please set Allowance Line for '%s' !") % rec.contract_id.name)

    @api.depends('contract_id')
    def _compute_struct_id(self):
        for slip in self.filtered(lambda p: not p.struct_id):
            slip.struct_id = slip.contract_id.structure_id or slip.contract_id.structure_type_id.default_struct_id

    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()
        return res

    def action_payslip_draft(self):
        for rec in self:
            date_from, date_to = rec._get_start_end_date()
            employee_id = rec.employee_id.id
            if rec.employee_id:
                resignation_request = self.env['hr.payslip'].search(
                    [('employee_id', '=', rec.employee_id.id), ('date_from', '=', rec.date_from),
                     ('date_to', '=', rec.date_to), ('state', 'not in', ['cancel'])])
                if resignation_request:
                    raise ValidationError(
                        _('The Salary slip is already created for %s for month %s to %s.', rec.employee_id.name,
                          rec.date_from, rec.date_to))
            if not rec.state == 'cancel':
                raise ValidationError(_('You can only set cancel payslip into draft state'))
        return super(HrPayslip, self).action_payslip_draft()

    def get_payslip_month(self):
        month = ''
        if self.date_from:
            month = datetime.datetime.strptime(str(self.date_from.month), "%m").strftime("%B") + ' ' + str(
                self.date_from.year)
        return month

    @api.depends('worked_days_line_ids')
    def _compute_present_day(self):
        for rec in self:
            rec.present_day = rec.get_present_days()

    @api.depends('date_from', 'date_to')
    def _compute_salary_total_days(self):
        for rec in self.filtered(lambda x: x.date_to and x.date_from):
            # date_from, date_to = rec._get_start_end_date()
            start_date = datetime.datetime.strptime(rec.date_from.strftime('%Y-%m-%d %H:%M:%S'),
                                                    DEFAULT_SERVER_DATETIME_FORMAT)
            end_date = datetime.datetime.strptime(rec.date_to.strftime('%Y-%m-%d %H:%M:%S'),
                                                  DEFAULT_SERVER_DATETIME_FORMAT)
            difference = end_date - start_date
            if difference:
                number_of_days = abs(difference.days + 1)
                rec.salary_days = number_of_days

    @api.depends('worked_days_line_ids')
    def _compute_shift_days(self):
        for rec in self:
            shift_days = rec.get_week_off_dates()
            rec.shift_days = len(shift_days)

    @api.depends('worked_days_line_ids')
    def _compute_leave_day(self):
        for rec in self:
            leave_days = rec._get_paid_leaves()
            rec.leave_day = leave_days

    @api.depends('worked_days_line_ids')
    def _compute_public_holidays(self):
        for rec in self:
            if rec.employee_id.public_holiday_eligible:
                public_holidays_days = rec.get_public_holidays_dates()
                rec.public_holidays = len(public_holidays_days)
            else:
                rec.public_holidays = 0

    @api.depends('worked_days_line_ids')
    def _compute_attendance_total_days(self):
        for rec in self:
            attendance_days = 0
            total_att_days = 0
            leave_days = rec._get_paid_leaves()
            # for work in rec.worked_days_line_ids.filtered(lambda x: x.work_entry_type_id and x.work_entry_type_id.code in ('WORK100', 'LEAVE120')):
            #     attendance_days += work.number_of_days
            #     total_att_days = attendance_days + leave_days
            #     if total_att_days > rec.salary_days:
            total_att_days = rec.public_holidays + rec.present_day + rec.leave_day + rec.shift_days
            rec.attendance_days = rec.salary_days if total_att_days > rec.salary_days else total_att_days

    def get_attendance_days_time(self):
        worked_hours = 0.0
        number_of_days = 0.0
        min_time = self.contract_id.min_time or 0.0
        max_time = self.contract_id.max_time or 0.0

        holidays_uni_days = []
        # Public holidays
        uni_holidays_dates = self.get_public_holidays_dates()
        for uni_days in uni_holidays_dates:
            number_of_days += 1
            holidays_uni_days.append(uni_days)

        # Week off days
        weekoff_dates = self.get_week_off_dates()
        # Overlapping dates
        holidays_week_off_days = []
        for weekoff_date in weekoff_dates:
            if weekoff_date not in uni_holidays_dates:
                number_of_days += 1
                holidays_week_off_days.append(weekoff_date)

        # Shift allocation
        worked_hours += number_of_days * self.contract_id.work_hours
        for day in self._get_date_list():
            if fields.Date.to_string(day) not in holidays_week_off_days and fields.Date.to_string(
                    day) not in holidays_uni_days:
                start, stop = self.get_start_stop_datetime(day)
                attendance_ids = self.env['hr.attendance'].search(
                    [('check_in', '>=', start), ('check_out', '<=', stop), ('employee_id', '=', self.employee_id.id)])
                if attendance_ids:
                    day_work_hours = sum(attendance_ids.mapped('worked_hours'))
                    if min_time <= day_work_hours and max_time >= day_work_hours:
                        worked_hours += day_work_hours
                        number_of_days += 0.5
                    if max_time < day_work_hours:
                        worked_hours += day_work_hours
                        number_of_days += 1
        return number_of_days, worked_hours

        def _get_new_worked_days_lines(self):
            if not self.contract_id.min_time and not self.contract_id.max_time:
                raise ValidationError(_('''Please define max time and min time in contract'''))
            if not self.contract_id or not self.contract_id.date_start:
                raise ValidationError(_("Contract or contract start not found"))
            if self.struct_id.use_worked_day_lines:
                number_of_days, worked_hours = self.get_attendance_days_time()
                worked_days_lines = self.worked_days_line_ids.browse([])
                worked_days_line_values = self._get_worked_day_lines()
                for r in worked_days_line_values:
                    if r.get('work_entry_type_id') in (1, 7):
                        r['number_of_days'] = number_of_days
                        r['number_of_hours'] = worked_hours
                        r['payslip_id'] = self.id
                return [(5, 0, 0)] + [(0, 0, vals) for vals in worked_days_line_values]
            return [(5, False, False)]

    @api.model
    def create(self, vals):
        print("_++_++_+_+_+_+create_+_+_+_+_+",vals,self,vals.get('date_from'))
       
        employee_id = vals.get('employee_id')
        if employee_id:
            resignation_request = self.env['hr.payslip'].search([('employee_id','=',vals.get('employee_id')),('date_from', '=', vals.get('date_from')),('date_to','=',vals.get('date_to')),('state', 'not in', ['cancel'])])
            print("========create=======resignation_request================",resignation_request)
            if resignation_request:
                raise ValidationError(_('The Salary slip is already created for %s for month %s to %s.', vals.get('name'), vals.get('date_from'), vals.get('date_to')))
        return super(HrPayslip, self).create(vals)


    def write(self, vals):
        print ("vals+_+_+_+_+_+_+_",vals)
        for rec in self:
            date_from, date_to = self._get_start_end_date()
            employee_id = rec.employee_id.id
            if vals.get('date_from') or vals.get('date_to'):
                print ("going in if")
                date_from = vals.get('date_from') or rec.date_from
                date_to = vals.get('date_to') or rec.date_to
                print ("date_from_)_)_)_)_)_vals",date_from)
                print ("date_to_)_)_)_)_)_vals",date_to)
                resignation_request = self.env['hr.payslip'].search(
                    [('employee_id', '=', rec.employee_id.id), ('date_from', '=', date_from),
                     ('date_to', '=', date_to), ('state', 'not in', ['cancel']),('id','!=',rec._origin.id)])
                print ("resignation_request__)_)_)_)",resignation_request)
                if resignation_request:
                    raise ValidationError(
                        _('The Salary slip is already created for %s for month %s to %s.', rec.employee_id.name,
                          date_from, date_to))
                resignation_request1 = self.env['hr.payslip'].search(
                    [('employee_id', '=', rec.employee_id.id), ('date_from', '=', date_from),
                        ('state', 'not in', ['cancel']),('id','!=',rec._origin.id)])
                print ("resignation_request1)_)_)_)",resignation_request1)
                if resignation_request1:
                    raise ValidationError(
                        _('The Salary slip is already created for %s for month %s to %s.', rec.employee_id.name,
                          date_from, date_to))
                resignation_request2 = self.env['hr.payslip'].search(
                    [('employee_id', '=', rec.employee_id.id), ('date_to', '=', date_to),
                        ('state', 'not in', ['cancel']),('id','!=',rec._origin.id)])
                print ("resignation_request2)_)_)_)",resignation_request2)
                if resignation_request2:
                    raise ValidationError(
                        _('The Salary slip is already created for %s for month %s to %s.', rec.employee_id.name,
                          date_from, date_to))
        return super(HrPayslip, self).write(vals)

    @api.onchange('employee_id')
    def _check_employee_dates(self):
        for rec in self:
            date_from, date_to = self._get_start_end_date()
            employee_id = self.employee_id.id
            if rec.employee_id:
                resignation_request = self.env['hr.payslip'].search(
                    [('employee_id', '=', rec.employee_id.id), ('date_from', '=', rec.date_from),
                     ('date_to', '=', rec.date_to), ('state', 'not in', ['cancel'])])
                if resignation_request:
                    raise ValidationError(
                        _('The Salary slip is already created for %s for month %s to %s.', rec.employee_id.name,
                          rec.date_from, rec.date_to))

    def compute_sheet(self):
        """function used for writing overtime record in payslip input tree."""
        for payslip in self:
            date_from, date_to = payslip._get_start_end_date()
            contract_id = payslip.contract_id
            if not contract_id or not contract_id.work_hours:
                return False

            payslip.input_line_ids = [(5, 0, 0)]
            payslip_input_users = []
            overtime_dict = {}
            earning_input_data = {}
            amount_value = 0.0

            input_type_input_type = self.env.ref('hr_overtime_automatic.hr_payslip_input_type_input')
            input_ids = self.env['hr.payslip.input'].browse(input_type_input_type)
            overtime_type = self.env['hr.salary.rule'].search([('code', '=', 'OT100')], limit=1)
            if not overtime_type:
                raise ValidationError(_("Rule for over time with code 'OT100' not found"))

            # Loan and Advance salary
            hr_loan_line = payslip._prepare_hr_loan_data()
            hr_advance_salary_line = payslip._prepare_hr_advance_salary_data()
            if hr_loan_line:
                payslip_input_users.append(hr_loan_line)
            if hr_advance_salary_line:
                payslip_input_users.append(hr_advance_salary_line)
            for pay_input in payslip_input_users:
                input_id = self.env['hr.payslip.input'].create(pay_input)
                input_id.write({
                    'is_loan': True,
                })

            # Overtime
            if payslip.employee_id.overtime_eligibility == "yes":
                overtime_ids = self.env['bt.hr.overtime']
                bt_overtime_ids = self.env['bt.hr.overtime'].search(
                    [('employee_id', '=', payslip.employee_id.id), ('start_date', '>=', date_from),
                     ('start_date', '<=', date_to), ('state', '=', 'validate'), ('is_payslip_create', '=', False)])
                overtime_ids |= bt_overtime_ids
                before_bt_overtime_ids = self.env['bt.hr.overtime'].search(
                    [('employee_id', '=', payslip.employee_id.id), ('start_date', '<=', date_from),
                     ('start_date', '<=', date_to), ('state', '=', 'validate'), ('is_payslip_create', '=', False)])
                overtime_ids |= before_bt_overtime_ids

                input_data = {
                    'name': overtime_type.name,
                    'code': overtime_type.code,
                    'payslip_id': payslip.id,
                    'contract_id': contract_id and contract_id.id,
                    'input_type_id': input_type_input_type.id,
                    'sequence': 1,
                    'amount': 0.0
                }

                for line in overtime_ids.filtered(lambda x: x.ot_type_id):
                    if line.ot_type_id not in overtime_dict:
                        overtime_dict[line.ot_type_id] = line
                    else:
                        overtime_dict[line.ot_type_id] |= line

                for key, values in overtime_dict.items():
                    overtime_amount = sum(values.mapped('overtime_hours'))
                    for rule_line_id in contract_id.rule_line_ids.filtered(
                            lambda x: x.ot_rule_id and x.ot_rule_id.ot_type_id and x.ot_rule_id.ot_type_id == key):
                        if rule_line_id.per_based_on == 'BASIC':
                            amount_value = payslip.contract_id.wage
                        elif rule_line_id.per_based_on == 'GROSS':
                            amount_value = payslip.contract_id.gross_amount
                        else:
                            amount_value = payslip.contract_id.net_amount

                        if rule_line_id.ot_type == 'fix':
                            input_data.update({'amount': overtime_amount * rule_line_id.fix_amount,
                                               'name': "%s-Rate-%s-Hours-%s" % (
                                               rule_line_id.ot_type_id.name, rule_line_id.fix_amount, overtime_amount)})
                            inputs = self.env['hr.payslip.input'].create(input_data)
                            values.write({'payslip_input_id': inputs.id})
                            inputs.write({
                                'is_overtime': True,
                            })

                        if rule_line_id.ot_type == 'percentage':
                            amount = round(((amount_value / 30) / contract_id.work_hours), 2)
                            per_amount = round(((amount * rule_line_id.per_amount) / 100), 2)
                            final_total = round(per_amount * overtime_amount, 2)
                            input_data.update({'amount': final_total, 'name': "%s-Rate-%s-Hours-%s" % (
                            rule_line_id.ot_type_id.name, per_amount, overtime_amount)})
                            inputs = self.env['hr.payslip.input'].create(input_data)
                            values.write({'payslip_input_id': inputs.id})
                            inputs.write({
                                'is_overtime': True,
                            })

            # other earnings
            map_earning_line_ids = self.env['other.earnings.line']
            earning_line_ids = self.env['other.earnings.line'].search(
                [('employee_id', '=', payslip.employee_id.id), ('date', '>=', date_from), ('date', '<=', date_to),
                 ('earnings_line_id.state', '=', 'confirm'), ('is_payslip_created', '=', False)])
            map_earning_line_ids |= earning_line_ids
            before_earning_line_ids = self.env['other.earnings.line'].search(
                [('employee_id', '=', payslip.employee_id.id), ('date', '<=', date_from), ('date', '<=', date_to),
                 ('earnings_line_id.state', '=', 'confirm'), ('is_payslip_created', '=', False)])
            map_earning_line_ids |= before_earning_line_ids
            payslip_input_ids = map_earning_line_ids
            for other_earnings in payslip_input_ids:
                inputs = other_earnings.mapped('payslip_input_type_id')
                other_rule_line_id = self.env['hr.salary.rule'].search([('code', '=', inputs.code)], limit=1)
                if other_rule_line_id:
                    code_lines = map_earning_line_ids.filtered(lambda x: x.payslip_input_type_id.code == inputs.code)
                    other_earn_amount = sum(code_lines.mapped('amount'))
                    final_earn_amount = other_earnings.amount if inputs.type == 'allowance' else - other_earnings.amount
                    if final_earn_amount != 0:
                        earning_input_data = {
                            'amount': final_earn_amount,
                            'code': inputs.code,
                            'payslip_id': payslip.id,
                            'contract_id': contract_id and contract_id.id,
                            'input_type_id': inputs.id,
                            'name': "Other-Earning-%s-%s" % (other_rule_line_id.name, final_earn_amount),
                            'sequence': 100,
                            'ref': other_earnings.earnings_line_id.id,
                            'is_other_earning': True,
                        }
                        self.env['hr.payslip.input'].create(earning_input_data)
        return super(HrPayslip, self).compute_sheet()

    def _get_start_end_date(self):
        """ This method will check start date and end date in payslip """
        for rec in self:
            date_start = rec.date_from
            date_end = rec.date_to
            if rec.contract_id and rec.contract_id.date_start and rec.date_from < rec.contract_id.date_start:
                date_start = rec.contract_id.date_start
            if rec.contract_id and rec.contract_id.date_end and rec.contract_id.date_end < rec.date_to:
                date_end = rec.contract_id.date_end
            return date_start, date_end

    def _get_date_list(self):
        from datetime import datetime, timedelta
        date_start, date_end = self._get_start_end_date()
        delta = date_end - date_start  # as timedelta
        return [date_start + timedelta(days=i) for i in range(delta.days + 1)]

    def get_start_stop_datetime(self, day):
        date_start = day.strftime(DEFAULT_SERVER_DATE_FORMAT) + " 00:00:00"
        date_stop = day.strftime(DEFAULT_SERVER_DATE_FORMAT) + " 23:59:59"
        date_utc_start = self._get_utc_time(date_start)
        date_utc_stop = self._get_utc_time(date_stop)
        return date_start, date_stop

    def _get_utc_time(self, date):
        """ Need to configure a time (local to server) in proper manners"""
        user_tz = self.env.user.tz or self.env.context.get('tz') or 'UTC'
        local = pytz.timezone(user_tz)
        date = datetime.datetime.strptime(datetime.datetime.strftime(
            local.localize(datetime.datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(pytz.utc),
            "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
        return date

    # def get_public_holidays_dates(self):
    #     public_holidays = []
    #     # weekoff_dates = self.get_week_off_dates()
    #     for day in self._get_date_list():
    #         start, stop = self.get_start_stop_datetime(day)
    #         rec = self.env['resource.calendar.leaves'].search([('date_from', '<=', start), ('date_to', '>=', stop), ('resource_id', '=',False),('holiday_task', '=', False)])
    #         leave_id = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id), ('request_date_from', '<=', day), ('request_date_to', '>=', day),('state','=','validate')])
    #         if not leave_id and rec:
    #             delta = rec.date_to - rec.date_from  # as timedelta
    #             for rec_record in rec:
    #                 delta = rec_record.date_to - rec_record.date_from  # as timedelta
    #                 for i in range(delta.days + 1):
    #                     public_holidays.append(rec_record.date_from.date() + timedelta(days=i))
    #     return list(set(public_holidays))

    def removeall_inplace(self, x, l):
        new_val = []
        for val in l:
            new_val.append(str(val))
        for _ in range(new_val.count(str(x))):
            new_val.remove(str(x))
        return [datetime.datetime.strptime(date, '%Y-%m-%d').date() for date in new_val]

    def get_public_holidays_dates(self):
        public_holidays = []
        for day in self._get_date_list():
            start, stop = self.get_start_stop_datetime(day)
            leave_id = self.env['hr.leave'].search(
                [('employee_id', '=', self.employee_id.id), ('request_date_from', '<=', day),
                 ('request_date_to', '>=', day), ('state', '=', 'validate')])
            if not leave_id:
                rec = self.env['resource.calendar.leaves'].search(
                    [('date_from', '<=', start), ('date_to', '>=', stop), ('resource_id', '=', False),
                     ('holiday_task', '=', False)])
                delta = rec.date_to - rec.date_from  # as timedelta
                for rec_record in rec:
                    delta = rec_record.date_to - rec_record.date_from  # as timedelta
                    for i in range(delta.days + 1):
                        record_leave_id = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id), (
                        'request_date_from', '<=', rec_record.date_from.date() + timedelta(days=i)), (
                                                                       'request_date_to', '>=',
                                                                       rec_record.date_from.date() + timedelta(days=i)),
                                                                       ('state', '=', 'validate')])
                        if len(record_leave_id.ids) == 0:
                            public_holidays.append(rec_record.date_from.date() + timedelta(days=i))
            else:
                delta = leave_id.request_date_to - leave_id.request_date_from  # as timedelta
                for rec_record in leave_id:
                    delta = rec_record.date_to - rec_record.date_from  # as timedelta
                    for i in range(delta.days + 1):
                        if rec_record and rec_record.date_from and rec_record.date_from.date() + timedelta(
                                days=i) in public_holidays:
                            public_holidays = self.removeall_inplace(rec_record.date_from.date() + timedelta(days=i),
                                                                     public_holidays)
        return list(set(public_holidays))

    def get_week_off_dates(self):
        date_start, date_end = self._get_start_end_date()
        day_of_week_ids = self.employee_id.dayofweek_ids.filtered(
            lambda x: x.date and x.date >= date_start and x.date <= date_end)
        day_of_week_days = day_of_week_ids.mapped('date')
        weekoff_dates = []
        for dates in day_of_week_days:
            start, stop = self.get_start_stop_datetime(dates)
            rec = self.env['resource.calendar.leaves'].search(
                [('date_from', '<=', start), ('date_to', '>=', stop), ('resource_id', '=', False),
                 ('holiday_task', '=', False)])
            if not rec:
                leave_id = self.env['hr.leave'].search(
                    [('employee_id', '=', self.employee_id.id), ('request_date_from', '<=', dates),
                     ('request_date_to', '>=', dates), ('state', '=', 'validate')])
                if not leave_id:
                    weekoff_dates.append(dates.strftime(DEFAULT_SERVER_DATE_FORMAT))
        return weekoff_dates

    # def get_public_holidays(self):
    #     public_holidays = 0.0
    #     weekoff_dates = self.get_week_off_dates()
    #     for day in self._get_date_list():
    #         start, stop = self.get_start_stop_datetime(day)
    #         leave_id = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id), ('request_date_from', '<=', day), ('request_date_to', '>=', day), ('state', '=', 'validate')])
    #         rec = self.env['resource.calendar.leaves'].search([('date_from', '<=', start), ('date_to', '>=', stop), ('resource_id', '=',False),('holiday_task', '=', False)])
    #         if not leave_id and rec:
    #             public_holidays += 1
    #     return public_holidays

    def get_public_holidays(self):
        public_holidays = 0.0
        weekoff_dates = self.get_week_off_dates()
        for day in self._get_date_list():
            start, stop = self.get_start_stop_datetime(day)
            leave_id = self.env['hr.leave'].search(
                [('employee_id', '=', self.employee_id.id), ('request_date_from', '<=', day),
                 ('request_date_to', '>=', day), ('state', '=', 'validate')])
            if not leave_id:
                # rec = self.env['resource.calendar.leaves'].search([('date_from', '<=', start), ('date_to', '>=', stop), ('resource_id', '=',False),('holiday_task', '=', False)])
                # if not leave_id and rec:
                public_holidays += 1
        return public_holidays

    def _get_paid_leaves(self):
        paid_leave = 0.0
        for day in self._get_date_list():
            leave_id = self.env['hr.leave'].search([
                ('state', '=', 'validate'),
                ('employee_id', '=', self.employee_id.id),
                ('request_date_from', '<=', day),
                ('request_date_to', '>=', day),
                ('holiday_status_id.is_sick_leave', '!=', True),
                ('holiday_status_id.work_entry_type_id.is_paid', '=', True),
            ])
            if leave_id:
                paid_leave += 1
        return paid_leave

    @api.depends('salary_days', 'attendance_days', 'unpaid_day')
    def _get_absent_leaves_days(self):
        for rec in self:
            rec.absent_day = rec.salary_days - rec.attendance_days - rec.unpaid_day

    # def _get_unpaid_leaves(self):
    #     unpaid_leave = 0.0
    #     self.unpaid_day = 0.0
    #     print('LLLLLLLLLLLLLLeave',self.unpaid_day)
    #     for day in self._get_date_list():
    #         leave_id = self.env['hr.leave'].search([
    #             ('state', '=', 'validate'),
    #             ('employee_id', '=', self.employee_id.id),
    #             ('request_date_from', '<=', day),
    #             ('request_date_to', '>=', day),
    #             ('holiday_status_id.work_entry_type_id.is_paid', '=', False),
    #             ('holiday_status_id.is_sick_leave', '=', False),
    #         ])
    #         print('LLLLLLLLLLLLLLeave',leave_id)
    #         if leave_id:
    #             unpaid_leave += 1
    #         self.unpaid_day = unpaid_leave
    # return unpaid_leave

    def _get_unpaid_leaves(self):
        unpaid_leave = 0.0
        for day in self._get_date_list():
            leave_id = self.env['hr.leave'].search([
                ('state', '=', 'validate'),
                ('employee_id', '=', self.employee_id.id),
                ('request_date_from', '<=', day),
                ('request_date_to', '>=', day),
                ('holiday_status_id.work_entry_type_id.is_paid', '=', False),
                ('holiday_status_id.is_sick_leave', '=', False),
            ])
            if leave_id:
                unpaid_leave += 1
        return unpaid_leave

    @api.depends('worked_days_line_ids')
    def _compute_unpaid_leaves(self):
        for rec in self:
            unpaid_days = rec._get_unpaid_leaves()
            rec.unpaid_day = unpaid_days

    def get_present_days(self):
        date_from, date_to = self._get_start_end_date()
        domain = [('employee_id', '=', self.employee_id.id), ('check_in', '>=', date_from), ('check_in', '<=', date_to)]
        ignore_ids = []
        for obj in self.env['hr.attendance'].search(domain):
            start_date = datetime.datetime.strptime(obj.check_in.strftime('%Y-%m-%d %H:%M:%S'),
                                                    DEFAULT_SERVER_DATETIME_FORMAT)
            record_check_in = fields.Date.from_string(start_date)
            day_of_week_ids = obj.employee_id.dayofweek_ids.filtered(lambda x: x.date == record_check_in)
            public_leaves = self.env['resource.calendar.leaves'].search(
                [('date_from', '<', obj.check_in), ('date_to', '>', obj.check_in), ('holiday_task', '=', False)])
            public_holidays = public_leaves.filtered(lambda x: not x.resource_id)
            if public_holidays or day_of_week_ids:
                ignore_ids.append(obj.id)
        domain = domain + [('id', 'not in', ignore_ids)]
        day_attandance_lines = self.env['hr.attendance'].read_group(domain, ['employee_id', 'worked_hours'],
                                                                    ['check_in:day'])
        return float(len(day_attandance_lines))

    def get_absent_days(self):
        absent_days = 0.0
        for day in self._get_date_list():
            attendance_id = self.env['hr.attendance'].search([
                ('employee_id', '=', self.employee_id.id),
                ('check_in', '<=', day),
                ('check_out', '>=', day),
            ])
            leave_id = self.env['hr.leave'].search([
                ('state', '=', 'validate'),
                ('employee_id', '=', self.employee_id.id),
                ('request_date_from', '<=', day),
                ('request_date_to', '>=', day),
            ])
            public_holidays = self.env['resource.calendar.leaves'].search(
                [('date_from', '<=', day), ('date_to', '>=', day), ('resource_id', '=', False),
                 ('holiday_task', '=', False)])
            if not attendance_id and not leave_id and not public_holidays:
                absent_days += 1
            self.absent_day = absent_days
        return absent_days

    def get_overtime(self):
        amount = 0.0
        date_from, date_to = self._get_start_end_date()
        overtime_ids = self.env['bt.hr.overtime'].search([
            ('state', '=', 'validate'),
            # ('start_date', '>=', date_from),
            # ('start_date', '<=', date_to),
            ('employee_id', '=', self.employee_id.id),
            ('ot_type_id.code', 'in', ('NOD', 'RAMD')),
        ])
        if overtime_ids and overtime_ids[0].payslip_input_id:
            amount = sum(overtime_ids.mapped('payslip_input_id').mapped('amount'))
        return round(sum(overtime_ids.mapped('overtime_hours')), 2), amount

    def get_special_overtime(self):
        amount = 0.0
        date_from, date_to = self._get_start_end_date()
        overtime_ids = self.env['bt.hr.overtime'].search([
            ('state', '=', 'validate'),
            # ('start_date', '>=', date_from),
            # ('start_date', '<=', date_to),
            ('employee_id', '=', self.employee_id.id),
            ('ot_type_id.code', 'not in', ('NOD', 'RAMD')),
        ])
        if overtime_ids and overtime_ids[0].payslip_input_id:
            amount = sum(overtime_ids.mapped('payslip_input_id').mapped('amount'))
        return round(sum(overtime_ids.mapped('overtime_hours')), 2), amount

    def get_other_data(self):
        day1 = 0.0
        day1_amt = 0.0
        day2 = 0.0
        day2_amt = 0.0

        for line in self.input_line_ids:
            type_id = self.input_line_ids.input_type_id
            if '-Rate' in line.name and 'Hours-' in line.name:
                if 'OT100' in type_id.sudo().mapped('code'):
                    ot_type = line.name.split('-Rate')[0]
                    ot_hours = line.name.split('Hours-')[1]
                    if ot_type in ['Weekday Days', 'Ramadan Days']:
                        day1 += float(ot_hours)
                        day1_amt += float(line.amount)
                    if ot_type in ['Weekend Days', 'Normal Holidays']:
                        day2 += float(ot_hours)
                        day2_amt += float(line.amount)
                elif 'OT100' not in type_id.sudo().mapped('code'):
                    pass

        date_from, date_to = self._get_start_end_date()
        domain = [('employee_id', '=', self.employee_id.id), ('check_in', '>=', date_from), ('check_in', '<=', date_to)]
        attendance_ids = self.env['hr.attendance'].search(domain)
        week_of = self.env['hr.day.of.week'].search_count(
            [('employee_id', '=', self.employee_id.id), ('date', '>=', date_from), ('date', '<=', date_to)])
        public_holidays = 0.0
        ph_ids = self.env['resource.calendar.leaves'].search([])
        for holiday in ph_ids:
            if (holiday.date_from.month == date_from.month) and (holiday.date_to.month == date_to.month):
                public_holidays += (holiday.date_to - holiday.date_from).days + 1
        overtime_hours, overtime_amount = self.get_overtime()
        special_overtime_hours, special_overtime_amount = self.get_special_overtime()
        total_hours = sum(attendance_ids.mapped('worked_hours'))
        data = {
            # 'Week Off': float(week_of),
            'Week Off': self.shift_days,
            # 'Public Holiday': self.get_public_holidays(),
            'Public Holiday': self.public_holidays,
            # 'Present Days': self.get_present_days(),
            'Present Days': self.present_day,
            'Total Hours': total_hours,
            'Unpaid Leave': self._get_unpaid_leaves(),
            'Absent Days': self.salary_days - self.attendance_days - self.unpaid_day,
            # 'Paid Leave': self._get_paid_leaves(),
            'Paid Leave': self.leave_day,
            'Overtime': day1,
            'Overtime Amount': day1_amt,
            'Special Overtime': day2,
            'Special Overtime Amount': day2_amt,
        }
        leave_data = []
        col = {}
        for key, value in data.items():
            if value <= 0:
                continue
            if len(col) == 3:
                leave_data.append(col)
                col = {}
            col[key] = value
        leave_data.append(col)
        return leave_data


class HrContract(models.Model):
    _inherit = "hr.contract"

    min_time = fields.Float(string="Min Time")
    max_time = fields.Float(string="Max Time")
    allowance_ids = fields.One2many('hr.allowance.type', 'contract_id')
    structure_id = fields.Many2one('hr.payroll.structure', string="Salary Structure")
    gross_amount = fields.Float(compute="_compute_total_salary", store=True)
    net_amount = fields.Float(compute="_compute_total_salary", store=True)
    allowance = fields.Float(compute="_compute_allowance", store=True)
    state = fields.Selection(selection_add=[('approval', 'Approval'),('open',),('rejects','Rejected')], ondelete={'approval': 'set default'})
    reject_reason = fields.Text(copy=False,readonly=True)
    is_approve_user = fields.Boolean(string="approve user",default=False)
    approver_count = fields.Integer(string="Count Approvers",store=True)
    current_approver_count = fields.Integer(string="current approve count",store=True)
    temp_approver_count = fields.Integer(string="current approve count",store=True,default=0)


    @api.depends('gross_amount', 'wage')
    def _compute_allowance(self):
        for rec in self:
            rec.allowance = rec.gross_amount - rec.wage

    @api.depends('allowance_ids', 'wage')
    def _compute_total_salary(self):
        amount = 0.0
        for rec in self:
            amount = sum(rec.allowance_ids.filtered(lambda x: x.category_id.code == 'ALW').mapped('amount'))
            rec.gross_amount = rec.wage + amount
            net_amount = sum(rec.allowance_ids.filtered(lambda x: x.category_id.code == 'DED').mapped('amount'))
            rec.net_amount = rec.gross_amount - net_amount

    @api.onchange('structure_id')
    def onchange_internal_type(self):
        if self.structure_id:
            rule_ids = [(5, 0, 0)]
            for rec in self.structure_id.mapped('rule_ids').filtered(
                    lambda x: x.category_id.code == 'ALW' or x.category_id.code == 'DED'):
                rule_ids.append([0, 0, {'name': rec.name, 'category_id': rec.category_id.id, 'code': rec.code}])
            if rule_ids:
                self.allowance_ids = rule_ids

    @api.constrains('allowance_ids')
    def _check_duplicate_allowance_code(self):
        for contract in self:
            for allowance_code in contract.allowance_ids.mapped("code"):
                if allowance_code:
                    allowance_ids = self.env['hr.allowance.type'].search_count(
                        [('contract_id', '=', contract.id), '|', ('code', '=', allowance_code), '|',
                         ('code', '=', allowance_code.lower()), ('code', '=', allowance_code.upper())])
                    if allowance_ids > 1:
                        raise ValidationError(_("%s Duplicated code") % (allowance_code))

    def approve_emp_contract(self):
        users = []
        users_obj = self.env['res.users']
        self.current_approver_count += 1
        user_count = []

        for user in users_obj.search([]):
            if user.has_group("hr_payroll_extended.group_hr_contract_approver"):
                users.append(user)
                # if user.id == self.env.user.id:
                #     user.is_approve_by_user = False
                if user.is_approve_by_user == True:
                    user_count.append(user)

                # if user.id in users:


        self.approver_count = len(users)
        print("==================counting======before============",self.current_approver_count,self.approver_count,self.env.user.is_approve_by_user,users,user_count,self.env.user.click_count)
        if self.current_approver_count == 1:
            self.env.user.is_approve_by_user = False

        if len(users) == len(user_count) and self.env.user.is_approve_by_user == True:
            print("==============if 1===========")
            # res = [i.is_approve_by_user==False for i in user_count]
            for user in user_count:
                user.is_approve_by_user = False
                user.click_count = 0
            self.state="open"
            self.current_approver_count = 0

        if self.current_approver_count == self.approver_count:
            print("==============if 2===========")

            if self.env.user.click_count > 1:
                print("==============if if 1===========")

                self.current_approver_count -= 1
                raise ValidationError(_('Yor Already Approved This Contract'))
            else:
                print("==============if else 1===========")

                self.env.user.is_approve_by_user = True
                self.env.user.click_count += 1


            self.current_approver_count = 0
            self.env.user.is_approve_by_user = False
            # self.current_approve_user = False
            self.env.user.click_count = 0

        if self.current_approver_count != self.approver_count and self.env.user.is_approve_by_user == True:
            print("==============if 3===========")

            self.current_approver_count -= 1
            raise ValidationError(_('Yor Already Approved This Contract'))

   
        else:
            print("==============else 3===========")

            self.env.user.is_approve_by_user = True
            # self.current_approve_user = True
            self.env.user.click_count += 1
            self.current_approver_count += 1


     
            # self.current_approver_count = 0

        
        # self.temp_approver_count = self.current_approver_count
        # self.current_approver_count = 0
        return True


    # def reject_emp_contract(self):
    #     approved_id = approve_records_obj.search([('contract_id','=',self.id),('user_id','=',self.env.uid)])
    #     print ("approved_id+_+_+_+_-while_approving",approved_id)
    #     if approved_id.state == "approved":
    #         raise UserError(_('Contract Once Approved Cannot be Rejected'))
    #     if approved_id:
    #         raise UserError(_('You have already Approved this Conttract, Hence You can Reject'))
    #     self.state = 'rejects'
    #     # print("============reject_emp_contract============",self)
    #     # self.unlink()
    #     return True
    
    def contract_reject(self):
        '''
        This function returns an action to Enter Contract Reject Reason
        of given Contract.
        '''
        approve_records_obj = self.env['contract.approval.records']
        approved_id = approve_records_obj.search([('contract_id','=',self.id),('user_id','=',self.env.uid),('contract_active','=',True)])
        print ("approved_id+_+_+_+_-while_approving",approved_id)
        if approved_id.state == "approved":
            raise UserError(_('Contract Once Approved Cannot be Rejected'))
        view = self.env.ref('hr_payroll_extended.reject_reason_wizard_form_view')
        action = {
            'name': _('Contract Reject'),
            'type': 'ir.actions.act_window',
            'res_model': 'contract.reject.reason.wizard',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
        }
        return action
    
    def send_to_expiry(self):
        self.state = 'close'
        return True
    
    def send_to_cancel(self):
        self.state = 'cancel'
        return True
    
    def resubmit_contract(self):
        self.state = 'approval'
        approve_records_obj = self.env['contract.approval.records']
        approved_id= approve_records_obj.search([('contract_id','=',self.id),('user_id','=',self.env.uid),('contract_active','=',True)])
        print ("approved_id+_+_+_+_+_+_",approved_id)
        if approved_id:
            approved_id.write({'contract_active':False})
        new_approval_id = approve_records_obj.create({'contract_id':self.id,'user_id':self.env.uid,'state':'pending', 'active':True,'contract_active':True})
        print ("approval_id++_+_+_+_+_",new_approval_id)
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'hr.contract')], limit=1)
        contract_approval_id = self.env['contract.approval.process'].search([])
        if approved_id.activity_id:
            old_activity_id.unlink()
        if contract_approval_id and model_id:
            activity_vals = {
                        'res_model_id': model_id.id,
                        'res_model': 'hr.contract',
                        'res_id': self.id,
                        'res_name': self.name,
                        'user_id': self.env.uid,
                        'activity_type_id': contract_approval_id.activity_type_id.id,
                        'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M'),
                        }
        activity_id = self.env['mail.activity'].create(activity_vals)
        print ("activity_id+__+_+_+_+_+_+",activity_id)
        return True
    
    def approve_contract(self):
        approve_records_obj = self.env['contract.approval.records']
        print ("self.uid+_+_+_+_+_",self.env.uid)
        
        approved_id = approve_records_obj.search([('contract_id','=',self.id),('user_id','=',self.env.uid),('contract_active','=',True)])
        print ("approved_id+_+_+_+_-while_approving",approved_id)
        if approved_id:
            print ("approved_id.state+_+_+_+_",approved_id.state)
            if approved_id.state == 'approved':
                raise UserError(_('You have already Approved this Conttract'))
                        
            if approved_id.state == 'pending':
                approved_id.write({'state':'approved'})
                self._cr.commit()
                contract_run = self._check_to_make_contract_running()
                print ("contract_run+_+_+__+",contract_run)
                if contract_run == 'all_approved':
                    self.write({'state':'open'})
                if approved_id.activity_id:
                    approved_id.activity_id.action_done()
        else:
            raise UserError(_('Either Record is not created or You dont have right to approve'))
        return True
    
    def _check_to_make_contract_running(self):
        approve_records_obj = self.env['contract.approval.records']
        approved_id = approve_records_obj.search([('contract_id','=',self.id),('state','=','pending')])
        print ("approved_id_+_+_+_+check_status",approved_id)
        if not approved_id:
            return 'all_approved'
        else:
            return 'all_not_approved'
    
    
    
    def open_approval_status(self):
        '''
        This function returns an action that display contract approval details
        of given Contract.
        '''
        view = self.env.ref('hr_payroll_extended.contract_approval_records_tree')
        action = {
            'name': _('Contract Approvals'),
            'type': 'ir.actions.act_window',
            'res_model': 'contract.approval.records',
            'view_mode': 'tree',
            'views': [(view.id, 'tree')],
            'view_id': view.id,
            'target': 'new',
        }
        contract_approval_ids = self.env['contract.approval.records'].search([('contract_id','=',self.id)])
        print ('contract_approval_ids+_+_+_+_+_+_',contract_approval_ids)
        if contract_approval_ids:
            action['domain'] = [('id', 'in', contract_approval_ids.ids)]
        else:
            action['domain'] = [('id', 'in', [])]
        return action
    
    @api.model
    def create(self, vals):
        res = super(HrContract, self).create(vals)
        contract_approval_id = self.env['contract.approval.process'].search([])
        if contract_approval_id:
            for lines in contract_approval_id.approver_ids:
                approval_id = self.env['contract.approval.records'].create({'contract_id':res.id,'user_id':lines.user_id.id,'state':'pending', 'active':True,'contract_active':True})
        return res
    



    def submit_contract(self):
        users_obj = self.env['res.users']
        approve_records_obj = self.env['contract.approval.records']
        contract_approval_id = self.env['contract.approval.process'].search([])
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'hr.contract')], limit=1)
        if contract_approval_id:
            for lines in contract_approval_id.approver_ids:
                activity_vals = {'res_model_id': model_id.id,
                                'res_model': 'hr.contract',
                                'res_id': self.id,
                                'res_name': self.name,
                                'user_id': lines.user_id.id,
                                'activity_type_id': contract_approval_id.activity_type_id.id,
                                'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')}
                activity_id = self.env['mail.activity'].create(activity_vals)
                print ("activity_id+__+_+_+_+_+_+",activity_id)
                approved_id = approve_records_obj.search([('contract_id','=',self.id),('user_id','=',lines.user_id.id),('contract_active','=',True)])
                if approved_id:
                    approved_id.write({'activity_id': activity_id})
        self.state="approval"

    def notify_contract_info(self):
        users_obj = self.env['res.users']
        users = []
        message = f"New Contract Is Created For {self.employee_id.name}"
        for user in users_obj.search([]):
            if user.has_group("hr_payroll_extended.group_hr_contract_approver"):
                print("===========user===========",user)
                users.append(user.partner_id.id)
                self.env['bus.bus']._sendone(
                    user.partner_id,
                    "simple_notification",
                    {
                    "title":"Information",
                    "message":message,
                    "sticky":True,
                    "warning":True,
                    })
                # self.is_approve_user = True
                # print("==========res_user_obj===========",user)
                # user.notify_info("New Contract Is Created")
                # res_user_obj = self.env['res.users'].search([('group','=','group_hr_contract_approver')])
                print("==========res_user_obj===========",users)

        self.message_post(body="your message", partner_ids=users)

        return True
      
    # @api.constrains('kanban_state','state')
    # def _check_current_contract(self):
    #     res = super(HrContract,self)._check_current_contract()
    #     approval = self.env['record.approval'].sudo().search([('model_id.model', '=', 'hr.contract')], limit=1)
    #     user_ids = approval.approver_ids.mapped('user_id.id')
    #     approved_ids = self.env['record.approved'].sudo().search([('res_model', '=', 'hr.contract'),('res_id','=',self.id),('user_id','in',user_ids)])
    #     approve_user_id = approved_ids.filtered(lambda x:x.state =='approved')
    #     non_approve_user = approved_ids.filtered(lambda x:x.state =='pending')
    #     print("______________check_current_contract________________",self.state,self,approval,len(user_ids),self.approver_count,approved_ids,len(approve_user_id),non_approve_user)
    # 
    #     # if self.state != 'approval':
    #     #     if self.env.user.id not in user_ids:
    #     #         print("_+_+_+_+_+non approver user_+_+_+_+_+_+_+")
    #     #     # self.is_approve_user = True
    #     #     # if self.state == 'open' or self.state == 'rejects'  or self.state == 'close' or self.state == 'approval':
    #     #         raise ValidationError(
    #     #             ('You dont  have permission to change the state of contracts')
    #     #         )
    #     # if len(approve_user_id) == len(user_ids):
    #     #     if self.state =='approval' or self.state == 'draft' or self.state == 'rejects':
    #     #         print("++++___________++++++++_________approver user__________++++for running sate+++++++")
    #     #         raise ValidationError(
    #     #             ('You dont  have permission to change the state of contracts')
    #     #             )
    #     if len(non_approve_user) > 0:
    #         if self.state == 'open':
    #             raise ValidationError(
    #                 ('You dont  have permission to change the state of contracts')
    #                 )
    # 
    #     # if self.state == 'rejects':
    #     #     raise ValidationError(
    #     #             ('This Contract has been rejected, you can not change its state')
    #     #             )
    #     return res


class HrAllowanceType(models.Model):
    _name = "hr.allowance.type"

    name = fields.Char()
    code = fields.Char()
    amount = fields.Float()
    category_id = fields.Many2one('hr.salary.rule.category', string="Type")
    contract_id = fields.Many2one('hr.contract')


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'
    _description = "Leave Type"

    is_paid = fields.Boolean(string="Leave Settlement")
    other_input_type = fields.Many2one('hr.payslip.input.type')


class TimeoffRamadan(models.Model):
    _name = 'timeoff.ramadan'
    _description = "Ramadan"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    hours = fields.Float(string="Hours")


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    is_other_earning = fields.Boolean(string="Other Earning")
    other_earning_id = fields.Many2one('other.earnings', string='Other Earning')

    is_overtime = fields.Boolean(string="Overtime")
    overtime_id = fields.Many2one('bt.hr.overtime', string='Overtime')

    is_loan = fields.Boolean(string="Loan")
    loan_id = fields.Many2one('hr.loan', string='Loan')
    ref = fields.Char(string="Ref fields")

class ResUsers(models.Model):
    _inherit = 'res.users'
   
    is_approve_by_user = fields.Boolean(string="Approved by user",default=False)
    click_count = fields.Integer(string="count click",default=0)
    
