# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from .base_tech import *


class AnalyticAccount(models.Model):
    _name = "analytic.template"
    _inherit = ['mail.thread', ]

    name = char_field('Name')
    code = char_field('Template code')
    analytic_account_ids = m2m_field('account.analytic.account', 'rel_analytic_temp', 'temp_id', 'analytic_id',
                                     'Analytic accounts')
    note = html_field('Notes')
    state = selection_field([('new', 'New'), ('active', 'Active'), ('close', 'Close')], string="Status", default='new',track_visibility='onchange')

    @api.one
    def active(self):
        self.state = 'active'

    @api.one
    def close(self):
        self.state = 'close'

    @api.one
    def reopen(self):
        self.state = 'active'

    @api.model
    def create(self, vals):
        res = super(AnalyticAccount, self).create(vals)
        seq = self.env['ir.sequence'].get('analytic.template')
        res.code = seq
        return res

    @api.one
    def unlink(self):
        if self.state == 'active':
            raise ValidationError(_("You can't delete an active template, to delete it , you have to close it first."))
        return super(AnalyticAccount, self).unlink()

    @api.one
    def copy(selfs):
        raise ValidationError(_("You cannot duplicate analytical template .. you have to create it manually. "))

