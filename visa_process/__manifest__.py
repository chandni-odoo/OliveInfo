# -*- coding: utf-8 -*-
{
    'name': "Visa Process",
    'summary': "Work Visa Process",
    'description': "Work Process",
    'category': 'operation',
    'version': '15.0.0',
    'author':'Dishicreation',
    'website': "http://www.dishicreation.com",
    'depends': ['hr_extended','mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/visa_details_view.xml',
        'views/visa_process_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}