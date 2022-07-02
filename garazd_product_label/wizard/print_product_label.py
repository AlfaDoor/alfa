# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning

class InheritStockQuant(models.Model):
    _inherit = 'stock.quant.package'

    total_quantity = fields.Float(compute='quantity_total')

    @api.depends('quant_ids.quantity')
    def quantity_total(self):
        for qty in self:
            total_qty = 0.0
            for line in qty.quant_ids:
                    total_qty += line.quantity
            qty.update({
                'total_quantity': total_qty,
                })


class PrintProductLabel(models.TransientModel):
    _name = "print.product.label"
    _description = 'Product Labels Wizard'

    # TODO:  tests - try_report_action

    @api.model
    def _get_products(self):
        print('Enter Product')
        res = []
        if self._context.get('active_model') == 'product.template':
            products = self.env[self._context.get('active_model')].browse(self._context.get('default_product_ids'))
            for product in products:
                label = self.env['print.product.label.line'].create({
                    'product_id': product.product_variant_id.id,
                })
                res.append(label.id)
        elif self._context.get('active_model') == 'product.product':
            products = self.env[self._context.get('active_model')].browse(self._context.get('default_product_ids'))
            for product in products:
                label = self.env['print.product.label.line'].create({
                    'product_id': product.id,
                })
                res.append(label.id)
        return res

    name = fields.Char(
        'Name',
        default='Print product labels',
    )
    message = fields.Char(
        'Message',
        readonly=True,
    )
    output = fields.Selection(
        selection=[('pdf', 'PDF')],
        string='Print to',
        default='pdf',
    )
    label_ids = fields.One2many(
        comodel_name='print.product.label.line',
        inverse_name='wizard_id',
        string='Labels for Products',
        default=_get_products,
    )
    template = fields.Selection(
        selection=[('garazd_product_label.report_product_label_A4_57x35', 'Label 50x25mm')],
        string='Label template',
        default='garazd_product_label.report_product_label_A4_57x35',
    )
    qty_per_product = fields.Integer(
        string='Label quantity per product',
        default=1,
    )
    humanreadable = fields.Boolean(
        string='Print digital code of barcode',
        default=True,
    )

    @api.multi
    def action_print(self):
        """ Print labels """
        print('Action Print Product')
        self.ensure_one()
        labels = self.label_ids.filtered(lambda x: x.selected == True and x.qty > 0).mapped('id')
        if not labels:
            raise Warning(_('Nothing to print, set the quantity of labels in the table.'))
        return self.env.ref(self.template).with_context(discard_logo_check=True).report_action(labels)

    @api.multi
    def action_set_qty(self):
        self.ensure_one()
        self.label_ids.write({'qty': self.qty_per_product})

    @api.multi
    def action_restore_initial_qty(self):
        self.ensure_one()
        for label in self.label_ids:
            if label.qty_initial:
                label.update({'qty': label.qty_initial})


class PrintPackageLabel(models.TransientModel):
    _name = "print.package.label"
    _description = 'Package Labels Wizard'

    # TODO:  tests - try_report_action

    @api.model
    def _get_packages(self):
        print('Enter Package')
        res = []
        if self._context.get('active_model') == 'stock.quant.package':
            products = self.env[self._context.get('active_model')].browse(self._context.get('default_package_ids'))
            for product in products:
                label = self.env['print.package.label.line'].create({
                    'package_id': product.id,
                })
                res.append(label.id)
        return res

    name = fields.Char(
        'Name',
        default='Print Package labels',
    )
    message = fields.Char(
        'Message',
        readonly=True,
    )
    output = fields.Selection(
        selection=[('pdf', 'PDF')],
        string='Print to',
        default='pdf',
    )
    package_label_ids = fields.One2many(
        comodel_name='print.package.label.line',
        inverse_name='wizard_package_id',
        string='Labels for Package',
        default=_get_packages,
    )
    template_pac = fields.Selection(
        selection=[('garazd_product_label.report_package_label_A4_57x35', 'Label 50x25mm')],
        string='Label template',
        default='garazd_product_label.report_package_label_A4_57x35',
    )
    qty_per_product = fields.Integer(
        string='Label quantity per product',
        default=1,
    )
    humanreadable = fields.Boolean(
        string='Print digital code of barcode',
        default=True,
    )

    @api.multi
    def action_print_package(self):
        """ Print labels """
        print('Action Print Package')
        self.ensure_one()
        labels = self.package_label_ids.filtered(lambda x: x.selected == True and x.qty > 0).mapped('id')
        print(labels)
        if not labels:
            raise Warning(_('Nothing to print, set the quantity of labels in the table.'))
        print(self.template_pac)
        return self.env.ref(self.template_pac).with_context(discard_logo_check=True).report_action(labels)

    @api.multi
    def action_set_qty(self):
        self.ensure_one()
        self.label_ids.write({'qty': self.qty_per_product})

    @api.multi
    def action_restore_initial_qty(self):
        self.ensure_one()
        for label in self.label_ids:
            if label.qty_initial:
                label.update({'qty': label.qty_initial})
