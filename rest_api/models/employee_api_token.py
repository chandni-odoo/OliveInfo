from odoo import models, fields, api
from datetime import timedelta


class EmployeeApiToken(models.Model):
    _name = 'employee.api.token'
    _description = 'API Tokens for Employee Authentication'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='cascade')
    token = fields.Char(string='Authentication Token', required=True)
    expiration_date = fields.Datetime(string='Expiration Date', required=True)
    is_active = fields.Boolean(string='Active', default=True)

    @api.model
    def clean_expired_tokens(self):
        expired_tokens = self.search([
            ('expiration_date', '<', fields.Datetime.now()),
            # ('is_active', '=', True)
        ])
        if expired_tokens:
            for token in expired_tokens:
                token.unlink()
            # expired_tokens.write({'is_active': False})
