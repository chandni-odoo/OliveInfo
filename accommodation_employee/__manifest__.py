# See LICENSE file for full copyright and licensing details.

{
    "name": "Manpower Accommodation",
    "version": "15.0.1.0.0",
    "author": "Dishi Creation",
    "category": "Accommodation Management",
    "website": "www.dishicreation.com",
    "license": "AGPL-3",
    "complexity": "easy",
    "summary": "This module is for manpower accommodation",
    "depends": ["account"],
    "data": [
        "security/accommodation_security.xml",
        "security/ir.model.access.csv",
        "data/accommodation_schedular.xml",
        "views/accommodation_view.xml",
        "data/accommodation_sequence.xml",
        # "report/accommodation_fee_receipt.xml",
        # "report/report_view.xml",
        # "wizard/terminate_reason_view.xml",
    ],
    # "demo": ["demo/school_accommodation_demo.xml"],
    "installable": True,
}
