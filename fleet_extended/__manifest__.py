{
    'name': "Fleet Extended",
    'description': "Custom Fleet Extended",
    'depends': ['base', 'fleet','hr','sale_management','project_extended','mail','account_asset_fleet','mtech_vehicle_extended'],
    'data': [
        'security/ir.model.access.csv',
        'data/document_expiry_cron.xml',
        'reports/report_template.xml',
        'views/fleet_vehicle_views.xml',
        'wizard/employee_allocation_wizard.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
