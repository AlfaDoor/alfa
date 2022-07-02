# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Extend HR Recruitment',
    'version': '1.1',
    'summary': 'Adding new fields in Applications',
    'sequence': 1,
    'description': "",
    'category': 'Saudi HR',
    'author': "OserGroup",
    'website': "",
    'depends': [
        'hr',
        'hr_recruitment',
        'basic_hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_recruitment_view.xml',
        'reports/report_job_offer.xml',
        'views/report_view.xml',
        'views/sequence.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}