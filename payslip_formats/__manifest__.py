# -*- coding: utf-8 -*-
{
    'name': "Payslip Bank Format",
    'summary': """Custom module for bank report format""",
    'author': "SIT & think digital",
    'website': "http://sitco.odoo.com/",
    'category': 'Custom',
    'version': '12.0.1',

    'depends': ['base','hr','saudi_hr_employee'],

    'data': [
        'security/ir.model.access.csv',
        'views/payslip_excel_report_view.xml',
            ],

    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
