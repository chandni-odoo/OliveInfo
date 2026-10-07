# -*- coding: utf-8 -*-
{
    'name': "Purchase Extended",
    'summary': "Purchase Extended",
    'description': "Purchase Extended",
    'category': 'Purchase',
    'version': '15.0.0',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['purchase', 'branch_extended', 'sale_extended', 'pways_terms_condition'],
    'data': [
        'security/ir.model.access.csv',
        'report/report_actions.xml',
        'report/purchase_template.xml',
        'views/purchase_extended.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
