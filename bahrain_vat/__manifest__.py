# -*- coding: utf-8 -*-
###################################################################################
#
#    inteslar software trading llc.
#    Copyright (C) 2018-TODAY inteslar (<https://www.inteslar.com>).
#    Author:   (<https://www.inteslar.com>)
#
###################################################################################
{
    'name': 'Bahrain VAT.',
    'version': '1.0',
    'sequence': 1,
    'category': 'accounting',
    'price': 1500.00,
    'currency': 'EUR',
    'license': 'OPL-1',
    'website': 'https://www.inteslar.com',
    'images': ['static/description/banner.jpg'],
    'author': 'inteslar',
    'summary': 'Easily calculate and file taxes in Bahrain',
    'description': """
    Key Features
    ------------
    * Bahrain VAT Filing and Accounting
            """,
    'depends':['base','account'],
    'data':['security/ir.model.access.csv',
            'wizard/roll_over_view.xml',
            'wizard/wizard_tax_adjustments_view.xml',
            'views/report_uae_vat_return.xml',
            'views/account_report_uae.xml',
            'wizard/vat_return_payment.xml',
            'wizard/open_tax_balances_view.xml',
            'wizard/import_return_payment_view.xml',
            'views/uae_vat_customization.xml'],
    'application': True,
    'installable': True,
    'auto_install': False,
}