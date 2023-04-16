# -*- coding: utf-8 -*-
{
    'name': "Custom HR",
    'summary': """Custom some HR requirements""",
    'author': "SIT & think digital",
    'website': "http://sitco.odoo.com/",
    'category': 'Custom',
    'version': '12.0.1',

    'depends': ['base','hr','saudi_hr_employee','saudi_hr_leaves','overtime_late','saudi_hr_payroll','basic_hr','saudi_hr_eos','account'],

    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'wizard/wizard_view.xml',
        # 'wizard/payslip_report_view.xml',
        'views/model_view.xml',
        'views/cron_view.xml'
            ],

    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
