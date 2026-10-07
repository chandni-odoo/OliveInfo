# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class purchaseOrderReport(models.AbstractModel):
	_name = 'report.purchase_extended.report_purchase_order'

	@api.model
	def _get_report_values(self, docids, data=None):
		report = self.env['ir.actions.report']._get_report_from_name('purchase_extended.report_purchase_order')
		po_docs = self.env['purchase.order'].browse(docids)
		docs = po_docs.filtered(lambda x: x.state == 'purchase')
		for doc in docs:
			if doc.state != 'purchase':
				raise ValidationError(_('Please Confirm the order %s to print the report.')%doc.name)
		return {
				'doc_ids': docs.ids,
				'doc_model': report.model,
				'docs': docs,
				'proforma': True
			}