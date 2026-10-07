# -*- coding: utf-8 -*-
{
    "name": "Employees Payslip Send By Email",
    'summary': "Employees Payslip Send By Email",
    'description': "Employees Payslip Send By Email",
    "version": "15.0",
    'author': 'Preciseways',
    'website': "http://www.preciseways.com",
    "category": "Hr",
    "depends": ['hr_payroll_extended'],
    "data": [
        'security/ir.model.access.csv',
        'report/hr_payslip_report.xml',
        'data/mail_template_data.xml',
        'views/hr.payslip_view.xml',
    ],
    "installable": True,
    "application": True,
    'license': 'LGPL-3',
}
