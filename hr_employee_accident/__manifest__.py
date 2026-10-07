# -*- coding: utf-8 -*-
{
    'name': "Hr Accident",
    'summary': "Report Accident in organisation",
    'category': 'HR',
    'version': '14.0.0',
    'author': 'Preciseways',
    'depends': ['hr'],
    'data': [
            'security/ir.model.access.csv',
            'data/data.xml',
            'views/hr_accident.xml',             
             ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
