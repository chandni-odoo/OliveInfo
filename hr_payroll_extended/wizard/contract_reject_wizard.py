# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError


class RejectReasonWizard(models.TransientModel):
    _name = "contract.reject.reason.wizard"
    _description = "Contract Reject Reason Wizard"

    reject_reason = fields.Text(string="Reject Reason")

    def action_reject(self):
        active_model = self.env.context.get('active_model')
        active_id = self.env[active_model].browse(self.env.context.get('active_id'))
        approved_id = self.env['contract.approval.records'].search([('contract_id','=',active_id.id),('user_id','=',self.env.uid),('active','=',True)])
        if approved_id:
            approved_id.write({'state':'rejected'})
        else:
            raise UserError(_('You Dont have access to reject this contract'))
        active_id.write({'reject_reason': self.reject_reason,'state':'rejects'})
