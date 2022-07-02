# -*- coding: utf-8 -*-

from odoo import models, fields, api , exceptions, _
# import openerp.addons.decimal_precision as dp

class res_user(models.Model):
    _inherit = 'res.users'

    def show_dialogue(self,message,model_name,method_name,record_id):
        ctx = {'default_message': message,'default_model_name': model_name,'default_method_name': method_name,'default_object_id': record_id}
        return {
            'domain': "[]",
            'name': _('Confirmation Box'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'confirmation.box',
            'view_id': self.env.ref('custom_confirmation_box.confirmation_box').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }