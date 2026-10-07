# -*- coding: utf-8 -*-
{
    'name': "Leave Balance",
    'summary': "Leave Balance",
    'description': "Leave Balance",
    'category': 'Human Resources Balance',
    'version': '15.0.0',
    'author': 'Dishi Creation',
    'website': "www.dishicreation.com",
    'depends': ['hr_holidays'],
    'data': [
        # 'security/approval_security.xml',
        # 'security/ir.model.access.csv',
        # 'data/data.xml',
        # 'views/leave.xml',
        # 'views/hr_employee.xml',
        # 'views/visa_profession.xml',
        # 'views/resource_reporting_view.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'leave_balance/static/src/js/time_off_calendar_employee_custom.js',
        ],
        'web.assets_qweb': [
            'leave_balance/static/src/xml/*.xml',
        ],
    },

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
