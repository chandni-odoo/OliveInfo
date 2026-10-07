# -*- coding: utf-8 -*-
{
    'name': 'Pways Record Approval',
    'version': '15.0.0',
    'author': 'Preciseways',
    'website': "http://www.preciseways.com",
    'summary': 'Record Approval',
    'depends': ['base', 'web', 'sale'],
    'data': [
        'data/activity_data.xml',
        'security/ir.model.access.csv',
        'views/record_approval_view.xml',
        'wizard/pending_details_wizard.xml',
        'wizard/reject_reason_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pways_record_approval/static/src/**/*',
        ],
        'web.assets_qweb': [
            'pways_record_approval/static/src/xml/systray.xml',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
