{
    'name': 'Budget Customizations',
    'version': '1.0',
    'summary': 'Add branch field and additional order line fields to budgets',
    'description': """
        This module adds:
        - Branch field under company field in budget form
        - Remark and Working Details fields in budget lines
        - Filtering of budget lines based on selected branch
    """,
    'category': 'Accounting',
    'author': 'Olive Infocraft',
    'depends': ['account_budget', 'account','base','analytic','branch', 'mail','bi_branch_budget_ent'], 
    'data': [
        'security/ir.model.access.csv',
        'security/account_admin_security.xml',
        "reports/variance_report.xml",
        "reports/monthly_variance_report.xml",
        'reports/budget_spread_report_action.xml',
        'views/account_budget_views.xml',
        'views/budget_import_views.xml',
        'views/menu_access.xml',
        "wizard/variance_report_wizard.xml",
        "wizard/monthly_variance_report_wizard.xml",
        "wizard/budget_spread_wizard_views.xml",
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}