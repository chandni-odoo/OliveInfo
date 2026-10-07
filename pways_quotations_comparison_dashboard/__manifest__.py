# -*- coding: utf-8 -*-
{
    'name': "RFQ Comparison Dashboard",
    'summary': "You can compare RFQ based on price or delivery date.System will tell you which rfq is best for your need and you can update or confirm RFQ from dashboard with multiple filteres",
    'description': "System will tell you which RFQ is best for your need based on multiple comparison filteres like Min price or Expected delivery date. You can also manual select RFQ or update and confirm RFQ from dashboard.When you confirm any purchase order rest will be cancel automatically and manual process also available. Dashboard shows RFQ with product (Left) vs vendors (Top) and qty and price in middle.",
    'category': 'purchases',
    'version': '15.0.0',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['purchase', 'purchase_requisition'],
    'data': ['views/rfq_comparison_report_view.xml',],
    'assets': {
        'web.assets_backend': [
            'pways_quotations_comparison_dashboard/static/src/js/rfq_comp_dashboard.js',
            'pways_quotations_comparison_dashboard/static/src/css/rfq_dashboard.css',
        ],
        'web.assets_qweb': [
            'pways_quotations_comparison_dashboard/static/src/xml/rfq_comp_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'price': 35.0,
    'currency': 'EUR',
    'images':['static/description/banner.png'],
    'license': 'OPL-1',
}
