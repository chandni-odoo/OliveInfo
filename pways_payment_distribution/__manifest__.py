# -*- coding: utf-8 -*-

{
    'name': 'Payment Distribution',
    'category': 'accounting',
    'summary': 'Distribute payment into multiple invoices, bills and credit notes',
    'version': '15.0.0',
    'author': 'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['account', 'sale', 'payment'],
    'data': [
            'security/ir.model.access.csv',
            'wizard/payment_distribution_view.xml'
            ],
    'application': True,
    'license': 'LGPL-3',
}