from odoo import models, fields

class PLGroup(models.Model):
    _name = 'pl.group'
    _description = 'Profit & Loss Group'

    name = fields.Char(required=True)
    code = fields.Char()
    is_net_revenue = fields.Boolean(string="Is Net Revenue")
    is_grand_total = fields.Boolean(string="Is Grand Total")


class BSGroup(models.Model):
    _name = 'bs.group'
    _description = 'Balance Sheet Group'

    name = fields.Char(required=True)
    code = fields.Char()
    is_subtotal     = fields.Boolean(
        string="Is Sub-Total",
    )
    is_section_total = fields.Boolean(
        string="Is Section Total"
    )
    is_grand_total  = fields.Boolean(
        string="Is Grand Total"
    )
    is_retained_earnings = fields.Boolean(
        string="Retained Earnings"
    )
    reverse_sign = fields.Boolean(
        string="Reverse Sign",
        default=False,
        help="Enable this option to reverse the sign of the balance for this group."
    )