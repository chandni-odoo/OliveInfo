{
    "name": "Odoo Approval All in One",
    "version": "15.0.1.0.0",
    "category": "Approvals",
    "summary": """
    Setup the approval flow for all the models: Sale Order,
    Purchase Order, MRP Order,.. Centralize all the approval requests
    in one place which help the manager reviews easily
    """,
    "live_test_url": "https://demo17.domiup.com",
    'author': 'Onestone Software LLP',
    'website': "www.onestonesoftware.in",
    "price": 110,
    "currency": "USD",
    "license": "OPL-1",
    "support": "info@onestone.in",
    "depends": ["multi_level_approval"],
    "data": [
        # Security
        "security/ir.model.access.csv",
        "security/security.xml",
        # Wizards
        "wizard/cancel_approval_views.xml",
        "wizard/change_approver_views.xml",
        # Views
        "views/multi_approval_type_views.xml",
        "views/multi_approval_views.xml",
        # Wizards
        "wizard/request_approval_views.xml",
        "wizard/rework_approval_views.xml",
        "wizard/test_approval_views.xml",
    ],
    "images": ["static/description/banner.gif"],
    "test": [],
    "demo": [],
    "installable": True,
    "application": True,
}
