# -*- coding: utf-8 -*-

{
    'name': 'Automatic Overtime',
    'summary': 'Automatic Overtime',
    'description': """Management of overtime taken by the employees.""",
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends':['hr_contract','hr_attendance', 'hr_extended', 'hr_payroll', 'hr_holidays','resource'],
    'data': [
        'security/ir.model.access.csv',
        'views/bt_hr_overtime_view.xml',
        'views/hr_ot_rule_view.xml',
        'wizard/overtime_approval_view.xml',
        'data/bt_hr_overtime_data.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
