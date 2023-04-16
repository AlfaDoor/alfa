from odoo import models, fields, api

class RequisitionLine(models.Model):
    _name = "requisition.line"
    
    requisition_id = fields.Many2one(
        'internal.requisition',
        string='Requisitions', 
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    layout_category_id = fields.Many2one(
        'sale.layout_category',
        string='Section',
    )
    description = fields.Char(
        string='Description',
        required=True,
    )
    qty = fields.Float(
        string='Requested Quantity',
        default=1,
        required=True,
    )
    uom = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
    )
    rec_qty = fields.Float(
        string='Received Quantity',
        default=0.0,
    )
    
    remarks = fields.Char(string="Remarks")
    
    @api.onchange('product_id')
    def set_uom(self):
        for rec in self:
            rec.description = rec.product_id.name
            rec.uom = rec.product_id.uom_id.id