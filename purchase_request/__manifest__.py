{
    "name": "Purchase Requests.",
    "author": "SIT & Think Digital",
    "version": "12.0.1",
    "summary": "Use this module to have notification of requirements of "
               "materials and/or external services and keep track of such "
               "requirements.",
    "category": "Purchase Management",
    "depends": [
        "purchase",
        "product"
    ],
    "data": [
        "security/purchase_request.xml",
        "security/ir.model.access.csv",
        "data/purchase_request_sequence.xml",
        "data/purchase_request_data.xml",
        "views/purchase_request_view.xml",
        "reports/report_purchaserequests.xml",
        "views/purchase_request_report.xml",
    ],
    
    'installable': True,
    'auto_install': False,
}