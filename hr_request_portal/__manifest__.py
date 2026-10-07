# -*- coding: utf-8 -*-
{
    'name': "Hr Request",
    'summary': "Employee Requests",
    'category': 'HR',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'version': '14.0.0',
    'depends': ['base','hr', 'website','hr_resignation'],
    'data': [
            'security/ir.model.access.csv',
            'security/hr_request_security.xml',
            'data/ir_cron_data.xml',
            'data/data.xml',
            'views/hr_request.xml',
            'views/clearance_views.xml',
            'views/hr_request_portal.xml',
            'views/hr_resignation.xml',
             ],
    'assets': {
        'web.assets_frontend': [
            'hr_request_portal/static/src/js/hr_request_portal.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
