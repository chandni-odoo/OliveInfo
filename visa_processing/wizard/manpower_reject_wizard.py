from odoo import models, fields, api, _

class ManpowerRequisitionReject(models.TransientModel):
    _name = 'manpower.requisition.reject'
    _description = 'Reject Manpower Requisition'

    reject_reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        active_id = self.env.context.get('active_id')
        requisition = self.env['manpower.requisition'].browse(active_id)
        
        if not requisition:
            return {'type': 'ir.actions.act_window_close'}
            
        requisition.write({'reject_reason': self.reject_reason})
        
        current_approval = requisition.approval_history_ids.filtered(
            lambda h: h.user_id == self.env.user and h.status == 'pending'
        )
        
        if current_approval:
            current_approval.write({
                'status': 'rejected',
                'date_done': fields.Datetime.now()
            })
            
            activity = self.env['mail.activity'].search([
                ('res_model', '=', 'manpower.requisition'),
                ('res_id', '=', requisition.id),
                ('user_id', '=', self.env.uid),
                ('activity_type_id.name', '=', 'Manpower Requisition To Approve')
            ])
            if activity:
                activity.action_done()
        
        requisition.write({
            'state': 'reject',
            'is_approved': False
        })
        requisition.message_post(
            body=_("Manpower Requisition rejected by %s. Reason: %s") % 
            (self.env.user.name, self.reject_reason)
        )
        
        return {'type': 'ir.actions.act_window_close'}
    