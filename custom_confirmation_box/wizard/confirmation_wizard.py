# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api , exceptions



class confirmation_box(models.TransientModel):
    _name = "confirmation.box"

    message = fields.Text(string="Message")
    model_name = fields.Char(string="Model")
    object_id = fields.Char(string="Object Id")
    method_name = fields.Char(string="Method To Execute")



    @api.multi
    def accept(self):
        for rec in self:
            model_object = self.env[rec.model_name].browse(int(rec.object_id))
            return  getattr(model_object, self.method_name)()


