# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Saudi HR Employees',
    'version': '1.1',
    'summary': 'Adding new fields in HR',
    'sequence': 2,
    'description': "",
    'category': 'Saudi HR',
    'author': "SIT",
    'website': "",
    'depends': [
        'base',
        'hr','basic_hr',
        'hr_contract',
        # 'saudi_hr_recruitment',
        'custom_confirmation_box',
        ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/hr_seq.xml',
        'wizard/wizard_view.xml',
        'views/hr_view.xml',
        'views/departments.xml',
		'views/hr_branch_job_view.xml',
        'views/effective_notice.xml',
        'views/employee_history.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
