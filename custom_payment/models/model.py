# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, QWebException

class InheritPayment(models.Model):
    _inherit = 'account.payment'

    have_bank_fees = fields.Selection([('nf','No Fees'),('wf','With Fees')],default='nf')
    bank_fees = fields.Float('Bank Fees')
    bank_fees_account = fields.Many2one('account.account')
    vat_fees = fields.Float('VAT Amount')
    vat_fees_account = fields.Many2one('account.account')
    has_bank_payment = fields.Boolean(default=False)
    has_expense_bank_payment = fields.Boolean(default=False)
    bank_fees_id = fields.Boolean(default=False)
    analytical_account = fields.Many2one('account.analytic.account')
    analytical_tag = fields.Many2many('account.analytic.tag')

    @api.multi
    def cancel_bank_fees(self):
        for rec in self:
            if rec.bank_fees_id == True:
                bank_moves = self.env['account.move.line'].search([('bank_payment_id', '=', rec.id)])
                if bank_moves:
                    if bank_moves[0].move_id.state != 'draft':
                        bank_moves[0].move_id.button_cancel()
                    bank_moves[0].move_id.unlink()
                rec.bank_fees_id = False

    @api.multi
    def cancel(self):
        self.cancel_bank_fees()
        res = super(InheritPayment, self).cancel()
        return res

    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconcilable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted."))

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # keep the name in case of a payment reset to draft
            if not rec.name:
                # Use the right sequence to set the name
                if rec.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                else:
                    if rec.partner_type == 'customer':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.customer.invoice'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund'
                    if rec.partner_type == 'supplier':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice'
                rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
                    sequence_code)
                if not rec.name and rec.payment_type != 'transfer':
                    raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(
                    lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()
            if self.have_bank_fees == 'wf':
                self.has_bank_payment = True
            if self.has_expense_bank_payment == True:
                self.has_bank_payment = False
            rec.write({'state': 'posted', 'move_name': move.name})
        return True

    @api.multi
    def create_bank_je(self):
        tag = 0
        for rec in self.analytical_tag:
            tags = [(4, rec.id,)]
        if self.have_bank_fees == 'wf':
            sequence_code = self.journal_id.sequence_id.code
            bank_moves = self.env['account.move'].create({
                            'name': self.env['ir.sequence'].next_by_code(sequence_code),
                            'ref': 'Bank Fees'+':'+self.name,
                            'journal_id': self.journal_id.id,
                            'date': self.payment_date,
                            'line_ids': [
                                (0, 0, {
                                    'name': 'Bank Fees'+':'+self.name,
                                    'debit': self.bank_fees,
                                    'account_id': self.bank_fees_account.id,
                                    'analytic_account_id': self.analytical_account.id,
                                    'partner_id': self.partner_id.id,
                                    'date': self.payment_date,
                                    'date_maturity':self.payment_date,
                                    'bank_payment_id': self.id,
                                    'analytic_tag_ids': tags if self.analytical_tag else False
                                }),
                                (0, 0, {
                                    'name': 'Bank Fees tax'+':'+self.name,
                                    'debit': self.vat_fees,
                                    'account_id': self.vat_fees_account.id,
                                    'analytic_account_id': self.analytical_account.id,
                                    'partner_id': self.partner_id.id,
                                    'date': self.payment_date,
                                    'date_maturity': self.payment_date,
                                    'bank_payment_id': self.id,
                                    'analytic_tag_ids': tags if self.analytical_tag else False
                                }),
                                (0, 0, {
                                    'name': 'Bank Charges',
                                    'credit': self.vat_fees+self.bank_fees,
                                    'account_id': self.journal_id.default_credit_account_id.id,
                                    'analytic_account_id': self.analytical_account.id,
                                    'partner_id': self.partner_id.id,
                                    'date': self.payment_date,
                                    'date_maturity': self.payment_date,
                                    'bank_payment_id': self.id,
                                    'analytic_tag_ids': tags if self.analytical_tag else False
                                }),
                            ]
                        })
            self.has_bank_payment = False
            self.bank_fees_id = True
            bank_moves.post()

    @api.multi
    def action_draft(self):
        return self.write({'state': 'draft'})

    def create_je_register_payment(self):
        if self.have_bank_fees == 'wf':
            sequence_code = self.journal_id.sequence_id.code
            bank_moves = self.env['account.move'].create({
                            'name': self.env['ir.sequence'].next_by_code(sequence_code),
                            'ref': self.communication,
                            'journal_id': self.journal_id.id,
                            'date': self.payment_date,
                            'line_ids': [
                                (0, 0, {
                                    'name': 'Bank Fees'+':'+self.communication,
                                    'debit': self.bank_fees,
                                    'account_id': self.bank_fees_account.id,
                                    'partner_id': self.partner_id.id,
                                    'date': self.payment_date,
                                    'date_maturity': self.payment_date
                                }),
                                (0, 0, {
                                    'name': 'Bank Fees tax' + ':' + self.communication,
                                    'debit': self.vat_fees,
                                    'account_id': self.vat_fees_account.id,
                                    'partner_id': self.partner_id.id,
                                    'date': self.payment_date,
                                    'date_maturity': self.payment_date
                                }),
                                (0, 0, {
                                    'name': 'Bank Charges',
                                    'credit': self.vat_fees + self.bank_fees,
                                    'account_id': self.bank_fees_account.id,
                                    'partner_id': self.partner_id.id,
                                    'date': self.payment_date,
                                    'date_maturity': self.payment_date
                                }),
                            ]
                        })
            bank_moves.post()

    def action_validate_invoice_payment(self):
        self.create_je_register_payment()
        """ Posts a payment used to pay an invoice. This function only posts the
        payment by default but can be overridden to apply specific post or pre-processing.
        It is called by the "validate" button of the popup window
        triggered on invoice form by the "Register Payment" button.
        """
        if any(len(record.invoice_ids) != 1 for record in self):
            # For multiple invoices, there is account.register.payments wizard
            raise UserError(_("This method should only be called to process a single invoice's payment."))
        return self.post()

    def _create_payment_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency, currency_id = aml_obj.with_context(
            date=self.payment_date)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)
        move = self.env['account.move'].create(self._get_move_vals())

        # Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id,})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)

        # Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            print('test1')
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(
                date=self.payment_date)._compute_amount_fields(self.payment_difference, self.currency_id,
                                                               self.company_id.currency_id)
            writeoff_line['name'] = self.writeoff_label
            writeoff_line['account_id'] = self.writeoff_account_id.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit'] or (writeoff_line['credit'] and not counterpart_aml['credit']):
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit'] or (writeoff_line['debit'] and not counterpart_aml['debit']):
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo

        # Write counterpart lines
        if not self.currency_id.is_zero(self.amount):
            if not self.currency_id != self.company_id.currency_id:
                amount_currency = 0
            liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
            liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
            aml_obj.create(liquidity_aml_dict)

        # validate the payment
        if not self.journal_id.post_at_bank_rec:
            move.post()

        # reconcile the invoice receivable/payable line(s) with the payment
        if self.invoice_ids:
            self.invoice_ids.register_payment(counterpart_aml)
        return move

    def _create_transfer_entry(self, amount):
        """ Create the journal entry corresponding to the 'incoming money' part of an internal transfer, return the reconcilable move line
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency, dummy = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(
            amount, self.currency_id, self.company_id.currency_id)
        amount_currency = self.destination_journal_id.currency_id and self.currency_id._convert(amount,
                                                                                                self.destination_journal_id.currency_id,
                                                                                                self.company_id,
                                                                                                self.payment_date or fields.Date.today()) or 0

        dst_move = self.env['account.move'].create(self._get_move_vals(self.destination_journal_id))

        dst_liquidity_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, dst_move.id)
        dst_liquidity_aml_dict.update({
            'name': _('Transfer from %s') % self.journal_id.name,
            'account_id': self.destination_journal_id.default_credit_account_id.id,
            'currency_id': self.destination_journal_id.currency_id.id,
            'journal_id': self.destination_journal_id.id})
        aml_obj.create(dst_liquidity_aml_dict)
        transfer_debit_aml_dict = self._get_shared_move_line_vals(credit, debit, 0, dst_move.id)
        transfer_debit_aml_dict.update({
            'name': self.name,
            'account_id': self.company_id.transfer_account_id.id,
            'journal_id': self.destination_journal_id.id})
        print(transfer_debit_aml_dict)
        if self.currency_id != self.company_id.currency_id:
            transfer_debit_aml_dict.update({
                'currency_id': self.currency_id.id,
                'amount_currency': -self.amount,
            })
        transfer_debit_aml = aml_obj.create(transfer_debit_aml_dict)
        print(transfer_debit_aml)
        if not self.destination_journal_id.post_at_bank_rec:
            dst_move.post()
        return transfer_debit_aml

    def _get_move_vals(self, journal=None):
        """ Return dict to create the payment move
        """
        journal = journal or self.journal_id
        move_vals = {
            'date': self.payment_date,
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }
        if self.move_name:
            move_vals['name'] = self.move_name
        return move_vals

    def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id, invoice_id=False):
        """ Returns values common to both move lines (except for debit, credit and amount_currency which are reversed)
        """
        tags = 0
        for rec in self.analytical_tag:
            tags = [(4, rec.id,)]
        so_str = ','.join([str(i.name) for i in self.so_reference_ids])
        return {
            'partner_id': self.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False,
            'invoice_id': invoice_id and invoice_id.id or False,
            'move_id': move_id,
            'debit': debit,
            'credit': credit,
            'sale_reference': so_str,
            'analytic_account_id': self.analytical_account.id,
            'analytic_tag_ids':tags if self.analytical_tag else False,
            'amount_currency': amount_currency or False,
            'payment_id': self.id,
            'journal_id': self.journal_id.id,
        }

    def _get_counterpart_move_line_vals(self, invoice=False):
        if self.payment_type == 'transfer':
            name = self.name
        else:
            name = ''
            if self.partner_type == 'customer':
                if self.payment_type == 'inbound':
                    name += _("Customer Payment")
                elif self.payment_type == 'outbound':
                    name += _("Customer Credit Note")
            elif self.partner_type == 'supplier':
                if self.payment_type == 'inbound':
                    name += _("Vendor Credit Note")
                elif self.payment_type == 'outbound':
                    name += _("Vendor Payment")
            if invoice:
                name += ': '
                for inv in invoice:
                    if inv.move_id:
                        name += inv.number + ', '
                name = name[:len(name) - 2]
        return {
            'name': name,
            'account_id': self.destination_account_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
        }

    def _get_liquidity_move_line_vals(self, amount):
        name = self.name
        if self.payment_type == 'transfer':
            name = _('Transfer to %s') % self.destination_journal_id.name
        vals = {
            'name': name,
            'account_id': self.payment_type in ('outbound',
                                                'transfer') and self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
        }

        # If the journal has a currency specified, the journal item need to be expressed in this currency
        if self.journal_id.currency_id and self.currency_id != self.journal_id.currency_id:
            amount = self.currency_id._convert(amount, self.journal_id.currency_id, self.company_id,
                                               self.payment_date or fields.Date.today())
            debit, credit, amount_currency, dummy = self.env['account.move.line'].with_context(
                date=self.payment_date)._compute_amount_fields(amount, self.journal_id.currency_id,
                                                               self.company_id.currency_id)
            vals.update({
                'amount_currency': amount_currency,
                'currency_id': self.journal_id.currency_id.id,
            })
            print(vals)

        return vals

    def create_currency_record(self):
        active_curr = self.env['res.currency'].sudo().search([])
        for rec in active_curr:
            rec.rate_ids.create({'rate': rec.rate_ids[-1].rate, 'name': fields.Date.today(), 'currency_id': rec.id})

    @api.multi
    def button_bank_entries(self):
        return {
            'name': _('Bank Fees Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('bank_payment_id', 'in', self.ids)],
            }

class InheritMoveLine(models.Model):
    _inherit = 'account.move.line'

    bank_payment_id = fields.Integer()
    sale_reference = fields.Char()


