# -*- coding: utf-8 -*-
{
    'name': 'Pways Sick Leave Rule',
    'summary': "Pways Sick Leave Rule",
    'description': "Pways Sick Leave Rule",
    'category': 'hr',
    'version': '15.0.0',
    'author': 'Preciseways',
    'website': "http://www.preciseways.com",
    'summary': ' Pways Sick Leave Rule',
    'depends': ['hr_holidays', 'hr_payroll_extended'],
    'data': [
        'security/ir.model.access.csv',
        'views/sick_leave_rule.xml',
        'views/hr_payroll_inherit.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
