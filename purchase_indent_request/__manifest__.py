# -*- coding: utf-8 -*-
{
    'name' : 'Purchase Indent Request',
    'summary': 'Indent Request',
    'sequence': 1,
    'description': """ Indent Request """,
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['hr', 'stock', 'purchase', 'purchase_requisition_stock', 'branch', 'purchase_extended'],
    'data': [
        'data/indent_request_data.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/indent_request_view.xml',
        'views/hr_department_view.xml',
        'views/purchase_order_view.xml',
        'report/indent_request_report.xml',
        'wizard/indent_request_wizard.xml',
        'wizard/merge_tender_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}