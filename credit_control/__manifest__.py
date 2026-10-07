{
    'name': 'Credit Control Extension',
    'version': '15.0.1.0.0',
    'summary': 'Add Unbilled Value and Current Outstanding fields to partner view',
    'description': '''
        This module adds two new fields to the partner form:
        - Unbilled Value
        - Current Outstanding (pulls from due amount)
    ''',
    'category': 'Accounting',
    'author': 'olive infocraft',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'account', 'sale', 'branch', 'sale_extended','project','custom_trip', 'branch_extended','hr_timesheet','project_extended','crm', 'custom_trip','hr_timesheet'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/pdc_cheque_sequence.xml',
        "wizard/release_credit_hold.xml",
        'views/res_partner_views.xml',
        'views/credit_request.xml',
        'views/credit_hold_customer.xml',
        'views/lpo_control.xml',
        'views/sale_order_invoice_details.xml',
        'views/ribbon_views.xml',
        'views/account_analytic.xml',
        'views/pdc_cheque_views.xml',
        'views/receipt_book_views.xml',
        'wizard/accrued_revenue_views.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}