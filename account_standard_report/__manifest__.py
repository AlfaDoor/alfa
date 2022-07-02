# -*- coding: utf-8 -*-

{
    'name': 'Standard Accounting Reports',
    'version': '9.0.1.0.1',
    'category': 'saudi account',
    'author': "Mamdouh Yousef",
    'website': "",
    'summary': 'Standard Accounting Report',
    'depends': [
        'account',
        'report_xlsx',
        'base_accounting',
        'account_account',
        'hr',
        'analytic',
    ],
    'data': [
        'data/report_paperformat.xml',
        'data/data_account_standard_report.xml',
        'data/res_currency_data.xml',
        'report/report_account_standard_report.xml',
        'views/account_view.xml',
        'views/account_standard.xml',
        'views/res_currency_views.xml',
        'wizard/account_standard_report_view.xml',
        'views/static_reports.xml',
    ],
    'price': 0.0,
    'currency': 'EUR',
    'installable': True,
    'images': ['images/main_screenshot.png'],
}
