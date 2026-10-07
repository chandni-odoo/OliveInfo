# -*- coding: utf-8 -*-
{
    'name': 'Open HRMS Gratuity Settlement',
    'version': '15.0',
    'summary': """Employee Gratuity Settlement During Resignation """,
    'category': 'Human Resources',
    'author':'Preciseways',
    'depends': ['base', 'hr_resignation','mail','hr_payroll'],
    'data': ['security/ir.model.access.csv',
             'data/gratuity_sequence.xml',
             'views/employee_gratuity_view.xml',
            ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
