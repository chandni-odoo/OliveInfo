# -*- coding: utf-8 -*-
{
    'name': "Custom Reports",
    'summary': "Reports",
    'description': "All Custom Reports",
    'category': 'Sale',
    'version': '15.0.0',
    'author': 'Dishicreation',
    'depends': ['sale_extended', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'reports/sale_template_standard_hro.xml',
        'reports/report_timesheet_xls.xml',
        'reports/report.xml',
        'wizard/create_new_wizard.xml',
        # 'views/menu_timesheet.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
