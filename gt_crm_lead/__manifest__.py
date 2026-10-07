# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Custom Trip Sheet",
    'description': "",
    'depends': ['crm', 'sale_extended', 'purchase_indent_request'],
    'data': [
        # 'security/ir.model.access.csv',
        'data/email_template.xml',
        'views/gt_check_availability.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
