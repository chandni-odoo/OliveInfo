# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Custom Trip Sheet",
    'description': "Custom Trip Sheet",
    'depends': ['project_extended', 'fleet', 'maintenance','sale_extended'],
    'data': [
        'security/ir.model.access.csv',
        'data/trip_sheet_data.xml',
        'views/trip.xml',
        'views/uom_uom.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
