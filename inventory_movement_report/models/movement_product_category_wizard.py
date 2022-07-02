# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import base64
from io import StringIO
from odoo import api, fields, models
from datetime import date
from odoo.tools.float_utils import float_round
from odoo.exceptions import ValidationError

import io

try:
    import xlwt
except ImportError:
    xlwt = None


class sale_day_book_wizard(models.TransientModel):
    _name = "sale.day.book.wizard"

    start_date = fields.Date('Start Period', required=True)
    end_date = fields.Date('End Period', required=True)
    warehouse = fields.Many2many('stock.warehouse', 'wh_wiz_rel_inv_val', 'wh', 'wiz', string='Warehouse')
    category = fields.Many2one('product.category',required=True, string='Item Category')
    location_id = fields.Many2one('stock.location', string='Location')
    location_ft = fields.Many2one('stock.location', string='From/To Location')
    item = fields.Many2one('product.product')
    company_id = fields.Many2one('res.company', string='Company')
    all_prod = fields.Boolean(default=True)
    net_sale = 0
    net_return = 0
    net_sale_amount = 0
    net_return_amount = 0

    @api.multi
    def print_report(self):
        datas = {
            'ids': self._ids,
            'model': 'sales.day.book.wizard',
            'start_date': self.start_date,
            'end_date': self.end_date,
            'warehouse': self.warehouse,
            'location_id': self.location_id,
            'location_ft':self.location_ft,
            'company_id': self.company_id,
            'product_id': self.item.id or False,
            'category':self.category.id or False,
            'all_prod':self.all_prod
        }
        return self.env.ref('inventory_movement_report.inventory_product_category_template_pdf').report_action(
            self)

    @api.onchange('category')
    def set_products(self):
        products = []
        if self.category:
            prods = self.env['product.product'].search([('categ_id','=',self.category.id),('qty_available', '!=', 0)])
            for rec in prods:
                products.append(rec.id)
        return {'domain': {'item': [('id', 'in', products)]}}

    def get_warehouse(self):
        if self.warehouse:
            l1 = []
            l2 = []
            for i in self.warehouse:
                obj = self.env['stock.warehouse'].search([('id', '=', i.id)])
                for j in obj:
                    l2.append(j.id)
            return l2
        return []

    def _get_warehouse_name(self):
        if self.warehouse:
            l1 = []
            l2 = []
            for i in self.warehouse:
                obj = self.env['stock.warehouse'].search([('id', '=', i.id)])
                l1.append(obj.name)
                myString = ",".join(l1)
            return myString
        return ''

    def get_company(self):
        if self.company_id:
            l1 = []
            l2 = []
            obj = self.env['res.company'].search([('id', '=', self.company_id.id)])
            l1.append(obj.name)
            return l1

    def get_currency(self):
        if self.company_id:
            l1 = []
            l2 = []
            obj = self.env['res.company'].search([('id', '=', self.company_id.id)])
            l1.append(obj.currency_id.name)
            return l1

    def get_category(self):
        if self.category:
            l2 = []
            obj = self.env['product.category'].search([('id', 'in', self.category)])
            for j in obj:
                l2.append(j.id)
            return l2
        return ''

    def get_date(self):
        date_list = []
        obj = self.env['stock.history'].search([('date', '>=', self.start_date), ('date', '<=', self.end_date)])
        for j in obj:
            date_list.append(j.id)
        return date_list

    def _compute_quantities_product_quant_dic(self, lot_id, owner_id, package_id, from_date, to_date, product_obj,
                                              data):

        loc_list = []

        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = product_obj._get_domain_locations()
        custom_domain = []
        if data['company_id']:
            obj = self.env['res.company'].search([('name', '=', data['company_id'])])

            custom_domain.append(('company_id', '=', obj.id))

        if data['location_id']:
            custom_domain.append(('location_id', '=', data['location_id'].id))

        if data['warehouse']:
            ware_check_domain = [a.id for a in data['warehouse']]
            locations = []
            for i in ware_check_domain:
                loc_ids = self.env['stock.warehouse'].search([('id', '=', i)])
                locations.append(loc_ids.view_location_id.id)
                for i in loc_ids.view_location_id.child_ids:
                    locations.append(i.id)
                loc_list.append(loc_ids.lot_stock_id.id)
            custom_domain.append(('location_id', 'in', locations))
        domain_quant = [('product_id', 'in', product_obj.ids)] + domain_quant_loc + custom_domain
        dates_in_the_past = False
        if to_date and to_date < date.today():
            dates_in_the_past = True

        domain_move_in = [('product_id', 'in', product_obj.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', product_obj.ids)] + domain_move_out_loc
        if lot_id is not None:
            domain_quant += [('lot_id', '=', lot_id)]
        if owner_id is not None:
            domain_quant += [('owner_id', '=', owner_id)]
            domain_move_in += [('restrict_partner_id', '=', owner_id)]
            domain_move_out += [('restrict_partner_id', '=', owner_id)]
        if package_id is not None:
            domain_quant += [('package_id', '=', package_id)]
        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)
        if from_date:
            domain_move_in += [('date', '>=', from_date)]
            domain_move_out += [('date', '>=', from_date)]
        if to_date:
            domain_move_in += [('date', '<=', to_date)]
            domain_move_out += [('date', '<=', to_date)]

        Move = self.env['stock.move']
        Quant = self.env['stock.quant']
        domain_move_in_todo = [('state', 'in',
                                ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
        domain_move_out_todo = [('state', 'in',
                                 ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
        moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in
                            Move.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id'],
                                            orderby='id'))
        moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in
                             Move.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id'],
                                             orderby='id'))
        quants_res = dict((item['product_id'][0], item['quantity']) for item in
                          Quant.read_group(domain_quant, ['product_id', 'quantity'], ['product_id'], orderby='id'))

        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
            domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
            domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done
            moves_in_res_past = dict((item['product_id'][0], item['product_qty']) for item in
                                     Move.read_group(domain_move_in_done, ['product_id', 'product_qty'], ['product_id'],
                                                     orderby='id'))
            moves_out_res_past = dict((item['product_id'][0], item['product_qty']) for item in
                                      Move.read_group(domain_move_out_done, ['product_id', 'product_qty'],
                                                      ['product_id'], orderby='id'))

        res = dict()
        for product in product_obj.with_context(prefetch_fields=False):
            product_id = product.id
            rounding = product.uom_id.rounding
            res[product_id] = {}
            if dates_in_the_past:
                qty_available = quants_res.get(product_id, 0.0) - moves_in_res_past.get(product_id,
                                                                                        0.0) + moves_out_res_past.get(
                    product_id, 0.0)
            else:
                qty_available = quants_res.get(product_id, 0.0)
            res[product_id]['qty_available'] = float_round(qty_available, precision_rounding=rounding)
            res[product_id]['incoming_qty'] = float_round(moves_in_res.get(product_id, 0.0),
                                                          precision_rounding=rounding)
            res[product_id]['outgoing_qty'] = float_round(moves_out_res.get(product_id, 0.0),
                                                          precision_rounding=rounding)
            res[product_id]['virtual_available'] = float_round(
                qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'],
                precision_rounding=rounding)
        return res

    def get_lines(self, data):
        product_res = self.env['product.product'].search([('type', '=', 'product')])
        category_lst = []
        if data['category']:
            for cate in data['category']:
                if cate.id not in category_lst:
                    category_lst.append(cate.id)
                for child in cate.child_id:
                    if child.id not in category_lst:
                        category_lst.append(child.id)
        if len(category_lst) > 0:
            product_res = self.env['product.product'].search(
                [('categ_id', 'in', category_lst), ('type', '=', 'product')])
        lines = []
        net_sale = 0.0
        net_return = 0.0
        net_sale_amount = 0.0
        net_return_amount = 0.0
        all_data = {}
        for product in product_res:
            sales_value = 0.0
            sales_return = 0.0
            sales_price = 0.0
            incoming = 0.0
            opening = self._compute_quantities_product_quant_dic(self._context.get('lot_id'),
                                                                 self._context.get('owner_id'),
                                                                 self._context.get('package_id'), False,
                                                                 data['start_date'], product, data)


            # ending = self._compute_quantities_product_quant_dic(False,data['end_date'],product,data)

            # if opening[product.id]['qty_available'] > 0 :

            custom_domain = []
            if data['company_id']:
                obj = self.env['res.company'].search([('name', '=', data['company_id'])])

                custom_domain.append(('company_id', '=', obj.id))

            if data['warehouse']:
                warehouse_lst = [a.id for a in data['warehouse']]
                custom_domain.append(('picking_id.picking_type_id.warehouse_id', 'in', warehouse_lst))

            stock_move_line = self.env['stock.move'].search([
                                                                ('product_id', '=', product.id),
                                                                ('picking_id.date_done', '>=', data['start_date']),
                                                                ('picking_id.date_done', "<=", data['end_date']),
                                                                ('state', '=', 'done')
                                                            ] + custom_domain)

            for move in stock_move_line:
                if move.picking_id.picking_type_id.code == "outgoing":
                    if data['location_id']:
                        locations_lst = [data['location_id'].id]
                        for i in data['location_id'].child_ids:
                            locations_lst.append(i.id)
                        if move.location_id.id in locations_lst:
                            sales_value = sales_value + move.product_uom_qty
                            net_sale = net_sale + move.product_uom_qty
                        if move.location_dest_id.id in locations_lst:
                            sales_return = sales_return + move.product_uom_qty
                            net_return = net_return + move.product_uom_qty
                    else:
                        sales_value = sales_value + move.product_uom_qty
                        net_sale = net_sale + move.product_uom_qty
                if move.picking_id.picking_type_id.code == "incoming":
                    if data['location_id']:
                        locations_lst = [data['location_id'].id]
                        for i in data['location_id'].child_ids:
                            locations_lst.append(i.id)
                        if move.location_dest_id.id in locations_lst:
                            incoming = incoming + move.product_uom_qty
                    else:
                        incoming = incoming + move.product_uom_qty
            inventory_domain = [
                ('date', '>=', data['start_date']),
                ('date', "<=", data['end_date'])
            ]
            stock_pick_lines = self.env['stock.move'].search(
                [('location_id.usage', '=', 'inventory'), ('product_id.id', '=', product.id)] + inventory_domain)
            stock_internal_lines = self.env['stock.move'].search(
                [('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'internal'),
                 ('product_id.id', '=', product.id)] + inventory_domain)
            stock_internal_lines_2 = self.env['stock.move'].search(
                [('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'inventory'),
                 ('product_id.id', '=', product.id)] + inventory_domain)
            adjust = 0
            internal = 0
            plus_picking = 0
            total_adjust = 0
            min_picking = 0
            plus_min = 0
            if stock_pick_lines:
                for invent in stock_pick_lines:
                    adjust += invent.product_uom_qty
                    plus_picking = invent.id

            if stock_internal_lines_2:
                for inter in stock_internal_lines_2:
                    plus_min += -int(inter.product_uom_qty)
                    min_picking = inter.id

            total_adjust = adjust + plus_min
            # if plus_picking > min_picking:
            #     picking_id = self.env['stock.move'].browse(plus_picking)
            #     adjust = picking_id.product_uom_qty
            # else :
            #     picking_id = self.env['stock.move'].browse(min_picking)
            #     adjust = -int(picking_id.product_uom_qty)

            if stock_internal_lines:
                for inter in stock_internal_lines:
                    internal = inter.product_uom_qty

            ending_bal = opening[product.id]['qty_available'] - sales_value + incoming + total_adjust
            net_sale_amount += sales_value * product.lst_price or 0
            net_return_amount += sales_return * product.lst_price or 0

            vals = {
                'sku': product.default_code or '',
                'name': product.name or '',
                'category': product.categ_id.name or '',
                'cost_price': product.standard_price or 0,
                'old_barcode': product.old_barcode,
                'barcode': product.barcode,
                'sale_price': product.lst_price,
                'available': 0,
                'virtual': 0,
                'incoming': incoming or 0,
                'outgoing': total_adjust,
                # 'adjust':  adjust,
                # 'min_adjust':  plus_min,
                'net_on_hand': ending_bal,
                'total_value': ending_bal * product.standard_price or 0,
                'sale_value_price': (sales_value * product.lst_price) - (sales_return * product.lst_price) or 0,
                'sale_value': sales_value or 0,
                'sale_return': sales_return or 0,
                'purchase_value': 0,
                'beginning': opening[product.id]['qty_available'] or 0,
                'internal': internal,
            }
            lines.append(vals)
        all_data = {
            'data': lines,
            'net_sale': net_sale,
            'net_return': net_return,
            'net_sale_amount': net_sale_amount,
            'net_return_amount': net_return_amount,
        }

        return all_data

    def get_data(self, data):
        print(222222222222222222)
        product_res = self.env['product.product'].search([('type', '=', 'product')])
        category_lst = []
        if data['category']:

            for cate in data['category']:
                if cate.id not in category_lst:
                    category_lst.append(cate.id)

                for child in cate.child_id:
                    if child.id not in category_lst:
                        category_lst.append(child.id)

        if len(category_lst) > 0:
            product_res = self.env['product.product'].search(
                [('categ_id', 'in', category_lst), ('type', '=', 'product')])

        lines = []
        net_sale = 0.0
        net_return = 0.0
        net_sale_amount = 0.0
        net_return_amount = 0.0
        all_data = {}
        for product in product_res:
            # if product.create_date.date() <= data['start_date'] :

            sales_value = 0.0
            sales_return = 0.0
            sales_price = 0.0
            incoming = 0.0
            opening = self._compute_quantities_product_quant_dic(self._context.get('lot_id'),
                                                                 self._context.get('owner_id'),
                                                                 self._context.get('package_id'), False,
                                                                 data['start_date'], product, data)

            # ending = self._compute_quantities_product_quant_dic(False,data['end_date'],product,data)

            # if opening[product.id]['qty_available'] > 0 :

            # print ("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",ending)
            custom_domain = []
            if data['company_id']:
                obj = self.env['res.company'].search([('name', '=', data['company_id'])])

                custom_domain.append(('company_id', '=', obj.id))

            if data['warehouse']:
                warehouse_lst = [a.id for a in data['warehouse']]
                custom_domain.append(('picking_id.picking_type_id.warehouse_id', 'in', warehouse_lst))

            stock_move_line = self.env['stock.move'].search([
                                                                ('product_id', '=', product.id),
                                                                ('picking_id.date_done', '>=', data['start_date']),
                                                                ('picking_id.date_done', "<=", data['end_date']),
                                                                ('state', '=', 'done')
                                                            ] + custom_domain)

            for move in stock_move_line:
                if move.picking_id.picking_type_id.code == "outgoing":
                    if data['location_id']:
                        locations_lst = [data['location_id'].id]
                        for i in data['location_id'].child_ids:
                            locations_lst.append(i.id)
                        if move.location_id.id in locations_lst:
                            sales_value = sales_value + move.product_uom_qty
                            net_sale = net_sale + move.product_uom_qty
                        if move.location_dest_id.id in locations_lst:
                            sales_return = sales_return + move.product_uom_qty
                            net_return = net_return + move.product_uom_qty

                    else:

                        sales_value = sales_value + move.product_uom_qty
                        net_sale = net_sale + move.product_uom_qty

                if move.picking_id.picking_type_id.code == "incoming":
                    if data['location_id']:
                        locations_lst = [data['location_id'].id]
                        for i in data['location_id'].child_ids:
                            locations_lst.append(i.id)
                        if move.location_dest_id.id in locations_lst:
                            incoming = incoming + move.product_uom_qty

                    else:

                        incoming = incoming + move.product_uom_qty

            inventory_domain = [
                ('date', '>=', data['start_date']),
                ('date', "<=", data['end_date'])
            ]
            stock_pick_lines = self.env['stock.move'].search(
                [('location_id.usage', '=', 'inventory'), ('product_id.id', '=', product.id)] + inventory_domain)
            stock_internal_lines = self.env['stock.move'].search(
                [('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'internal'),
                 ('product_id.id', '=', product.id)] + inventory_domain)
            stock_internal_lines_2 = self.env['stock.move'].search(
                [('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'inventory'),
                 ('product_id.id', '=', product.id)] + inventory_domain)
            adjust = 0
            internal = 0
            plus_picking = 0

            if stock_pick_lines:
                for invent in stock_pick_lines:
                    adjust = invent.product_uom_qty
                    plus_picking = invent.id

            min_picking = 0
            if stock_internal_lines_2:
                for inter in stock_internal_lines_2:
                    plus_min = inter.product_uom_qty
                    min_picking = inter.id

            if plus_picking > min_picking:
                picking_id = self.env['stock.move'].browse(plus_picking)
                adjust = picking_id.product_uom_qty

            else:
                picking_id = self.env['stock.move'].browse(min_picking)
                adjust = -int(picking_id.product_uom_qty)
            if stock_internal_lines:

                for inter in stock_internal_lines:
                    internal = inter.product_uom_qty

            ending_bal = opening[product.id]['qty_available'] - sales_value + incoming + adjust

            flag = False
            for i in lines:
                if i['category'] == product.categ_id.name:
                    i['beginning'] = i['beginning'] + opening[product.id]['qty_available']
                    i['internal'] = i['internal'] + internal
                    i['incoming'] = i['incoming'] + incoming
                    i['sale_value'] = i['sale_value'] + sales_value
                    i['outgoing'] = i['outgoing'] + adjust
                    i['net_on_hand'] = i['net_on_hand'] + ending_bal
                    i['total_value'] = i['total_value'] + (ending_bal * product.standard_price)
                    flag = True
            if flag == False:
                vals = {
                    'category': product.categ_id.name,
                    'cost_price': product.standard_price or 0,
                    'old_barcode': product.old_barcode,
                    'barcode': product.barcode,
                    'sale_price': product.lst_price,
                    'available': 0,
                    'virtual': 0,
                    'incoming': incoming or 0,
                    'outgoing': adjust or 0,
                    'net_on_hand': ending_bal or 0,
                    'total_value': ending_bal * product.standard_price or 0,
                    'sale_value_price': (sales_value * product.lst_price) - (sales_return * product.lst_price) or 0,
                    'sale_value': sales_value or 0,
                    'sale_return': sales_return or 0,
                    'purchase_value': 0,
                    'beginning': opening[product.id]['qty_available'] or 0,
                    'internal': internal or 0,
                }
                lines.append(vals)

        all_data = {
            'data': lines,
            'net_sale': net_sale,
            'net_return': net_return,
            'net_sale_amount': net_sale_amount,
            'net_return_amount': net_return_amount,
        }

        return all_data


class sale_day_book_report_excel(models.TransientModel):
    _name = "sale.day.book.report.excel"

    excel_file = fields.Binary('Excel Report For Sale Book Day ')
    file_name = fields.Char('Excel File', size=64)

