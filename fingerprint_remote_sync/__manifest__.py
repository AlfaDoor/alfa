# -*- coding: utf-8 -*-

{
    'name': "Fingerprint remote integration",
    'summary': " Fingerprint remote integration ",
    'sequence': 8,
    'description': """  """,
    'author': "MamdouhYousef",
    'website': "",
    'category': 'Saudi HR',
    'version': '0.1',
    'depends': [
        'base',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/fingerprint_remote_sync.xml',
        'views/ir_cron.xml',
    ],
    'demo': [
        # 'demo.xml',
    ]
}
