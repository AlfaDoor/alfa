# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo import time
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, AccessError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('first_approve', 'First Approval'),
        ('second_approve', 'Second Approval'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')


    @api.multi
    def action_firstapproval(self):
        return self.write({'state': 'first_approve'})

    @api.multi
    def action_secondapproval(self):
        return self.write({'state': 'second_approve'})

    @api.multi
    def button_confirm(self):
        for order in self:
            if order.state not in ['second_approve']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step'\
                    or (order.company_id.po_double_validation == 'two_step'\
                        and order.amount_total < self.env.user.company_id.currency_id._convert(
                            order.company_id.po_double_validation_amount, order.currency_id, order.company_id, order.date_order or fields.Date.today()))\
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
        return True

