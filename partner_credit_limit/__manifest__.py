# See LICENSE file for full copyright and licensing details.

{
    'name': 'Partner Credit Limit',
    'version': '12.0.1.0.0',
    'category': 'Custom',
    'license': 'AGPL-3',
    'author': 'SIT & think digital',
    'website': 'http://sitco.odoo.com/',
    'summary': 'Set credit limit warning',
    'depends': [
        'sale_management',
    ],
    'data': [
        'views/partner_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
