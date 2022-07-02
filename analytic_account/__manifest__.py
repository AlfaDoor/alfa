# -*- coding: utf-8 -*-

{
    'name': "Analytic Accounts",
    'summary': """  """,
    'sequence': 0,
    'description': """  """,
    'author': "Mamdouh Yousef",
    'website': "",
    'category': 'saudi account',
    'version': '0.1',
    'depends': [
        'base',
        'analytic',
        'account',
        'base_accounting',
        'account_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/analytic_account.xml',
        'views/analytic_template.xml',
        'views/journal_entry.xml',
        'views/general_ledger.xml',
        'views/data.xml',
    ],
    'demo': [
        # 'demo.xml',
 ]}