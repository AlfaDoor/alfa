# -*- coding: utf-8 -*-
{
    'name': "Chart of account",
    'summary': """ """,
    'description': """ """,
    'author': "Mamdouh Yousef",
    'website': "",
    'sequence': 1,
    'category': 'saudi account',
    'version': '0.1',
    'depends': [
        'base',
        'account',
        # 'analytic_account',
        'purchase',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'security/security.xml',
        'views/account_account.xml',
        'views/base.xml',
        'views/account_type.xml',
        'views/account_journal.xml',
        'views/invoice.xml',
        'data/account.account.type.csv'
    ],
    'demo': [
        'demo/demo.xml',
    ],
}