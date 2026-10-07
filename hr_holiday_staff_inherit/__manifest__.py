# -*- coding: utf-8 -*-
{
    'name': 'HR Holiday Staff Extra Leave',
    'summary': 'HR Holiday Inherit For allow extra leave for Staffs',
    'description': """HR Holiday Inherit For allow extra leave for Staffs on timeoff.""",
    'author':'GlobalTeckz',
    'depends':['hr_holidays'],
    'data': [
        'views/hr_leave_inherit_view.xml',
    ],

    'assets': {
        'web.assets_qweb': [
            'hr_holiday_staff_inherit/static/src/xml/time_off_dashboard_inherit.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
