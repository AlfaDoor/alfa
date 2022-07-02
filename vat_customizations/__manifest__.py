# -*- coding: utf-8 -*-
{
    'name': "Custom VAT Module",
    'summary': """Custom some Tax and VAT requirements""",
    'sequence': 0,
    'author': "SIT & think digital",
    'website': "http://sitco.odoo.com/",
    'category': 'Custom',
    'version': '12.0.1',

    'depends': ['bahrain_vat'],

    'data': [
        'views/report_vat_customizations_uae_vat_return.xml',
        'views/reports.xml',
        'views/views.xml',
        ],

    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
