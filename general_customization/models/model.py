import logging
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError

class InheritCategory(models.Model):
    _inherit = 'product.category'

    reference_code = fields.Char('Reference Code')

class InheritProduct(models.Model):
    _inherit = 'product.template'

    out_of_stock = fields.Boolean('Qty AVL',default=False,compute='_count_stock')


    @api.one
    def _count_stock(self):
        if self.qty_available:
            if self.qty_warning_out_stock >= self.qty_available:
                self.out_of_stock = True
        else:
            self.out_of_stock = False

    def generate_reference(self):
        if not self.categ_id.reference_code:
            raise ValidationError(_('Reference Code is not defined on %s')%self.categ_id.display_name)
        if not self.default_code:
            self.default_code = self.categ_id.reference_code + self.env['ir.sequence'].next_by_code('category.sequence')

class MultiReferenceGenWiz(models.TransientModel):
    _name = 'multi.internal.reference.wizard'
    _description = 'Multi Internal Reference Wizard'

    @api.multi
    def multi_internal_ref(self):
        product_ids = self.env['product.template'].browse(self._context.get('active_ids'))
        for product in product_ids:
            product.generate_reference()
        return {'type': 'ir.actions.act_window_close'}



