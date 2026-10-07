# -*- coding: utf-8 -*-
{
    'name': 'HR Leave Wizard',
    'summary': "Hr Leave Extended Report",
    'description': "HrLeave Reports Extended",
    'category': 'Human Resources Leave',
    'version': '15.0.0',
    'author': 'Onestone Software LLP',
    'website': "www.onestonesoftware.in",
    'depends': ['hr', 'hr_holidays', 'base','pways_hr_shift_allocation'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/hr_leave_wizard_view.xml',
    ],

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
