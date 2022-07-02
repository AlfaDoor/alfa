from odoo import models, fields, api,_
from datetime import date, datetime
from odoo.exceptions import ValidationError

class InheritManufacturing(models.Model):
    _inherit = 'mrp.production'
    has_requisition = fields.Boolean(default=False)
    requisition_count = fields.Integer(compute='_requisition_count')

    def create_requisition(self):
        if self.has_requisition == True:
            raise ValidationError(_('Requisition Already Created for this document.'))
        if not self.location_src_id:
            raise ValidationError(_('Please set Raw Material Source Location before create requisition.'))
        rec = []
        for items in self.move_raw_ids:
            difference = items.product_uom_qty - items.reserved_availability
            if difference > 0:
                rec.append((0, 0, {'product_id': items.product_id.id,
                                   'description': items.product_id.name,
                                   'qty': difference,
                                   'uom':items.product_id.uom_id.id}))
        employee = self.env['hr.employee'].search([('request_user_id', '=', self.env.uid)],limit=1)
        if not employee:
            raise ValidationError(_('Please select the related user on your employee form.'))
        location = self.env['stock.location'].search([('name', '=', 'Stock'),('location_id.name', '=', 'RM-ML')])
        picking_type = self.env['stock.picking.type'].search([('warehouse_id.name', '=', 'Semi Production W/H - MALHAM'), ('name', '=', 'Receipts')])
        self.env['internal.requisition'].create({'request_emp':employee.id,
                                                 'department_id':employee.department_id.id,
                                                 'desti_loca_id':self.location_src_id.id,
                                                 'request_date':date.today(),
                                                 'date_end':datetime.now(),
                                                 'mo_reference':self.name,
                                                 'location':location.id if location else False,
                                                 'custom_picking_type_id':picking_type.id if picking_type else False,
                                                 'requisition_line_ids': rec})
        self.has_requisition = True

    def requisition_view(self):
        req_ids = []
        for obj in self:
            req_obj = self.env['internal.requisition'].sudo().search([])
            requisition_id = req_obj.filtered(
                lambda x: x.mo_reference == self.name)
            for item in requisition_id:
                req_ids.append(item.id)
            view_id = self.env.ref('material_internal_requisitions.material_internal_requisition_form_view').id
            if req_ids:
                value = {
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'internal.requisition',
                        'view_id': view_id,
                        'type': 'ir.actions.act_window',
                        'name': _('Internal Requisition'),
                        'res_id': req_ids and req_ids[0]
                    }
                return value

    @api.multi
    def _requisition_count(self):
        for obj in self:
            requisition_ids = self.env['internal.requisition'].sudo().search([])
            requisition = requisition_ids.filtered(lambda x: x.mo_reference == self.name)
        obj.requisition_count = len(requisition)

class InheritWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    code = fields.Char('Short Name', required=True, size=10, help="Short name used to identify your warehouse")

class InheritManufacturingOrder(models.Model):
    _inherit = 'mrp.production'
    need_requisition = fields.Boolean(default=False)

    @api.multi
    def action_assign(self):
        for production in self:
            production.move_raw_ids._action_assign()
        if self.availability in ['waiting','partially_available']:
            self.need_requisition = True
        return True

    @api.model
    def create(self, vals):
        vals['has_requisition'] = False
        return super(InheritManufacturingOrder, self).create(vals)
