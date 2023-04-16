# -*- coding: utf-8 -*-
# Copyright (C) 2016-TODAY info@odoo-experte.com <https://www.odoo-experte.com>
# See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta


class CreateMrpWizard(models.TransientModel):
    _name = 'create.mrp.wizard'

    @api.multi
    def mrp_stock_filtered(self, stock_moves_lines):
        all_selected_stock_line = stock_moves_lines.filtered(
            lambda stock_line: stock_line.need_mrp)

        stock_line_filter = lambda x: x.filtered(
            lambda stock_line: not stock_line.production_id.id)
        return all_selected_stock_line, stock_line_filter

    @api.model
    def default_get(self, fields_list):
        res = super(CreateMrpWizard, self).default_get(fields_list)
        move_obj = self.env['stock.move']
        stock_lines = move_obj.search([('picking_id','=',self.env.context.get('active_id')),('need_mrp','=',True)])
        lines = []
        line_wizard_pool = self.env['create.mrp.line.wizard']

        # sol: sale_order_line
        all_selected_stock_line, stock_line_filter = self.mrp_stock_filtered(
                stock_lines)

        if not all_selected_stock_line:
            filtered_sol = stock_line_filter(stock_lines)
        else:
            filtered_sol = stock_line_filter(stock_lines)

        for line in filtered_sol:
            line_wizard = line_wizard_pool. \
                create({'name': line.name,
                        'product_id': line.product_id.id,
                        'product_qty': (line.product_uom_qty - line.reserved_availability),
                        'product_uom': line.product_uom.id,
                        'product_bom_id': self.env['mrp.bom'].search([('product_tmpl_id','=',line.product_id.product_tmpl_id.id)],limit=1).id,
                        'stock_line_id': line.id,
                        })
            lines.append(line_wizard.id)
        res.update({'order_line_ids': [(6, 0, lines)]})
        return res

    order_line_ids = fields.One2many('create.mrp.line.wizard',
                                     'order_wizard_id',
                                     string='Products')

    @api.one
    def action_create_mrp(self):
        all_number = len(self.order_line_ids)
        number = 1
        for line in self.order_line_ids:
            mrp_bom = self.env['mrp.bom'].search(
                [('product_tmpl_id', '=',
                  line.product_id.product_tmpl_id.id),
                 ('product_id', '=', line.product_id.id)])
            if not mrp_bom:
                mrp_bom = self.env['mrp.bom'].search(
                    [('product_tmpl_id', '=',
                      line.product_id.product_tmpl_id.id)])
                if mrp_bom:
                    mrp_bom.copy().product_id = line.product_id.id
            if not mrp_bom:
                bom_values = {
                    'product_tmpl_id':
                        line.product_id.product_tmpl_id.id,
                    'type': 'normal',
                    'product_qty': 1,
                    'product_uom_id': line.product_uom.id,
                    'name': line.product_id.product_tmpl_id.name,
                }
                mrp_bom = self.env['mrp.bom'].create(bom_values)
            production_vals = {
                    'product_id': line.product_id.id,
                    'bom_id': mrp_bom[0].id,
                    'product_qty': line.product_qty,
                    'product_uom_id': line.product_uom.id,
                    'date_planned': datetime.now(),
                    'requition_mo': self.env.context.get('active_id'),
                    'origin': self.env['stock.picking'].search([('id','=',self.env.context.get('active_id'))]).origin,
                    'all_number': all_number,
                    'number': number,
                }
            mrp_id = self.env['mrp.production'].create(production_vals)
        number += 1
        back_paicking = self.env['stock.picking'].search([('id', '=', self.env.context.get('active_id'))])
        back_paicking.have_mo = True
        back_paicking.have_mo_request = False
        # unlink created records
        for line in self.order_line_ids:
            line.unlink()


class CreateMrpLineWizard(models.TransientModel):
    _name = 'create.mrp.line.wizard'

    order_wizard_id = fields.Many2one('create.mrp.wizard',
                                      string='Purchase Order',
                                      ondelete='cascade', )
    name = fields.Text(string='Description')
    product_id = fields.Many2one('product.product', string='Product', )
    product_qty = fields.Float(string='Quantity',
                               digits=dp.get_precision(
                                   'Product Unit of Measure'))
    product_uom = fields.Many2one('uom.uom',
                                  string='Product Unit of Measure',
                                  required=True)
    product_bom_id = fields.Many2one('mrp.bom',domain=[('product_tmpl_id', '=', 'product_id.product_tmpl_id')], strimg='Product BOM')
    stock_line_id = fields.Many2one('stock.move', string="Stock move")
