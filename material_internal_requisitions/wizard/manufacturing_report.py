from odoo import models, fields, api, _

class RequisitionReports(models.TransientModel):
    _name = 'requisition.report'
    date_from = fields.Date()
    date_to = fields.Date()
    location = fields.Many2one('stock.location')

    def print_report(self):

        requisition = self.env['internal.requisition'].search([('request_date','>=',self.date_from),('request_date','<=',self.date_to),
                                                               ('location','=',self.location.id),('state','=','stock')])
        qty = 0
        products_sold = {}
        for rec in requisition:
            product = self.env['requisition.line'].search([('requisition_id','=',rec.id)])

            for line in product:
                key = (line.product_id)
                products_sold.setdefault(key, 0.0)
                products_sold[key] += line.qty

        res = {
            'start_date': self.date_from,
            'end_date': self.date_to,
            'location': self.location.complete_name,
            'products': sorted([{'product_name':product.name,
                                 'quantity': qty
                                 }for (product), qty in products_sold.items()], key=lambda l: l['product_name'])}
        data = {
            'form': res,
        }
        return self.env.ref('material_internal_requisitions.report_internal_req').report_action([], data=data)
