# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, QWebException


# class PaymentConfigSettings(models.TransientModel):
#     _inherit = 'res.config.settings'
#
#     default_sale_inv_seq = fields.Boolean(string='Sales invoice sequence', default_model='account.config.settings')
#     default_purchase_inv_seq = fields.Boolean(string='Purchase invoice sequence', default_model='account.config.settings')
#     default_sale_refund_seq = fields.Boolean(string='sales refund sequence', default_model='account.config.settings')
#     default_purchase_refund_seq = fields.Boolean(string='Purchase refund sequence', default_model='account.config.settings')
#     default_payment_in_seq = fields.Boolean(string='Payment in sequence', default_model='account.config.settings')
#     default_payment_out_seq = fields.Boolean(string='Payment out sequence', default_model='account.config.settings')
#     default_payment_int_seq = fields.Boolean(string='Internal payment sequence', default_model='account.config.settings')
