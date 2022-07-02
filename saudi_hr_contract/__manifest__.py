# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Saudi HR Contract',
    'version': '1.1',
    'summary': 'Adding new fields in HR contract',
    'sequence': 3,
    'author': "OserGroup",
    'website': "",
    'description': "",
    'category': 'Saudi HR',
    'depends': [
        'hr',
        'hr_contract',
        'hr_payroll',
        'saudi_hr_employee',
        # 'hr_recruitment',
    ],
    'data': [
        'data/hr_payroll_data.xml',
        'views/hr_contract_view.xml',
        'views/sequence.xml',
        'views/print_config.xml',
        'report/report.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
