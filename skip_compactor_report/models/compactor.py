from odoo import models, fields, api
from datetime import datetime


class CompactorReportWizard(models.TransientModel):
    _name = 'compactor.report.wizard'
    _description = 'Compactor Vehicle Report Wizard'

    scheduled_date = fields.Date(string='Scheduled Date', required=True, default=fields.Date.today())
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle No', required=True)
    vehicle_type_id = fields.Many2one('vehicle.type', string='Vehicle Type', readonly=True)
    shift_id = fields.Many2one('fleet.shift.type', string='Shift', required=True)
    trip_sheet_ids = fields.Many2many(
        'custom.trip.sheet',
        string='Trip Sheets',
        compute='_compute_trip_sheets'
    )

    @api.depends('scheduled_date', 'vehicle_id', 'shift_id')
    def _compute_trip_sheets(self):
        for wizard in self:
            if wizard.scheduled_date and wizard.vehicle_id and wizard.shift_id:
                date_start = datetime.combine(wizard.scheduled_date, datetime.min.time())
                date_end = datetime.combine(wizard.scheduled_date, datetime.max.time())
                
                trip_domain = [
                    ('schedule_date', '>=', date_start),
                    ('schedule_date', '<=', date_end),
                    ('vehicle_no_id', '=', wizard.vehicle_id.id),
                    ('shift_id', '=', wizard.shift_id.id),
                ]
                wizard.trip_sheet_ids = self.env['custom.trip.sheet'].search(trip_domain, order='sequence asc')
            else:
                wizard.trip_sheet_ids = False

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        """Auto-fetch vehicle type based on vehicle selection"""
        if self.vehicle_id:
            self.vehicle_type_id = self.vehicle_id.vehicle_type_id.id
        else:
            self.vehicle_type_id = False

    def action_generate_excel_report(self):
        """Generate Excel report with compactor vehicle data"""
        data = {
            'scheduled_date': fields.Date.to_string(self.scheduled_date),  
            'vehicle_id': self.vehicle_id.id,
            'vehicle_type_id': self.vehicle_type_id.id,
            'shift_id': self.shift_id.id,
        }
        return self.env.ref('skip_compactor_report.action_compactor_vehicle_report').report_action(self, data=data)
   
    # updated