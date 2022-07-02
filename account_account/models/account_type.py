# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from .base_tech import *
from odoo.exceptions import UserError, ValidationError, QWebException


class AccountType(models.Model, base):
    _inherit = 'account.account.type'

    code = char_field('Code')
    arabic_name = char_field('Arabic name')
    type = selection_field(selection_add=[
        ('other', 'Other'),
        ('view', 'Main account'),
        ('temp', 'Temporary accounts'),
        ('regular', 'Regular')])
    location = selection_field([
        ('current_asset', 'Current asset'),
        ('non_current_asset', 'Non-Current asset'),
        ('current_liabilities', 'Current liabilities'),
        ('non_current_liabilities', 'Non-current liabilities'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expenses'),
        ('temp', 'Temporary accounts'),
    ], string="Location in Financial statement")
    debit_credit = selection_field([
        ('debit', 'debit'),
        ('credit', 'credit'),
        ('temp', 'Temporary'),
    ], string="default Debit / Credit")
    account_count_ = fields.Integer('Number of accounts', compute='get_number_of_account', store=True)
    account_ids = fields.One2many('account.account', 'user_type_id', 'Accounts')

    @api.one
    @api.depends('code', 'type', 'location', 'debit_credit', 'account_ids','name')
    def get_number_of_account(self):
        self.account_count_ = len(self.account_ids)

    _sql_constraints = [
        ('unique_code', 'UNIQUE (code)', _("Code must be unique"))
    ]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        arabic_chars = 'اأإبتثحخجدذرزوؤءئسشصضطظعغفقنهكوملىيﻻﻵة'
        arabic_lang = False
        if name:
            # for char in name:
            #     if char in arabic_chars:
            #         arabic_lang = True
            #         break
            domain = ['|', '|', '|',
                      ('code', 'ilike', name),
                      ('arabic_name', 'ilike', name),
                      ('name', 'ilike', name),
                      ('location', 'ilike', name),
                      ]
        types = self.search(domain + args, limit=limit, order='code')
        return types.name_get(arabic_lang)

    @api.multi
    def name_get(self, arab=False):
        result = []
        for account in self:
            name = str((account.arabic_name or account.name) if arab else account.name)
            result.append((account.id, name))
        return result
