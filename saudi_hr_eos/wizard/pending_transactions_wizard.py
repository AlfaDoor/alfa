# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api , exceptions,_



class pending_transactions_wizard(models.TransientModel):
    _name = "pending.transactions.wizard"

    line_ids = fields.One2many('pending.transactions.wizard.line','wizard_id','dssff')


    @api.multi
    def apply(self):
        eos = self.env['employee.eos'].browse(self._context.get('active_id', False))
        return eos.action_approve_continue()

    @api.multi
    def apply_final(self):
        for rec in self:
            eos = self.env['employee.eos'].browse(self._context.get('active_id', False))
            return eos.action_final_approve_continue()


class pending_transactions_wizard_line(models.TransientModel):
    _name = "pending.transactions.wizard.line"

    wizard_id = fields.Many2one('pending.transactions.wizard')
    name = fields.Char('Transaction')
    model = fields.Char('Model')
    domain = fields.Char('Domain')
    count = fields.Integer('Pending Transaction')

    @api.multi
    def open_pending(self):
        domain_str = self.domain
        if domain_str == '[]':
            domain_list = []
        else:
            remove_brackets = domain_str.strip('[')
            remove_brackets = remove_brackets.strip(']')
            remove_brackets = remove_brackets.strip(' ')
            domain_list = remove_brackets.split(',')
        return {
            'domain': [('id','in',domain_list)],
            'name': _('Pending Transactions For %s') %(self.name),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': self.model,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
