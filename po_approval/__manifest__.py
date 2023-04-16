# -*- coding: utf-8 -*-

{
    'name': 'Purchase Order Double Approval Workflow',
    'summary': 'odoo app manage purchase order two way approval process workflow',
    'author': "SIT & think digital",
    'website': "http://sitco.odoo.com/",
    'category': 'Custom',
    'version': '12.0.1',

    'depends': ['purchase',
                ],

    'data': [
        'security/security.xml',
#        'views/view_res_config_settings.xml',
        'views/purchase_order_view.xml',
        ],

    'demo': [],

    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

