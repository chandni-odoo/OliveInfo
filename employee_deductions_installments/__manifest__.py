{
    "name": "Employee Deduction Installments",
    "version": "15.0.1.0.0",
    "summary": "Manage employee loan, traffic fine and other deductions with installments integrated into payroll",
    "category": "Human Resources",
    "author": "ChatGPT Assistant",
    "website": "https://openai.com",
    "depends": ['base',"hr_payroll",'hr_loan_management','hr'],
    "data": [
        "security/ir.model.access.csv",
        "security/employee_deductions_security.xml",
        "data/sequence_data.xml",
        "data/deduction_types_data.xml",
        "views/hr_employee_deduction_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}