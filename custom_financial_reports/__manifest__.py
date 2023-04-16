# -*- coding: utf-8 -*-
{
    'name': "Custom Financial Reports",

    'summary': """
        Custom Financial Reports""",

    'description': """
        Custom Financial Reports
    """,

    'author': "Mamdouh Yousef",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'saudi account',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base_accounting',
        'account_standard_report',
        'account_budget',
        'analytic_account',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/financial_report_config.xml',
        'views/custom_report_template.xml',
        'views/financia_report_data.xml',
    ],
}