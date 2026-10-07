{
    'name': 'Employee Settlement',
    'summary': """Employee Settlement During Resignation """,
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['hr_gratuity_settlement', 'account_extended','hr_payroll'],
    'data': [
             'security/ir.model.access.csv',
    		 'data/data.xml',
             'views/other_settlements.xml',
             'report/report_action.xml',
             'report/other_sattelment_template.xml',],
    'demo': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
