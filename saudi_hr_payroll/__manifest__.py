# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Saudi HR Payroll',
    'version': '1.1',
    'summary': 'Adding new fields in HR payroll',
    'sequence': 4,
    'description': "",
    'category': 'Saudi HR',
    'author': "OserGroup",
    'website': "",
    'depends': [
        'hr_contract',
        'hr_payroll',
        # 'hr_payroll_account',
        'saudi_hr_employee',
        # 'saudi_hr_recruitment',
        'saudi_hr_contract',
    ],
    'data': [
        'security/ir.model.access.csv',
        #'data/hr_payroll_data.xml',
        'views/hr_payroll_view.xml',
        'views/salary_structure_data.xml',
        'views/payroll_report.xml',
        'wizard/payroll_wizard.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
