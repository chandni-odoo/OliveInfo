# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression

class ResBranch(models.Model):
    _name = 'res.branch'
    _description = 'Branch'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True)
    telephone = fields.Char(string='Telephone No')
    address = fields.Text('Address')

    def name_get(self):
        res_list = []
        for rec in self:
            if rec.name and rec.code:
                res_list.append((rec.id,rec.code +' - ' + rec.name))
            else:
                res_list.append((rec.id, rec.name))
        return res_list

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = ['|', ('name', 'ilike', name), ('code', 'ilike', name)]
            if self._context.get('allowed_company_ids'):
                selected_company_ids = self.env['res.company'].browse(self._context.get('allowed_company_ids'))
                if selected_company_ids:
                    branches_ids = self.env['res.branch'].search([('company_id','in',selected_company_ids.ids)])
                    domain += [('id', 'in', branches_ids.ids)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)