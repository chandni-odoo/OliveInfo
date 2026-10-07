# -*- coding: utf-8 -*-
{
    'name': "Leave Extended",
    'summary': "Leave Extended",
    'description': "Leave Extended",
    'category': 'Human Resources Leave',
    'version': '15.0.0',
    'author': 'Dishi Creation',
    'website': "www.dishicreation.com",
    'depends': ['hr_holidays', 'pways_hr_shift_allocation','hr_attendance'],
    'data': [
        'security/approval_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/leave.xml',
        'views/absentes.xml',
        # 'views/visa_profession.xml',
        # 'views/resource_reporting_view.xml',
    ],

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
