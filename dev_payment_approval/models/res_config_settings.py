# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_double_verify = fields.Boolean(string="Second Approval")
    payment_double_validation_amount = fields.Float(string="Minimum Amount")
    payment_triple_verify = fields.Boolean(string="Third Approval")
    payment_triple_validation_amount = fields.Float(string="Minimum Amount")

    @api.model
    def set_values(self):
        ir_param = self.env['ir.config_parameter'].sudo()
        ir_param.set_param('dev_payment_approval.payment_double_verify',
                           self.payment_double_verify)
        ir_param.set_param('dev_payment_approval.'
                           'payment_double_validation_amount',
                           self.payment_double_validation_amount)
        ir_param.set_param('dev_payment_approval.payment_triple_verify',
                           self.payment_triple_verify)
        ir_param.set_param('dev_payment_approval.'
                           'payment_triple_validation_amount',
                           self.payment_triple_validation_amount)
        super(ResConfigSettings, self).set_values()

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ir_param = self.env['ir.config_parameter'].sudo()
        payment_double_verify = ir_param.get_param(
            'dev_payment_approval.payment_double_verify')
        payment_double_validation_amount = ir_param.get_param(
            'dev_payment_approval.payment_double_validation_amount')
        payment_triple_verify = ir_param.get_param(
            'dev_payment_approval.payment_triple_verify')
        payment_triple_validation_amount = ir_param.get_param(
            'dev_payment_approval.payment_triple_validation_amount')
        res.update(
            payment_double_verify=bool(payment_double_verify),
            payment_double_validation_amount=float(
                payment_double_validation_amount),
            payment_triple_verify=bool(payment_triple_verify),
            payment_triple_validation_amount=float(
                payment_triple_validation_amount),
        )
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: