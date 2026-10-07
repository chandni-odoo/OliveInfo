# -*- coding: utf-8 -*-
{
    'name': "Pways Purchase Approval",
    'summary': "Pways Purchase Approval",
    'description': "Pways Purchase Approval",
    'category': 'Purchase',
    'version': '15.0.0',
    'author': 'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['purchase_indent_request', 'branch', 'purchase_extended'],
    'data': [
        'security/ir.model.access.csv',
        'data/purchase_data.xml',
        'wizard/approval_reject_wizard.xml',
        'views/indent_request_view.xml',
        'views/purchase_approval_view.xml',
        'views/purchase_view.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'pways_purchase_approval/static/src/js/systray_activity_menu.js',
        ],
        'web.assets_qweb': [
            'pways_purchase_approval/static/src/xml/systray.xml',
        ],
    },
    'license': 'LGPL-3',
}
