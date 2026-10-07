from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class WarningCheckStopWizard(models.TransientModel):
    _name = "warning.check.stop.wizard"
    _description = "Warning Check Stop"

    name = fields.Char('Name')

