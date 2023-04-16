# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError

class MultiExcuseConfirmWiz(models.TransientModel):
    _name = 'multi.excuse.confirm.wizard'
    _description = 'Multi Excuse Confirm Wizard'

    @api.multi
    def multi_confirm(self):
        excuse_idsxx = self.env['hr.excuse'].browse(self._context.get('active_ids'))
        for excusexx in excuse_idsxx:
            if excusexx.state != 'draft':
                raise UserError(_("Selected Excuse(s) cannot be process by HR as they are not in 'Draft' state."))
            excusexx.confirm()
        return {'type': 'ir.actions.act_window_close'}

class MultiExcueDraftWiz(models.TransientModel):
    _name = 'multi.excuse.draft.wizard'
    _description = 'Multi Excuse Draft Wizard'

    @api.multi
    def multi_draft(self):
        excuse_idsx = self.env['hr.excuse'].browse(self._context.get('active_ids'))
        for excusex in excuse_idsx:
            if excusex.state != 'confirmed':
                raise UserError(_("Selected Reward(s) cannot be process by HR as they are not in 'Confirmed' state."))
            excusex.reset()
        return {'type': 'ir.actions.act_window_close'}

