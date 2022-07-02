from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime


class procurement(models.Model):
    _name = 'requisition.procurement'
    _order = 'date desc'

    name = fields.Char(copy=False, string="Store Requisition", readonly=True,
                       index=True, default=lambda self: _('New'))
    product_id = fields.Many2one('product.product', string="Product")
    product_qty = fields.Float(string="Quantity")
    date = fields.Date(string="Date Requested")
    requisition_id = fields.Many2one('internal.requisition', string="Internal requisition")
    purchase_request_id = fields.Many2one('purchase.request', string="Purchase Request")
    status = fields.Selection([('waiting', 'Waiting'), ('done', 'Done')], default="waiting", string="Status")
    remarks = fields.Char(string='Remarks')

    # sr_bool = fields.Boolean(string="Store Requisition", default=False)

    @api.model
    def create(self, vals):
        if 'purchase_request_id' in vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('procurement_sequence')
        else:
            vals['name'] = False
        res = super(procurement, self).create(vals)
        return res
        # if vals.get('name', _('New')) == _('New'):
        #     vals['name'] = self.env['ir.sequence'].next_by_code('procurement_sequence') or _('New')
        #     res = super(procurement, self).create(vals)
        #     return res


class wizard_create_purchase(models.TransientModel):
    _name = 'wizard.create.purchase'
    type = fields.Selection([('purchase_request', 'Purchase Request'), ('purchase_agreement', 'Purchase Agreement')])

    @api.multi
    def create_purchase_request(self):
        records = self.env['requisition.procurement'].browse(self.env.context.get('active_ids'))
        for rec in records:
            source = ','.join(list(set(
                rec.mapped('requisition_id').mapped('name') if rec.requisition_id else rec.mapped('name'))))

        if len(records.filtered(lambda x: x.status != 'waiting')) > 0:
            raise UserError(_('Selected Records should be in Waiting state'))

        if len(records.filtered(lambda x: x.status == 'done')) > 0:
            raise UserError(_('Wrong Selection,Purchase Request already created'))

        if not rec.purchase_request_id:
            value = {'requested_by': self.env.uid, 'origin': source, 'date_start': datetime.date.today()}
            PR = self.env['purchase.request'].create(value)
            domain = []
            for rec in records:
                domain.extend(
                    [('product_id', '=', rec.product_id.id), ('request_id', '=', PR.id), ('origin', '=', source)])
                pr_line = self.env['purchase.request.line'].search(domain)
                if pr_line:
                    pr_line.write({'product_qty': sum(records.mapped('product_qty'))})
                else:
                    PR.line_ids.create(
                        {'product_id': rec.product_id.id, 'remarks': rec.remarks,
                         'requisition_id': rec.requisition_id.id, 'product_qty': rec.product_qty, 'request_id': PR.id})
                    rec.write({'purchase_request_id': PR.id, 'status': 'done'})
        else:
            for rec in records:
                purchase_request = rec.purchase_request_id

                if purchase_request.state not in ['draft', 'to_approve']:
                    raise UserError(_('Selected Purchase Request should be in draft state'))

                line = purchase_request.line_ids.filtered(lambda x: x.product_id == rec.product_id)

                if line:
                    rec.purchase_request_id.write({'origin': purchase_request.origin + ',' + source})
                    line.write({'product_qty': line.product_qty + rec.product_qty})
                    rec.write({'status': 'done'})
                else:
                    purchase_request.line_ids.create(
                        {'product_id': rec.product_id.id, 'remarks': rec.remarks, 'product_qty': rec.product_qty,
                         'request_id': purchase_request.id})


class inherit_Purchase_request(models.Model):
    _inherit = 'purchase.request'

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state == 'draft':
                self._cr.execute(
                    "update requisition_procurement set status='waiting' where purchase_request_id=%s" % (rec.id))

        return super(inherit_Purchase_request, self).unlink()

class MoveStockInherit(models.Model):
    _inherit = 'stock.move'

    need_mrp = fields.Boolean(string="MRP", default=False,
                              help='Need Manufacturing')


class inherit_stock_picking(models.Model):
    _inherit = 'stock.picking'

    purchase_request_done = fields.Boolean(default=False)
    have_mo_request = fields.Boolean(default=False)
    have_mo = fields.Boolean(default=False)
    mo_count = fields.Integer(compute='_manufacturing_count')

    @api.multi
    def _manufacturing_count(self):
        for obj in self:
            manufacturing_ids = self.env['mrp.production'].sudo().search([])
            manufacture = manufacturing_ids.filtered(lambda x: x.origin == self.origin)
        obj.mo_count = len(manufacture)

    def procure_requisition(self):
        msg = ''
        diff = 0
        if self.purchase_request_done:

            return 'procurement_already_created'

        else:

            for rec in self.move_lines.filtered(lambda r: r.product_uom_qty != r.reserved_availability):
                diff = rec.product_uom_qty - rec.reserved_availability
                if diff:
                    if rec.product_id.route_ids.id == 5:
                        self.env['requisition.procurement'].create(
                            {'remarks': rec.remarks, 'product_id': rec.product_id.id, 'product_qty': diff,
                             'date': datetime.date.today(), 'requisition_id': self.inter_requi_id.id})
                    if rec.product_id.route_ids.id == 6:
                        rec.need_mrp = True
                        self.have_mo_request = True
                    self.purchase_request_done = True
            if diff:
                msg = msg + "Procurement Created ! \n"

            if self.move_lines.filtered(lambda r: r.product_uom_qty == r.reserved_availability):
                msg = msg + "Quantity Reserved !"

            return msg

    @api.multi
    def action_assign(self):
        context = dict(self._context or {})

        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        self.filtered(lambda picking: picking.state == 'draft').action_confirm()
        moves = self.mapped('move_lines').filtered(lambda move: move.state not in ('draft', 'cancel', 'done'))
        if not moves:
            raise UserError(_('Nothing to check the availability for.'))
        # If a package level is done when confirmed its location can be different than where it will be reserved.
        # So we remove the move lines created when confirmed to set quantity done to the new reserved ones.
        package_level_done = self.mapped('package_level_ids').filtered(
            lambda pl: pl.is_done and pl.state == 'confirmed')
        package_level_done.write({'is_done': False})
        moves._action_assign()
        package_level_done.write({'is_done': True})

        value = self.procure_requisition()

        if value == 'procurement_already_created':
            context['message'] = context['message'] = 'Procurement already Created.'
            view_id = self.env['ir.model.data'].get_object_reference(
                'sh_message',
                'sh_message_wizard')[1]
            return {
                'name': _('Message'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.message.wizard',
                'view_id': view_id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context
            }

        else:
            context['message'] = context['message'] = value
            view_id = self.env['ir.model.data'].get_object_reference(
                'sh_message',
                'sh_message_wizard')[1]
            return {
                'name': _('Message'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.message.wizard',
                'view_id': view_id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context
            }

    @api.multi
    def do_unreserve(self):
        records = self.env['requisition.procurement'].search(
            [('requisition_id', '=', self.inter_requi_id.id), ('status', '=', 'waiting')])

        for rec in records:
            rec.unlink()
            self.purchase_request_done = False

        return super(inherit_stock_picking, self).do_unreserve()

    @api.multi
    def action_view_mo(self):
        for rec in self.move_lines.filtered(lambda r: r.product_uom_qty != r.reserved_availability):
            diff = rec.product_uom_qty - rec.reserved_availability
            if diff:
                if rec.product_id.route_ids.id == 6:
                    self.mo_count = 1
                    return {
                        'res_model': 'mrp.production',
                        'type': 'ir.actions.act_window',
                        'context': {'default_product_id': rec.product_id.id, 'default_product_uom_qty':diff,
                                    'default_origin':self.origin,
                                    'default_product_uom_id':rec.product_uom.id,'default_requition_mo':self.id},
                        'view_mode': 'form',
                        'view_type': 'form',
                        'view_id': self.env.ref("mrp.mrp_production_form_view").id,
                        'target': 'new'
                    }

    @api.multi
    def action_view_mo_picking(self):
        return {
            'name': _('Manufacturing Order'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'mrp.production',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('requition_mo', '=', self.id)],
        }


class InheritMrp(models.Model):
    _inherit = 'mrp.production'

    requition_mo = fields.Integer()
