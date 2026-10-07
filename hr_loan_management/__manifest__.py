# -*- coding: utf-8 -*-
{
    'name': 'Loan Management',
    'version': '15.0.1.0.0',
    'summary': 'Manage Loan Requests',
    'description': """Helps you to manage Loan Requests of your company's staff.""",
    'category': 'Generic Modules/Human Resources',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['hr_payroll', 'hr_extended', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/salary_rule_loan.xml',
        'wizard/journal_entry.xml',
        'views/hr_loan.xml',
        'views/hr_payroll.xml',
    ],
    'license': 'LGPL-3',
}
