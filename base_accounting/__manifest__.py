# -*- coding: utf-8 -*-

{
    'name': "Base for Accounting changes",
    'summary': " ",
    'sequence': 0,
    'description': " ",
    'author': "Osergroup",
    'website': "",
    'category': 'saudi account',
    'version': '0.1',
    'depends': [
        'base',
        'account',
        # 'account_asset',
        # 'account_deferred_revenue',
        'base_setup',
        'custom_confirmation_box',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/base_accounting.xml',
        'views/accounting_menus.xml',
    ],
    'demo': [
        # 'demo.xml',
    ]
}
