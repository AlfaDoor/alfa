# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import datetime
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools import __


class AdvanceReconcileAmount(models.Model):
    _name = 'advance.reconcile.amount'

    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain=[('type', '=', 'general')])
    advance_account = fields.Many2one('account.account', string="Advance Account", domain=[('deprecated', '=', False),('user_type_id.name', '!=', 'Cash and banks')],required=True, copy=False)
    amount = fields.Float(string='Payment Amount', required=True)
    analytical_account = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytical_tags = fields.Many2many('account.analytic.tag', string='Analytic Tags', ondelete='restrict')
    memo_communication = fields.Char(string='Memo', required=True)
    invoice_id = fields.Many2one('account.invoice', string='Invoice ID', ondelete='restrict')
    

    def action_validate_advance_reconcile_amount(self):
        active_id = self.env.context.get('active_id')
        invoice = self.env['account.invoice'].browse(active_id)
        account_move = self.env['account.move']

        line_ids = []

        comment = 'Memo: '+self.memo_communication
        for inv in invoice:
            account_receivable_id = inv.account_id.id
            partner_id = inv.partner_id.id
            ref = inv.reference
            date = inv.date or inv.date_invoice
            if inv.comment:
                comment = comment+' | Comment: '+inv.comment,

        move_dict = {
            'ref': ref,
            'journal_id': self.journal_id.id,
            'date': date,
            'narration': comment,
        }

        if account_receivable_id:
            
            receivable_line = (0, 0, {
                'partner_id': partner_id,
                'account_id': account_receivable_id,
                'journal_id': self.journal_id.id,
                'date': date,
                'name':self.memo_communication,
                'analytic_account_id':self.analytical_account.id,
                'analytic_tag_ids':self.analytical_tags and [(6, 0, self.analytical_tags.ids)],
                'debit': 0.0,
                'credit': self.amount > 0.0 and self.amount or 0.0,
            })
            line_ids.append(receivable_line)

        if self.advance_account:
            advance_account_line = (0, 0, {
                'partner_id': partner_id,
                'account_id': self.advance_account.id,
                'journal_id': self.journal_id.id,
                'date': date,
                'name':self.memo_communication,
                'analytic_account_id':self.analytical_account.id,
                'analytic_tag_ids':self.analytical_tags and [(6, 0, self.analytical_tags.ids)],
                'debit': self.amount > 0.0 and self.amount or 0.0,
                'credit': 0.0,
            })
            line_ids.append(advance_account_line)

        move_dict['line_ids'] = line_ids
        move = self.env['account.move'].create(move_dict)
        move.action_post()
        
    @api.model
    def default_get(self, fields):
        rec = super(AdvanceReconcileAmount, self).default_get(fields)
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.invoice':
            return rec

        invoices = self.env['account.invoice'].browse(active_ids)

        # Check all invoices are open
        if any(invoice.state != 'open' for invoice in invoices):
            raise UserError(_("You can only register advance reconcile amount for open invoices"))

        rec.update({
            'memo_communication': ' '.join([ref for ref in invoices.mapped('reference') if ref])[:2000]
        })
        return rec
        #test
