# from odoo import models, fields, api


# class CampDetailsReport(models.AbstractModel):
#     _name = 'report.employee_accommodation.report_camp_details'
#     _description = 'Camp Details Report'

#     @api.model
#     def _get_report_values(self, docids, data=None):
#         if not data:
#             data = {}
#         docs = self.env['accommodation.camp'].browse(docids)
#         return {
#             'doc_ids': docids,
#             'doc_model': 'accommodation.camp',
#             'docs': docs,
#             'data': data,
#         }
