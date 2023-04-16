# -*- coding: utf-8 -*-

{
    'name': "HR GOSI",
    'summary': """ Gosi """,
    'sequence': 5,
    'description': """ Gosi """,
    'author': "OserGroup",
    'website': "",
    'category': 'Saudi HR',
    'version': '0.1',
    'depends': [
        'base',
        'hr',
        'saudi_hr_contract',
        'saudi_hr_employee',
        'saudi_hr_payroll',
    ],
    'data': [
        # 'security/security.xml',
        # 'security/ir.model.access.csv',
        'views/hr_gosi.xml',
        'views/salary_structure_data.xml',
    ],
    'demo': [
        # 'demo.xml',
    ]
}
