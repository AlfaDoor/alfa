# -*- coding: utf-8 -*-

{
    'name': "Basic for HR changes",
    'summary': """  """,
    'sequence': 0,
    'description': """  """,
    'author': "OserGroup",
    'website': "",
    'category': 'Saudi HR',
    'version': '0.1',
    'depends': [
        'base',
        'hr',
        'mail',
        # 'account',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/basic_hr.xml',
        'views/res_country.xml',
        'views/basic_tech.xml',
        'views/hr_management.xml',
    ],
    'demo': [
        # 'demo.xml',
    ]
}
