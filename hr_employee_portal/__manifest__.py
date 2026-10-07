# -*- coding: utf-8 -*-
{
    'name': "Hr Attendance Portal",
    'summary': "Hr Attendance Portal",
    'category': 'HR',
    'version': '15.0.0',
    'author': 'Preciseways',
    'depends': ['sale_extended', 'website', 'hr_holidays', 'hr_attendance', 'contacts_extended'],
    'data': [
        'views/hr_attendance.xml',
        'views/hr_employee_view.xml',
        'views/hr_timesheet_portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'hr_employee_portal/static/src/css/style.css',
            'hr_employee_portal/static/src/js/hr_employee_portal.js',
            'hr_employee_portal/static/src/js/create_leave.js',
            'hr_employee_portal/static/src/js/create_duty_resumption.js',
            'hr_employee_portal/static/src/js/create_attendance.js'
        ]
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3'
}
