# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import UserError, ValidationError

class PurchaseApproval(models.Model):
    _name = "purchase.approval"
    _description = "Purchase Approval"
    _rec_name = 'model'

    model = fields.Selection([('indent', 'Indent Request'), ('purchase', 'Purchase')], string='Model', required=True, default='indent')
    approval_line_ids = fields.One2many('purchase.approval.lines', 'approval_id', string="Approval Line")
    purchase_type = fields.Selection([('capex', 'Capex'), ('opex', 'Opex'), ('small','Small'), ('other','Other')], default='other', string="Type")
    branch_id = fields.Many2one('res.branch', string="Branch")

    @api.constrains('approval_line_ids')
    def _check_duplicate_user_id(self):
        for approval in self:
            for user in approval.approval_line_ids.mapped("user_id"):
                line_ids = self.env['purchase.approval.lines'].search_count([('approval_id', '=', approval.id), ('user_id', '=', user.id)])
                if line_ids > 1:
                    raise ValidationError(("Duplicated approver not allow"))

class PurchaseApprovalLines(models.Model):
    _name = "purchase.approval.lines"
    _description = 'Purchase Approval Lines'

    approval_id = fields.Many2one("purchase.approval")
    user_id = fields.Many2one("res.users", string="Approver")
    limit = fields.Float(string="Limit")
