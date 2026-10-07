# -*- coding: utf-8 -*-

{
    'name': "Salary Bank Report Xlsx",
    'summary': "Salary Bank Report Xlsx",
    'description': "Salary Bank Report Xlsx",
    'category': 'Human Resources',
    'version': '15.0.0',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['hr_payroll_extended','report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'views/payroll_batch_view.xml',
        'views/salary_bank_report_view.xml',
            ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}