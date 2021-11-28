import json
from odoo import models, fields, api,_
from odoo.tools import email_re, email_split, email_escape_char, float_is_zero, float_compare, \
    pycompat, date_utils

from datetime import date, datetime
from odoo.exceptions import ValidationError


class InheritWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_raw_location = fields.Boolean(default=False)


class SaleInherit(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _default_warehouse_id(self):
        if self.env.user.company_id.id == 1:
            warehouse_ids = self.env['stock.warehouse'].search([('id', '=', 3)], limit=1)
        else:
            company = self.env.user.company_id.id
            warehouse_ids = self.env['stock.warehouse'].search([('company_id','=', company)], limit=1)
        return warehouse_ids

    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, domain="[('is_raw_location','=',False)]",
        default=_default_warehouse_id)

    order_type = fields.Selection([('local','Local'),('export','Export')], default='local')


class InheritProduction(models.Model):
    _inherit = 'mrp.production'

    produced_quantity = fields.Float(compute='calculate_quantities', store=True)
    remain_quantity = fields.Float(compute='calculate_quantities', store=True)
    machine_number = fields.Char('Machine number')

    def calculate_quantities(self):
        for qty in self:
            produce_qty = 0.0
            for line in qty.finished_move_line_ids:
                produce_qty += line.qty_done
            qty.update({
                'produced_quantity': produce_qty,
                'remain_quantity': qty.product_qty - produce_qty,
            })

class InheritEmployee(models.Model):
    _inherit = 'hr.employee'

    request_user_id = fields.Many2one('res.users')
    overtime_eligible = fields.Boolean(default=False)


class PartnerInherit(models.Model):
    _inherit = 'res.partner'

    res_status = fields.Selection([('new', 'Draft'), ('submitted', 'Submit'), ('approve', 'Approve')], default='new')
    english_name = fields.Char()
    allow_credit_sale = fields.Boolean(default=False)

    def get_payment_current_so(self):
        print('Enterrrrr')
        payment_obj = self.env['account.payment'].search([('partner_id','=',self.partner_id.id),('state','=','posted'),('sale_order_id','=',self.id)])
        if self.partner_id.allow_credit_sale == False:
            if not payment_obj:
                raise ValidationError(_('Kindly, Enter the payment against this sale order, credit sale is not allowed to this customer'))
        else:
            payment_amount = 0.0
            for rec in payment_obj:
                payment_amount += rec.amount
            if payment_amount < ((self.amount_total * 50)/100):
                raise ValidationError(_('Payment amount should must be 50% of the total amount, kindly check the payment against this sale order'))

    def to_submit(self):
        return self.write({'res_status': 'submitted'})

    def to_approve(self):
        return self.write({'res_status': 'approve'})

    def to_draft(self):
        return self.write({'res_status': 'new'})


class InheritPayment(models.Model):
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one('sale.order')
    so_reference_ids = fields.Many2many('sale.order')

    @api.onchange('partner_id')
    def sale_domain(self):
        orders = []
        if self.partner_id:
            order_ids = self.env['sale.order'].search([('partner_id','=',self.partner_id.id),('state','!=','cancel')])
            for rec in order_ids:
                orders.append(rec.id)
        return {'domain': {'so_reference_ids': [('id', 'in', orders)]}}


class InvoiceInherit(models.Model):
    _inherit = 'account.invoice'

    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'open':
            domain = [('account_id', '=', self.account_id.id),
                      ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
                      ('reconciled', '=', False),
                      ('move_id.state', '=', 'posted'),
                      '|',
                        '&', ('amount_residual_currency', '!=', 0.0), ('currency_id','!=', None),
                        '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id','=', None), ('amount_residual', '!=', 0.0)]
            if self.type in ('out_invoice', 'in_refund'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0),('sale_reference','like',self.origin)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = self.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == self.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        currency = line.company_id.currency_id
                        amount_to_show = currency._convert(abs(line.amount_residual), self.currency_id, self.company_id, line.date or fields.Date.today())
                    if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                        continue
                    if line.ref :
                        title = '%s : %s' % (line.move_id.name, line.ref)
                    else:
                        title = line.move_id.name
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'title': title,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True


class LoanInherit(models.Model):
    _inherit = 'loan.advance.request'

    @api.multi
    def check_loan_status(self):
        loans = self.env['loan.advance.request'].search([('state','=','GM Approve')])
        for rec in loans:
            if rec.installment_ids:
                remaining = 0.0
                for line in rec.installment_ids:
                    remaining += line.remaining
                if remaining == 0.0:
                    rec.write({'state': 'Loan Fully Paid'})