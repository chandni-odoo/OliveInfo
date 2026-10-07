# -*- coding: utf-8 -*-
{
    'name': "HR Extended",
    'summary': "HR Extended",
    'description': "HR Extended",
    'category': 'Human Resources',
    'version': '15.0.0',
    'author': 'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['hr_contract', 'contacts_extended', 'hr_recruitment', 'branch', 'account_bank_branch',
                'hr_work_entry_contract_enterprise', 'hr_skills', 'hr_attendance', 'hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/ir_cron.xml',
        'wizard/employee_leave_view.xml',
        'wizard/employee_bulk_reported_view.xml',
        'wizard/overtime_correction_view.xml',
        'views/employee.xml',
        'views/hr_employee.xml',
        'views/visa_profession.xml',
        'views/resource_reporting_view.xml',


    ],

    # 'assets': {
    #     'web.assets_backend': [
    #         'hr_extended/static/src/js/time_off_calendar_employee_custom.js',
    #     ],
    #     'web.assets_qweb': [
    #         'hr_extended/static/src/xml/*.xml',
    #     ],
    # },

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
