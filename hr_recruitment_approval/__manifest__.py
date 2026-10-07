{
    'name': 'HR Recruitment Approval',
    'version': '15.0.1.0.0',
    'summary': 'Add Offer Approval workflow to HR Recruitment',
    'description': """
        Adds an Offer Approval stage with sequential approval workflow to HR Recruitment process.
        Uses activity notifications instead of emails for approval requests.
    """,
    'author': 'Olive Infocraft',
    'website': 'https://www.yourcompany.com',
    'category': 'Human Resources',
    'depends': ['hr_recruitment', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/approval_group.xml',
        'data/stage.xml',
        'views/hr_recruitment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}