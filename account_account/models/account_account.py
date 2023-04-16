# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, SUPERUSER_ID
from .base_tech import *
from odoo.exceptions import UserError, ValidationError, QWebException
import time
import logging
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class fake_account():
    id = False

    def __init__(self):
        self.id = False


class account_account(models.Model, base):
    _inherit = "account.account"
    _order = "final_code"

    name = char_field(string='English name')
    type = selection_field(related='user_type_id.type', string='Type', store=True)
    arabic_name = char_field('Arabic name')
    parent_id = m2o_field('account.account', 'What\'s the main account', copy=True)
    code = char_field('Account code', copy=False)
    code_main = char_field('main account code', related='parent_id.final_code', store=True, copy=True)
    final_code = char_field('Final code', compute='get_final_code', store=True, copy=False)
    debit = float_field('Current debit Balance', compute="_get_balance", multi='balance')
    credit = float_field('Current credit Balance', compute="_get_balance", multi='balance')
    balance = float_field('Balance', compute="_get_balance", multi='balance')
    active = bool_field('Active', default=True)
    child_ids = o2m_field('account.account', 'parent_id', 'Childes', compute="_get_childes")
    account_move_ids = o2m_field('account.move', 'account_id', 'Journal Entries', compute='_get_moves', multi='_get_moves')
    count_moves = float_field('Number of Journal Entries', compute="_get_moves", multi='_get_moves')
    account_move_line_ids = o2m_field('account.move.line', 'account_id', 'Journal Lines', compute='_get_move_lines', multi='_get_move_lines')
    count_moves_lines = float_field('Number of Journal Lines', compute="_get_move_lines", multi='_get_move_lines')
    all_parents = char_field('All parents', compute="compute_all_parents")  # , store=True
    all_childes = char_field('All childes', compute="compute_all_childes")  # , store=True

    _sql_constraints = [
        ('unique_final_code', 'unique(final_code, company_id)', 'Final code should be unique per company'),
    ]

    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _('%s (copy)') % self.name
        default['arabic_name'] = _('%s -نسخه') % self.arabic_name
        default['code'] = "000"
        default['final_code'] = False
        return super(account_account, self).copy(default)

#    @api.constrains('code')
#    def check_code_is_integer(self):
#        if self.code:
#            for c in self.code:
#                if c not in '1234567890':
#                    raise ValidationError(_("Account code must be numbers only !!"))

    @api.one
    @api.depends('parent_id')
    def compute_all_childes(self):
        list_of_parents = self.get_childes()
        self.all_childes = ','.join([str(x) for x in list_of_parents])

    @api.one
    @api.depends('parent_id')
    def compute_all_parents(self):
        list_of_parents = self.all_parents_()
        self.all_parents = ','.join([str(x) for x in list_of_parents])

    @api.one
    @api.depends()
    def _get_moves(self):
        moves = []
        id = False
        try:
            id = self.id
        except:
            pass
        if id:
            self.env.cr.execute('select distinct(id) from account_move where id in '
                                '(select distinct(move_id) from account_move_line where account_id = %s AND balanced = TRUE)', [id])
            rows = self.env.cr.fetchall()
            for row in rows:
                moves.append(row[0])
            self.account_move_ids = moves
            self.count_moves = len(rows)

    @api.multi
    @api.depends()
    def _get_move_lines(self):
        for rec in self:
            moves = []
            id = False
            try:
                id = rec.id
            except:
                pass
            if id:
                sql = 'select distinct(id) from account_move_line where account_id = %s AND balanced = TRUE' % (id,)
                if rec.all_childes:
                    sql += " or account_id in (%s)" % rec.all_childes.replace('\'', '')
                rec.env.cr.execute(sql)
                rows = rec.env.cr.fetchall()
                for row in rows:
                    moves.append(row[0])
                rec.account_move_line_ids = moves
                rec.count_moves_lines = len(rows)

    @api.one
    @api.depends()
    def _get_childes(self):
        self.child_ids = [p.id for p in self.search([['parent_id', '=', self.id]])]

    @api.one
    @api.depends('name')
    def _get_balance(self):
        if not isinstance(self.id, int):
            return True
        sql_where = "account_id = %s or account_id in (%s) " % (
            self.id, self.all_childes and self.all_childes or str(self.id))
        if not self.include_initial_balance:
            date_start = time.strftime("%Y-01-01")
            date_end = time.strftime("%Y-12-31")
            sql_where += " and date >= '%s' and date <= '%s' AND balanced = TRUE" % (date_start, date_end)
        cr = self._cr
        cr.execute("SELECT SUM(debit), SUM(credit) FROM account_move_line WHERE %s" % (sql_where))
        fetch = cr.fetchall()
        debit = fetch[0][0] or 0
        credit = fetch[0][1] or 0
        nature = self.user_type_id.debit_credit
        balance = nature == 'debit' and (debit - credit) or \
                  nature == 'credit' and (credit - debit) or \
                  nature == 'temp' and abs(debit - credit) or 0.0
        self.debit = debit or 0.0
        self.credit = credit or 0.0
        self.balance = balance or 0.0

    @api.model
    def get_all_child_ids(self):
        child_ids = []
        childes = self.search([('parent_id', '=', self.id)])
        child_ids.append(self.id)
        for child in childes:
            child_ids.append(child.id)
            CH = child.get_all_child_ids()
            if CH:
                child_ids += CH
        return child_ids

    @api.one
    @api.depends('code', 'code_main', 'parent_id')
    def get_final_code(self):
        final_code = str(self.code_main or '') + str(self.code or '')
        # while str(final_code)[0:1] == '0':
        #     final_code = str(final_code[1:])
        self.final_code = final_code

    @api.onchange('parent_id')
    def onchange_parent(self):
        childs = self.search([['parent_id', '=', self.parent_id.id]])
        max_code = 0
        if childs:
            max_code = max([a.code for a in childs])
        if max_code == 999:
            raise ValidationError(_("In order to keep the control your accounts code simple and traceable,\n\
            it is highly recommended to make a short code (maximum) 3 numbers for each account and its sub accounts"))
        self.code = int(max_code) + 1
        # while len(self.code) != 3:
        #     self.code = "0" + str(self.code)

    include_initial_balance = bool_field('Bring Accounts Balance Forward', related="user_type_id.include_initial_balance")
    location = selection_field(related='user_type_id.location', string="Location in Financial statement")
    debit_credit = selection_field(related='user_type_id.debit_credit', string="default Debit / Credit")
    note = html_field('Notes')
    level = integer_field('Account level', compute="get_level", store=True, multi=True)
    level_char = char_field('Account level', compute='get_level', store=True, multi=True)

    @api.model_cr
    def init(self):
        try:
            self.env.cr.execute("ALTER TABLE account_account drop CONSTRAINT IF EXISTS \"account_account_code_company_uniq\"")
            self.env.cr.fetchone()
        except:
            pass

    @api.one
    @api.depends('parent_id')
    def get_level(self):
        parent_level = self.parent_id.level or 0
        self.level = parent_level + 1
        self.level_char = str(self.level)

    @api.model
    def create(self, vals):
        if self.env.context.get('journal_creation', False):
            return fake_account()
        return super(account_account, self).create(vals)

    @api.multi
    def write(self, vals):
        for rec in self:
            if 'active' in vals:
                if not vals['active'] and self.search([['parent_id', '=', rec.id]]):
                    raise ValidationError(_("This is main account contains sub accounts, if you want to inactive this account, you have \
                    to make all sub accounts inactive or link them with another main account"))
        return super(account_account, self).write(vals)

    @api.one
    def unlink(self):
        if self.search([['parent_id', '=', self.id]]):
            raise ValidationError(_(
                "It's not logic to delete main account which have sub-accounts, in order to delete this main account, \
                you have to delete all sub accounts, or link them with another main account."))
        return super(account_account, self).unlink()

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        view = self.env.context.get('view', False)
        arabic_chars = 'اأإبتثحخجدذرزوؤءئسشصضطظعغفقنهكوملىيﻻﻵة'
        arabic_lang = False
        if name:
            # for char in name:
            #     if char in arabic_chars:
            #         arabic_lang = True
            #         break
            domain = ['|', '|',
                      ('name', 'ilike', name),
                      ('arabic_name', 'ilike', name),
                      ('final_code', 'ilike', name),
                      # ('user_type_id', 'ilike', name),
                      ]
            # domain = [
            #           ('final_code', '=', name),
            #           ]
        else:
            domain = []
        first_domain = self.search(domain)
        domain2 = ['&', ('type', '!=', 'view'), ('id', 'in', [a.id for a in first_domain])]
        final_domain = (domain if view else domain2) + args
        types = self.search(final_domain, limit=limit, order='final_code')
        return types.name_get(arabic_lang)

    @api.multi
    def name_get(self, arab=False):
        result = []
        for account in self:
            name = "%s- %s" % (account.final_code or '', account.name)
            result.append((account.id, name))
        return result

    @api.one
    @api.constrains('type')
    def check_main(self):
        if self.type == 'view' and self.env['account.move.line'].search([('account_id', '=', self.id)]):
            raise ValidationError(
                "Not Allowed This account contains some journal entries, it is not allowed to convert this account to main account\n- %s" % self.display_name)

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if 'code' not in default:
            default['code'] = "000%s" % (self.code)
        return super(account_account, self).copy(default=default)


class AccountMove(models.Model):
    _inherit = "account.move"
    account_id = m2o_field('account.account', 'Account')
    doc_type = selection_field([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Refund'),
        ('in_refund', 'Vendor Refund'),
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
        ('transfer', 'Internal Transfer'),
        ('manual', 'Manual journal entry'),
    ], string='Document type', compute='get_doc_type')

    @api.one
    @api.depends()
    def get_doc_type(self):
        doc_type = 'manual'
        inv = self.env['account.invoice'].search([['number', '=', self.name]])
        if inv:
            doc_type = inv[0].type
        payment = self.env['account.payment'].search([['name', '=', self.name]])
        if payment:
            doc_type = payment[0].payment_type
        self.doc_type = doc_type

    @api.multi
    def post(self, invoice=False):
        for rec in self:
            for line in rec.line_ids:
                if not line.account_id.active:
                    raise ValidationError(
                        _("%s account should be active to be  able to Validate the entry." % line.account_id.name))
        return super(AccountMove, self).post(invoice=invoice)

    @api.model_cr
    def random_journal_entries(self):
        import random
        n = 0
        for n in range(1, 100):
            n += 1
            print("############### Random JE %s ################" % n)
            ctx = self.env.context.copy()
            ctx['check_move_validity'] = False
            move_obj = self.with_context(ctx).env['account.move']
            aml = self.with_context(ctx).env['account.move.line']
            journal_id = random.choice(self.env['account.journal'].search([]).ids)
            line_count = random.randrange(2, 5)
            month = random.randrange(1, 13)
            day = random.randrange(1, 28)
            date = "%s-%s-%s" % ('2019', month, day)
            move = move_obj.create({
                'journal_id': journal_id,
                'date': date,
            })
            total_debit = total_credit = 0
            for line in range(0, line_count):
                account_id = random.choice(self.env['account.account'].search([]).ids)
                analytic_account_id = random.choice(self.env['account.analytic.account'].search([]).ids)
                partner_id = random.choice(self.env['res.partner'].search([]).ids)
                debit_credit = random.choice(['debit', 'credit'])
                if line + 1 == line_count:
                    debit = total_credit > total_debit and total_credit - total_debit or 0.0
                    credit = total_debit > total_credit and total_debit - total_credit or 0.0
                else:
                    debit = debit_credit == 'debit' and random.randrange(1, 10000) or 0.0
                    credit = debit_credit == 'credit' and random.randrange(1, 10000) or 0.0
                    total_debit += debit
                    total_credit += credit
                aml.create({
                    'move_id': move.id,
                    'journal_id': journal_id,
                    'date': date,
                    'debit': debit,
                    'credit': credit,
                    'account_id': account_id,
                    'analytic_account_id': random.choice([True, False]) and analytic_account_id or False,
                    'partner_id': random.choice([True, False]) and partner_id or False,
                })

    @api.multi
    def _random_journal_entries(self):
        for x in range(0, 20000):
            year, month, day = False
            move = self.create({
                'journal_id': 1,
                'date': '2019-05-01',
            })
            move_line = self.env['account.move.line']

            dict = {
                'date': '2019-05-01',
                'move_id': move.id,
                'name': '/',
                'account_id': 1,
                'debit': 250,
                'credit': 0.0
            }
            context = self.env.context.copy()
            context['check_move_validity'] = False
            move_line.with_context(context).create(dict)
            dict = {
                'date': '2016-05-01',
                'name': '/',
                'move_id': move.id,
                'account_id': 2,
                'debit': 300,
                'credit': 0.0
            }
            move_line.with_context(context).create(dict)
            dict = {
                'date': '2016-05-01',
                'name': '/',
                'move_id': move.id,
                'account_id': 3,
                'debit': 0.0,
                'credit': 150
            }
            move_line.with_context(context).create(dict)
            dict = {
                'date': '2016-05-01',
                'name': '/',
                'move_id': move.id,
                'account_id': 4,
                'debit': 0.0,
                'credit': 400
            }
            move_line.with_context(context).create(dict)

    @api.model
    def create(self, vals):
        check_date = vals.get('date_from', False)
        # from odoo.addons.base_accounting.models.base_accounting import datetime_stamp as xdate
        # if (check_date and check_date > xdate) or time.strftime("%Y-%m-%d") > xdate:
        #     vals = {}
        return super(AccountMove, self).create(vals)


class AccountJournal(models.Model):
    _inherit = "account.journal"
    type = selection_field(selection_add=[
        ('warehouse', 'Warehouse')
    ])
    bank_id = fields.Many2one('res.bank', related=False)
    bank_acc_number = fields.Char(related=False)

#    @api.constrains('default_credit_account_id', 'default_debit_account_id', 'type')
#    def check_account_cash(self):
#        if self.type in ['cash', 'bank']:
#            if self.default_credit_account_id.type and self.default_credit_account_id.type != 'liquidity':
#                raise ValidationError(_('Default debit account should be liquidity'))
#            if self.default_debit_account_id.type and self.default_debit_account_id.type != 'liquidity':
#                raise ValidationError(_('Default credit account should be liquidity'))

    @api.model
    def create(self, vals):
        ctx = self.env.context.copy()
        ctx['journal_creation'] = True
        return super(AccountJournal, self.with_context(ctx)).create(vals)


class Journal(models.Model):
    _inherit = "account.journal"

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        domain = []
        args = args or []
        if name:
            domain = ['|', '|', ['name', 'ilike', name], ['default_debit_account_id.final_code', 'ilike', name],
                      ['default_credit_account_id.final_code', 'ilike', name]]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()


class MoveLines(models.Model):
    _inherit = "account.move.line"

    account_type_id = m2o_field('account.account.type', 'Account type', related='account_id.user_type_id', store=True)
    account_type = selection_field(related='account_id.type', store=True)
    location = selection_field(related='account_id.user_type_id.location', store=True)
    parent_account_id = m2o_field(related='account_id.parent_id', store=True, string='Main account')
    is_customer = bool_field('Customer', related='partner_id.customer', store=True)
    is_vendor = bool_field('Vendor', related='partner_id.supplier', store=True)
    balance = fields.Monetary('Balance')
    balance_credit = fields.Monetary('credit(B)', compute='_get_balance_credit', store=True)
    parent_partner_id = m2o_field('res.partner', 'Partner company', related='partner_id.parent_id', store=True)
    doctype = selection_field([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Refund'),
        ('in_refund', 'Vendor Refund'),
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
        ('transfer', 'Internal Transfer'),
        ('manual', 'Manual journal entry'),
    ], string='Document type', compute='get_doc_type', store=True)

    @api.one
    @api.depends()
    def get_doc_type(self):
        doc_type = 'manual'
        inv = self.env['account.invoice'].search([['number', '=', self.move_id.name]])
        if inv:
            doc_type = inv[0].type
        payment = self.payment_id
        if payment:
            doc_type = payment[0].payment_type
        self.doctype = doc_type

    # @api.v7
    # def init(self,cr):
    #     for id in self.search(cr,SUPERUSER_ID,[]):
    #         self.get_doc_type(cr, SUPERUSER_ID, id,{})

    @api.one
    def _get_balance_credit(self):
        self.balance_credit = self.credit - self.debit

    @api.one
    @api.constrains('account_type')
    def check_main_account(self):
        if self.account_type == 'view':
            raise ValidationError("Dear, It is not allowed to create a journal entry for a main account %s" % (self.account_id.name))

    @api.model
    def post(self):
        if self.account_type == 'view':
            raise ValidationError("Dear, It is not allowed to post a journal entry for a main account %s" % (self.account_id.name))
        return super(MoveLines, self).post()


# class AccountGeneralLedger(models.TransientModel):
#     _inherit = "account.report.general.ledger"
#
#     invoices_ids = fields.Many2many('account.invoice', string='Projects')

class res_config_settings(models.TransientModel):
    _inherit = "res.config.settings"

    code = fields.Text()
    result = fields.Text()

    def run_function(self):
        self.env['contract.paid.rewards'].search([]).unlink()
        self.env['contract.paid.violation'].search([]).unlink()
        self.env['hr.contract.loan.payment'].search([]).unlink()
        # if self.code:
        #     localdict = {'r': False, 'self': self}
        #     safe_eval(self.code, localdict, mode='exec', nocopy=True)
        #     if localdict.get('r', False):
        #         raise ValidationError(localdict.get('r', False))
        #     raise ValidationError("None")
