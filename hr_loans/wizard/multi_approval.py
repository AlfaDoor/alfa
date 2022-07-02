# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError

class MultiRewardReviewWiz(models.TransientModel):
    _name = 'multi.rewards.review.wizard'
    _description = 'Multi Rewards Review Wizard'

    @api.multi
    def multi_review(self):
        reward_idsx = self.env['hr.employee.rewards'].browse(self._context.get('active_ids'))
        for rewardsx in reward_idsx:
            if rewardsx.state != 'new':
                raise UserError(_("Selected Reward(s) cannot be process by HR as they are not in 'New' state."))
            rewardsx.review()
        return {'type': 'ir.actions.act_window_close'}

class MultiRewardConfirmWiz(models.TransientModel):
    _name = 'multi.rewards.confirm.wizard'
    _description = 'Multi Rewards Confirm Wizard'

    @api.multi
    def multi_confirm(self):
        reward_idsxx = self.env['hr.employee.rewards'].browse(self._context.get('active_ids'))
        for rewardsxx in reward_idsxx:
            if rewardsxx.state != 'reviewed':
                raise UserError(_("Selected Reward(s) cannot be process by HR as they are not in 'Review' state."))
            rewardsxx.confirm()
        return {'type': 'ir.actions.act_window_close'}


class MultiRewardResetWiz(models.TransientModel):
    _name = 'multi.rewards.reset.wizard'
    _description = 'Multi Rewards Reset Wizard'

    @api.multi
    def multi_reset(self):
        reward_idsxxx = self.env['hr.employee.rewards'].browse(self._context.get('active_ids'))
        for rewardsxxx in reward_idsxxx:
            if rewardsxxx.state != 'confirmed':
                raise UserError(_("Selected Reward(s) cannot be process by HR as they are not in 'Confirm' state."))
            rewardsxxx.reset()
        return {'type': 'ir.actions.act_window_close'}


class MultiDeductionReviewWiz(models.TransientModel):
    _name = 'multi.deduction.review.wizard'
    _description = 'Multi Deduction Review Wizard'

    @api.multi
    def multi_review(self):
        deduction_idsx = self.env['employee.deductions.violations'].browse(self._context.get('active_ids'))
        for deductionx in deduction_idsx:
            if deductionx.state != 'new':
                raise UserError(_("Selected Reward(s) cannot be process by HR as they are not in 'New' state."))
            deductionx.review()
        return {'type': 'ir.actions.act_window_close'}

class MultiDeductionConfirmWiz(models.TransientModel):
    _name = 'multi.deduction.confirm.wizard'
    _description = 'Multi Deduction Confirm Wizard'

    @api.multi
    def multi_confirm(self):
        deduction_idsxx = self.env['employee.deductions.violations'].browse(self._context.get('active_ids'))
        for deductionxx in deduction_idsxx:
            if deductionxx.state != 'reviewed':
                raise UserError(_("Selected Reward(s) cannot be process by HR as they are not in 'Review' state."))
            deductionxx.confirm()
        return {'type': 'ir.actions.act_window_close'}


class MultiDeductionResetWiz(models.TransientModel):
    _name = 'multi.deduction.reset.wizard'
    _description = 'Multi Deduction Reset Wizard'

    @api.multi
    def multi_reset(self):
        deduction_idsxxx = self.env['employee.deductions.violations'].browse(self._context.get('active_ids'))
        for deductionxxx in deduction_idsxxx:
            if deductionxxx.state != 'confirmed':
                raise UserError(_("Selected Reward(s) cannot be process by HR as they are not in 'Confirm' state."))
            deductionxxx.set_draft()
        return {'type': 'ir.actions.act_window_close'}


