# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sit Advance Reconciliation',
    'version': '1.1',
    'summary': 'Adding new customizations for Advance Reconciliation',
    'sequence': 3,
    'author': "SIT Group",
    'website': "https://www.sitco.odoo.com",
    'description': "Advance Reconciliation in Customer Invoices",
    'category': 'Accouting',
    'depends': [
        'analytic','account'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
