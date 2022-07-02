# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def action_invoice_open(self):
        res = super(AccountInvoice, self).action_invoice_open()
        expense_product_line = self.env['account.invoice.line'].search(
            [('invoice_id', '=', self.id), ('expense_nature', '=', 'prepaid')])
        if expense_product_line:
            vals = {
                'date': fields.Date.today(),
                'journal_id': self.journal_id.id,
                'amortization_method': 'monthly',
                'reference': self.number,
                'payment_type': 'credit',
                'vendor_id': self.partner_id.id,
                'invoice_id': self.id,
                'move_id': self.move_id.id
            }
            transaction_rec = self.env['account.expense.transaction'].create(vals)
            for rec in expense_product_line:
                transaction_rec.expense_detail_ids.create({
                    'expense_transaction_id': transaction_rec.id,
                    'expense_type_id': rec.expense_type_id.id,
                    'description': rec.name,
                    'prepaid_expense_account_id': rec.expense_type_id.prepaid_expense_account_id.id,
                    'expense_account_id': rec.expense_type_id.expense_account_id.id,
                    'analytic_account_id': rec.account_analytic_id.id,
                    'analytic_tag_ids': rec.analytic_tag_ids and [(6, 0, rec.analytic_tag_ids.ids)],
                    'start_date': rec.start_date,
                    'end_date': rec.end_date,
                    'quantity': rec.quantity,
                    'price_unit': rec.price_unit})
        return res


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    expense_nature = fields.Selection([('normal', 'Normal'), ('prepaid', 'Prepaid')],
                                      string='Type Bills', required=True,
                                      default="normal")

    expense_type_id = fields.Many2one("account.expense.type",
                                             string="Expense Type",
                                             domain=[('state', '=', 'confirmed')])
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")

    @api.onchange('expense_nature')
    def onchange_expense_nature(self):
        if self.expense_nature != 'prepaid':
            for invoice_line in self:
                invoice_line.end_date = False
                invoice_line.start_date = False
                invoice_line.expense_type_id = False
        if self.expense_nature == 'prepaid':
            for invoice_line in self:
                invoice_line.account_id = invoice_line.product_id.expense_type_id.prepaid_expense_account_id.id
                invoice_line.expense_type_id = invoice_line.product_id.expense_type_id.id

    @api.onchange('expense_type_id')
    def onchange_expense_type(self):
        if self.expense_type_id:
            for invoice_line in self:
                invoice_line.account_id = invoice_line.expense_type_id.prepaid_expense_account_id.id


    @api.onchange('product_id')
    def onchange_product_id_expense(self):
        if self.product_id and self.expense_nature == 'prepaid':
            self.expense_type_id = self.product_id.expense_type_id.id
