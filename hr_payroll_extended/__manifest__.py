# -*- coding: utf-8 -*-
{
    'name': "HrPayslip Extended",
    'summary':'Hr Payslip Extended',
    'description': 'HrPayslip Extended',
    'category': 'HR',
    'version': '15.0.1',
    'author':'Preciseways',
    'website': "http://www.preciseways.com",
    'depends': ['base','hr_payroll', 'hr_holidays', 'hr_contract', 'hr_attendance', 'pways_hr_shift_allocation','hr_overtime_automatic','hr_loan_management','peoplesol_other_earnings'],
    'data': [
        'data/contract_approval.xml',
        'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',
        # 'wizard/payroll_batch_wizard.xml',
        'wizard/contract_reject_wizard.xml',
        'wizard/payroll_summary_wizard_view.xml',
        'views/contract_approval_view.xml',
        'views/hr_payslip_view.xml',
        'views/payroll_batch.xml',
        'wizard/hr_payroll_register_wizard_view.xml',
        'report/report.xml',
        'report/report_template_summary.xml',
        'report/report_template.xml',
        'report/report_action.xml',
        'report/payroll_register_template.xml',
    ],
    
    
    'license': 'LGPL-3',
}
