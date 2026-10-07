# -*- coding: utf-8 -*-
{
    'name': "Bulk Overtime Rule Configuration",
    'summary':'Bulk Overtime Rule Configuration',
    'description': 'Bulk Overtime Rule Configuration',
    'category': 'Human Resources',
    'version': '15.0.0',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['hr_overtime_automatic'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bulk_ot_rule_wizard_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
