from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict

class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    def print_eosb_report_xls(self):
        active_record = self
        data = {
            'active_record': active_record.id,
        }
        return self.env.ref('pways_eosb_xls_report.eosb_xlsx').report_action(self, data=data)
