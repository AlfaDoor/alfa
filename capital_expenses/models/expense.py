# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from .base_tech import *
import logging
import calendar
from datetime import datetime


def days_between(d1, d2):
    d1 = datetime.strptime(d1, "%Y-%m-%d")
    d2 = datetime.strptime(d2, "%Y-%m-%d")
    return (d2 - d1).days + 1


class expenses_transaction(models.Model):
    _name = "capital.expense"
    _description = "Capital Expenses"
    _rec_name = "asset_id"

    amount = fields.Float('Expense amount')
    asset_id = fields.Many2one('account.asset.asset', 'Asset')
    type = fields.Selection([
        ('Increase Asset Age', 'Increase Asset Age'),
        ('Increase Asset Capacity', 'Increase Asset Capacity'),
        ('Both', 'Both'),
    ], string='Type')
    increase_age = fields.Integer('Increase In Age / Month')
    date = fields.Date('Expense date')
    effect_date = fields.Date('Effect Date')
    state = fields.Selection([('new', 'New'), ('reviewed', 'Reviewed'), ('approved', 'Approved'), ], string='Status', default='new')

    @api.one
    def action_review(self):
        self.state = 'reviewed'

    @api.one
    def action_approve(self):
        if self.asset_id:
            self.asset_id.method_number += self.increase_age
            self.asset_id.value += self.amount
            self.asset_id.compute_depreciation_board()
        self.state = 'approved'

class AccountAsset(models.Model):
    _inherit = 'account.asset.asset'


    expenses_ids = fields.One2many('capital.expense', 'asset_id', 'Capital Expenses')
    total_capital = fields.Float('Total Capital Expenses', compute='_compute_total_capital')

    @api.one
    @api.depends('expenses_ids')
    def _compute_total_capital(self):
        self.total_capital = sum([e.amount for e in self.expenses_ids])
