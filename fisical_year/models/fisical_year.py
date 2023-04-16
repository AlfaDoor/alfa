# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from .base_tech import *
import calendar
from odoo.tools import __

class FiscalYear(models.Model):
    _name = 'fiscal.year'
    _description = "Fiscal year"
    _inherit = ['mail.thread',  ]

    state = selection_field([('new', 'New'), ('active', 'Active'), ('freeze', 'Freeze'), ('close', 'Close')],
                            string="Status", track_visibility='onchange', default='new')
    name = char_field('Fiscal Year name')
    code = char_field('Code', compute="_get_dates", multi='xxx', store=True)
    start_date = date_field('Date Start', compute="_get_dates", multi='xxx', store=True)
    start_end = date_field('Date End', compute="_get_dates", multi='xxx', store=True)
    period_ids = o2m_field('periods', 'year_id', 'Periods')
    note = html_field('Notes')
    open_journal_id = m2o_field('account.move', 'Opening Journal Entry')
    close_move_id = m2o_field('account.move', 'Close Journal Entry')
    close_journal_id = m2o_field('account.journal', 'Close Journal')
    close_account_id = m2o_field('account.account', 'Close Account')
    open_journal_lines_ids = o2m_field('account.move.line', 'year_open_id', 'Opening Journal Lines')
    close_journal_lines_ids = o2m_field('account.move.line', 'year_close_id', 'Closing Journal Lines')
    periods_count = integer_field('Number of periods', compute='no_of_periods')
    total_expenses = float_field('Total expenses', compute='_get_net_profit', multi=True)
    total_income = float_field('Total Income', compute='_get_net_profit', multi=True)
    net_profit = float_field('Net profit', compute='_get_net_profit', multi=True)

    _sql_constraints = [
        ('unique_name', "unique(name)", 'Period must be unique')
    ]

    @api.model
    def where_cluster(self):
        return " date >='%s' and date <='%s'" % (__(self.start_date), __(self.start_end))

    @api.one
    def _get_net_profit(self):
        accounts_in = self.env['account.account'].search([['user_type_id.location', 'in', ['income']]])
        accounts_ex = self.env['account.account'].search([['user_type_id.location', 'in', ['expense']]])
        total_ex = total_in = 0
        if accounts_in:
            Accounts = [str(a.id) for a in accounts_in]
            Accounts = ','.join(Accounts)
            sql_in = "select sum(credit - debit) from account_move_line where account_id in(%s) and %s" % (Accounts, self.where_cluster())
            self.env.cr.execute(sql_in)
            rows = self.env.cr.fetchall()
            total_in = rows[0][0] or 0
            self.total_income = total_in
        if accounts_ex:
            Accounts = [str(a.id) for a in accounts_ex]
            Accounts = ','.join(Accounts)
            sql_ex = "SELECT sum(debit)- sum(credit) FROM account_move_line WHERE account_id in(%s) AND %s" % (Accounts, self.where_cluster())
            self.env.cr.execute(sql_ex)
            rows = self.env.cr.fetchall()
            total_ex = rows[0][0] or 0
            self.total_expenses = total_ex
        self.net_profit = total_in - total_ex

    @api.one
    def generate_close_move(self):
        accounts = self.env['account.account'].search([['user_type_id.location', 'in', ['income', 'expense']]])
        if not accounts:
            raise ValidationError(_("No Income or expense account"))
        if not self.close_account_id:
            raise ValidationError(_("Please assign Close Account to close Profit and loss in it"))
        if not self.close_journal_id:
            raise ValidationError(_("Please specify Close Journal"))
        Accounts = [str(a.id) for a in accounts]
        Accounts = ','.join(Accounts)
        sql = """SELECT account_id, SUM(debit) , SUM(credit), analytic_account_id
                 FROM account_move_line
                 WHERE account_id IN(%s) AND %s AND NOT (debit=0 AND credit=0)
                 GROUP BY account_id, analytic_account_id
                 ORDER BY account_id, analytic_account_id """ % (Accounts, self.where_cluster())
        self.env.cr.execute(sql)
        rows = self.env.cr.fetchall()
        ctx = dict(self.env.context.copy(), check_move_validity=False)
        total = 0
        lines = []
        seq = 0
        for row in rows:
            seq += 1
            debit = row[1]
            credit = row[2]
            balance = abs(debit - credit)
            new_debit = (credit > debit) and balance or 0
            new_credit = (debit > credit) and balance or 0
            total = total + new_debit - new_credit
            vals = {
                # 'move_id': move.id,
                'sequence': seq,
                'name': 'Close %s' % self.name,
                'debit': new_debit,
                'credit': new_credit,
                'account_id': row[0],
                'analytic_account_id': row[3],
                'date': __(self.start_end),
                'date_maturity': __(self.start_end),
            }
            lines.append((0, 0, vals))

        if total:
            diff_vals = {
                'sequence': seq + 1,
                'name': 'Close %s' % self.name,
                'account_id': self.close_account_id.id,
                'debit': total < 0 and total or 0.0,
                'credit': total > 0 and total or 0.0,
                'analytic_account_id': False,
                'date': __(self.start_end),
                'date_maturity': __(self.start_end),
            }
            lines.append((0, 0, diff_vals))
        move_vals = {
            'journal_id': self.close_journal_id.id,
            'date': __(self.start_end),
            'ref': 'Close %s' % self.name,
            'line_ids': lines
        }
        move = self.with_context(ctx).env['account.move'].create(move_vals)
        self.close_move_id = move.id

    @api.onchange('name')
    def onchange_name(self):
        name = ''
        no_no = ''
        for c in self.name or '':
            if c in '0123456789':
                name += c
            else:
                no_no += c
        self.name = self.code = name
        if name and (float(name) > 2100 or float(name) < 2000):
            raise ValidationError(_("Financial year must be between 2000 and 2100"))
        if no_no != '':
            return {'warning': {'title': _('Name Error'),
                                'message': _('You can not user this (%s) in period name.' % no_no)}}

    @api.one
    @api.depends('name')
    def _get_dates(self):
        if self.name:
            self.code = self.name
            self.start_date = str(self.name) + '-01-01'
            self.start_end = str(self.name) + '-12-31'

    @api.one
    @api.depends('period_ids')
    def no_of_periods(self):
        self.periods_count = len(self.period_ids)

        @api.one
        def active(self):
            self.state = 'active'
            for month in range(1, 12):
                self.env['periods'].create({
                    'name': self.period_ids.decimal(month),
                    # len(str(month)) == 1 and '0' + str(month) or str(month),
                    'year_id': self.id
                })

    @api.one
    def active(self):
        if self.state == 'active':
            raise ValidationError(_("You can't active fiscal year more than one time"))
        self.state = 'active'
        for month in range(1, 13):
            period = self.env['periods'].create({
                'name': self.period_ids.decimal(month),
                'year_id': self.id,
                'state': 'new',
            })
            period.get_dates()
            period._get_code()

    @api.one
    def freeze(self):
        self.state = 'freeze'

    @api.one
    def reactive(self):
        self.state = 'active'

    @api.one
    def close(self):
        for period in self.period_ids:
            if period.state != 'close':
                raise ValidationError(
                    _("In order to close this financial year, you have to close all periods which belong to this year"))
        if self.env['account.move'].search([['period_id', '=', self.id]]) and not self.close_move_id:
            raise ValidationError(_(
                "We found that this financial year contains some transactions. You have to create journal entry to close those accounts"))
        self.state = 'close'

    @api.one
    def set_to_draft(self):
        if self.env['account.move'].search([['period_id', '=', self.id]]):
            raise ValidationError(_(
                "This financial year contains some journal entries and cannot be set as a )new financial year( in order to set this financial year to new , you have to delete all transactions related to this year."))
        self.period_ids.unlink()
        self.state = 'new'

    @api.one
    def unlink(self):
        if self.state != 'new':
            raise ValidationError(_("Financial year state must be in (New) in order to delete it"))
        return super(FiscalYear, self).unlink()

    @api.one
    def copy(selfs):
        raise ValidationError(_("Duplicate Disabled in this window"))


class Periods(models.Model):
    _name = 'periods'
    _description = "Periods"
    _inherit = ['mail.thread', ]
    _rec_name = 'code'

    year_id = m2o_field('fiscal.year', 'Fiscal year')
    name = selection_field([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'), ('05', 'May'),
                            ('06', 'June'), ('07', 'July'), ('08', 'August'),
                            ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December'),
                            ], string='Period name')
    code = char_field('Code', compute="_get_code", store=True)  #
    date_start = date_field('Date Start', compute='get_dates', store=True)  #
    date_end = date_field('Date End', compute='get_dates', store=True)  #
    state = selection_field([('new', 'New'), ('active', 'Active'), ('freeze', 'Freeze'), ('close', 'Close')],
                            string='Status', default='new', track_visibility='onchange')
    note = html_field('Notes')

    @api.model
    def get_default_period(self, date):
        periods = self.search([['date_start', '<=', date], ['date_end', '>=', date], ['state', '=', 'active']])
        if date and periods:
            return periods[0]
        else:
            return False

    @api.one
    def active(self):
        self.state = 'active'

    @api.one
    def freeze(self):
        self.state = 'freeze'

    @api.one
    def close(self):
        self.state = 'close'

    @api.one
    def reactive(self):
        self.state = 'active'

    @api.one
    @api.depends('year_id')
    def get_dates(self):
        self.date_start = str(self.year_id.name) + '-' + str(self.name) + '-01'
        last_date = calendar.monthrange(int(self.year_id.name), int(self.name))[1]
        self.date_end = str(self.year_id.name) + '-' + str(self.name) + '-' + str(self.decimal(last_date))

    @api.multi
    def decimal(self, n):
        for c in str(n):
            if str(c) not in '0123456789':
                raise ValidationError(_("Programming Error"))
        return len(str(n)) == 2 and str(n) or ('0' + str(n))

    @api.one
    def _get_code(self):
        self.code = str(self.year_id.name) + "/" + str(self.name)

    @api.one
    def copy(self):
        raise ValidationError(_("Duplicate Disabled in this window"))


class AccountMove(models.Model):
    _inherit = 'account.move'

    period_id = m2o_field('periods', 'Period', readonly=True)
    year_open_id = m2o_field('fiscal.year', 'open year')
    year_close_id = m2o_field('fiscal.year', 'close year')

    @api.constrains('date')
    def check_period_for_this_date(self):
        period = self.env['periods'].search([['date_start', '<=', __(self.date)], ['date_end', '>=', __(self.date)]])
        if not period:
            raise ValidationError(_(
                "It seems that there is no active period for the selected date... In order to accept this transaction \
                you have to communicate with your financial manager to create or activate a financial period for the \
                selected date"))
        if period.year_id.state != 'active':
            raise ValidationError(_(
                "It seems that there is no active financial year for the selected date... In order to accept this \
                transaction you have to communicate with your financial manager to create or activate a financial \
                period for the selected date"))

    @api.onchange('date')
    def get_period(self):
        period = self.env['periods'].get_default_period(__(self.date))
        self.period_id = period and period.id or False

    @api.model
    def create(self, vals):
        date = vals['date']
        periods = self.env['periods'].search([['date_start', '<=', date], ['date_end', '>=', date]])
        period = False
        for p in periods:
            if p.state == 'active':
                period = p
                break
        if period:
            vals['period_id'] = p.id
        else:
            raise ValidationError(_("It seems that no active period for selected date"))
        return super(AccountMove, self).create(vals)

    @api.model_cr
    def init(self):
        ams = self.with_context(dict(self._context, force_edit=True)).search([('period_id', '=', False)])
        for am in ams:
            am.get_period()

    @api.multi
    def write(self, vals):
        for rec in self:
            if rec.id and rec.period_id.state != 'active' and not rec._context.get('force_edit', False):
               raise ValidationError(_(
                "You can not edit in the Journal entry %s because period '%s isn't active\nPlease open it first to ba able to edit in it" % (
                    rec.name or rec.seq or rec.id, rec.period_id.code)))
            return super(AccountMove, self).write(vals)

    @api.one
    def unlink(self):
        if self.period_id.state != 'active' and not self._context.get('force_edit', False):
            raise ValidationError(_("You can't delete that journal entry %s because period '%s isn't active\nPlease open it first to ba able to edit in it" % (
                self.name or self.seq, self.period_id.code)))
        return super(AccountMove, self).unlink()


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    @api.constrains('date')
    def check_period_for_this_date(self):
        period = self.env['periods'].search([['date_start', '<=', __(self.date)], ['date_end', '>=', __(self.date)]])
        if not period:
            raise ValidationError(_(
                "It seems that there is no active period for the selected date... In order to accept this transaction \
                you have to communicate with your financial manager to create or activate a financial period for the \
                selected date"))
        if period.year_id.state != 'active':
            raise ValidationError(_(
                "It seems that there is no active financial year for the selected date... In order to accept this \
                transaction you have to communicate with your financial manager to create or activate a financial \
                period for the selected date"))


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    year_open_id = m2o_field('fiscal.year', 'open year')
    year_close_id = m2o_field('fiscal.year', 'close year')
