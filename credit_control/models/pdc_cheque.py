from odoo import models, fields, api
from datetime import timedelta
from dateutil.relativedelta import relativedelta

class PdcCheque(models.Model):
    _name = 'pdc.cheque'
    _description = 'PDC Cheque'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'cheque_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
    )

    customer_id = fields.Many2one('res.partner', string="Customer Name", required=True)
    cheque_date = fields.Date(string="Cheque Date")
    cheque_expiry_date = fields.Date(string="Cheque Expiry Date")
    collection_date = fields.Date(string="Date of Collection")
    collected_by = fields.Many2one('hr.employee', string="Collected By")

    amount = fields.Float(string="Amount", required=True)

    cheque_type = fields.Selection([
        ('guarantee', 'Guarantee Cheque'),
        ('pdc', 'PDC Cheque'),
        ('security', 'Security Cheque'),
        ('advance', 'Advance Payment Cheque'),
    ], string="Type of Cheque", required=True)

    cheque_status = fields.Selection([
        ('blank', 'Blank Cheque'),
        ('valid', 'Valid'),
        ('expired', 'Expired'),
    ], string="Cheque Status", compute="_compute_status", store=True)

    replacement_date = fields.Date(
        string="Cheque Replacement Obtained",
        compute="_compute_replacement_date",
        store=True
    )

    notes = fields.Text(string="Notes / Remarks")

    state = fields.Selection(
        selection=[
            ('collected', 'Collected'),
            ('submitted', 'Submitted to Bank'),
            ('returned', 'Returned to Customer'),
            ('bounced', 'Bounced'),
        ],
        string='Stage',
        default='collected',
        tracking=True,
    )
    active = fields.Boolean(default=True)

    # -------------------------
    # AUTO STATUS
    # -------------------------
    # @api.depends('cheque_expiry_date')
    # def _compute_status(self):
    #     today = fields.Date.today()
    #     for rec in self:
    #         if rec.cheque_expiry_date and rec.cheque_expiry_date < today:
    #             rec.cheque_status = 'expired'
    #         else:
    #             rec.cheque_status = 'valid'

    @api.depends('cheque_expiry_date', 'cheque_date')
    def _compute_status(self):
        today = fields.Date.today()
        for rec in self:
            # Blank Cheque condition
            if not rec.cheque_date:
                rec.cheque_status = 'blank'

            # Expired condition
            elif rec.cheque_expiry_date and rec.cheque_expiry_date < today:
                rec.cheque_status = 'expired'

            # Default valid
            else:
                rec.cheque_status = 'valid'

    # -------------------------
    # AUTO REPLACEMENT DATE
    # -------------------------
    @api.depends('cheque_date')
    def _compute_replacement_date(self):
        for rec in self:
            if rec.cheque_date:
                rec.replacement_date = rec.cheque_date + relativedelta(months=5)
            else:
                rec.replacement_date = False

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('pdc.cheque') or 'New'
        return super().create(vals)


    # -------------------------
    # STAGE BUTTONS
    # -------------------------
    def action_submitted(self):
        self.state = 'submitted'

    def action_returned(self):
        self.state = 'returned'

    def action_bounced(self):
        self.state = 'bounced'

    def action_collected(self):
        self.state = 'collected'