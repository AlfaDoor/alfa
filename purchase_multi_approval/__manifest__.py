# -*- coding: utf-8 -*-
{
    'name': 'Purchase Multi Approval',
    'summary': """All custom requirement related customizations""",
    'author': "SIT & think digital",
    'website': "http://sitco.odoo.com/",
    'category': 'Custom',
    'version': '12.0.1',

    'depends': ['purchase'],

    'data': [
#        'security/ir.model.access.csv',
        'views/inherited_views.xml'],

    'demo': [],

    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
