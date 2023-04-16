
{
    'name': 'Stock Movement Report in Odoo',
    'version': '12.0.0.6',
    'category': 'Warehouse',
    'summary': 'This modules helps to print inventory movement Report for particular date with Excel and PDF both option.',
    'description': """
    This modules helps to print inventory movement Report for particular date with Excel and PDF both options
    """,
    'author': 'SIT & Think Digital',
    'website': 'http://sitco.odoo.com',
    'depends': ['stock','sale','account','purchase','sale_stock'],
    'data': [
        'views/movement_report_product_category_wizard.xml',
        'views/report_pdf.xml',
        'views/inventory_movement_detail_template.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}


