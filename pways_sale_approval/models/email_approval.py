from odoo import models,fields,api
from odoo.exceptions import UserError, ValidationError

class HrApprovalEmail(models.Model):
    _name = "hr.approval.email"
    _description = "HR Approval Email"

    document_type = fields.Selection([('procurement', 'Procurement'),('accommodation','Accommodation')], string='Document Type', required=True)
    approval_line_ids = fields.One2many('hr.approval.email.lines', 'hr_id', string="Approval Line")
    branch_id = fields.Many2one('res.branch', string="Branch")

    @api.constrains('approval_line_ids')
    def _check_duplicate_email_user_id(self):
        for approval in self:
            for user in approval.approval_line_ids.mapped("user_id"):
                line_ids = self.env['hr.approval.email.lines'].search_count([('hr_id', '=', approval.id), ('user_id', '=', user.id)])
                if line_ids > 1:
                    raise ValidationError(("Duplicated approver not allow"))

class HRApprovalLines(models.Model):
    _name = "hr.approval.email.lines"
    _description = 'Hr Approval Lines'

    hr_id = fields.Many2one("hr.approval.email")
    user_id = fields.Many2one("res.users", string="Approver")
    limit = fields.Float(string="Limit")


class EmailManagement(models.Model):
    _name = 'email.notification.management'
    _description = 'Email Management'

    customer_service_email = fields.Char(string='Customer Service Email')
    scheduler_email = fields.Char(string='Scheduler Email')
    accommodation_email = fields.Char(string='Accommodation Email')
    procurement_email = fields.Char(string='Procurement Email')
