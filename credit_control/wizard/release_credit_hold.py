from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, date


class ReleaseCreditHoldWizard(models.TransientModel):
    _name = 'release.credit.hold.wizard'
    _description = 'Wizard to release credit hold'

    partner_ids = fields.Many2many('res.partner', string='Partners')
    release_until = fields.Date(string='Release Until', required=True)
    note = fields.Text(string='Notes')

    def release_credit_hold_action(self):
        self.ensure_one()
        if not self.partner_ids:
            raise UserError(_('No partners selected'))
        
        for partner in self.partner_ids:
            # Validate partner is actually under credit block
            if partner.credit_block != 'yes' or partner.hold_option != 'credit_block':
                raise UserError(_('Partner %s is not currently under credit block hold') % partner.name)
            
            # Check if there's an existing active release
            if partner.release_until and partner.release_until > fields.Date.today():
                raise UserError(_('Partner %s already has an active temporary release until %s') %
                               (partner.name, partner.release_until))
            
            # Update approval position and last approver
            if partner.hold_position == 'first_escalate':
                partner.last_approver = partner.approver_1 or self.env.user
                partner.hold_position = 'released_by_1st'
            elif partner.hold_position == 'released_by_1st':
                partner.last_approver = partner.approver_2 or self.env.user
                partner.hold_position = 'released_by_2nd'
            elif partner.hold_position == 'released_by_2nd':
                partner.last_approver = partner.approver_3 or self.env.user
                partner.hold_position = 'released_by_3rd'
            
            # Store original values for reinstatement
            original_hold_reason = partner.hold_reason
            
            # Temporarily release the credit hold
            partner.write({
                'hold_option': '',  # Changed from False to empty string
                'credit_block': 'no',
                'hold_reason': f"Temporarily released until {self.release_until}. Notes: {self.note}" if self.note 
                              else f"Temporarily released until {self.release_until}",
                'release_until': self.release_until,
            })
            
        return {'type': 'ir.actions.act_window_close'}

    # def action_release_credit_hold(self):
    #     self.ensure_one()
    #     if not self.partner_ids:
    #         raise UserError(_('No partners selected'))
        
    #     for partner in self.partner_ids:
    #         if partner.hold_position == 'first_escalate':
    #             partner.last_approver = partner.approver_1 or self.env.user
    #             partner.hold_position = 'released_by_1st'
    #         elif partner.hold_position == 'released_by_1st':
    #             partner.last_approver = partner.approver_2 or self.env.user
    #             partner.hold_position = 'released_by_2nd'
    #         elif partner.hold_position == 'released_by_2nd':
    #             partner.last_approver = partner.approver_3 or self.env.user
    #             partner.hold_position = 'released_by_3rd'

    #         partner.approver_comment = self.note
            
    #         partner.release_until = self.release_until

    #         original_credit_status = partner.credit_bal_negative
    #         original_hold_reason = partner.hold_reason
            
    #         # Temporarily release the credit hold
    #         if partner.last_approver and partner.release_until:
    #             partner.write({
    #                 'hold_option': False,  # Temporarily set to False
    #                 'credit_block': 'no',
    #                 'hold_reason': False if not self.note else f"Temporarily released until {self.release_until}. Notes: {self.note}",
    #             })
        
    #     return {'type': 'ir.actions.act_window_close'}