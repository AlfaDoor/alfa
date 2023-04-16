# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, fields, models, _
from odoo.tools import start_of, end_of, add, date_range


class ExpenseTransaction(models.Model):
    _name = "account.expense.transaction"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'expense_nature'
    _description = "Account Expense Transaction"

    date = fields.Date(required=True, readonly=True, states={'draft': [('readonly', False)]},
                       track_visibility='onchange')
    state = fields.Selection([('draft', 'Draft'), ('reviewed', 'Reviewed'),
                              ('confirmed', 'Confirmed'), ('final_approval', 'Final Approval'),
                              ('full_amortization', 'Full Amortization')],
                             string='Status', required=True, readonly=True,
                             copy=False, default='draft',
                             track_visibility='onchange')
    expense_nature = fields.Selection([('prepaid', 'Prepaid'), ('accrual', 'Accrual')],
                                      string='Expense Nature', required=True, readonly=True,
                                      default="prepaid",
                                      track_visibility='onchange', states={'draft': [('readonly', False)]})
    # expense_type_id = fields.Many2one("account.expense.type", string="Expense Type",
    #                                   domain="[('state', '=', 'confirmed'),('expense_nature', '=', expense_nature)]")
    amortization_method = fields.Selection([('monthly', 'Monthly'), ('on_time', 'On Time')],
                                           string='Amortization Method', required=True, readonly=True,
                                           track_visibility='onchange', states={'draft': [('readonly', False)]})
    reference = fields.Char(required=True, readonly=True, states={'draft': [('readonly', False)]})
    move_id = fields.Many2one("account.move", string="Journal Entry",
                              readonly=True, copy=False)
    payment_type = fields.Selection([('bank_cash', 'Bank/Cash'), ('credit', 'Credit')],
                                    string='Payment type', readonly=True,
                                    track_visibility='onchange', states={'draft': [('readonly', False)]})
    # When payment_type is bank_cash
    payment_journal_id = fields.Many2one("account.journal", string="Payment Method",
                                         domain="[('type', 'in', ['bank', 'cash']),('company_id','=',company_id)]", readonly=True,
                                         states={'draft': [('readonly', False)]})
    bank_account_id = fields.Many2one("account.account", string="Bank/Cash Account",
                                         domain="[('user_type_id.type', '=', 'liquidity'),('company_id','=',company_id)]", readonly=True,
                                         states={'draft': [('readonly', False)]})
    # When payment_type is credit
    journal_id = fields.Many2one("account.journal", string="Amortization Journal",
                                 domain="[('type', 'in', ['purchase', 'general']),('company_id','=',company_id)]", readonly=True, required=True,
                                 states={'draft': [('readonly', False)]})
    vendor_id = fields.Many2one("res.partner", string="Vendor",
                                 domain="[('supplier', '=', True)]", readonly=True,
                                 states={'draft': [('readonly', False)]})
    invoice_id = fields.Many2one("account.invoice", string="Invoice",
                                readonly=True,
                                states={'draft': [('readonly', False)]})
    expense_detail_ids = fields.One2many('expense.detail.line',
                                         'expense_transaction_id',
                                         string="Expense Detail Lines",
                                         copy=True)
    amortization_board_ids = fields.One2many('amortization.board.line',
                                             'expense_transaction_id',
                                             string="Amortization Board Lines")
    entry_count = fields.Integer(compute='_entry_count', string='# Journal Entries')
    type_jv = fields.Selection([('all_line', 'JV for all line'), ('each_line', 'JV for each line')],
                               default='each_line')
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id)

    @api.multi
    @api.depends('amortization_board_ids.move_id')
    def _entry_count(self):
        for expense_transaction in self:
            res = self.env['amortization.board.line'].search(
                [('expense_transaction_id', '=', expense_transaction.id), ('move_id', '!=', False)])
            expense_transaction.entry_count = res and len(set(res.mapped('move_id.id'))) or 0

    @api.multi
    def open_entries(self):
        move_ids = []
        for expense_transaction in self:
            for amortization_board_line in expense_transaction.amortization_board_ids:
                if amortization_board_line.move_id:
                    move_ids.append(amortization_board_line.move_id.id)
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids)],
        }

    @api.onchange('payment_type')
    def onchange_payment_type(self):
        if self.payment_type == 'bank_cash':
            self.vendor_id = False
            self.invoice_id = False
        elif self.payment_type == 'credit':
            self.payment_journal_id = False
            self.bank_account_id = False
        else:
            self.vendor_id = False
            self.invoice_id = False
            self.payment_journal_id = False
            self.bank_account_id = False

    @api.onchange('expense_nature')
    def onchange_expense_nature(self):
        if self.expense_nature == 'prepaid':
            return {'domain': {'journal_id': [('type', 'in', ['purchase', 'general']),
                                              ('company_id', '=', self.company_id.id)]}}
        if self.expense_nature == 'accrual':
            return {'domain': {'journal_id': [('type', 'in', ['general']),
                                              ('company_id', '=', self.company_id.id)]}}


    @api.onchange('payment_journal_id')
    def onchange_payment_journal(self):
        if self.payment_journal_id and self.payment_journal_id.default_credit_account_id:
            self.bank_account_id = self.payment_journal_id.default_credit_account_id.id
        else:
            self.bank_account_id = False

    @api.multi
    def action_review(self):
        for expense_rec in self:
            expense_rec.write({
                'state': 'reviewed'
            })

    @api.multi
    def action_confirm(self):
        for expense_rec in self:
            expense_rec.write({
                'state': 'confirmed'
            })

    def get_date_range(self, start_date, end_date):
        min_time = datetime.min.time()
        date_list = []
        single_month = False

        # Calculate the last day of month of start date
        month_end = end_of(start_date, 'month')
        if start_date != end_date and end_date > month_end:
            date_list.append((start_date, month_end))
            next_month_start = add(month_end, days=1)
            end_month_start = start_of(end_date, 'month')
            if end_month_start == end_date:
                previous_month_end = end_month_start
            elif next_month_start > add(end_month_start, days=-1):
                previous_month_end = end_month_start
            else:
                previous_month_end = add(end_month_start, days=-1)
        else:
            date_list.append((start_date, end_date))
            next_month_start = start_date
            end_month_start = start_of(end_date, 'month')
            previous_month_end = end_date
            single_month = True

        if not single_month and next_month_start != previous_month_end:
            # Loop over "date_range" odoo library function
            for start_day_month in date_range(datetime.combine(next_month_start, min_time),
                                              datetime.combine(previous_month_end, min_time)):
                end_day_month = end_of(start_day_month.date(), 'month')
                if end_day_month <= end_date:
                    date_list.append((start_day_month.date(), end_day_month))

        if end_month_start > start_date and end_month_start != end_date:
            date_list.append((end_month_start, end_date))
        elif end_month_start > start_date and end_month_start == end_date:
            date_list.append((end_date, end_date))
        return date_list

    def create_expense_journal_entry(self):
        iml = []
        total_amount = 0
        if self.type_jv == 'all_line':
            for expense_detail_rec in self.expense_detail_ids:
                iml.append((0, 0, {
                    'name': expense_detail_rec.description,
                    'debit': expense_detail_rec.price_total,
                    'account_id': expense_detail_rec.prepaid_expense_account_id.id,
                    'analytic_account_id': expense_detail_rec.analytic_account_id.id,
                    'analytic_tag_ids': expense_detail_rec.analytic_tag_ids and [(6, 0, expense_detail_rec.analytic_tag_ids.ids)],
                }))
                total_amount += expense_detail_rec.price_total
            iml.append((0, 0, {
                'name': self.reference,
                'credit': total_amount,
                'account_id': self.bank_account_id.id or self.journal_id.default_credit_account_id.id,
                'analytic_account_id': self.expense_detail_ids and self.expense_detail_ids[0].analytic_account_id.id or False,
            }))
            self.move_id = self.env['account.move'].create({
                'journal_id': self.payment_journal_id.id,
                'line_ids': iml,
                'date': self.date,
                'ref': self.reference,
            })
        if self.type_jv == 'each_line':
            for expense_detail_rec in self.expense_detail_ids:
                iml.append((0, 0, {
                    'name': expense_detail_rec.description,
                    'debit': expense_detail_rec.price_total,
                    'account_id': expense_detail_rec.prepaid_expense_account_id.id,
                    'analytic_account_id': expense_detail_rec.analytic_account_id.id,
                    'analytic_tag_ids': expense_detail_rec.analytic_tag_ids and [(6, 0, expense_detail_rec.analytic_tag_ids.ids)],
                }))
                iml.append((0, 0, {
                    'name': self.reference,
                    'credit': expense_detail_rec.price_total,
                    'account_id': self.bank_account_id.id or self.journal_id.default_credit_account_id.id,
                    'analytic_account_id': self.expense_detail_ids and self.expense_detail_ids[0].analytic_account_id.id or False,
                }))
                self.move_id = self.env['account.move'].create({
                    'journal_id': self.payment_journal_id.id,
                    'line_ids': iml,
                    'date': self.date,
                    'ref': self.reference,
                })
        self.move_id.action_post()

    @api.multi
    def action_final_approval(self):
        for expense_rec in self:
            # Creating the journal Entry
            if expense_rec.expense_nature == 'prepaid' and expense_rec.payment_type == 'bank_cash':
                expense_rec.create_expense_journal_entry()

            # Creating Amortization Lines
            for expense_detail_rec in expense_rec.expense_detail_ids:
                # Storing start and end dates
                start_date = expense_detail_rec.start_date
                end_date = expense_detail_rec.end_date
                date_list = self.get_date_range(start_date, end_date)
                accumulated_amortization = 0
                remaining_value = expense_detail_rec.price_total
                for date_range in date_list:
                    accumulated_amortization, remaining_value = \
                        expense_detail_rec.create_amortization_line(
                            date_range[0], date_range[1], accumulated_amortization, remaining_value)

            # Setting the state to Final Approval
            expense_rec.write({
                'state': 'final_approval'
            })

    @api.multi
    def action_full_amortization(self):
        for expense_rec in self:
            expense_rec.write({
                'state': 'full_amortization'
            })

    @api.multi
    def action_draft(self):
        for expense_rec in self:
            expense_rec.write({
                'state': 'draft'
            })


class ExpenseDetailsLine(models.Model):
    _name = 'expense.detail.line'
    _description = 'Model for Expense Lines'

    expense_transaction_id = fields.Many2one("account.expense.transaction",
                                             string="Expense Transaction",
                                             ondelete='cascade')
    expense_type_id = fields.Many2one("account.expense.type",
                                             string="Expense Type",
                                             domain=[('state', '=', 'confirmed')],
                                             required=True)
    description = fields.Char(required=True, states={'draft': [('readonly', False)]})
    prepaid_expense_account_id = fields.Many2one("account.account", string="Prepaid/Accrual Expense account",
                                                 domain="[('internal_type', '=', 'other'),('company_id','=',company_id)]",
                                                 required=1)
    expense_account_id = fields.Many2one("account.account", string="Expense account",
                                         domain="[('internal_type', '=', 'other'),('company_id','=',company_id)]",
                                         required=1)
    analytic_account_id = fields.Many2one("account.analytic.account", string="Analytic Account")
    analytic_tag_ids = fields.Many2many('account.analytic.tag', 'expense_tag_rel', 'expense_line_id',
                                        'tag_id', string='Analytic Tags')
    start_date = fields.Date("Start Date", required=1)
    end_date = fields.Date("End Date", required=1)
    total_days = fields.Integer(compute='_compute_total_days', string='Total Days', store=True)
    quantity = fields.Float("Quantity", required=1)
    price_unit = fields.Float("Amount", required=1)
    price_total = fields.Float("Total", compute='_compute_price_total', store=True)
    company_id = fields.Many2one(string="Company", related='expense_transaction_id.company_id', store=True, readonly=True)

    _sql_constraints = [
        ('expense_date_greater', 'check(end_date >= start_date)',
         'Error ! Ending Date cannot be set before Start Date.')
    ]

    @api.model
    def default_get(self, fields):
        res = super(ExpenseDetailsLine, self).default_get(fields)
        if 'reference' in self._context:
            res.update({
                'description': self._context.get('reference'),
            })
        if 'company_id' in self._context:
            res.update({
                'company_id': self._context.get('company_id')
            })
        return res

    @api.onchange('expense_type_id')
    def onchange_expense_type(self):
        if self.expense_type_id:
            self.prepaid_expense_account_id = self.expense_type_id.prepaid_expense_account_id.id
            self.expense_account_id = self.expense_type_id.expense_account_id.id
        else:
            self.prepaid_expense_account_id = False
            self.expense_account_id = False

    @api.depends('start_date', 'end_date')
    @api.multi
    def _compute_total_days(self):
        for expense_line in self:
            if expense_line.start_date and expense_line.end_date:
                delta = expense_line.end_date - expense_line.start_date
                expense_line.total_days = delta.days + 1

    @api.depends('quantity', 'price_unit')
    @api.multi
    def _compute_price_total(self):
        for expense_line in self:
            expense_line.price_total = expense_line.quantity * expense_line.price_unit

    def create_amortization_line(self, start_date, end_date, accumulated_amortization, remaining_value):
        # Period Days
        delta = end_date - start_date
        period_days = delta.days + 1

        # Amortization Amount
        amount_day = self.price_total / self.total_days
        amortization_amount = amount_day * period_days

        # Accumulated Amortization
        accumulated_amortization = accumulated_amortization + amortization_amount
        remaining_value = remaining_value - amortization_amount

        vals = {
            'expense_transaction_id': self.expense_transaction_id.id,
            'expense_detail_line_id': self.id,
            'start_date': start_date,
            'end_date': end_date,
            'prepaid_expense_account_id': self.prepaid_expense_account_id.id,
            'expense_account_id': self.expense_account_id.id,
            'total_days': self.total_days,
            'period_days': period_days,
            'amortization_amount': amortization_amount,
            'amortization_accumulated': accumulated_amortization,
            'remaining_value': remaining_value
        }
        self.env['amortization.board.line'].create(vals)
        return accumulated_amortization, remaining_value


class AmortizationBoardLine(models.Model):
    _name = 'amortization.board.line'
    _description = 'Model for Amortization Lines'

    expense_transaction_id = fields.Many2one("account.expense.transaction",
                                             string="Expense Transaction",
                                             ondelete='cascade')
    expense_detail_line_id = fields.Many2one("expense.detail.line",
                                             string="Expense Detail Line",
                                             ondelete='cascade')
    start_date = fields.Date("Start Date", required=1)
    end_date = fields.Date("End Date", required=1)
    prepaid_expense_account_id = fields.Many2one("account.account", string="Prepaid/Accrual Expense account",
                                                 domain="[('internal_type', '=', 'other'),('company_id','=',company_id)]",
                                                 required=1)
    expense_account_id = fields.Many2one("account.account", string="Expense account",
                                         domain="[('internal_type', '=', 'other'),('company_id','=',company_id)]",
                                         required=1)
    total_days = fields.Integer("Total Days")
    period_days = fields.Integer("Period Days")
    amortization_amount = fields.Float("Amortization Amount")
    amortization_accumulated = fields.Float("Amortization Accumulated")
    remaining_value = fields.Float("Remaining Value")
    move_id = fields.Many2one("account.move", string="Journal Entry",
                              readonly=True, copy=False)
    company_id = fields.Many2one(string="Company", related='expense_transaction_id.company_id', store=True, readonly=True)

    @api.multi
    def post_entry(self, context=False, journal_id=False, group_entry=False):
        if not group_entry:
            for amortization_line in self:
                iml = list()

                iml.append((0, 0, {
                    'name': amortization_line.expense_detail_line_id.description,
                    'credit': amortization_line.amortization_amount,
                    'account_id': amortization_line.prepaid_expense_account_id.id,
                    'partner_id': amortization_line.expense_transaction_id.vendor_id.id,
                    'analytic_account_id': amortization_line.expense_detail_line_id.analytic_account_id.id,
                    'analytic_tag_ids': amortization_line.expense_detail_line_id.analytic_tag_ids and [
                        (6, 0, amortization_line.expense_detail_line_id.analytic_tag_ids.ids)],
                }))
                iml.append((0, 0, {
                    'name': amortization_line.expense_detail_line_id.description,
                    'debit': amortization_line.amortization_amount,
                    'account_id': amortization_line.expense_account_id.id,
                    'partner_id': amortization_line.expense_transaction_id.vendor_id.id,
                    'analytic_account_id': amortization_line.expense_detail_line_id.analytic_account_id.id,
                    'analytic_tag_ids': amortization_line.expense_detail_line_id.analytic_tag_ids and [
                        (6, 0, amortization_line.expense_detail_line_id.analytic_tag_ids.ids)],
                }))
                amortization_line.move_id = self.env['account.move'].create({
                    'journal_id': journal_id or amortization_line.expense_transaction_id.journal_id.id,
                    'partner_id': amortization_line.expense_transaction_id.vendor_id.id,
                    'line_ids': iml,
                    'date': amortization_line.start_date,
                    'ref': amortization_line.expense_transaction_id.reference
                })
                amortization_line.move_id.action_post()

            if all(amortization_line.move_id for amortization_line in self[0].expense_transaction_id.amortization_board_ids):
                self[0].expense_transaction_id.action_full_amortization()

        else:  # if Group Entry is Enabled
            expense_detail_line_ids = list(set(self.mapped('expense_detail_line_id')))

            for expense_detail_line_id in expense_detail_line_ids:
                current_lines = self.filtered(lambda r: r.expense_detail_line_id == expense_detail_line_id)
                amortization_amount = sum(current_lines.mapped('amortization_amount'))
                iml = list()
                last_amortization_line = current_lines[0]
                iml.append((0, 0, {
                    'name': last_amortization_line.expense_detail_line_id.description,
                    'credit': amortization_amount,
                    'account_id': last_amortization_line.prepaid_expense_account_id.id,
                    'partner_id': last_amortization_line.expense_transaction_id.vendor_id.id,
                    'analytic_account_id': last_amortization_line.expense_detail_line_id.analytic_account_id.id,
                    'analytic_tag_ids': last_amortization_line.expense_detail_line_id.analytic_tag_ids and [
                        (6, 0, last_amortization_line.expense_detail_line_id.analytic_tag_ids.ids)],
                }))
                iml.append((0, 0, {
                    'name': last_amortization_line.expense_detail_line_id.description,
                    'debit': amortization_amount,
                    'account_id': last_amortization_line.expense_account_id.id,
                    'partner_id': last_amortization_line.expense_transaction_id.vendor_id.id,
                    'analytic_account_id': last_amortization_line.expense_detail_line_id.analytic_account_id.id,
                    'analytic_tag_ids': last_amortization_line.expense_detail_line_id.analytic_tag_ids and [
                        (6, 0, last_amortization_line.expense_detail_line_id.analytic_tag_ids.ids)],
                }))
                new_move_rec = self.env['account.move'].create({
                    'journal_id': journal_id or last_amortization_line.expense_transaction_id.journal_id.id,
                    'partner_id': last_amortization_line.expense_transaction_id.vendor_id.id,
                    'line_ids': iml,
                    'date': last_amortization_line.start_date,
                    'ref': last_amortization_line.expense_transaction_id.reference
                })
                for current_line in current_lines:
                    current_line.move_id = new_move_rec
                new_move_rec.action_post()

                if all(amortization_line.move_id for amortization_line in last_amortization_line.expense_transaction_id.amortization_board_ids):
                    last_amortization_line.expense_transaction_id.action_full_amortization()

    _sql_constraints = [
        ('amortization_date_greater', 'check(end_date >= start_date)',
         'Error ! Ending Date cannot be set before Start Date.')
    ]
