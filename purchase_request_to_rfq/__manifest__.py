{
    "name": "Purchase Request to RFQ.",
    "author": "SIT & Think Digital",
    "version": "12.0.1",
    "website": "http://sitco.odoo.com",
    "category": "Purchase Management",
    "depends": [
        "purchase_request",
        "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/purchase_request_line_make_purchase_order_view.xml",
        "views/purchase_request_view.xml",
        "views/purchase_order_view.xml",
    ],
    
    "installable": True,
    'auto_install': False,
}
