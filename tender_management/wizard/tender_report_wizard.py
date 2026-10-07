from odoo import models, fields, api


class TenderTrackingReportWizard(models.TransientModel):
    _name = 'tender.tracking.report.wizard'
    _description = 'Tender Tracking Report Wizard'

    date_from = fields.Date(string="From Date", required=True)
    date_to = fields.Date(string="To Date", required=True)

    branch_ids = fields.Many2many(
        'res.branch',
        string="Associated Branches"
    )

    working_status_id = fields.Many2one(
        'tender.working.status',
        string='Working Status'
    )

    include_archived = fields.Boolean(
        string='Include Archived',
        default=False
    )

    def action_generate_report(self):
        data = {
            'date_from': self.date_from.strftime('%Y-%m-%d'),
            'date_to': self.date_to.strftime('%Y-%m-%d'),
            'branch_ids': self.branch_ids.ids,
            'working_status_id': self.working_status_id.id if self.working_status_id else False,
            'include_archived': self.include_archived,
        }

        return self.env.ref(
            'tender_management.action_tender_tracking_report_xlsx'
        ).report_action(self, data=data)