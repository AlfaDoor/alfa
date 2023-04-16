# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from .base_tech import *

datetime_stamp = "2020-03-30"

from datetime import datetime
def localize_dt(date, to_tz):
    from dateutil import tz
    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz(to_tz)
    utc = date
    if type(date) == str:
        utc = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    utc = utc.replace(tzinfo=from_zone)
    res = utc.astimezone(to_zone)
    return res.strftime('%Y-%m-%d %H:%M:%S')


from odoo import tools
def __(date, is_datetime=False, localize=False,to_tz=False):
    if date:
        try:
            res = date.strftime(is_datetime and "%Y-%m-%d %H:%M:%S" or "%Y-%m-%d")
            if localize:
                res = localize_dt(res,to_tz)
        except:
            datetime.strptime(date, is_datetime and "%Y-%m-%d %H:%M:%S" or "%Y-%m-%d")
            res = date
        return res
    else:
        return False


tools.__ = __
tools.localize_dt = localize_dt



class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    picking_id = m2o_field('stock.picking', 'Picking')

    amount_total_company_signed = fields.Monetary(string='Total(Company Currency)', currency_field='company_currency_id',
                                                  store=True, readonly=True, compute='_compute_amount',
                                                  help="Total amount in the currency of the company, negative for credit notes.")
    amount_total_signed = fields.Monetary(string='Total(Invoice Currency)', currency_field='currency_id',
                                          store=True, readonly=True, compute='_compute_amount',
                                          help="Total amount in the currency of the invoice, negative for credit notes.")

    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()
        for line in res:
            line['name'] = self.env['account.invoice.line'].browse(line['invl_id']).name
        return res

    @api.model
    def line_get_convert(self, line, part):
        res = super(AccountInvoice, self).line_get_convert(line,part)
        res['name'] = line['name']
        return res


class move_line_tags(models.Model):
    _name = 'move.line.tags'

    name = char_field('Name')
    code = char_field('Code', )
    account_id = m2o_field('account.account', 'Account')

    _sql_constraints = [
        ('unique_code', 'unique(code,account_id)', 'Sub account code must be unique per account')
    ]


class BaseConfigSettings():

    @api.one
    def delete_views(self):

        views_fs = [
            ('stock.view_location_form', 'stock/stock_view.xml'),
            ('stock.view_inventory_form_inherit', 'stock_account/stock_account_view.xml'),
            ('product_expiry.view_move_form_expiry', 'product_expiry/product_expiry_view.xml'),
            ('stock.view_production_lot_tree', 'stock/stock_view.xml'),
            ('analytic.view_account_analytic_account_list', 'analytic/views/analytic_view.xml'),
            ('analytic.view_account_analytic_account_form', 'analytic/views/analytic_view.xml'),
            ('account.view_account_type_form', 'account/views/account_view.xml'),
            ('report.external_layout_header', 'report/views/layouts.xml'),
            ('stock_account.view_picking_inherit_form2', 'stock_account/stock_account_view.xml'),
        ]
        for view in views_fs:
            try:
                view_id = self.env.ref(view[0]).id
            except:
                continue
            view_obj = self.env['ir.ui.view']
            view_obj.browse(view_id).arch_fs = view[1]
        return True
        views = [
            'stock.view_location_form',
            'stock.view_inventory_form_inherit',
            'product_expiry.view_move_form_expiry',
            'stock.view_production_lot_tree',
            'analytic.view_account_analytic_account_list',
            'analytic.view_account_analytic_account_form',
            'account.view_account_type_form',
            'report.external_layout_header',
        ]
        for view in views:
            try:
                view_id = self.env.ref(view).id
            except:
                continue
            self.delete_inherits_of(view_id)
            # self.env['ir.ui.view'].browse(view_id).unlink()

    @api.one
    def delete_inherits_of(self, view_id):
        view_obj = self.env['ir.ui.view']
        for child in view_obj.search([['inherit_id', '=', view_id]]):
            self.delete_inherits_of(child.id)
        view_obj.browse(view_id).unlink()


class Partners(models.Model):
    _inherit = "res.partner"

    arabic_name = char_field('Arabic name')
    is_employee = fields.Boolean('Employee')

    @api.model_cr
    def init(self):
        self.set_partner_access()

    @api.model
    def set_partner_access(self):
        partner_access = self.env['ir.model'].search([['model', '=', self._name]]).access_ids
        for access in partner_access:
            if access.group_id == self.env.ref('base_accounting.group_partners', False):
                access.perm_create = True
            else:
                access.perm_create = False


class Company(models.Model):
    _inherit = "res.company"

    transfer_account_id = m2o_field(domain=lambda s: [])


class Move(models.Model):
    _inherit = "account.move"
    payment_id = m2o_field('account.payment')

    # line_data = char_field('Line data', compute='get_line_data', store=True)

    @api.one
    @api.depends()
    def get_line_data(self):
        line_data = ''
        for line in self.line_ids:
            line_data += line.account_id.final_code + ";" + line.account_id.name
            line_data += ";" + line.name + ';'
            line_data += line.partner_id.name or '' + ';'
            line_data += line.analytic_account_id.name or '' + ';'
            line_data += str(line.debit or line.credit or '') + ';'
            line_data += line.analytic_id.name or '' + ';'
            line_data += line.employee_id.display_name or '' + ';'
        self.line_data = line_data

        # @api.v7
        # def init(self, cr):
        #     self._init(cr, SUPERUSER_ID, )

        # @api.model
        # def _init(self):
        #     for move in self.search([('line_data', '=', False)]):
        #         move.get_line_data()


class Employee(models.Model):
    _inherit = "hr.employee"

    related_partner = fields.Many2one('res.partner')

    # @api.model
    # def create(self, vals):
    #     res = super(Employee, self).create(vals)
    #     if not res.related_partner:
    #         partner_id = self.env['res.partner'].create({'name': res.name, 'is_employee': True, })
    #         # print(partner_id)
    #         # print(self.id)
    #         # for rec in self:
    #         #     print(rec)
    #         res.related_partner = partner_id.id
    #     return res

    #
    # class ReportGeneralLedger(models.AbstractModel):
    #     _inherit = 'report.account.report_generalledger'
    #
    #     def _get_account_move_entry(self, accounts, init_balance, sortby, display_account):
    #         """
    #         :param:
    #                 accounts: the recordset of accounts
    #                 init_balance: boolean value of initial_balance
    #                 sortby: sorting by date or partner and journal
    #                 display_account: type of account(receivable, payable and both)
    #
    #         Returns a dictionary of accounts with following key and value {
    #                 'code': account code,
    #                 'name': account name,
    #                 'debit': sum of total debit amount,
    #                 'credit': sum of total credit amount,
    #                 'balance': total balance,
    #                 'amount_currency': sum of amount_currency,
    #                 'move_lines': list of move line
    #         }
    #         """
    #         cr = self.env.cr
    #         MoveLine = self.env['account.move.line']
    #         move_lines = dict(map(lambda x: (x, []), accounts.ids))
    #
    #         custom_where_params = self.get_custom_where_params()
    #
    #         # Prepare initial sql query and Get the initial move lines
    #         if init_balance:
    #             init_tables, init_where_clause, init_where_params = MoveLine.with_context(date_to=self.env.context.get('date_from'), date_from=False)._query_get()
    #             init_wheres = [""]
    #             if init_where_clause.strip():
    #                 init_wheres.append(init_where_clause.strip())
    #             init_filters = " AND ".join(init_wheres)
    #             filters = init_filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')
    #             sql = ("SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate, '' AS lcode, NULL AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance, '' AS lpartner_id,\
    #                 '' AS move_name, '' AS mmove_id, '' AS currency_code,\
    #                 NULL AS currency_id,\
    #                 '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
    #                 '' AS partner_name\
    #                 FROM account_move_line l\
    #                 LEFT JOIN account_move m ON (l.move_id=m.id)\
    #                 LEFT JOIN res_currency c ON (l.currency_id=c.id)\
    #                 LEFT JOIN res_partner p ON (l.partner_id=p.id)\
    #                 LEFT JOIN account_invoice i ON (m.id =i.move_id)\
    #                 JOIN account_journal j ON (l.journal_id=j.id)\
    #                 WHERE l.account_id IN %s" + filters + custom_where_params + ' GROUP BY l.account_id')
    #             params = (tuple(accounts.ids),) + tuple(init_where_params)
    #             cr.execute(sql, params)
    #             for row in cr.dictfetchall():
    #                 move_lines[row.pop('account_id')].append(row)
    #
    #         sql_sort = 'l.date, l.move_id'
    #         if sortby == 'sort_journal_partner':
    #             sql_sort = 'j.code, p.name, l.move_id'
    #
    #         # Prepare sql query base on selected parameters from wizard
    #         tables, where_clause, where_params = MoveLine._query_get()
    #         wheres = [""]
    #         if where_clause.strip():
    #             wheres.append(where_clause.strip())
    #         filters = " AND ".join(wheres)
    #         filters = filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')
    #
    #         # Get move lines base on sql query and Calculate the total balance of move lines
    #         sql = ('SELECT l.id AS lid, l.account_id AS account_id, l.date AS ldate, acc.final_code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,\
    #             m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name\
    #             FROM account_move_line l\
    #             JOIN account_move m ON (l.move_id=m.id)\
    #             LEFT JOIN res_currency c ON (l.currency_id=c.id)\
    #             LEFT JOIN res_partner p ON (l.partner_id=p.id)\
    #             JOIN account_journal j ON (l.journal_id=j.id)\
    #             JOIN account_account acc ON (l.account_id = acc.id) \
    #             WHERE l.account_id IN %s ' + filters + custom_where_params + ' GROUP BY l.id, l.account_id, l.date, acc.final_code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, p.name ORDER BY ' + sql_sort)
    #         params = (tuple(accounts.ids),) + tuple(where_params)
    #         cr.execute(sql, params)
    #
    #         for row in cr.dictfetchall():
    #             balance = 0
    #             for line in move_lines.get(row['account_id']):
    #                 balance += line['debit'] - line['credit']
    #             row['balance'] += balance
    #             move_lines[row.pop('account_id')].append(row)
    #
    #         # Calculate the debit, credit and balance for Accounts
    #         account_res = []
    #         for account in accounts:
    #             currency = account.currency_id and account.currency_id or account.company_id.currency_id
    #             res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
    #             res['code'] = account.code
    #             res['name'] = account.name
    #             res['move_lines'] = move_lines[account.id]
    #             for line in res.get('move_lines'):
    #                 res['debit'] += line['debit']
    #                 res['credit'] += line['credit']
    #                 res['balance'] = line['balance']
    #             if display_account == 'all':
    #                 account_res.append(res)
    #             if display_account == 'movement' and res.get('move_lines'):
    #                 account_res.append(res)
    #             if display_account == 'not_zero' and not currency.is_zero(res['balance']):
    #                 account_res.append(res)
    #
    #         return account_res
    #
    #     def get_custom_where_params(self):
    #         return ''


class Bank(models.Model):
    _inherit = "res.bank"
    po_box = char_field('P.O Box')

class InheritMoveLine(models.Model):
    _inherit = "account.move.line"

    balanced = fields.Boolean('Balanced', default=True)
    employee_id = m2o_field('hr.employee', 'Employee')

class InheritInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    empl_name = fields.Many2one('hr.employee', 'Employee')

