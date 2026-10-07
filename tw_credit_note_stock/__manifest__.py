# -*- coding: utf-8 -*-
{
    'name': "Credit Note Stock",
    'summary':'This module modify Credit Note Stock',
    'category': 'stock',
    'description': 'This module modify stock Move',
    "version": "15.0.1.0.0",
    "author": "Dishi Creation",
    "website": "www.dishicreation.com",
    "license": "AGPL-3",
    "complexity": "easy",
    'depends': ['stock', 'account'],
    'data': [
        'views/stock_view.xml',
    ],
    'installable': True,
    'application': True,
}
