from odoo import models, fields, api
from odoo.exceptions import UserError

class VisaQuotaReportWizard(models.TransientModel):
    _name = 'visa.quota.report.wizard'
    _description = 'Visa Quota Availability Report Wizard'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    visa_type_ids = fields.Many2many('visa.type', string='Visa Types')
    nationality_ids = fields.Many2many('res.country', string='Nationalities')

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError("Date From must be less than or equal to Date To")

    def action_print_report(self):
        self.ensure_one()
        domain = []
        
        if self.date_from and self.date_to:
            domain.extend([
                ('validity_from_date', '<=', self.date_to),
                ('validity_to_date', '>=', self.date_from),
            ])
        elif self.date_from:
            domain.append(('validity_to_date', '>=', self.date_from))
        elif self.date_to:
            domain.append(('validity_from_date', '<=', self.date_to))
        
        if self.visa_type_ids:
            domain.append(('visa_type_id', 'in', self.visa_type_ids.ids))
        
        date_from_str = self.date_from.strftime("%d/%m/%Y") if self.date_from else False
        date_to_str = self.date_to.strftime("%d/%m/%Y") if self.date_to else False
        
        data = {
            'date_from': date_from_str,
            'date_to': date_to_str,
            'visa_type_ids': self.visa_type_ids.ids if self.visa_type_ids else [],
            'nationality_ids': self.nationality_ids.ids if self.nationality_ids else [],
            'domain': domain,
        }
        
        return self.env.ref('visa_processing.action_visa_quota_availability_xlsx').report_action(self, data=data)
