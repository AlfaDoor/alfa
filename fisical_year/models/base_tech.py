# -*- coding: utf-8 -*-

from odoo import models, fields, api

selection_field = fields.Selection
char_field = fields.Char
m2o_field = fields.Many2one
o2m_field = fields.One2many
bool_field = fields.Boolean
html_field = fields.Html
text_field = fields.Text
integer_field = fields.Integer
float_field = fields.Float
date_field = fields.Date
datetime_field = fields.Datetime


class base():
    model__id = m2o_field('ir.model', compute='get_model', string='Model')
    external_id = char_field('External ID', compute="get_external_id")

    @api.one
    def _get_external_id(self):
        ir_model_data = self.env['ir.model.data']
        data = ir_model_data.search([('model', '=', self._name), ('res_id', '=', self.id)])
        if data:
            self.external_id = str(data.module)+"."+data.name

    @api.one
    def get_model(self):
        self.model__id = self.env['ir.model'].search([['model', '=', self._name]]).id

class AccountMove(models.Model, base):
    _inherit = "account.move"

class IrUiMenu(models.Model, base):
    _inherit = "ir.ui.menu"

    external_id = char_field('External ID', compute="_get_external_id")
