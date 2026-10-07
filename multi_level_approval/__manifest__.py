{
    "name": "Odoo Approval",
    "version": "15.0.1.0.0",
    "category": "Approvals",
    "summary": """
    Create and validate approval requests.
    Each request can be approved by many levels of different managers
    """,
    'author': 'Onestone Software LLP',
    'website': "www.onestonesoftware.in",
    "price": 180,
    "currency": "USD",
    "license": "OPL-1",
    "support": "info@onestone.in",
    "depends": ["mail", "product"],
    "data": [
        "data/ir_sequence_data.xml",
        "data/mail_template_data.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        # wizard
        "wizard/refused_reason_views.xml",
        "views/multi_approval_type_views.xml",
        "views/multi_approval_views.xml",
        # Add actions after all views.
        "views/actions.xml",
        # Add menu after actions.
        "views/menu.xml",
    ],
    "images": ["static/description/banner.jpg"],
    "test": [],
    "demo": [],
    "installable": True,
    "application": True,
}
