# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta, datetime, time, date
from odoo.tools.float_utils import float_round

import math

import datetime
import logging

from collections import defaultdict
from datetime import time, timedelta

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.addons.resource.models.resource import Intervals

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    @api.model
    def get_days_all_request(self):
        print('self._model_sorting_key+++++++++++', self._model_sorting_key)

        leave_types = sorted(self.search([]).filtered(lambda x: ((x.virtual_remaining_leaves > 0 or x.max_leaves))),
                             key=self._model_sorting_key, reverse=True)
        _logger.info("\n<<LEAVE TYPE FROM ADDONS METHOD>>-----------%s", leave_types)
        if leave_types:
            _logger.info("<<MAIN LIST>>-----------%s", [lt._get_days_request() for lt in leave_types])
            return [lt._get_days_request() for lt in leave_types]

        leave_types1 = sorted(self.search([]).filtered(lambda x: ((x.virtual_remaining_leaves < 0 or x.max_leaves))),
                              key=self._model_sorting_key, reverse=True)
        _logger.info("\n<<LEAVE TYPE111 FROM ADDONS METHOD>>-----------%s", leave_types1)
        if leave_types1:
            _logger.info("<<MAIN LIST1111>>-----------%s", [lt._get_days_request() for lt in leave_types1])
            return [lt._get_days_request() for lt in leave_types1]

        if not leave_types and not leave_types1:
            _logger.info("\n<<EMPTY DATA NO LEAVE TYPE>>-----------")
            return []
