{
    'name': 'Custom Trip Sheet Report',
    'version': '15.0.1.0.0',
    'summary': 'Generate Excel reports for Trip Sheets',
    'description': """
        This module allows generating Excel reports for Trip Sheets with various filters.
    """,
    'category': 'Operations',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'custom_trip', 'fleet', 'hr', 'report_xlsx','mtech_vehicle_extended'],
    'data': [
        'security/ir.model.access.csv',
        'reports/skip_report.xml',
        'reports/compactor_report.xml',
        'views/trip_report_views.xml',
        'views/compactor_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}