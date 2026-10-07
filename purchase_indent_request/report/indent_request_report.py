from odoo import models, fields, api
from itertools import groupby
from operator import itemgetter

class IndentRequestReport(models.AbstractModel):
    _name = 'report.purchase_indent_request.indent_request_report_template'
    _description = "report indent request"

    @api.model
    def _get_report_values(self, docids, data=None):
        departments = self.env['hr.department'].browse(data.get('department_ids'))
        data = []
        for dept in departments:
            indent_ids = self.env['indent.request'].search([('department_id', '=', dept.id)])
            moves = indent_ids.mapped('request_lines_ids').mapped('move_ids')
            lines = []
            for line in moves.mapped('move_line_ids'):
                lines.append({
                    'product': line.product_id.name,
                    'uom': line.product_uom_id.name,
                    'qty': line.qty_done,
                    'lot_id': line.lot_id.name or line.lot_name,
                    'from_location': line.location_id.name,
                    'to_location': line.location_dest_id.name,
                })
            data.append({'name': dept.name,'lines': lines})
        return {'docs': data}
