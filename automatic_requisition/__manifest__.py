# -*- coding: utf-8 -*-
{
    'name': "Automation Creation of Requisitions.",
    'summary': """customization for automated creation of internal requisition from manufacturing order.""",
    'author': "SIT & Think Digital",
    'website': "https://www.linkedin.com/in/engr-muhammad-faizan-80011782/",
    'category': 'Custom',
    'version': '11.0.1',

    'depends': ['mrp','stock'],

    'data': [
        'views/model_view.xml',
            ],

    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
