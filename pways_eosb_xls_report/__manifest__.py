# -*- coding: utf-8 -*-
{
    'name': "End of service Report",
    'summary': "End Of service Benefit Report Xlsx",
    'description': "End Of service Benefit Report Xlsx",
    'category': 'Human Resources',
    'version': '15.0.0',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['hr_extended','report_xlsx','hr_menu_extended'],
    'data': [
        'security/ir.model.access.csv',    
        'wizard/eosb_report_wizard_view.xml',
        'report/eosb_eport_action.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
