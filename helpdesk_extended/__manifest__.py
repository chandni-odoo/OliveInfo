# -*- coding: utf-8 -*-
{
    'name': "Helpdesk Extended",
    'summary': "helpdesk extended",
    'category': 'HR',
    'version': '15.0.0',
    'author': 'Dishicreation',
    'depends': ['helpdesk','base','custom_trip','mtech_vehicle_extended','project_extended','branch'],
    'data': [
            'security/ir.model.access.csv',
            'views/helpdesk_view.xml',
            'views/on_call_request_views.xml',             
             ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
