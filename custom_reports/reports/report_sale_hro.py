# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleQuotationReport(models.AbstractModel):
    _name = 'report.custom_reports.report_sale_quotation_test'
    _description = 'Module Reference Report (base)'


    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('custom_reports.report_sale_quotation_test')
        selected_modules = self.env['ir.module.module'].browse(docids)
        print("___docids",docids)
        model = self.env.context.get('active_model')
        docs = self.env['sale.order'].browse(self.env.context.get('active_id'))
        report = self.env.ref('custom_reports.report_sale_quotation_test')
        report_vals = report.render({'data': self.env.context.get('active_id')})
        last_page = report_vals['total_pages']
        print("___last_page",last_page)
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': docs,
            'last_page': last_page,
        }
