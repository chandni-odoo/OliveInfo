# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import UserError, ValidationError

class SaleApproval(models.Model):
    _name = "sale.approval"
    _description = "Sale Approval"

    document_type = fields.Selection([('costing', 'Costing'), ('draft', 'Quotation'),('customer_approve', 'Customer Approve'), 
        ('agreement', 'Agreement'), ('pre_approval', 'Pre Approval'), ('sale', 'Sales Order')], string='Document Type', required=True)
    approval_line_ids = fields.One2many('sale.approval.lines', 'approval_id', string="Approval Line")
    branch_id = fields.Many2one('res.branch', string="Branch")

    @api.constrains('approval_line_ids')
    def _check_duplicate_user_id(self):
        for approval in self:
            for user in approval.approval_line_ids.mapped("user_id"):
                line_ids = self.env['sale.approval.lines'].search_count([('approval_id', '=', approval.id), ('user_id', '=', user.id)])
                if line_ids > 1:
                    raise ValidationError(("Duplicated approver not allow"))

class SaleApprovalLines(models.Model):
    _name = "sale.approval.lines"
    _description = 'Sale Approval Lines'

    approval_id = fields.Many2one("sale.approval")
    user_id = fields.Many2one("res.users", string="Approver")
    limit = fields.Float(string="Limit")
