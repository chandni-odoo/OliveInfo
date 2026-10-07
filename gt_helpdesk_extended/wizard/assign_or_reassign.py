# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError


class AssignReAssign(models.TransientModel):
    _name = "assign.or.reassing"
    _description = "AssignReAssign"

    assigner_id = fields.Many2one('res.users',required=True,domain=lambda self: [('groups_id', 'in', self.env.ref('helpdesk.group_helpdesk_user').id)])

    def reassign_user(self):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            ticket_id = self.env['helpdesk.ticket'].browse(active_ids)
            if ticket_id:
                ticket_id.write({'user_id':self.assigner_id.id})
        return True