# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from werkzeug import url_encode

_logger = logging.getLogger(__name__)


class RollOverWizard(models.TransientModel):

    _name = "roll.over.wizard"
    _description = "Roll Over Wizard"

    select_action = fields.Selection([('rollover','Rollover'),('refund','Refund')],default='rollover' ,string="Action", required=True)
    account_id = fields.Many2one('account.account', string='Account', required=True, index=True)

    @api.multi
    def action_validate(self):
        self.ensure_one()
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        vat_return = self.env['uae.vat.return'].browse(active_ids)
        if self.select_action == 'refund':
            vat_return.tax_validate()
            return {'type': 'ir.actions.act_window_close'}
        elif self.select_action == 'rollover':
            vat_return.write({'tax_suspense_account_id':self.account_id.id})
            vat_return.roll_over()
            return {'type': 'ir.actions.act_window_close'}
        else:
            return {'type': 'ir.actions.act_window_close'}