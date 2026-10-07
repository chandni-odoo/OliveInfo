# -*- coding: utf-8 -*-
{
    'name': "Prepayroll Dashboard",
    'summary':'Prepayroll Dashboard',
    'description': 'Prepayroll Dashboard',
    'category': 'HR',
    'version': '15.0.1',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['hr_payroll_extended'],
    'data': [
        'security/ir.model.access.csv',
        'views/pre_payroll_dashboard_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pways_pre_payroll_dashboard/static/src/js/payslip_dashbord.js',
            'pways_pre_payroll_dashboard/static/src/css/payslip_dashboard.css',
        ],
        'web.assets_qweb': [
            'pways_pre_payroll_dashboard/static/src/xml/payslip_dashboard.xml',
        ],
    },
    'license': 'LGPL-3',
}
