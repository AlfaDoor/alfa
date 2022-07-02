# -*- coding: utf-8 -*-
{
    'name': "Hr EOS",

    'summary': """
        Saudi Arabia End of Services""",

    'description': """
        Saudi Arabia End of Services
    """,

    'author': "OserGroup",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Saudi HR',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'saudi_hr_employee',
        'saudi_hr_leaves',
        'hr_loans',
        'saudi_hr_payroll',
        'basic_hr',
    ],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/sequence.xml',
        'wizard/pending_transactions_wizard.xml',
        'data/data.xml',
    ],
}