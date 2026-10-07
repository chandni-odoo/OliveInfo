# -*- coding: utf-8 -*-
{
    'name': "Hr Expense",
    'summary': "Employee Expense",
    'category': 'HR',
    'version': '14.0.0',
    'author':'Preciseways',
    'depends': ['hr', 'website', 'hr_expense'],
    'data': [
            #'security/ir.model.access.csv',
            #'data/data.xml',
            #'views/hr_request.xml',
            'views/hr_expense_portal.xml',
             ],
    # 'assets': {
    #     'web.assets_frontend': [
    #         'hr_expense_portal/static/src/js/hr_expense_portal.js',
    #     ],
    # },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
