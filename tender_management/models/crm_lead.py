from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError
from datetime import datetime


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    tender_id = fields.Many2one(
        'tender.management',
        string='Tender'
    )

    tender_count = fields.Integer(
        string='Tender Count',
        compute='_compute_tender_count'
    )

    @api.depends('tender_id')
    def _compute_tender_count(self):
        for rec in self:
            rec.tender_count = 1 if rec.tender_id else 0

    def action_view_tender(self):

        self.ensure_one()

        if not self.tender_id:
            raise UserError(_("No Tender linked to this lead."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Tender'),
            'res_model': 'tender.management',
            'view_mode': 'form',
            'res_id': self.tender_id.id,
            'target': 'current',
        }
    

