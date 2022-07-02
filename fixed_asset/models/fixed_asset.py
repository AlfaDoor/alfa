# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, tools, _
from datetime import date, datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero
from .base_tech import *
from odoo.exceptions import ValidationError


class fake_model():
    id = False


class Assets(models.Model):
    _inherit = 'account.asset.asset'

    purchase_date = date_field('Purchase date')
    depreciation = float_field('Depreciation', compute='get_depreciation')
    purchase_price = float_field('Purchase Price')
    last_depreciation = float_field('Last Depreciation')
    invoice_line_id = m2o_field('account.invoice.line', 'Invoice line')
    analytic_account_id = m2o_field('account.analytic.account', 'Analytic account')
    sell_price = float_field('Sell price')
    profit_account_id = m2o_field('account.account', 'Profit/Loss account')
    loss_profit_amount = float_field('Loss/Profit amount', compute='get_loss_profit_amount')
    cash_account_id = m2o_field('account.account', 'Cash/Bank account', )
    total_depreciation = float_field('Total depreciation', compute='get_total_dep')
    close_move_id = m2o_field('account.move', 'Close journal entry')

    @api.one
    @api.depends('depreciation_line_ids')
    def get_total_dep(self):
        total_amount = 0.0
        for line in self.depreciation_line_ids:
            if line.move_check:
                total_amount += line.amount
        self.total_depreciation = total_amount

    @api.one
    @api.depends('sell_price', 'value_residual')
    def get_loss_profit_amount(self):
        self.loss_profit_amount = self.sell_price - self.value_residual - self.salvage_value

    @api.one
    @api.depends('depreciation_line_ids')
    def get_depreciation(self):
        self.depreciation = sum([l.amount for l in self.depreciation_line_ids if l.move_check])

    @api.model
    def create(self, vals):
        invoice_line_id = self._context.get('invoice_line_id', False)
        if invoice_line_id:
            vals['invoice_line_id'] = invoice_line_id.id
            vals['analytic_account_id'] = invoice_line_id.account_analytic_id.id
        return super(Assets, self).create(vals)

    @api.multi
    def set_to_close(self):
        res = super(Assets, self.with_context(dict(self._context, dont_create_move=True))).set_to_close()

        depreciation_date = fields.Date.context_today(self)
        company_currency = self.company_id.currency_id
        current_currency = self.currency_id
        sign = (self.category_id.journal_id.type == 'purchase' or self.category_id.journal_id.type == 'sale' and 1) or -1
        asset_name = self.name
        reference = self.code
        journal_id = self.category_id.journal_id.id
        partner_id = self.partner_id.id
        categ_type = self.category_id.type
        lines = []

        # Asset account
        move_line_1 = {
            'name': asset_name,
            'account_id': self.category_id.account_asset_id.id,
            'debit': 0.0,
            'credit': self.value,
            'journal_id': journal_id,
            'partner_id': partner_id,
            'currency_id': company_currency != current_currency and current_currency.id or False,
            'amount_currency': company_currency != current_currency and -1 * self.value or 0.0,
            'analytic_account_id': self.category_id.account_analytic_id.id if categ_type == 'sale' else False,
            'date': depreciation_date,
        }
        lines.append((0, 0, move_line_1))

        # depriciation account
        move_line_2 = {
            'name': asset_name,
            'account_id': self.category_id.account_depreciation_id.id,
            'debit': self.total_depreciation,
            'credit': 0.0,
            'journal_id': journal_id,
            'partner_id': partner_id,
            'currency_id': company_currency != current_currency and current_currency.id or False,
            'amount_currency': company_currency != current_currency and -1 * self.total_depreciation or 0.0,
            'analytic_account_id': self.category_id.account_analytic_id.id if categ_type == 'purchase' else False,
            'date': depreciation_date,
        }
        lines.append((0, 0, move_line_2))

        # Bank/Cash account
        if self.sell_price:
            move_line_3 = {
                'name': asset_name,
                'account_id': self.cash_account_id.id,
                'credit': 0,
                'debit': self.sell_price,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and sign * self.sell_price or 0.0,
                'analytic_account_id': self.category_id.account_analytic_id.id if categ_type == 'purchase' else False,
                'date': depreciation_date,
            }
            lines.append((0, 0, move_line_3))

        # Profit / Loss account
        if self.loss_profit_amount:
            if not self.profit_account_id:
                raise ValidationError(_("You forgot to select Profit/Loss account !!"))
            move_line_5 = {
                'name': asset_name,
                'account_id': self.profit_account_id.id,
                'credit': self.loss_profit_amount > 0 and self.loss_profit_amount or 0.0,
                'debit': self.loss_profit_amount < 0 and -1 * self.loss_profit_amount or 0.0,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and sign * self.loss_profit_amount or 0.0,
                'analytic_account_id': self.category_id.account_analytic_id.id if categ_type == 'purchase' else False,
                'date': depreciation_date,
            }
            lines.append((0, 0, move_line_5))
        move_vals = {
            'ref': reference,
            'date': depreciation_date or False,
            'journal_id': self.category_id.journal_id.id,
            'line_ids': lines,
            'asset_id': self.id,
        }
        move = self.env['account.move'].create(move_vals)
        self.close_move_id = move.id


class AssetAssetReport(models.Model):
    _inherit = "asset.asset.report"
    # depreciation = float_field('Depreciation')
    purchase_price = float_field('Purchase Price')
    last_depreciation = float_field('Last Depreciation')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'asset_asset_report')
        self._cr.execute("""
            create or replace view asset_asset_report as (
                select
                    min(dl.id) as id,
                    dl.name as name,
                    dl.depreciation_date as depreciation_date,
                    a.date as date,
                    (CASE WHEN dlmin.id = min(dl.id)
                      THEN a.value
                      ELSE 0
                      END) as gross_value,
                    dl.amount as depreciation_value,
                    dl.amount as installment_value,
                    (CASE WHEN dl.move_check
                      THEN dl.amount
                      ELSE 0
                      END) as posted_value,
                    (CASE WHEN NOT dl.move_check
                      THEN dl.amount
                      ELSE 0
                      END) as unposted_value,
                    dl.asset_id as asset_id,
                    dl.move_check as move_check,
                    a.category_id as asset_category_id,
                    a.partner_id as partner_id,
                    a.state as state,
                    a.purchase_price as purchase_price,
                    a.last_depreciation as last_depreciation,
                    count(dl.*) as installment_nbr,
                    count(dl.*) as depreciation_nbr,
                    a.company_id as company_id
                from account_asset_depreciation_line dl
                    left join account_asset_asset a on (dl.asset_id=a.id)
                    left join (select min(d.id) as id,ac.id as ac_id from account_asset_depreciation_line as d inner join account_asset_asset as ac ON (ac.id=d.asset_id) group by ac_id) as dlmin on dlmin.ac_id=a.id
                group by
                    dl.amount,dl.asset_id,dl.depreciation_date,dl.name,
                    a.date, dl.move_check, a.state, a.category_id, a.partner_id, a.company_id,
                    a.value, a.id, a.salvage_value, dlmin.id
        )""")


class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    @api.one
    def create_move(self, post_move=True):
        if self._context.get('dont_create_move', False):
            return fake_model
        ctx = dict(self._context, analytic_account_id=self.asset_id.analytic_account_id.id or self.asset_id.invoice_line_id.id or False)
        res = super(AccountAssetDepreciationLine, self.with_context(ctx)).create_move(post_move=post_move)
        if self._context.get('close', False):
            pass
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def create(self, vals):
        if self._context.get('dont_create_move', False):
            return fake_model
        analytic_account_id = self._context.get('analytic_account_id', False)
        if analytic_account_id and not vals.get('analytic_account_id'):
            vals['analytic_account_id'] = analytic_account_id
        return super(AccountMoveLine, self).create(vals)
