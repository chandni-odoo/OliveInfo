# -*- coding: utf-8 -*-
{
    'name': "HR Attendance Muster Report Xlsx",
    'summary': "HR Attendance Muster Report Xlsx",
    'description': "HR Attendance Muster Report Xlsx",
    'category': 'Human Resources',
    'version': '15.0.0',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['hr_attendance','hr_payroll_extended', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/hr_attendance_muster_wizard_view.xml',
        'report/attendance_muster_action.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}