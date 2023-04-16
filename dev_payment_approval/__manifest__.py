# -*- coding: utf-8 -*-

{
    'name': 'Payment/Voucher Double Approval Workflow',
    'summary': 'odoo app manage payment two three way approval process workflow',
    'author': "SIT & think digital",
    'website': "http://sitco.odoo.com/",
    'category': 'Custom',
    'version': '12.0.1',

    'depends': ['account',
                ],

    'data': [
        'security/security.xml',
        'views/view_res_config_settings.xml',
        'views/account_payment_view.xml',
        ],

    'demo': [],

    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

