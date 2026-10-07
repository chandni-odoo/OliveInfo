# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountDueRange(models.Model):
    _name = 'account.due.range'
    _description = 'Employee Task History'

    name = fields.Char(string='Name')
    from_range = fields.Float(string='From Range')
    to_range = fields.Float(string='To Range')

    @api.constrains('to_range','from_range')
    def _check_duplicate_from_range_to_range(self):
        """
        This method is used to validate the to_range and from_range.
        ------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        """
        for rec in self:
            record = self.search(
                [
                    ("from_range", "<=", rec.from_range),
                    ("to_range", ">=", rec.from_range),
                    ("to_range", ">=", rec.from_range)
                ]
            )
            if record and len(record) > 1:
                raise ValidationError(
                    _(
                        """To range and From Range Duplicate Exceeded!, """
                        """You Cannot Take Same %s , %s Range Twice!"""
                    )
                    % (rec.from_range, rec.to_range)
                )
