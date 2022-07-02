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
            self.external_id = str(data.module) + "." + data.name

    @api.one
    def get_model(self):
        self.model__id = self.env['ir.model'].search([['model', '=', self._name]]).id

    # ######################
    # ####   Childes  ######
    @api.model
    def _get_child(self, id, parent_field="parent_id"):
        childes = self.search([[parent_field, '=', id]])
        res = []
        for c in childes:
            res.append(c.id)
            cc = self._get_child(c.id, parent_field)
            res += cc
        return res

    @api.model
    def get_childes(self):
        # return : list of ids
        return self._get_child(self.id, parent_field="parent_id")

    # ######################
    # ####   Parents  ######
    @api.model
    def all_parents_(self):
        # return : list of ids
        return self._get_parents(self.id, self._name)

    @api.model
    def _get_parents(self, id, model, parent_field='parent_id'):
        model = self.env[model]
        res = []
        rec = model.browse(id)
        parent = getattr(rec, parent_field)
        while getattr(parent, 'id'):
            res.append(parent.id)
            parent = getattr(parent, parent_field)
        return res


# class AccountMove(models.Model, base):
#     _inherit = "account.move"


class ResGroup(models.Model, base):
    _inherit = "res.groups"
    external_id = char_field('External ID', compute="_get_external_id")


class AccessRights(models.Model, base):
    _inherit = "ir.model.access"
    external_id = char_field('External ID', compute="_get_external_id")


class IrModelField(models.Model):
    _inherit = "ir.model.fields"
    model_id_ = m2o_field('ir.model', compute='get_model')

    @api.one
    def get_model(self):
        relation_model = self.relation or False
        model = self.env['ir.model'].search([['model', '=', relation_model]])
        if model:
            self.model_id_ = model.id


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.one
    def name_get(self):
        ctx = self._context.copy()
        if ctx.get('special_name', False):
            return (self.id, "%s [%s]" % (self.model, self.name))
        return (self.id, self.name)


class IrUiMenu(models.Model, base):
    _inherit = "ir.ui.menu"
    external_id = char_field('External ID', compute="_get_external_id")
    action_id = m2o_field('ir.actions.act_window', 'Action', compute="nothing")

    @api.one
    @api.depends()
    def nothing(self):
        pass


class IrAction(models.Model):
    _inherit = "ir.actions.act_window"

    menu_ids = o2m_field('ir.ui.menu', 'action_id', 'Menus', compute="_get_menus")

    @api.one
    @api.depends()
    def _get_menus(self):
        menus = self.env['ir.ui.menu'].search([['action', '=', "ir.actions.act_window,%s" % self.id]])
        self.menu_ids = [m.id for m in menus]


class Views(models.Model):
    _inherit = "ir.ui.view"
    model_id = m2o_field('ir.model', 'Model', compute='get_model')

    @api.one
    @api.depends('model')
    def get_model(self):
        model = self.env['ir.model'].search([['model', '=', self.model]])
        self.model_id = model.id
