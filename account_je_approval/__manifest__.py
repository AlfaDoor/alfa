# -*- coding: utf-8 -*-
{
    "name": "Account JE Approval",
    "summary": "This module Adds functionality to manage Access rights to Post Journal Entries based on Sepcified Journal",
    'author': "SIT & think digital",
    'website': "http://sitco.odoo.com/",
    'category': 'Custom',
    'version': '12.0.1',

    'depends': ['account',
                ],

    'data': [
        "security/account_je_approval_security.xml",
        "views/account_journal_view.xml",
            ],

    'demo': [],

    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
