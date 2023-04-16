# -*- coding: utf-8 -*-

{
    'name': "Fingerprint integration",
    'summary': """  """,
    'sequence': 8,
    'description': """  """,
    'author': "Mamdouh Yousef",
    'website': "",
    'category': 'Saudi HR',
    'version': '0.1',
    'depends': [
        'base',
        'hr_attendance',
        'resource',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/fingerprint_sync.xml',
        'views/employees.xml',
        'views/resource.xml',
        'views/ir_cron.xml',
    ],
    'demo': [
        # 'demo.xml',
    ]
}
