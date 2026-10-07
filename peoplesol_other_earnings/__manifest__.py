# -*- coding: utf-8 -*-
{
    'name': "Employee Other Earnings",
    'summary': "Employee Other Earnings",
    'description': "Employee Other Earnings",
    'category': 'Human Resources',
    'version': '15.0.0',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['hr_payroll','branch_extended', 'hr', 'project', 'sale_project', 'bi_odoo_multi_branch_hr', 'project_extended', 'hr_payroll_account'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/other_earnings.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
