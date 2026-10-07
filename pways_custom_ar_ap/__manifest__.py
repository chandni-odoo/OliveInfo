# -*- coding: utf-8 -*-

{
    'name': "Custome Aged Report Xlsx",
    'summary': "Custome Aged Report Xlsx",
    'description': "Custome Aged Report Xlsx",
    'category': 'Accounting',
    'version': '15.0.0',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['account','report_xlsx','sale_extended','account_extended','branch'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/custom_ap_ar_view.xml',
        'views/custom_aged_report_view.xml',
        'views/account_due_range_view.xml',
            ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}