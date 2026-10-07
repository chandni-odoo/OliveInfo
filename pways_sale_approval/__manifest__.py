# -*- coding: utf-8 -*-
{
    'name': "Pways Sale Approval",
    'summary': "Pways Sale Approval",
    'description': "Pways Sale Approval",
    'category': 'Sale',
    'version': '15.0.0',
    'author': 'Preciseways',
    'website': "http://www.preciseways.com",
    'summary': ' Pways Terms Condition',
    'depends': ['sale', 'branch', 'sale_extended'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'wizard/sale_approval_reject_wizard.xml',
        'views/sale_approval_view.xml',
        'views/sale_order_view.xml',
        'views/email_approval.xml',
    ],
    'license': 'LGPL-3',
}
