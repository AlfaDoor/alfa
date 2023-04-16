# -*- coding: utf-8 -*-

import calendar

import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta
from odoo import api, models, fields, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import AccessError, UserError
from odoo.tools import __

D_LEDGER = {'general': {'name': _('General Ledger'),
                        'group_by': 'account_id',
                        'model': 'account.account',
                        'short': 'code',
                        },
            'partner': {'name': _('Partner Ledger'),
                        'group_by': 'partner_id',
                        'model': 'res.partner',
                        'short': 'name',
                        },
            'journal': {'name': _('Journal Ledger'),
                        'group_by': 'journal_id',
                        'model': 'account.journal',
                        'short': 'code',
                        },
            'open': {'name': _('Open Ledger'),
                     'group_by': 'account_id',
                     'model': 'account.account',
                     'short': 'code',
                     },
            'aged': {'name': _('Aged Balance'),
                     'group_by': 'partner_id',
                     'model': 'res.partner',
                     'short': 'name',
                     },
            'analytic': {'name': _('Analytic Ledger'),
                         'group_by': 'analytic_account_id',
                         'model': 'account.analytic.account',
                         'short': 'name',
                         },
            'sub_account': {'name': _('Sub account Ledger'),
                            'group_by': 'analytic_id',
                            'model': 'account.analytic.tag',
                            'short': 'name',
                            },
            'employees': {'name': _('Employee ledger'),
                          'group_by': 'employee_id',
                          'model': 'hr.employee',
                          'short': 'name',
                          },

            }


class AccountStandardLedgerPeriode(models.TransientModel):
    _name = 'account.report.standard.ledger.periode'

    name = fields.Char('Name')
    date_from = fields.Datetime('Date from')
    date_to = fields.Datetime('Date to')


class AccountStandardLedgerReport(models.TransientModel):
    _name = 'account.report.standard.ledger.report'

    name = fields.Char()
    report_object_ids = fields.One2many('account.report.standard.ledger.report.object', 'report_id')
    report_name = fields.Char()
    line_total_ids = fields.Many2many('account.report.standard.ledger.line', relation='table_standard_report_line_total')
    line_super_total_id = fields.Many2one('account.report.standard.ledger.line')
    print_time = fields.Char()
    date_from = fields.Date(string='Start Date', help='Use to compute initial balance.')
    date_to = fields.Date(string='End Date', help='Use to compute the entrie matched with futur.')


class AccountStandardLedgerLines(models.TransientModel):
    _name = 'account.report.standard.ledger.line'
    _order = 'id'
    _rec_name = 'move_id'

    report_id = fields.Many2one('account.report.standard.ledger.report')
    account_id = fields.Many2one('account.account', 'Account')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    type = fields.Selection([('0_init', 'Initial'),
                             ('1_init_line', 'Init Line'),
                             ('2_line', 'Line'),
                             ('3_compact', 'Compacted'),
                             ('4_total', 'Total'),
                             ('5_super_total', 'Super Total')], string='Type')
    type_view = fields.Selection([('init', 'Init'), ('normal', 'Normal'), ('total', 'Total')])
    journal_id = fields.Many2one('account.journal', 'Journal')
    partner_id = fields.Many2one('res.partner', 'Partner')
    analytic_id = fields.Many2one('account.analytic.tag', 'Sub account')
    employee_id = fields.Many2one('hr.employee', 'Employee')
    group_by_key = fields.Char()
    move_id = fields.Many2one('account.move', 'Entrie')
    label = fields.Char('Description')
    doctype = fields.Char('Document type')
    move_line_id = fields.Many2one('account.move.line')
    date = fields.Date()
    date_maturity = fields.Date('Due Date')
    debit = fields.Monetary(default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(default=0.0, currency_field='company_currency_id')
    balance = fields.Monetary(default=0.0, currency_field='company_currency_id')
    cumul_balance = fields.Monetary(default=0.0, currency_field='company_currency_id', string='Balance')
    init_debit = fields.Monetary(default=0.0, currency_field='company_currency_id', string='Initial Debit')
    init_credit = fields.Monetary(default=0.0, currency_field='company_currency_id', string='Initial Credit')
    full_reconcile_id = fields.Many2one('account.full.reconcile', 'Match.')
    reconciled = fields.Boolean('Reconciled')
    report_object_id = fields.Many2one('account.report.standard.ledger.report.object')

    current = fields.Monetary(default=0.0, currency_field='company_currency_id', string='Not due')
    age_30_days = fields.Monetary(default=0.0, currency_field='company_currency_id', string='30 days')
    age_60_days = fields.Monetary(default=0.0, currency_field='company_currency_id', string='60 days')
    age_90_days = fields.Monetary(default=0.0, currency_field='company_currency_id', string='90 days')
    age_120_days = fields.Monetary(default=0.0, currency_field='company_currency_id', string='120 days')
    older = fields.Float(default=0.0, digits=dp.get_precision('Account'), string='Older')

    amount_currency = fields.Monetary(default=0.0, currency_field='currency_id', string='Amount Currency')
    currency_id = fields.Many2one('res.currency')

    company_currency_id = fields.Many2one('res.currency')

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(AccountStandardLedgerLines, self).read_group(domain, fields, groupby, offset, limit=limit, orderby=orderby, lazy=lazy)
        if 'cumul_balance' in fields and 'debit' in fields and 'credit' in fields:
            for line in res:
                line['cumul_balance'] = line['debit'] - line['credit']
        return res

    def compute_line(self, account_id, report_id, report_object_id):
        line = self.env['account.report.standard.ledger.line'].search(
            [('type', 'in', ['4_total']), ('report_id', '=', self.report_id.id), ('account_id', '=', account_id)])
        query = """
        SELECT
            COALESCE(SUM(debit), 0) AS debit,
            COALESCE(SUM(credit), 0) AS credit,
            COALESCE(SUM(balance), 0) AS balance
        FROM
            account_report_standard_ledger_line
        WHERE
            report_id = %s
            AND account_id = %s
            AND type = '2_line'
            AND report_object_id IS NOT NULL
        """
        params = [
            # WHERE
            self.report_id.id,
            account_id,
        ]
        self.env.cr.execute(query, tuple(params))
        line_moves_balance = self.env.cr.fetchone()
        account = self.env['account.account'].browse(account_id)
        child_lines = self.env['account.report.standard.ledger.line'].search(
            [('type', 'in', ['4_total']), ('report_id', '=', self.report_id.id), ('account_id', 'in', account.child_ids.ids)])
        debit = sum([l.debit for l in child_lines]) + line_moves_balance[0]
        credit = sum([l.credit for l in child_lines]) + line_moves_balance[1]
        init_debit = sum([l.init_debit for l in child_lines])
        init_credit = sum([l.init_credit for l in child_lines])
        balance = sum([l.balance for l in child_lines]) + line_moves_balance[2]
        vals = {'type_view': 'total',
                'type': '4_total',
                'report_id': report_id,
                'account_id': account_id,
                'report_object_id': report_object_id,
                'debit': debit,
                'credit': credit,
                'balance': balance,
                'init_debit': init_debit,
                'init_credit': init_credit,
                }
        if line:
            line.write(vals)
        else:
            line = self.env['account.report.standard.ledger.line'].create(vals)
        return line

    @api.one
    def compute_parents(self):
        if self.account_id.parent_id:
            parent_line = self.compute_line(self.account_id.parent_id.id, self.report_id.id, self.report_object_id.id)
            if parent_line:
                parent_line.compute_parents()


class AccountStandardLedgerReportObject(models.TransientModel):
    _name = 'account.report.standard.ledger.report.object'
    _order = 'name, id'

    name = fields.Char()
    object_id = fields.Integer()
    report_id = fields.Many2one('account.report.standard.ledger.report')
    line_ids = fields.One2many('account.report.standard.ledger.line', 'report_object_id')
    account_id = fields.Many2one('account.account', 'Account')
    journal_id = fields.Many2one('account.journal', 'Journal')
    partner_id = fields.Many2one('res.partner', 'Partner')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    analytic_id = fields.Many2one('account.analytic.tag', 'Sub account')
    employee_id = fields.Many2one('hr.employee', 'Employee')


class AccountStandardLedger(models.TransientModel):
    _name = 'account.report.standard.ledger'
    _description = 'Account Standard Ledger'
    _order = "sequence, id"

    sequence = fields.Integer('Sequence', default=10)

    def _get_periode_date(self):
        lang_code = self.env.user.lang or 'en_US'
        lang_id = self.env['res.lang']._lang_get(lang_code)
        date_format = lang_id.date_format

        today_year = fields.datetime.now().year
        company = self.env.user.company_id
        last_day = company.fiscalyear_last_day or 31
        last_month = company.fiscalyear_last_month or 12

        periode_obj = self.env['account.report.standard.ledger.periode']
        periode_obj.search([]).unlink()
        periode_ids = periode_obj
        for year in range(today_year, today_year - 4, -1):
            date_from = datetime(year - 1, last_month, last_day) + timedelta(days=1)
            date_to = datetime(year, last_month, last_day)
            user_periode = "%s - %s" % (date_from.strftime(date_format),
                                        date_to.strftime(date_format),
                                        )
            vals = {
                'name': user_periode,
                'date_from': date_from.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'date_to': date_to.strftime(DEFAULT_SERVER_DATE_FORMAT), }
            periode_ids += periode_obj.create(vals)
        return False

    name = fields.Char(default='Standard Report')
    static = fields.Boolean('Static')
    type_ledger = fields.Selection([
        ('general', 'General Ledger'),
        ('partner', 'Partner Ledger'),
        ('journal', 'Journal Ledger'),
        # ('open', 'Open Ledger'),
        ('aged', 'Aged Balance'),
        ('analytic', 'Analytic Ledger'),
        ('sub_account', 'Sub account'),
        ('employees', 'Employees'),
    ], string='Type', default='general', required=True,
        help=' * General Ledger : Journal entries group by account\n'
             ' * Partner Leger : Journal entries group by partner, with only payable/recevable accounts\n'
             ' * Journal Ledger : Journal entries group by journal, without initial balance\n'
             ' * Open Ledger : Opening journal at Start date\n'
             ' * Analytic Ledger : Journal entries group by analytic account\n')
    summary = fields.Boolean('Trial Balance', default=False,
                             help=' * Check : generate a trial balance.\n'
                                  ' * Uncheck : detail report.\n')
    account_types = fields.Selection([('expense','Expense'),('income','Income')],default='')
    amount_currency = fields.Boolean("With Currency", help="It adds the currency column on report if the currency differs from the company currency.")
    reconciled = fields.Boolean('With Reconciled Entries', default=True,
                                help='Only for entrie with a payable/receivable account.\n'
                                     ' * Check this box to see un-reconcillied and reconciled entries with payable.\n'
                                     ' * Uncheck to see only un-reconcillied entries. Can be use only with parnter ledger.\n')
    partner_select_ids = fields.Many2many(comodel_name='res.partner', string='Partners',
                                          domain=['|', ('is_company', '=', True), ('parent_id', '=', False)],
                                          help='If empty, get all partners')
    account_methode = fields.Selection([('include', 'Include'), ('exclude', 'Exclude')], string="Methode")
    account_in_ex_clude = fields.Many2many(comodel_name='account.account', string='Accounts', help='If empty, get all accounts')
    analytic_account_select_ids = fields.Many2many(comodel_name='account.analytic.account', string='Analytic Accounts')
    taxes_select_ids = fields.Many2many(comodel_name='account.tax', string='Taxes')
    analytic_recursive = fields.Boolean('recursive', default=True)
    init_balance_history = fields.Boolean('Initial balance with history.', default=True,
                                          help=' * Check this box if you need to report all the debit and the credit sum before the Start Date.\n'
                                               ' * Uncheck this box to report only the balance before the Start Date\n')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self:
    self.env.user.company_id)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True,
                                          help='Utility field to express amount currency', store=True)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True,
                                   default=lambda self: self.env['account.journal'].search([('company_id', '=', self.env.user.company_id.id)]),
                                   help='Select journal, for the Open Ledger you need to set all journals.')
    date_from = fields.Date(string='Start Date', help='Use to compute initial balance.')
    date_to = fields.Date(string='End Date', help='Use to compute the entrie matched with future.')
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='all')
    periode_date = fields.Many2one('periods', 'Periode', default=_get_periode_date, help="Auto complete Start and End date.")
    month_selec = fields.Selection([(1, '01 Junary'), (2, '02 Febuary'), (3, '03 March'), (4, '04 April'), (5, '05 May'), (6, '06 June'),
                                    (7, '07 Jully'), (8, '08 August'), (9, '09 September'), (10, '10 October'), (11, '11 November'),
                                    (12, '12 December')],
                                   string='Month')
    result_selection = fields.Selection([('all', 'All'),
                                         ('customer', 'Customers'),
                                         ('supplier', 'Suppliers'),
                                         ('customer_supplier', 'Customers and Suppliers only')
                                         ], string="Partner's", required=True, default='customer_supplier')
    report_name = fields.Char('Report Name')
    compact_account = fields.Boolean('Compacte account.', default=False)
    report_id = fields.Many2one('account.report.standard.ledger.report')
    account_ids = fields.Many2many('account.account', relation='table_standard_report_accounts')
    partner_ids = fields.Many2many('res.partner', relation='table_standard_report_partner')
    analytic_ids = fields.Many2many('account.analytic.tag', string='Tags', relation='table_standard_report_analytic')
    # employee_ids = fields.Many2many('hr.employee', string='Employees', relation='table_standard_report_employee')
    employee_ids = fields.Many2many('hr.employee', string='Employees', relation='table_standard_report_employee', domain=['|', ('active', '=', True), ('active', '=', False)])
    
    type = fields.Selection([('account', 'Account'), ('partner', 'Partner'), ('journal', 'Journal'), ('analytic', 'Analytic'),
                             ('sub_account', 'Sub account'),
                             ('employees', 'Employees'), ])
    level = fields.Integer('Level', default=5)\

    @api.onchange('account_types')
    def required_accounts(self):
        account_list = []
        if self.account_types:
            accounts = self.env['account.account'].search([])
            if self.account_types == 'expense':
                selected_accounts = accounts.filtered(lambda x:x.user_type_id.location == 'expense')
            if self.account_types == 'income':
                selected_accounts = accounts.filtered(lambda x:x.user_type_id.location == 'income')
            for rec in selected_accounts:
                account_list.append(rec.id)
        return {'domain': {'account_in_ex_clude': [('id', 'in',account_list)]}}


    @api.multi
    def save_report(self):
        pass

    @api.one
    @api.constrains('level')
    def check_level(self):
        if self.level < 0:
            raise UserError('Level can not be minus')

    @api.onchange('account_in_ex_clude')
    def on_change_summary(self):
        list=[]
        if self.account_in_ex_clude:
            self.account_methode = 'include'
        else:
            self.account_methode = False
        accounts = self.env['account.account'].search([('company_id','=',self.company_id.id)])
        for item in accounts:
            list.append(item.id)
        return {'domain': {'account_in_ex_clude': [('id', 'in', list)]}}

    @api.onchange('type_ledger')
    def on_change_type_ledger(self):
        if self.type_ledger in ('partner', 'journal', 'open', 'aged'):
            self.compact_account = False
        if self.type_ledger == 'aged':
            self.date_from = False
            self.reconciled = False
        else:
            # self.on_change_periode_date()
            self.on_change_month_selec()
        if self.type_ledger not in ('partner', 'aged',):
            self.reconciled = True
            return {'domain': {'account_in_ex_clude': []}}
        self.account_in_ex_clude = False
        if self.result_selection == 'supplier':
            return {'domain': {'account_in_ex_clude': [('type_third_parties', '=', 'supplier')]}}
        if self.result_selection == 'customer':
            return {'domain': {'account_in_ex_clude': [('type_third_parties', '=', 'customer')]}}
        return {'domain': {'account_in_ex_clude': [('type_third_parties', 'in', ('supplier', 'customer'))]}}

    @api.onchange('periode_date')
    def on_change_periode_date(self):
        if self.periode_date:
            self.fiscal_year = False
            if self.custom_report and self.custom_report_type == 'no_date_range':
                self.date_from = False
            else:
                self.date_from = self.periode_date.date_start
            self.date_to = self.periode_date.date_end
            if self.month_selec:
                self.on_change_month_selec()

    @api.onchange('month_selec')
    def on_change_month_selec(self):
        if self.periode_date and self.month_selec:
            date_from = datetime.strptime(self.periode_date.date_start, DEFAULT_SERVER_DATE_FORMAT)
            date_from = datetime(date_from.year, self.month_selec, 1)
            date_to = datetime(date_from.year, self.month_selec, calendar.monthrange(date_from.year, self.month_selec)[1])
            if self.custom_report_type == 'no_date_range':
                self.date_from = False
            else:
                self.date_from = date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
            self.date_to = date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
        elif self.periode_date and not self.month_selec:
            self.on_change_periode_date()

    @api.multi
    def action_view_lines(self):
        self.ensure_one()
        self._compute_data()
        return {
            'name': self.report_id.name,
            'view_type': 'form',
            'view_mode': 'tree,form,pivot',
            'views': [(self.env.ref('account_standard_report.view_aged_tree').id if self.type_ledger == 'aged' else False, 'tree'), (False, 'form')],
            'res_model': 'account.report.standard.ledger.line',
            'type': 'ir.actions.act_window',
            'domain': "[('report_id','=',%s),('type','not in',('5_super_total','4_total'))]" % (self.report_id.id),
            'context': {'search_default_%s' % self.type_ledger: 1},
            'target': 'current',
        }

    @api.multi
    def print_pdf_report(self):
        self.ensure_one()
        self._compute_data()
        return self.env.ref('account_standard_report.action_standard_report').report_action(self.id, data={})
        # return self.env['report'].get_action(self, 'account_standard_report.report_account_standard_report')

    @api.multi
    def print_excel_report(self):
        self.ensure_one()
        if self.type_ledger != 'custom':
            self._compute_data()
        return self.env.ref('account_standard_report.action_standard_excel').report_action(self.id, data={})
        # return self.env['report'].get_action(self, '')

    def _pre_compute(self):
        lang_code = self.env.context.get('lang') or 'en_US'
        lang_id = self.env['res.lang']._lang_get(lang_code)
        date_format = lang_id.date_format
        time_format = lang_id.time_format

        vals = {'report_name': self._get_name_report(),
                'name': self._get_name_report(),
                'print_time': '%s' % fields.Datetime.context_timestamp(self.with_context(tz=self.env.user.tz), datetime.now()).strftime(
                    ('%s %s') % (date_format, time_format)),
                'date_to': __(self.date_to) if __(self.date_to) else "2099-01-01",
                'date_from': __(self.date_from) if __(self.date_from) else "1970-01-01",
                }
        self.report_id = self.env['account.report.standard.ledger.report'].create(vals)
        self.account_ids = self._search_account()
        self.partner_ids = self._search_partner()
        self.analytic_account_ids = self._search_analytic_account()

        if self.type_ledger in ('general', 'open'):
            self.type = 'account'
        elif self.type_ledger in ('partner', 'aged'):
            self.type = 'partner'
        elif self.type_ledger == 'analytic':
            self.type = 'analytic'
        elif self.type_ledger == 'sub_account':
            self.type = 'sub_account'
        elif self.type_ledger == 'employees':
            self.type = 'employees'
        else:
            self.type = 'journal'

        if self.type_ledger in ('partner', 'journal', 'open', 'aged', 'analytic'):
            self.compact_account = False
        if self.type_ledger not in ('partner', 'aged',):
            self.reconciled = True
            # self.partner_select_ids = False

    @api.model
    def _general_where_cluster(self, aml='aml', start_with_and=True, type=False):
        res = ''

        def and_():
            x = ' and ' if res or start_with_and else ''
            return x

        # Sub account
        if self.type_ledger == 'sub_account':
            res += "%s %s.tags_str is not null" % (and_(), aml)
        if self.analytic_ids:
            x = " or ".join(["%s.tags_str ilike  '%%%%;'|| %s || ';%%%%'" % (aml, tag.id) for tag in self.analytic_ids])
            res += ' %s ( %s )' % (
                and_(), x)

        #Taxes
        if self.taxes_select_ids:
            x = " or ".join(["%s.tax_ids.name ilike  '%%%%;'|| %s || ';%%%%'" % (aml, tax.id) for tax in self.taxes_select_ids])
            res += ' %s ( %s )' % (
                and_(), x)
        # Employees
        if self.type_ledger == 'employees':
            res += ' %s %s.employee_id is not null' % (and_(), aml,)
        if self.employee_ids:
            res += ' %s %s.employee_id in %s' % (
                and_(), aml, len(self.employee_ids.ids) > 1 and tuple(self.employee_ids.ids) or '(%s)' % self.employee_ids[0].id)
        # Analytic account
        if self.type_ledger == 'analytic':
            res += ' %s %s.analytic_account_id is not null' % (and_(), aml,)

        if self.analytic_account_select_ids:
            if self.analytic_recursive:  # and (type != 'object' or self.type_ledger != 'analytic'):
                if self.analytic_account_select_ids:
                    aa_res = []
                    for a_id in self.analytic_account_select_ids.ids:
                        aa_res.append("%s.analytic_parent_ids_str ilike '%%%%;%s;%%%%'" % (aml, a_id,))
                    if aa_res:
                        res += " %s  (%s)" % (and_(), ' OR '.join(aa_res))
            else:
                res += ' %s %s.analytic_account_id in %s' % (and_(), aml,
                                                             len(self.analytic_account_select_ids.ids) > 1 and tuple(
                                                                 self.analytic_account_select_ids.ids) or '(%s)' %
                                                             self.analytic_account_select_ids[0].id)
        # Partners
        if self.partner_select_ids:
            res += '%s %s.partner_id in %s' % \
                   (and_(), aml, len(self._search_partner().ids) > 1 and tuple(self._search_partner().ids) or '(%s)' % self._search_partner()[0].id)
        return res + ' '

    def _compute_data(self):
        if not self.user_has_groups('account.group_account_user'):
            raise UserError(_('Your are not an accountant !'))
        self._pre_compute()
        if self.type != 'sub_account':
            self._sql_report_object()
        else:
            self._sql_report_object_tags()
        if self.type == 'account':
            self._sql_unaffected_earnings()
        if self.type in ('account', 'partner', 'sub_account', 'employees', 'analytic') and self.type_ledger != 'aged':
            self._sql_init_balance()
        # if self.type != 'sub_account':
        # else:
        #     self._sql_init_balance_tags()
        self._sql_lines()
        if self.compact_account and self.type_ledger == 'account':
            self._sql_lines_compacted()
        self._sql_total()
        self._sql_super_total()
        self.refresh()

        # complet total line
        line_obj = self.env['account.report.standard.ledger.line']
        self.report_id.line_total_ids = line_obj.search([('report_id', '=', self.report_id.id), ('type', '=', '4_total')])
        self.report_id.line_super_total_id = line_obj.search([('report_id', '=', self.report_id.id), ('type', '=', '5_super_total')], limit=1)
        self._format_total()
        # //////////////  compute Parents ///////////////////////////////
        lines = self.env['account.report.standard.ledger.line'].search([('type', 'in', ['4_total']), ('report_id', '=', self.report_id.id)])
        # for line in lines:
        #     line.compute_parents()

    def _sql_report_object(self):
        query = """INSERT INTO  account_report_standard_ledger_report_object (report_id, create_uid, create_date, object_id, name, account_id, partner_id, journal_id, analytic_account_id, analytic_id, employee_id)
            SELECT DISTINCT 
                %s AS report_id,
                %s AS create_uid,
                NOW() AS create_date,
                CASE
                    WHEN %s = 'account' THEN aml.account_id
                    WHEN %s = 'partner' THEN aml.partner_id
                    WHEN %s = 'analytic' THEN an_acc.id
                    WHEN %s = 'sub_account' THEN aml.analytic_id
                    WHEN %s = 'employees' THEN aml.employee_id
                    ELSE aml.journal_id
                END AS object_id,
                CASE
                    WHEN %s = 'account' THEN acc.final_code || ' ' || acc.name
                    WHEN %s = 'partner' THEN CASE WHEN rep.ref IS NULL THEN rep.name ELSE rep.ref || ' ' || rep.name END
                    WHEN %s = 'analytic' THEN CASE WHEN an_acc.final_code IS NULL THEN an_acc.name ELSE an_acc.final_code || ' ' || an_acc.final_code END
                    WHEN %s = 'sub_account' THEN sub_account.name
                    WHEN %s = 'employees' THEN emp.name
                    ELSE acj.code || ' ' || acj.name
                END AS name,
                CASE WHEN %s = 'account' THEN aml.account_id ELSE NULL END AS account_id,
                CASE WHEN %s = 'partner' THEN aml.partner_id ELSE NULL END AS partner_id,
                CASE WHEN %s = 'journal' THEN aml.journal_id ELSE NULL END AS journal_id,
                CASE WHEN %s = 'analytic' THEN an_acc.id ELSE NULL END AS analytic_account_id,
                CASE WHEN %s = 'sub_account' THEN aml.analytic_id ELSE NULL END AS analytic_id,
                CASE WHEN %s = 'employees' THEN aml.employee_id ELSE NULL END AS employee_id
            FROM
                account_move_line aml
                LEFT JOIN account_account acc ON (acc.id = aml.account_id)
                LEFT JOIN res_partner rep ON (rep.id = aml.partner_id)
                LEFT JOIN account_journal acj ON (acj.id = aml.journal_id)
                FULL OUTER JOIN account_analytic_account an_acc ON (CASE
                  WHEN %s = 'analytic' THEN (aml.analytic_parent_ids_str ilike '%%;'|| an_acc.id || ';%%' and an_acc.id in %s)
                  ELSE an_acc.id = aml.analytic_account_id END)
                LEFT JOIN move_line_tags sub_account ON (sub_account.id = aml.analytic_id)
                LEFT JOIN hr_employee emp ON (emp.id = aml.employee_id)
            WHERE
                aml.company_id = %s
                AND aml.journal_id IN %s
                AND aml.account_id IN %s
                AND (%s IN ('account','journal','analytic','sub_account','employees') OR aml.partner_id IN %s)
                --AND (%s != 'analytic' OR aml.analytic_account_id IN %s)
                """ + self._general_where_cluster(type='object') + """
            ORDER BY
                name
                """
        params = [
            # SELECT
            self.report_id.id,
            self.env.uid,
            self.type, self.type, self.type, self.type, self.type,
            self.type, self.type, self.type, self.type, self.type,
            self.type, self.type, self.type, self.type, self.type, self.type,
            # FROM
            self.type, tuple(self.analytic_account_ids.ids) if self.analytic_account_ids else (None,),
            # WHERE
            self.company_id.id,
            tuple(self.journal_ids.ids) if self.journal_ids else (None,),
            tuple(self.account_ids.ids) if self.account_ids else (None,),
            self.type,
            tuple(self.partner_ids.ids) if self.partner_ids else (None,),
            self.type,
            tuple(self.analytic_account_ids.ids) if self.analytic_account_ids else (None,),
        ]

        self.env.cr.execute(query, tuple(params))
        # res = self.env.cr.dictfetchall()
        # print res
        pass

    def _sql_unaffected_earnings(self):
        company = self.company_id
        unaffected_earnings_account = self.env['account.account'].search(
            [('company_id', '=', company.id), ('user_type_id', '=', self.env.ref('account.data_unaffected_earnings').id)], limit=1)
        if unaffected_earnings_account not in self.account_ids:
            return

        report_object_id = self.report_id.report_object_ids.filtered(lambda x: x.object_id == unaffected_earnings_account.id)
        if not report_object_id:
            report_object_id = self.report_id.report_object_ids.create({'report_id': self.report_id.id,
                                                                        'object_id': unaffected_earnings_account.id,
                                                                        'name': '%s %s' % (
                                                                            unaffected_earnings_account.final_code, unaffected_earnings_account.name),
                                                                        'account_id': unaffected_earnings_account.id})
        query = """
        INSERT INTO account_report_standard_ledger_line
            (report_id, create_uid, create_date, account_id, type, type_view, date, debit, credit, balance, cumul_balance, company_currency_id, reconciled, report_object_id)
        SELECT
            %s AS report_id,
            %s AS create_uid,
            NOW() AS create_date,
            %s AS account_id,
            '0_init' AS type,
            'init' AS type_view,
            %s AS date,
            CASE WHEN %s THEN COALESCE(SUM(aml.debit), 0) ELSE CASE WHEN COALESCE(SUM(aml.balance), 0) <= 0 THEN 0 ELSE COALESCE(SUM(aml.balance), 0) END END AS debit,
            CASE WHEN %s THEN COALESCE(SUM(aml.credit), 0) ELSE CASE WHEN COALESCE(SUM(aml.balance), 0) >= 0 THEN 0 ELSE COALESCE(-SUM(aml.balance), 0) END END AS credit,
            COALESCE(SUM(aml.balance), 0) AS balance,
            COALESCE(SUM(aml.balance), 0) AS cumul_balance,
            %s AS company_currency_id,
            FALSE as reconciled,
            %s AS report_object_id
        FROM
            account_move_line aml
            LEFT JOIN account_account acc ON (aml.account_id = acc.id)
            LEFT JOIN account_account_type acc_type ON (acc.user_type_id = acc_type.id)
            LEFT JOIN account_move m ON (aml.move_id = m.id)
        WHERE
            m.state IN %s
            AND aml.company_id = %s
            AND aml.date < %s
            AND acc_type.include_initial_balance = FALSE
        HAVING
            CASE
                WHEN %s = FALSE THEN ABS(SUM(aml.balance)) > %s
                ELSE ABS(SUM(aml.debit)) > %s OR ABS(SUM(aml.debit)) > %s OR ABS(SUM(aml.balance)) > %s
            END
        """

        date_from_fiscal = self.company_id.compute_fiscalyear_dates(datetime.strptime(__(self.report_id.date_from), DEFAULT_SERVER_DATE_FORMAT))[
            'date_from']

        params = [
            # SELECT
            self.report_id.id,
            self.env.uid,
            unaffected_earnings_account.id,
            date_from_fiscal,
            self.init_balance_history,
            self.init_balance_history,
            self.company_currency_id.id,
            report_object_id.id,
            # WHERE
            ('posted',) if self.target_move == 'posted' else ('posted', 'draft',),
            company.id,
            __(self.report_id.date_from),
            # HAVING
            self.init_balance_history,
            self.company_currency_id.rounding, self.company_currency_id.rounding, self.company_currency_id.rounding,
            self.company_currency_id.rounding,
        ]

        self.env.cr.execute(query, tuple(params))

    def _sql_init_balance(self):
        company = self.company_id
        # initial balance partner
        query = """ 
        INSERT INTO account_report_standard_ledger_line(report_id, create_uid, create_date, account_id, partner_id, analytic_id, employee_id,  analytic_account_id, type, type_view, date, debit, credit, balance, cumul_balance, company_currency_id, reconciled, report_object_id)
        WITH matching_in_futur_before_init (id) AS
        (
        SELECT DISTINCT
            afr.id as id
        FROM
            account_full_reconcile afr
        INNER JOIN account_move_line aml ON aml.full_reconcile_id=afr.id
        WHERE
            aml.company_id = %s
            AND aml.date >= %s
        )
        SELECT
            %s AS report_id,
            %s AS create_uid,
            NOW() AS create_date,
            MIN(aml.account_id),
            CASE WHEN %s = 'partner' THEN MIN(aml.partner_id) ELSE NULL END,
            CASE WHEN %s = 'sub_account' THEN MIN(ro.object_id) ELSE NULL END,
            CASE WHEN %s = 'employees' THEN MIN(aml.employee_id) ELSE NULL END,
            CASE WHEN %s = 'analytic' THEN MIN(aml.analytic_account_id) ELSE NULL END,
            '0_init' AS type,
            'init' AS type_view,
            %s AS date,
            CASE WHEN %s THEN COALESCE(SUM(aml.debit), 0) ELSE CASE WHEN COALESCE(SUM(aml.balance), 0) <= 0 THEN 0 ELSE COALESCE(SUM(aml.balance), 0) END END AS debit,
            CASE WHEN %s THEN COALESCE(SUM(aml.credit), 0) ELSE CASE WHEN COALESCE(SUM(aml.balance), 0) >= 0 THEN 0 ELSE COALESCE(-SUM(aml.balance), 0) END END AS credit,
            COALESCE(SUM(aml.balance), 0) AS balance,
            COALESCE(SUM(aml.balance), 0) AS cumul_balance,
            %s AS company_currency_id,
            FALSE as reconciled,
            MIN(ro.id) AS report_object_id
        FROM
            account_report_standard_ledger_report_object ro
            INNER JOIN account_move_line aml ON (CASE
                WHEN %s = 'account' THEN aml.account_id = ro.object_id
                WHEN %s = 'analytic' THEN CASE
                  WHEN %s = TRUE THEN aml.analytic_parent_ids_str  ilike '%%;'|| ro.object_id || ';%%'
                  ELSE aml.analytic_account_id = ro.object_id  END
                WHEN %s = 'sub_account' THEN aml.tags_str ilike '%%;'|| ro.object_id || ';%%'
                WHEN %s = 'employees' THEN aml.employee_id = ro.object_id
                ELSE aml.partner_id = ro.object_id END)
            LEFT JOIN account_account acc ON (aml.account_id = acc.id)
            LEFT JOIN account_account_type acc_type ON (acc.user_type_id = acc_type.id)
            LEFT JOIN account_move m ON (aml.move_id = m.id)
            LEFT JOIN matching_in_futur_before_init mif ON (aml.full_reconcile_id = mif.id)
       	WHERE
            m.state IN %s
            AND ro.report_id = %s
            AND aml.company_id = %s
            AND aml.date < %s
            --AND acc_type.include_initial_balance = TRUE
            AND aml.journal_id IN %s
            AND aml.account_id IN %s
            --AND (%s != 'analytic' OR aml.analytic_account_id IN %s)
            AND (%s IN ('account', 'journal', 'sub_account', 'employees','analytic') OR aml.partner_id IN %s)
            --AND ((%s AND acc.compacted = TRUE) OR acc.type_third_parties = 'no' OR (aml.full_reconcile_id IS NOT NULL AND mif.id IS NULL))
            """ + self._general_where_cluster() + """
        GROUP BY
            ro.object_id 
        HAVING
            CASE
                WHEN %s = FALSE THEN ABS(SUM(aml.balance)) > %s
                ELSE ABS(SUM(aml.debit)) > %s OR ABS(SUM(aml.debit)) > %s OR ABS(SUM(aml.balance)) > %s
            END
            """
        params = [
            # matching_in_futur
            company.id,
            __(self.report_id.date_from),
            # init_account_table
            # SELECT
            self.report_id.id,
            self.env.uid,
            self.type, self.type, self.type, self.type,  # self.type, self.type, self.type, self.type,
            __(self.report_id.date_from),
            self.init_balance_history,
            self.init_balance_history,
            self.company_currency_id.id,
            # FROM
            self.type, self.type, self.analytic_recursive, self.type, self.type,
            # WHERE
            ('posted',) if self.target_move == 'posted' else ('posted', 'draft',),
            self.report_id.id,
            company.id,
            __(self.report_id.date_from),
            tuple(self.journal_ids.ids) if self.journal_ids else (None,),
            tuple(self.account_ids.ids) if self.account_ids else (None,),
            self.type, tuple(self.analytic_account_ids.ids) if self.analytic_account_ids else (None,),
            self.type, tuple(self.partner_ids.ids) if self.partner_ids else (None,),
            self.compact_account,

            # HAVING
            self.init_balance_history,
            self.company_currency_id.rounding, self.company_currency_id.rounding, self.company_currency_id.rounding,
            self.company_currency_id.rounding,
        ]

        self.env.cr.execute(query, tuple(params))
        # res = self.env.cr.dictfetchall()
        # print res
        pass

    def _sql_lines(self):
        # lines_table
        query = """
        INSERT INTO account_report_standard_ledger_line
         (report_id, create_uid, create_date, account_id, analytic_account_id, type, type_view, journal_id, partner_id, move_id,label,doctype, move_line_id,
         date, date_maturity, debit, credit, balance, full_reconcile_id, reconciled, report_object_id, cumul_balance, init_debit, init_credit, current,
         age_30_days, age_60_days, age_90_days, age_120_days, older, company_currency_id, amount_currency, currency_id, analytic_id, employee_id)
        WITH matching_in_futur_before_init (id) AS
        (
            SELECT DISTINCT
                afr.id AS id
            FROM
                account_full_reconcile afr
            INNER JOIN account_move_line aml ON aml.full_reconcile_id=afr.id
            WHERE
                aml.company_id = %s
                AND aml.date >= %s
        ),
        matching_in_futur_after_date_to (id) AS
        (
            SELECT DISTINCT
                afr.id AS id
            FROM
                account_full_reconcile afr
                INNER JOIN account_move_line aml ON aml.full_reconcile_id = afr.id
            WHERE
                aml.company_id = %s
                AND aml.date > %s --date_to
        ),
        initial_balance (id, balance) AS
        (
            SELECT
                MIN(report_object_id) AS id,
                COALESCE(SUM(balance), 0) AS balance,
                COALESCE(SUM(debit), 0) AS debit,
                COALESCE(SUM(credit), 0) AS credit
            FROM
                account_report_standard_ledger_line
            WHERE
                report_id = %s
                AND type = '0_init'
            GROUP BY
                report_object_id
        ),
        date_range AS
            (
            SELECT
                %s AS date_current,
                DATE %s - INTEGER '30' AS date_less_30_days,
                DATE %s - INTEGER '60' AS date_less_60_days,
                DATE %s - INTEGER '90' AS date_less_90_days,
                DATE %s - INTEGER '120' AS date_less_120_days,
                DATE %s - INTEGER '150' AS date_older
            )
        SELECT
            %s AS report_id,
            %s AS create_uid,
            NOW() AS create_date,
            aml.account_id,
            aml.analytic_account_id,
            CASE WHEN aml.date >= %s THEN '2_line' ELSE '1_init_line' END AS type,
            CASE WHEN aml.date >= %s THEN 'normal' ELSE 'init' END AS type_view,
            aml.journal_id,
            aml.partner_id,
            aml.move_id,
            aml.name,
            aml.doctype,
            aml.id,
            aml.date,
            aml.date_maturity,
            aml.debit,
            aml.credit,
            aml.balance,
            aml.full_reconcile_id,
            CASE WHEN aml.full_reconcile_id is NOT NULL AND NOT mifad.id IS NOT NULL THEN TRUE ELSE FALSE END AS reconciled,
            ro.id AS report_object_id,
            CASE
                WHEN %s = 'account' THEN COALESCE(init.balance, 0) + (SUM(aml.balance) OVER (PARTITION BY aml.account_id ORDER BY aml.account_id, aml.date, aml.id))
                WHEN %s = 'partner' THEN COALESCE(init.balance, 0) + (SUM(aml.balance) OVER (PARTITION BY aml.partner_id ORDER BY aml.partner_id, aml.date, aml.id))
                WHEN %s = 'analytic' THEN COALESCE(init.balance, 0) + (SUM(aml.balance) OVER (PARTITION BY ro.analytic_account_id ORDER BY ro.analytic_account_id, aml.date, aml.id))
                WHEN %s = 'sub_account' THEN COALESCE(init.balance, 0) + (SUM(aml.balance) OVER (PARTITION BY ro.analytic_id ORDER BY ro.analytic_id, aml.date, aml.id))
                WHEN %s = 'employees' THEN COALESCE(init.balance, 0) + (SUM(aml.balance) OVER (PARTITION BY aml.employee_id ORDER BY aml.employee_id, aml.date, aml.id))
                ELSE SUM(aml.balance) OVER (PARTITION BY aml.journal_id ORDER BY aml.journal_id, aml.date, aml.id)
            END AS cumul_balance,
            COALESCE(init.debit, 0) AS init_debit,
            COALESCE(init.credit, 0) AS init_credit,
            CASE WHEN aml.date_maturity > date_range.date_less_30_days THEN aml.balance END AS current,
            CASE WHEN aml.date_maturity > date_range.date_less_60_days AND aml.date_maturity <= date_range.date_less_30_days THEN aml.balance END AS age_30_days,
            CASE WHEN aml.date_maturity > date_range.date_less_90_days AND aml.date_maturity <= date_range.date_less_60_days THEN aml.balance END AS age_60_days,
            CASE WHEN aml.date_maturity > date_range.date_less_120_days AND aml.date_maturity <= date_range.date_less_90_days THEN aml.balance END AS age_90_days,
            CASE WHEN aml.date_maturity > date_range.date_older AND aml.date_maturity <= date_range.date_less_120_days THEN aml.balance END AS age_120_days,
            CASE WHEN aml.date_maturity <= date_range.date_older THEN aml.balance END AS older,
            %s AS company_currency_id,
            aml.amount_currency AS amount_currency,
            aml.currency_id AS currency_id,
            aml.analytic_id,
            aml.employee_id
        FROM
            date_range,
            account_report_standard_ledger_report_object ro
            INNER JOIN account_move_line aml ON (
                CASE
                    WHEN %s = 'account' THEN aml.account_id = ro.object_id
                    WHEN %s = 'partner' THEN aml.partner_id = ro.object_id
                    WHEN %s = 'analytic' THEN CASE
                      WHEN %s = TRUE THEN aml.analytic_parent_ids_str ilike '%%;'|| ro.analytic_account_id || ';%%'
                      ELSE aml.analytic_account_id = ro.object_id  END
                    WHEN %s = 'sub_account' THEN aml.tags_str ilike '%%;'|| ro.object_id || ';%%'
                    WHEN %s = 'employees' THEN aml.employee_id = ro.object_id
                    ELSE aml.journal_id = ro.object_id
                END)
            LEFT JOIN account_journal j ON (aml.journal_id = j.id)
            LEFT JOIN account_account acc ON (aml.account_id = acc.id)
            LEFT JOIN account_account_type acc_type ON (acc.user_type_id = acc_type.id)
            LEFT JOIN account_move m ON (aml.move_id = m.id)
            LEFT JOIN matching_in_futur_before_init mif ON (aml.full_reconcile_id = mif.id)
            LEFT JOIN matching_in_futur_after_date_to mifad ON (aml.full_reconcile_id = mifad.id)
            LEFT JOIN initial_balance init ON (ro.id = init.id)
        WHERE
            m.state IN %s
            AND ro.report_id = %s
            AND aml.company_id = %s
            AND (CASE
                    WHEN %s = 'journal' THEN aml.date >= %s
                    WHEN aml.date >= %s THEN %s != 'open'
                    ELSE 1 = 2 -- acc.type_third_parties IN ('supplier', 'customer') AND (aml.full_reconcile_id IS NULL OR mif.id IS NOT NULL)
                END)
            AND aml.date <= %s
            AND aml.journal_id IN %s
            AND aml.account_id IN %s
            AND (%s IN ('account','journal','analytic','sub_account','employees') OR aml.partner_id IN %s)
            --AND (%s != 'analytic' OR aml.analytic_account_id IN %s)
            AND NOT (%s AND acc.compacted = TRUE)
            AND (%s OR NOT (aml.full_reconcile_id is NOT NULL AND NOT mifad.id IS NOT NULL))
            """ + self._general_where_cluster() + """
        ORDER BY
            aml.date, aml.id
        """
        params = [
            # matching_in_futur init
            self.company_id.id,
            __(self.report_id.date_from),
            # matching_in_futur date_to
            self.company_id.id,
            __(self.report_id.date_to),
            # initial_balance
            self.report_id.id,
            # date_range
            __(self.report_id.date_to), __(self.report_id.date_to), __(self.report_id.date_to), __(self.report_id.date_to),
            __(self.report_id.date_to), __(self.report_id.date_to),
            # lines_table
            # SELECT
            self.report_id.id,
            self.env.uid,
            __(self.report_id.date_from),
            __(self.report_id.date_from),
            self.type, self.type, self.type, self.type, self.type,
            self.company_currency_id.id,
            # FROM
            self.type, self.type, self.type, self.analytic_recursive, self.type, self.type,

            # WHERE
            ('posted',) if self.target_move == 'posted' else ('posted', 'draft',),
            self.report_id.id,
            self.company_id.id,
            self.type, __(self.report_id.date_from),
            __(self.report_id.date_from),
            self.type_ledger,
            __(self.report_id.date_to),
            tuple(self.journal_ids.ids) if self.journal_ids else (None,),
            tuple(self.account_ids.ids) if self.account_ids else (None,),
            self.type, tuple(self.partner_ids.ids) if self.partner_ids else (None,),
            self.type, tuple(self.analytic_account_ids.ids) if self.analytic_account_ids else (None,),
            self.compact_account,
            self.reconciled,
        ]
        # self.type,
        self.env.cr.execute(query, tuple(params))
        # res = self.env.cr.dictfetchall()
        # print res
        pass

    def _sql_lines_compacted(self):
        query = """
        INSERT INTO account_report_standard_ledger_line(report_id, create_uid, create_date, account_id, type, type_view, date, debit, credit, balance, cumul_balance, company_currency_id, report_object_id)

        WITH initial_balance (id, balance) AS
        (
        SELECT
            MIN(report_object_id) AS id,
            COALESCE(SUM(balance), 0) AS balance
        FROM
            account_report_standard_ledger_line
        WHERE
            report_id = %s
            AND type = '0_init'
        GROUP BY
            report_object_id
        )

        SELECT
            %s AS report_id,
            %s AS create_uid,
            NOW() AS create_date,
            MIN(aml.account_id) AS account_id,
            '3_compact' AS type,
            'normal' AS type_view,
            %s AS date,
            COALESCE(SUM(aml.debit), 0) AS debit,
            COALESCE(SUM(aml.credit), 0) AS credit,
            COALESCE(SUM(aml.balance), 0) AS balance,
            COALESCE(MIN(init.balance), 0) + COALESCE(SUM(aml.balance), 0) AS cumul_balance,
            %s AS company_currency_id,
            MIN(ro.id) AS report_object_id
        FROM
            account_report_standard_ledger_report_object ro
            INNER JOIN account_move_line aml ON (aml.account_id = ro.object_id)
            LEFT JOIN account_journal j ON (aml.journal_id = j.id)
            LEFT JOIN account_account acc ON (aml.account_id = acc.id)
            LEFT JOIN account_account_type acc_type ON (acc.user_type_id = acc_type.id)
            LEFT JOIN account_move m ON (aml.move_id = m.id)
            LEFT JOIN initial_balance init ON (ro.id = init.id)
        WHERE
            m.state IN %s
            AND ro.report_id = %s
            AND aml.company_id = %s
            AND aml.date >= %s
            AND aml.date <= %s
            AND aml.journal_id IN %s
            AND aml.account_id IN %s
            AND (%s AND acc.compacted = TRUE)
        GROUP BY
            aml.account_id
        """

        params = [
            # initial_balance
            self.report_id.id,

            # SELECT
            self.report_id.id,
            self.env.uid,
            __(self.report_id.date_from),
            self.company_currency_id.id,
            # FROM

            # WHERE
            ('posted',) if self.target_move == 'posted' else ('posted', 'draft',),
            self.report_id.id,
            self.company_id.id,
            __(self.report_id.date_from),
            __(self.report_id.date_to),
            tuple(self.journal_ids.ids) if self.journal_ids else (None,),
            tuple(self.account_ids.ids) if self.account_ids else (None,),
            self.compact_account,
        ]

        self.env.cr.execute(query, tuple(params))

    def _sql_total(self):
        query = """
        INSERT INTO account_report_standard_ledger_line
            (report_id, create_uid, create_date, account_id, partner_id, journal_id, analytic_account_id, type, type_view, date, debit, credit, balance, cumul_balance,
            init_debit,init_credit, report_object_id, current, age_30_days, age_60_days, age_90_days, age_120_days, older, company_currency_id)
        SELECT
            %s AS report_id,
            %s AS create_uid,
            NOW() AS create_date,
            CASE WHEN %s = 'account' THEN MIN(account_id) ELSE NULL END AS account_id,
            CASE WHEN %s = 'partner' THEN MIN(partner_id) ELSE NULL END AS partner_id,
            CASE WHEN %s = 'journal' THEN MIN(journal_id) ELSE NULL END AS journal_id,
            CASE WHEN %s = 'analytic' THEN MIN(analytic_account_id) ELSE NULL END AS analytic_account_id,
            '4_total' AS type,
            'total' AS type_view,
            %s AS date,
            COALESCE(SUM(debit), 0) AS debit,
            COALESCE(SUM(credit), 0) AS credit,
            COALESCE(SUM(balance), 0) AS balance,
            COALESCE(SUM(balance), 0) AS cumul_balance,
            COALESCE(MIN(init_debit), 0) AS init_debit,
            COALESCE(MIN(init_credit), 0) AS init_credit,
            MIN(report_object_id) AS report_object_id,
            COALESCE(SUM(current), 0) AS current,
            COALESCE(SUM(age_30_days), 0) AS age_30_days,
            COALESCE(SUM(age_60_days), 0) AS age_60_days,
            COALESCE(SUM(age_90_days), 0) AS age_90_days,
            COALESCE(SUM(age_120_days), 0) AS age_120_days,
            COALESCE(SUM(older), 0) AS older,
            %s AS company_currency_id
        FROM
            account_report_standard_ledger_line
        WHERE
            report_id = %s
            AND report_object_id IS NOT NULL
        GROUP BY
            report_object_id
        ORDER BY
            report_object_id
        """
        params = [
            # SELECT
            self.report_id.id,
            self.env.uid,
            self.type, self.type, self.type, self.type,
            __(self.report_id.date_from),
            self.company_currency_id.id,
            # WHERE
            self.report_id.id,
        ]
        self.env.cr.execute(query, tuple(params))

    def _sql_super_total(self):
        query = """
        INSERT INTO account_report_standard_ledger_line
            (report_id, create_uid, create_date, type, type_view, date, debit, credit, balance, cumul_balance, current, age_30_days, age_60_days, age_90_days, age_120_days, older, company_currency_id)
        SELECT
            %s AS report_id,
            %s AS create_uid,
            NOW() AS create_date,
            '5_super_total' AS type,
            'total' AS type_view,
            %s AS date,
            COALESCE(SUM(debit), 0) AS debit,
            COALESCE(SUM(credit), 0) AS credit,
            COALESCE(SUM(balance), 0) AS balance,
            COALESCE(SUM(balance), 0) AS cumul_balance,
            COALESCE(SUM(current), 0) AS current,
            COALESCE(SUM(age_30_days), 0) AS age_30_days,
            COALESCE(SUM(age_60_days), 0) AS age_60_days,
            COALESCE(SUM(age_90_days), 0) AS age_90_days,
            COALESCE(SUM(age_120_days), 0) AS age_120_days,
            COALESCE(SUM(older), 0) AS older,
            %s AS company_currency_id
        FROM
            account_report_standard_ledger_line
        WHERE
            report_id = %s
            AND type = '4_total'
        """
        params = [
            # SELECT
            self.report_id.id,
            self.env.uid,
            __(self.report_id.date_from),
            self.company_currency_id.id,
            self.report_id.id,
        ]
        self.env.cr.execute(query, tuple(params))

    def _search_account(self):
        type_ledger = self.type_ledger
        domain = [('deprecated', '=', False), ('company_id', '=', self.company_id.id)]
        if type_ledger in ('partner', 'aged',):
            result_selection = self.result_selection
            if result_selection == 'supplier':
                acc_type = ('supplier',)
            elif result_selection == 'customer':
                acc_type = ('customer',)
            elif result_selection == 'customer_supplier':
                acc_type = ('supplier', 'customer',)
            if result_selection not in [False, 'all']:
                domain.append(('type_third_parties', 'in', acc_type))

        account_in_ex_clude = self.account_in_ex_clude.ids
        acc_methode = self.account_methode
        if account_in_ex_clude:
            if acc_methode == 'include':
                domain.append(('id', 'in', account_in_ex_clude))
            elif acc_methode == 'exclude':
                domain.append(('id', 'not in', account_in_ex_clude))
        return self.env['account.account'].search(domain)

    def _search_analytic_account(self):
        if self.type_ledger == 'analytic':
            if self.analytic_account_select_ids:
                return self.analytic_account_select_ids
            else:
                return self.env['account.analytic.account'].search([])
        return False

    def _search_partner(self):
        # if self.type_ledger in ('partner', 'aged'):
        if self.partner_select_ids:
            return self.partner_select_ids
        return self.env['res.partner'].search([])
        return False

    def _get_name_report(self):
        report_name = D_LEDGER[self.type_ledger]['name']
        if self.summary:
            report_name += _(' Balance')
        return report_name

    def _sql_get_line_for_report(self, type_l, report_object=None):
        query = """SELECT
                    aml.report_object_id AS report_object_id,
                    aml.type_view AS type_view,
                    CASE
                        WHEN %s = 'account' THEN acc.final_code
                        WHEN %s = 'journal' THEN acj.code
                        WHEN %s = 'analytic' THEN an_acc.final_code
                        ELSE rep.ref
                    END AS code,
                    CASE
                        WHEN %s = 'account' THEN acc.name
                        WHEN %s = 'journal' THEN acj.name
                        WHEN %s = 'analytic' THEN an_acc.name
                        WHEN %s = 'sub_account' THEN mlt.name
                        WHEN %s = 'employees' THEN emp.employee_english_name
                        ELSE rep.name
                    END AS name,
                    acj.code AS j_code,
                    acc.final_code AS a_code,
                    acc.name AS a_name,
                    acc.level AS level,
                    an_acc.final_code AS an_code,
                    an_acc.name AS an_name,
                    aml.current AS current,
                    aml.age_30_days AS age_30_days,
                    aml.age_60_days AS age_60_days,
                    aml.age_90_days AS age_90_days,
                    aml.age_120_days AS age_120_days,
                    aml.older AS older,
                    aml.credit AS credit,
                    aml.debit AS debit,
                    antg.name AS tags,
                    actg.name AS tax,
                    aml.cumul_balance AS cumul_balance,
                    aml.init_debit AS init_debit,
                    aml.init_credit AS init_credit,
                    aml.balance AS balance,
                    ml.name AS move_name,
                    aml.label AS label,
                    aml.doctype AS doctype,
                    ml.ref AS displayed_name,
                    rep.name AS partner_name,
                    aml.date AS date,
                    aml.date_maturity AS date_maturity,
                    aml.amount_currency AS amount_currency,
                    cr.excel_format AS currency,
                    CASE
                        WHEN aml.full_reconcile_id IS NOT NULL THEN (CASE WHEN aml.reconciled = TRUE THEN afr.name ELSE '*' END)
                        ELSE ''
                    END AS matching_number
                FROM
                    account_report_standard_ledger_line aml
                    LEFT JOIN account_account acc ON (acc.id = aml.account_id)
                    LEFT JOIN account_journal acj ON (acj.id = aml.journal_id)
                    LEFT JOIN res_partner rep ON (rep.id = aml.partner_id)
                    LEFT JOIN account_move ml ON (ml.id = aml.move_id)
                    LEFT JOIN account_full_reconcile afr ON (aml.full_reconcile_id = afr.id)
                    LEFT JOIN account_analytic_account an_acc ON (aml.analytic_account_id = an_acc.id)
                    LEFT JOIN res_currency cr ON (aml.currency_id = cr.id)
                    LEFT JOIN hr_employee emp ON (aml.employee_id = emp.id)
                    LEFT JOIN account_analytic_tag_account_move_line_rel aatm ON (aml.move_line_id = aatm.account_move_line_id)
                    LEFT JOIN account_analytic_tag antg ON (aatm.account_analytic_tag_id = antg.id)
                    LEFT JOIN account_move_line_account_tax_rel actm ON (aml.move_line_id = actm.account_move_line_id)
                    LEFT JOIN account_tax actg ON (actm.account_tax_id = actg.id)
                    LEFT JOIN move_line_tags mlt ON (aml.analytic_id = mlt.id)
                WHERE
                    aml.report_id = %s
                    AND (%s OR aml.report_object_id = %s)
                    AND aml.type IN %s
                ORDER BY
                     aml.date, aml.id,acc.final_code
                """
        params = [
            self.type, self.type, self.type, self.type, self.type, self.type, self.type, self.type,
            self.report_id.id,
            True if report_object is None else False,
            report_object,
            type_l
        ]

        self.env.cr.execute(query, tuple(params))
        return self.env.cr.dictfetchall()

    def _format_total(self):
        if not self.company_currency_id:
            return
        lines = self.report_id.line_total_ids + self.report_id.line_super_total_id
        for line in lines:
            line.write({
                'debit': self.company_currency_id.round(line.debit) + 0.0,
                'credit': self.company_currency_id.round(line.credit) + 0.0,
                'balance': self.company_currency_id.round(line.balance) + 0.0,
                'current': self.company_currency_id.round(line.current) + 0.0,
                'age_30_days': self.company_currency_id.round(line.age_30_days) + 0.0,
                'age_60_days': self.company_currency_id.round(line.age_60_days) + 0.0,
                'age_90_days': self.company_currency_id.round(line.age_90_days) + 0.0,
                'age_120_days': self.company_currency_id.round(line.age_120_days) + 0.0,
                'older': self.company_currency_id.round(line.older) + 0.0,
            })

    def get_account_trial_balance(self, workbook):
        self._search_account()
        sql = """SELECT  COALESCE(SUM(debit), 0) AS debit,COALESCE(SUM(credit), 0) AS credit, aml.account_id AS acc, MAX(acc.final_code) as final_code,
                 MAX(acc.name) as acc_name
          FROM account_move_line aml
          LEFT JOIN account_move m ON (aml.move_id = m.id)
          LEFT JOIN account_account acc ON (aml.account_id = acc.id)
          WHERE
            m.state IN %s
            AND aml.company_id = %s
            AND aml.date < %s
            AND aml.journal_id IN %s
            AND aml.account_id IN %s
            AND aml.balanced = TRUE
        GROUP BY aml.account_id
        """
        params = [
            # init
            ('posted',) if self.target_move == 'posted' else ('posted', 'draft',),
            self.company_id.id,
            __(self.report_id.date_from),
            tuple(self.journal_ids.ids) if self.journal_ids else (None,),
            tuple(self.account_ids.ids) if self.account_ids else (None,),
        ]

        self.env.cr.execute(sql, params)
        init_rows = self.env.cr.dictfetchall()

        sql = """SELECT aml.account_id as account_id,COALESCE(SUM(aml.debit), 0) as debit,COALESCE(SUM(aml.credit), 0) as credit,
            MAX(acc.final_code) as final_code, MAX(acc.name) as acc_name
            FROM account_move_line aml
                LEFT JOIN account_move m ON (aml.move_id = m.id)
                LEFT JOIN account_account acc ON (acc.id = aml.account_id)
            WHERE
                    m.state IN %s
                    AND aml.company_id = %s
                    AND aml.date >= %s
                    AND aml.date <= %s
                    AND aml.journal_id IN %s
                    AND aml.account_id IN %s
                    AND aml.balanced = TRUE
            GROUP BY aml.account_id
        """
        params = [
            # WHERE
            ('posted',) if self.target_move == 'posted' else ('posted', 'draft',),
            self.company_id.id,
            __(self.report_id.date_from),
            __(self.report_id.date_to),
            tuple(self.journal_ids.ids) if self.journal_ids else (None,),
            tuple(self.account_ids.ids) if self.account_ids else (None,),
        ]
        self.env.cr.execute(sql, params)
        moves_rows = self.env.cr.dictfetchall()
        rows = {}
        for r in init_rows:
            rows[r['final_code']] = {'init_debit': r['debit'], 'init_credit': r['credit'], 'name': r['acc_name']}
        for r in moves_rows:
            if not rows.get(r['final_code'], False):
                rows[r['final_code']] = {'init_debit': 0.0, 'init_credit': 0.0, }
            rows[r['final_code']].update({'debit': r['debit'], 'credit': r['credit'], 'name': r['acc_name']})

        sheet = workbook.add_worksheet(self.report_id.name)
        init_row = row_num = 8
        report_name_format = workbook.add_format(
            {'font_size': 18, 'align': 'center', 'valign': 'center', 'bg_color': '#cccccc', 'border': 1, 'border_color': '#000000', })
        sheet.merge_range('F4:G4', 'الفترة')
        sheet.write(4, 6, 'From / من')
        sheet.write(5, 6, 'To  / إلى')
        sheet.write(4, 5, __(self.date_from) or '')
        sheet.write(5, 5, __(self.date_to) or '')
        sheet.merge_range('A1:K1', 'ميزان المراجعة بالمجاميع و الأرصدة', report_name_format)
        report_name_format1 = workbook.add_format({'font_size': 18, 'align': 'center', 'valign': 'center', 'bg_color': '#a24689', })
        report_name_format2 = workbook.add_format({'font_size': 18, 'align': 'center', 'valign': 'center', 'bg_color': '#6bbcd6', })
        sheet.merge_range('D%s:E%s' % (row_num, row_num), 'الرصيد الافتاحى', report_name_format1)
        sheet.merge_range('F%s:G%s' % (row_num, row_num), 'الحركات خلال الفترة', report_name_format2)
        sheet.merge_range('H%s:I%s' % (row_num, row_num), 'المجاميع / Totals', report_name_format1)
        sheet.merge_range('J%s:K%s' % (row_num, row_num), 'الأرصده / Balances', report_name_format2)
        report_name_format1 = workbook.add_format({'font_size': 12, 'align': 'center', 'valign': 'center', 'bg_color': '#a24689',
                                                   'border': 1, 'border_color': '#000000', })
        report_name_format2 = workbook.add_format({'font_size': 12, 'align': 'center', 'valign': 'center', 'bg_color': '#6bbcd6',
                                                   'border': 1, 'border_color': '#000000', })
        sheet.write(row_num, 0, '#')
        sheet.write(row_num, 1, 'Code / الكود')
        sheet.write(row_num, 2, 'Account / الحساب')
        report_name_format = workbook.add_format({'font_size': 18, 'align': 'center', 'valign': 'center', 'bg_color': '#a24689', })
        sheet.write(row_num, 3, 'الرصيد الإفتتاحى (مدين) \nInitial debit', report_name_format1)
        sheet.write(row_num, 4, 'الرصيد الإفتتاحى (دائن)\nInitial credit', report_name_format1)
        sheet.write(row_num, 5, 'مدين\nDebit', report_name_format2)
        sheet.write(row_num, 6, 'دائن\nCredit', report_name_format2)
        sheet.write(row_num, 7, 'اجمالى مدين\nTotal Debit', report_name_format1)
        sheet.write(row_num, 8, 'إجمالى دائن\nTotal Credit', report_name_format1)
        sheet.write(row_num, 9, 'الرصيد مدين\nBalance Debit', report_name_format2)
        sheet.write(row_num, 10, 'الرصيد دائن\nBalance Credit', report_name_format2)
        sheet.set_column(0, 0, 5)
        sheet.set_row(0, 25)
        sheet.set_row(7, 25)
        sheet.set_row(8, 25)
        sheet.set_column(2, 2, 40)
        sheet.set_column(3, 3, 15)
        sheet.set_column(4, 4, 15)
        sheet.set_column(5, 5, 15)
        sheet.set_column(6, 6, 15)
        sheet.set_column(7, 7, 15)
        sheet.set_column(8, 8, 15)
        sheet.set_column(9, 9, 15)
        sheet.set_column(10, 10, 15)
        row_num += 1
        sorted_vals = sorted(rows)
        for r in sorted_vals:
            sheet.write(row_num, 0, row_num - 8)
            sheet.write(row_num, 1, r)
            sheet.write(row_num, 2, rows[r]['name'])
            sheet.write(row_num, 3, rows[r].get('init_debit', False) and rows[r]['init_debit'] or 0.0, report_name_format1)
            sheet.write(row_num, 4, rows[r].get('init_credit', False) and rows[r]['init_credit'] or 0.0, report_name_format1)
            sheet.write(row_num, 5, rows[r].get('debit', False) and rows[r]['debit'] or 0.0, report_name_format2)
            sheet.write(row_num, 6, rows[r].get('credit', False) and rows[r]['credit'] or 0.0, report_name_format2)
            sheet.write(row_num, 7, '=SUM(D%s + F%s)' % (row_num + 1, row_num + 1), report_name_format1)
            sheet.write(row_num, 8, '=SUM(E%s + G%s)' % (row_num + 1, row_num + 1), report_name_format1)
            sheet.write(row_num, 9, '=IF(H%s >I%s, H%s-I%s, 0)' % (row_num + 1, row_num + 1, row_num + 1, row_num + 1,), report_name_format2)
            sheet.write(row_num, 10, '=IF(I%s >H%s, I%s-H%s, 0)' % (row_num + 1, row_num + 1, row_num + 1, row_num + 1,), report_name_format2)
            row_num += 1

        sheet.merge_range('B%s:C%s' % (row_num + 1, row_num + 1), 'الاجـــــمــــــالــــــي')
        sheet.write(row_num, 3, "=SUM(D%s:D%s)" % (init_row + 2, row_num))
        sheet.write(row_num, 4, "=SUM(E%s:E%s)" % (init_row + 2, row_num))
        sheet.write(row_num, 5, "=SUM(F%s:F%s)" % (init_row + 2, row_num))
        sheet.write(row_num, 6, "=SUM(G%s:G%s)" % (init_row + 2, row_num))
        sheet.write(row_num, 7, "=SUM(H%s:H%s)" % (init_row + 2, row_num))
        sheet.write(row_num, 8, "=SUM(I%s:I%s)" % (init_row + 2, row_num))
        sheet.write(row_num, 9, "=SUM(J%s:J%s)" % (init_row + 2, row_num))
        sheet.write(row_num, 10, "=SUM(K%s:K%s)" % (init_row + 2, row_num))

        return workbook
