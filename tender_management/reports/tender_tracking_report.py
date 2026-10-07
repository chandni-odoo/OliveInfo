from odoo import models


class TenderTrackingReportXlsx(models.AbstractModel):
    _name = 'report.tender_management.tender_tracking_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Tender Tracking XLSX Report'

    def generate_xlsx_report(self, workbook, data, wizard):

        date_from = data.get('date_from')
        date_to = data.get('date_to')
        branch_ids = data.get('branch_ids', [])
        working_status_id = data.get('working_status_id')
        include_archived = data.get('include_archived')

        sheet = workbook.add_worksheet('Tender Tracking Report')

        # =========================
        # Formats
        # =========================

        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 14,
        })

        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'bg_color': '#002060',
            'font_color': 'white',
        })

        bold = workbook.add_format({
            'bold': True,
            'align': 'left'
        })

        left = workbook.add_format({
            'align': 'left',
            'border': 1
        })

        center = workbook.add_format({
            'align': 'center',
            'border': 1
        })

        amount_format = workbook.add_format({
            'align': 'right',
            'border': 1,
            'num_format': '#,##0.00'
        })

        # =========================
        # Column Widths
        # =========================

        sheet.set_column('A:A', 18)
        sheet.set_column('B:B', 18)
        sheet.set_column('C:C', 25)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 22)
        sheet.set_column('H:H', 20)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 18)
        sheet.set_column('K:K', 30)
        sheet.set_column('L:L', 30)
        sheet.set_column('M:M', 20)
        sheet.set_column('N:N', 18)

        # =========================
        # Report Header
        # =========================

        sheet.merge_range('A1:N1', 'Tender Tracking Report', title_format)

        sheet.write('A3', 'From Date', bold)
        sheet.write('B3', date_from or '')

        sheet.write('A4', 'To Date', bold)
        sheet.write('B4', date_to or '')

        sheet.write('A5', 'Associated Branch', bold)

        branch_names = ', '.join(
            self.env['res.branch'].browse(branch_ids).mapped('name')
        ) if branch_ids else 'All Branches'

        sheet.write('B5', branch_names)

        sheet.write('A6', 'Working Status', bold)

        working_status = ''
        if working_status_id:
            working_status = self.env[
                'tender.working.status'
            ].browse(working_status_id).name

        sheet.write('B6', working_status or 'All')

        sheet.write('A7', 'Include Archived', bold)
        sheet.write('B7', 'Yes' if include_archived else 'No')

        # =========================
        # Table Headers
        # =========================

        headers = [
            'Sequence No',
            'Tender No',
            'Tender Name',
            'Client',
            'Tender Submission Date',
            'Duration',
            'Total Contract Value',
            'Tender Bond Amount',
            'Tender Bond Expiry',
            'Tender Bond Validity Days',
            'Associated Partners',
            'Associated Branch',
            'Working Status',
            'Stage',
            'Tender Status'
        ]

        row = 9
        col = 0

        for header in headers:
            sheet.write(row, col, header, header_format)
            col += 1

        row += 1

        # =========================
        # Domain
        # =========================

        domain = [
            ('tender_submission_date', '>=', date_from),
            ('tender_submission_date', '<=', date_to),
        ]

        if branch_ids:
            domain.append(('branch_ids', 'in', branch_ids))

        if working_status_id:
            domain.append(('working_status_id', '=', working_status_id))

        if not include_archived:
            domain.append(('active', '=', True))

        tenders = self.env['tender.management'].search(domain)

        # =========================
        # Data Rows
        # =========================

        for tender in tenders:

            partner_names = ', '.join(
                tender.partner_ids.mapped('name')
            )

            branch_names = ', '.join(
                tender.branch_ids.mapped('name')
            )

            stage = dict(
                tender._fields['state'].selection
            ).get(tender.state, '')

            tender_status = dict(
                tender._fields['result_state'].selection
            ).get(tender.result_state, '')

            sheet.write(row, 0, tender.sequence_no or '', left)
            sheet.write(row, 1, tender.tender_no or '', left)
            sheet.write(row, 2, tender.tender_name or '', left)
            sheet.write(row, 3, tender.client_id.name or '', left)

            sheet.write(
                row,
                4,
                str(tender.tender_submission_date or ''),
                center
            )

            sheet.write(row, 5, tender.duration or '', left)

            sheet.write(
                row,
                6,
                tender.total_contract_value or '',
                amount_format
            )

            sheet.write(
                row,
                7,
                tender.tender_bond_amount or '',
                amount_format
            )

            sheet.write(
                row,
                8,
                str(tender.tender_bond_expiry or ''),
                center
            )

            sheet.write(
                row,
                9,
                tender.tender_bond_validity_days or 0,
                center
            )

            sheet.write(row, 10, partner_names or '', left)
            sheet.write(row, 11, branch_names or '', left)

            sheet.write(
                row,
                12,
                tender.working_status_id.name or '',
                left
            )

            sheet.write(row, 13, stage or '', left)
            sheet.write(row, 14, tender_status or '', left)

            row += 1