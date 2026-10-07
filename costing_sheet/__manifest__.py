# -*- coding: utf-8 -*-
{
    'name': "Costing Sheet",
    'summary': "Cost Sheet",
    'description': "Cost Sheet",
    'category': 'Sale',
    'version': '15.0.0',
    'author':'Dishicreation',
    'depends': ['product'],
    'data': [
            'security/ir.model.access.csv',
            'views/product_costing_sheet.xml',

    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}