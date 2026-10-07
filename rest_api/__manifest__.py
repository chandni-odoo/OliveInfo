# -*- coding: utf-8 -*-

{
    'name': 'Rest API,',
    'version': '16.0',
    'author': 'Geo Technosoft',
    'website': 'http://www.geotechnosoft.com',
    'company': 'Geo Technosoft',
    'sequence': 1,
    'depends': [
        'base',
        'hr'
    ],
    'summary': 'Rest API',
    'description': '''Rest API''',
    'data': [
        "security/ir.model.access.csv",
        "data/cron.xml",
        "views/hr_employee_view.xml",
    ],
    'price': 15,
    'currency': 'USD',
    'license': 'OPL-1',
    'installable': True,
    'application': True,
}
