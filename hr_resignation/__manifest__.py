# -*- coding: utf-8 -*-
{
    'name': 'HR Resignation',
    'version': '14.0.0',
    'summary': 'Handle the resignation process of the employee',
    'depends': ['hr', 'mail', 'hr_extended', 'hr_payroll_extended'],
    'category': 'Human Resources',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'demo': [],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        # 'data/resign_employee.xml',
        'views/hr_employee.xml',
        'views/resignation_view.xml',
        'views/approved_resignation.xml',
        'views/resignation_sequence.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

