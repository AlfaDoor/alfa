# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GenerateTransactionWizard(models.TransientModel):
    _name = "generate.transaction.wizard"
    _description = 'Wizard to generate transactions'

    account_date = fields.Date("Account Date", required=1)
    expense_nature = fields.Selection([('prepaid', 'Prepaid'), ('accrual', 'Accrual')],
                                      string='Expense Nature', required=True,
                                      default="prepaid")
    journal_id = fields.Many2one("account.journal", string="Journal",
                                 domain="[('type', 'in', ['cash', 'bank'])]")
    group_journal_entries = fields.Boolean("Group Journal Entries")

    @api.multi
    def action_generate_entries(self):
        amortization_lines = self.env['amortization.board.line'].search([
            '|',
            ('start_date', '<=', self.account_date),
            ('end_date', '<=', self.account_date),
            ('move_id', '=', False),
            ('expense_transaction_id.expense_nature', '=', self.expense_nature)
        ], order='expense_transaction_id desc')
        if amortization_lines:
            amortization_lines.post_entry(journal_id=self.journal_id.id,
                                          group_entry=self.group_journal_entries)
