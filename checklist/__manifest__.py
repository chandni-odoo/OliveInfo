{
    'name': "Checklist",
    'version': '1.0.01',
    'category':'Checklist',
    'website': 'https://www.dishicreation.com',
    'summary': 'Checklist application',
    'description': """Checklist appication system""",
    'depends': ['base'],
    'data': [ 
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/conf_view.xml'
        ],
    'demo': [],
    'installable': True,
    'auto install':'False',
    'application': True,
    'license': 'LGPL-3',
    'sequence': 3,
}
