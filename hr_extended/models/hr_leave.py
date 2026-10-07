# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date_state(self):
        res = super(HolidaysRequest, self)._check_date_state()
        for leave in self:
            hr_contract_ids = leave.employee_id.contract_ids.filtered(lambda x: x.state == 'open')
            if not hr_contract_ids:
                raise ValidationError(_("Employee does not have any running contract"))
            for hr_contract in hr_contract_ids:
                if not hr_contract.date_start:
                    raise ValidationError(_("Start date not found in contract"))
                req_date_from = leave.request_date_from
                req_date_to = leave.request_date_to
                # if hr_contract.date_start and hr_contract.date_end:
                #     if hr_contract.date_start > req_date_from or hr_contract.date_end < req_date_from or hr_contract.date_end < req_date_to:
                #         pass
                #         # raise ValidationError(_("Employee contract has expired. Please renew it."))
                # else:
                # point no 7
                if hr_contract.state in ['close', 'cancel']:
                    # if hr_contract.date_start and req_date_from and hr_contract.date_start > req_date_from:
                    # raise ValidationError(_("Employee contract start date is smaller then leave start date"))
                    raise ValidationError(_("Employee contract has expired. Please renew it."))
        return res
