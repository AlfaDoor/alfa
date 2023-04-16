# -*- coding: utf-8 -*-

{
    'name': "Payroll Account",
    'summary': """Payroll Account (Journal entry)""",
    'sequence': 6,
    'description': """  """,
    'author': "",
    'website': "",
    'category': 'Saudi HR',
    'version': '0.1',
    'depends': [
        'saudi_hr_payroll',
        'account',
        'hr_loans',
    ],
    'data': [
        'views/payroll_account.xml',
        'views/journal_entry.xml',
        'views/rewards_account.xml',
    ],
    'demo': [
        # 'demo.xml',
    ]
}
