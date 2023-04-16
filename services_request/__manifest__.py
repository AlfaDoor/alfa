# -*- coding: utf-8 -*-
{
    'name': "Request for services",

    'summary': """
        Request for services""",

    'description': """
        Request for services
    """,

    'author': "OserGroup",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Saudi HR',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['saudi_hr_employee'],

    # always loaded
    'data': [
        'views/views.xml',
        'views/sequence.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'report/identification_report.xml',
    ],
}