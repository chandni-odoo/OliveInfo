{
    'name': 'CRM Developement',
    'version': '1.0',
    'summary': 'Implementation of 2001-Industrial Supply Solution vertical CRM Development',
    'description': """
        This module adds:
        - CRM Development
    """,
    'category': 'CRM',
    'author': 'Olive Infocraft',
    'depends': ['base','crm','product','project_extended','stock','sale_extended','gt_crm_lead','purchase_indent_request','sale'], 
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/crm_lead_views.xml',
        'views/sale_order_line_views.xml',
        "views/landing_cost_views.xml",
        'views/invoice_extended_views.xml',
        'report/report_action.xml',
        'report/quotation_industrial_supply.xml',
        'report/delivery_report.xml',
        
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}