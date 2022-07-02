# -*- coding: utf-8 -*-
{
    'name': "Loan Batches",
    'summary': """Custom module to generate loan batches""",
    'author': "SIT & think digital",
    'website': "http://sitco.odoo.com/",
    'category': 'Custom',
    'version': '12.0.1',

    'depends': ['base','hr','saudi_hr_employee','hr_loans'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/loan_batch_by_employees_view.xml',
        'views/loan_batch_view.xml',
        'views/loan_excel_report_view.xml',
            ],

    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
