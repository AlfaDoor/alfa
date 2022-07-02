# -*- coding: utf-8 -*-
import logging
import datetime
from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import base64
import xlwt
import io



_logger = logging.getLogger(__name__)

# class AccountMoveLine(models.Model):
#     _inherit = "account.move.line"
#
#     vat_return_id = fields.Many2one('uae.vat.return', string='VAT Return ID', copy=False, help="VAT Return where the move line come from")
#
#     @api.multi
#     def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
#         res = super(AccountMoveLine, self).reconcile(writeoff_acc_id=writeoff_acc_id, writeoff_journal_id=writeoff_journal_id)
#         account_move_ids = [l.move_id.id for l in self if float_compare(l.move_id.matched_percentage, 1, precision_digits=5) == 0]
#         if account_move_ids:
#             vat_return_ids = self.env['uae.vat.return'].search([
#                 ('move_id', 'in', account_move_ids)
#             ])
#             vat_return_ids.set_to_paid()
#         return res

class ReverseChargeService(models.Model):
    _name = 'reverse.charge.service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Reverse Charge Service'

    def _get_company(self):
        return self.env.user.company_id

    # Special behavior for this field: res.company.search() will only return the companies
    # available to the current user (should be the user's companies?), when the user_preference
    # context is set.
    state = fields.Selection([('draft', 'draft'), ('validate', 'Validate')], readonly=True, default='draft', copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=_get_company)
    name = fields.Char('Name', default='/')
    partner_id = fields.Many2one('res.partner', string='Tax Agent')
    vendor_bill = fields.Many2one('account.invoice', 'Vendor Bill')
    amount = fields.Monetary(string='Declared Amount',required=True, related='vendor_bill.amount_total')
    description =  fields.Text('Description')
    date = fields.Date(string="Date", default=fields.Date.today)
    reverse_charge_tax = fields.Many2one('account.tax', 'Reverse Charge Output')
    move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade", readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    reverse_charge_tax_input = fields.Many2one('account.tax', 'Reverse Charge Input')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    reverse_charge_amount = fields.Float('Reverse Charge Amount', compute='compute_reverse_charge')

    @api.multi
    def save_reverse_charge(self):
        self.write({'name': "RC/"+self.date})
        self.vendor_bill.write({'reverse_charge_entry': self.id})

    @api.multi
    @api.depends('reverse_charge_tax','amount')
    def compute_reverse_charge(self):
        for line in self:
            line.reverse_charge_amount = line.amount *(line.reverse_charge_tax.amount/100)

    @api.multi
    def action_move_create(self):
        for line in self:
            reverse_charge_amount = line.amount *(line.reverse_charge_tax.amount/100)
            debit_vals = {
                'name': line.name,
                'debit': reverse_charge_amount,
                'credit': 0.0,
                'account_id': line.reverse_charge_tax_input.account_id.id,
                'tax_line_id': line.reverse_charge_tax_input.id,
            }
            credit_vals = {
                'name': line.name ,
                'debit': 0.0,
                'credit': reverse_charge_amount,
                'account_id': line.reverse_charge_tax.account_id.id,
                'tax_line_id': line.reverse_charge_tax.id,
            }

            vals = {
                'journal_id': line.journal_id.id,
                'date': line.date,
                'state': 'draft',
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move = self.env['account.move'].create(vals)
            move.post()
            line.write({'move_id':move.id,'state':'validate'})
            line.vendor_bill.write({'reverse_charge_entry':line.id})
            action = self.env.ref(self.env.context.get('action', 'account.action_move_line_form'))
            result = action.read()[0]
            result['views'] = [(False, 'form')]
            result['res_id'] = move.id
            return result

class ReverseCharge(models.Model):
    _name = 'reverse.charge'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Reverse Charge'

    def _get_company(self):
        return self.env.user.company_id

    # Special behavior for this field: res.company.search() will only return the companies
    # available to the current user (should be the user's companies?), when the user_preference
    # context is set.
    company_id = fields.Many2one('res.company', string='Company', required=True, default=_get_company)
    name = fields.Char('Name', default='/')
    partner_id = fields.Many2one('res.partner', string='Tax Agent', required=True)
    vendor_bill = fields.Many2one('account.invoice', 'Vendor Bill')
    amount = fields.Monetary(string='Declared Amount',required=True)
    description =  fields.Text('Description')
    reverse_charge_line_ids = fields.One2many('reverse.charge.line', 'reverse_charge_id')
    date = fields.Date(string="Date", default=fields.Date.today)
    state = fields.Selection([('draft', 'draft'), ('validate', 'Validate'), ('paid', 'Paid'), ('cancel', 'Cancelled')], readonly=True, default='draft', copy=False)
    move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade")
    input_move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade")
    reverse_charge_tax = fields.Many2one('account.tax', 'Reverse Charge Output')
    reverse_charge_tax_input = fields.Many2one('account.tax', 'Reverse Charge Input')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    custom_account_id = fields.Many2one('account.account', string='Customs Account', index=True)
    move_id_tax = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade")
    custom_amount = fields.Float('Customs Amount')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    port = fields.Char('Port')
    ref = fields.Char('Reference')
    reverse_charge_amount = fields.Float('Reverse Charge Amount', compute='compute_reverse_charge')
    custom_amount_and_reverse = fields.Float('Total Pay', compute='compute_reverse_charge')

    @api.multi
    @api.depends('reverse_charge_tax')
    def compute_reverse_charge(self):
        for line in self:
            if line.custom_amount:
                after_custom  = line.amount +line.custom_amount
                line.reverse_charge_amount = after_custom *(line.reverse_charge_tax.amount/100)
                line.custom_amount_and_reverse= line.reverse_charge_amount+line.custom_amount

    @api.multi
    def tax_compute(self):
        for line in self:
            line.reverse_charge_line_ids.unlink()
            after_custom = line.custom_amount + line.amount
            reverse_charge_amount = after_custom *(line.reverse_charge_tax.amount/100)
            line_dict2 = {
                'name': 'Reverse Charge',
                'amount': reverse_charge_amount,
                'reverse_charge_id':line.id,
            }
            self.env['reverse.charge.line'].create(line_dict2)
            line.write({'name':"BOE/" + line.vendor_bill.number})

    @api.multi
    def action_move_create(self):
        for line in self:
            reverse_charge_amount =line.reverse_charge_amount
            debit_vals = {
                'name': line.name,
                'debit': reverse_charge_amount,
                'credit': 0.0,
                'account_id': line.reverse_charge_tax_input.account_id.id,
                'tax_line_id': line.reverse_charge_tax_input.id,
            }
            credit_vals = {
                'name': line.name ,
                'debit': 0.0,
                'credit': reverse_charge_amount,
                'account_id': line.reverse_charge_tax.account_id.id,
                'tax_line_id': line.reverse_charge_tax.id,
            }

            vals = {
                'journal_id': line.journal_id.id,
                'date': line.date,
                'state': 'draft',
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move = self.env['account.move'].create(vals)
            move.post()
            line.write({'move_id':move.id})

            debit_vals_pay = {
                'name': line.name,
                'debit': line.custom_amount,
                'credit': 0.0,
                'partner_id':line.partner_id.id,
                'account_id': line.custom_account_id.id,
            }

            debit_vals_pay1 = {
                'name': line.name,
                'debit': reverse_charge_amount,
                'credit': 0.0,
                'partner_id':line.partner_id.id,
                'account_id': line.reverse_charge_tax.account_id.id,
            }

            credit_vals_pay1 = {
                'name': line.name ,
                'debit': 0.0,
                'credit': line.custom_amount + reverse_charge_amount,
                'partner_id': line.partner_id.id,
                'account_id': line.partner_id.property_account_payable_id.id,
            }

            vals1 = {
                'journal_id': line.journal_id.id,
                'date': line.date,
                'state': 'draft',
                'line_ids': [(0, 0, debit_vals_pay),(0, 0, debit_vals_pay1), (0, 0, credit_vals_pay1)]
            }

            move_two = self.env['account.move'].create(vals1)
            move_two.post()
            line.write({'move_id_tax':move_two.id,'state':'validate'})

class ReverseChargeLine(models.Model):
    _name = 'reverse.charge.line'
    _description = 'Reverse Charge Line'

    product_id = fields.Many2one('product.product',string='Product')
    name = fields.Char('Description')
    amount = fields.Float(string='Amount',required=True)
    reverse_charge_id = fields.Many2one('reverse.charge', 'Reverse Charge ID')


class TaxAdjustmentLog(models.Model):
    _name = 'tax.adjustment.log'
    _description = 'Tax Adjustments'

    reason = fields.Char(string='Justification', required=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    amount = fields.Float(required=True)
    tax_id = fields.Many2one('account.tax', string='Adjustment Tax', ondelete='restrict', required=True)
    move_id = fields.Many2one('account.move', 'Adjustment Entry', readonly=True, copy=False)
    return_id = fields.Many2one('uae.vat.return', 'VAT Return')

class UaeVatReturn(models.Model):
    _name = "uae.vat.return"
    _description = 'Saudi VAT Return'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', readonly=True)
    report = fields.Binary('Excel File', filters='.xls', readonly=True)
    name_r = fields.Char('File Name', size=32)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env.user.company_id)
    state = fields.Selection([('new', 'New'), ('validate', 'Validated'),('rollover', 'Rollover'),('paid', 'Paid'), ('filed', 'Filed')], 'Status', required=True, copy=False, track_visibility='onchange', default='new')
    start_date = fields.Date('Start Date', store=True, track_visibility='onchange')
    end_date = fields.Date('End Date', store=True, track_visibility='onchange')
    total_sales_in_period_before_tax = fields.Float('Sales')
    total_taxable_sales_in_period_before_tax = fields.Float('Taxable sales')
    total_collected_on_sales = fields.Float('Sales tax')
    total_purchase_in_period_before_tax = fields.Float('Total purchases')
    total_taxable_purchase_in_period_before_tax = fields.Float('Taxable purchases')
    total_collected_on_purchase = fields.Float('Purchase tax')
    return_line_ids = fields.One2many('uae.vat.return.line', 'return_id')
    total_payable = fields.Float('Net Amount', compute='compute_total_payable', store=True)
    total_minus = fields.Boolean('Minus', compute='compute_total_payable')
    partner_id = fields.Many2one('res.partner', 'Tax Agent')
    zero_rated_total = fields.Float('Zero Rated', compute='compute_zero_rate_tax')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, copy=False)
    adjust_move_id = fields.Many2one('account.move', 'Adjustment Entry', readonly=True, copy=False)
    tax_suspense_account_id = fields.Many2one('account.account', string='Account', index=True)
    adjustment_tax = fields.Many2one('account.tax', 'Adjustment Tax')
    adjustment_amount = fields.Float('Adjustment Amount')
    tax_adjustment_log_ids = fields.One2many('tax.adjustment.log', 'return_id')
    total_sale_adjustment_amount = fields.Float('Total Sales Adjustment', compute='compute_adjustment')
    total_purchase_adjustment_amount = fields.Float('Total Purchases Adjustment', compute='compute_adjustment')
    total_sales = fields.Float('Total Sales', compute='compute_total_sales')
    total_purchase = fields.Float('Total Purchases', compute='compute_total_sales')
    reverse_charge_line_ids = fields.One2many('vat.reverse.charge.line', 'return_id')
    total_reverse_charge_service_declared = fields.Float('Total Reverse Charge', compute='compute_reverse_charge')
    total_reverse_charge_service = fields.Float('Total Reverse Charge', compute='compute_reverse_charge')
    total_reverse_charge_goods_declared = fields.Float('Total Reverse Charge', compute='compute_reverse_charge')
    total_reverse_charge_goods = fields.Float('Total Reverse Charge', compute='compute_reverse_charge')
    total_declared = fields.Float('Total Declared', compute='compute_reverse_charge')
    total_reversed = fields.Float('Total Import', compute='compute_reverse_charge')
    total_declared_amount = fields.Float('Total Amount in purchase', compute='compute_reverse_charge')
    total_recover = fields.Float('Total amount in purchase recover', compute='compute_reverse_charge')
    total_sale_payable_value = fields.Float('Total Sales Payable Value', compute='compute_reverse_charge')
    total_sales_value = fields.Float('Total Sale Value', compute='compute_reverse_charge')
    total_payable_value = fields.Float('Total Payable Value', compute='compute_reverse_charge')
    purchase_tax_in_purchase = fields.Float('Total Payable Value', compute='compute_purchase_tax_charge')
    domestic_sales = fields.Float('Domestic Sales', compute='compute_reverse_charge')
    domestic_purchases = fields.Float('Domestic Purchase', compute='compute_reverse_charge')
    domestic_purchases_tax = fields.Float('Domestic Purchase', compute='compute_reverse_charge')
    exempt_sales = fields.Float('Exempt Sales', compute='compute_purchase_tax_charge')
    zero_rated_sales = fields.Float('Zero Rated Sales', compute='compute_purchase_tax_charge')
    total_purchase_without_import = fields.Float('Taxable Purchases')
    total_purchase_tax_without_import = fields.Float('Tax in purchases')
    export_sales = fields.Float('Export Sales')
    total_sales_in_form = fields.Float('Total Sales', compute='compute_total_charge')
    total_purchase_in_form = fields.Float('Total Purchase', compute='compute_total_charge')
    total_purchase_tax_in_form = fields.Float('Total Purchase Tax', compute='compute_total_charge')
    sales_in_form = fields.Float('Sales in Form', compute='compute_purchase_tax_charge')
    sales_tax_in_form = fields.Float('Sales Tax in Form', compute='compute_purchase_tax_charge')

    @api.model
    def create(self, vals):
        start_date = vals['start_date']
        vat_obj = self.env['uae.vat.return']
        vats = vat_obj.search([])
        if vats:
            for vat in vats:
                vat_end = datetime.datetime.strptime(str(vat.end_date), "%Y-%m-%d")
                start = datetime.datetime.strptime(str(start_date), "%Y-%m-%d")
                if start <= vat_end:
                    raise UserError(_('The VAT return period which you have selected is already exist!'))
        return super(UaeVatReturn, self).create(vals)

    @api.multi
    def compute_total_charge(self):
        for line in self:
            line.total_sales_in_form = line.sales_in_form + line.domestic_sales + line.zero_rated_sales + line.export_sales + line.exempt_sales
            line.total_purchase_in_form = line.total_purchase_without_import + line.total_reverse_charge_goods_declared + line.domestic_purchases
            line.total_purchase_tax_in_form = line.total_purchase_tax_without_import + line.total_reverse_charge_goods + line.domestic_purchases_tax

    @api.multi
    @api.depends('return_line_ids')
    def compute_purchase_tax_charge(self):
        for line in self:
            purchase_tax = 0.0
            exempt_sales = 0.0
            zero_rated_sales = 0.0
            total_taxable_sales = 0.0
            total_tax = 0.0
            for return_line in line.return_line_ids:
                if return_line.scope == 'Purchase' and return_line.reverse_charge == False:
                    purchase_tax += return_line.tax_amount
                    _logger.info(purchase_tax)
                if return_line.name == 'Exempt' and return_line.scope == 'Sale' and return_line.reverse_charge == False:
                    exempt_sales += return_line.base_amount
                if return_line.name == 'Zero-Rated' and return_line.scope == 'Sale' and return_line.reverse_charge == False:
                    zero_rated_sales += return_line.base_amount
                if return_line.tax_amount and return_line.scope == 'Sale' and return_line.reverse_charge == False:
                    total_taxable_sales += return_line.base_amount
                    total_tax += return_line.tax_amount

        _logger.info(exempt_sales)
        _logger.info(zero_rated_sales)
        line.purchase_tax_in_purchase = purchase_tax
        line.exempt_sales = exempt_sales
        line.zero_rated_sales = zero_rated_sales
        line.sales_in_form = total_taxable_sales
        line.sales_tax_in_form = total_tax

    @api.multi
    @api.depends('return_line_ids')
    def compute_reverse_charge(self):
        for line in self:
            for reverse in line.reverse_charge_line_ids:
                if reverse.type == 'import':
                    line.total_reverse_charge_goods_declared = float(reverse.amount) + reverse.custom_amount
                    line.total_reverse_charge_goods = reverse.reverse_charge_amount
                if reverse.type == 'export':
                    line.export_sales = reverse.amount
                if reverse.type == 'domestic_sales':
                    line.domestic_sales = reverse.amount
                if reverse.type == 'domestic_purchases':
                    line.domestic_purchases = reverse.amount
                    line.domestic_purchases_tax = reverse.reverse_charge_amount
            line.total_declared_amount = line.total_declared + line.total_purchase_in_period_before_tax
            line.total_recover = line.total_collected_on_purchase + line.total_reversed
            line.total_sale_payable_value = line.total_collected_on_sales
            line.total_sales_value = line.total_declared + line.total_taxable_sales_in_period_before_tax
            line.total_payable_value = line.total_sale_payable_value - line.total_recover

    @api.multi
    def compute_total_sales(self):
        for line in self:
            total_sales = 0.0
            total_purchase = 0.0
            invoice_ids = self.env['account.invoice'].search([
                ('type', 'in', ['out_invoice']),
                ('state', 'not in', ['draft', 'cancel']),
                ('date_invoice', '>=', line.start_date),
                ('date_invoice', '<=', line.end_date)
            ])
            for invoice in invoice_ids:
                total_sales+=invoice.amount_total
            vendor_invoice_ids = self.env['account.invoice'].search([
                ('type', 'in', ['in_invoice']),
                ('state', 'not in', ['draft', 'cancel']),
                ('date_invoice', '>=', line.start_date),
                ('date_invoice', '<=', line.end_date)
            ])
            for in_invoice in vendor_invoice_ids:
                total_purchase+=in_invoice.amount_total
            line.total_sales = total_sales
            line.total_purchase = total_purchase

    @api.multi
    def compute_total_purchase_without_import(self):
        for line in self:
            purchase_base_amount = 0.0
            purchase_tax_amount = 0.0
            vendor_invoice_ids = self.env['account.invoice'].search([
                ('type', 'in', ['in_invoice']),
                ('state', 'not in', ['draft', 'cancel']),
                ('date_invoice', '>=', line.start_date),
                ('date_invoice', '<=', line.end_date),
                ('import_charge', '=', False)
            ])
            for invoice in vendor_invoice_ids:
                for line in invoice.invoice_line_ids:
                    if line.invoice_line_tax_ids:
                        for tax in line.invoice_line_tax_ids:
                            purchase_tax_amount+=line.price_subtotal*(tax.amount/100)
                        purchase_base_amount+=line.price_subtotal
            line.total_purchase_without_import = base_amount
            line.total_purchase_tax_without_import = tax_amount

    @api.multi
    def compute_adjustment(self):
        for line in self:
            sales_adjustment = 0.0
            purchase_adjustment = 0.0
            for log in line.tax_adjustment_log_ids:
                if log.tax_id.type_tax_use == 'sale':
                    sales_adjustment+= log.amount
                if log.tax_id.type_tax_use == 'purchase':
                    purchase_adjustment+= log.amount
            line.total_sale_adjustment_amount = sales_adjustment
            line.total_purchase_adjustment_amount = purchase_adjustment

    @api.multi
    def export_for_import(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('VAT Report')
        fp = io.BytesIO()
        sub_header_style = xlwt.easyxf('pattern: pattern solid, fore_colour blue;font: bold 1,height 280;align: horiz center')
        line_content_style = xlwt.easyxf("font: name Helvetica, height 170;align: horiz center")
        row=0
        worksheet.write_merge(0, 1, 0, 4,"VAT Return Form Report", sub_header_style)
        worksheet.write_merge(2, 2, 0, 4, "Number", sub_header_style)
        worksheet.write_merge(3, 3, 0, 4, self.name, sub_header_style)
        row=4
        worksheet.write(row, 0, 'S.No', sub_header_style)
        worksheet.write(row, 1, 'Description', sub_header_style)
        worksheet.write(row, 2, 'Amount', sub_header_style)
        worksheet.write(row, 3, 'Adjustment', sub_header_style)
        worksheet.write(row, 4, 'VAT Amount', sub_header_style)
        row+=1
        worksheet.write(row, 0,'', sub_header_style)
        worksheet.write(row, 1, 'VAT on Sales', sub_header_style)
        worksheet.write(row, 2,'', sub_header_style)
        worksheet.write(row, 3,'', sub_header_style)
        worksheet.write(row, 4,'', sub_header_style)
        row+=1
        worksheet.write(row, 0, 1, line_content_style)
        worksheet.write(row, 1, "Standard rated sales", line_content_style)
        worksheet.write(row, 2, self.sales_in_form, line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, self.sales_tax_in_form, line_content_style)
        row+=1
        worksheet.write(row, 0, 2, line_content_style)
        worksheet.write(row, 1, "Sales to registered taxpayers in other GCC States", line_content_style)
        worksheet.write(row, 2, '', line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, '', line_content_style)
        row+=1
        worksheet.write(row, 0, 3, line_content_style)
        worksheet.write(row, 1, "Sales subject to domestic reverse charge mechanism", line_content_style)
        worksheet.write(row, 2, self.domestic_sales, line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, '', line_content_style)
        row+=1
        worksheet.write(row, 0, 4, line_content_style)
        worksheet.write(row, 1, "Zero rated domestic sales", line_content_style)
        worksheet.write(row, 2, self.zero_rated_sales, line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, '', line_content_style)
        row+=1
        worksheet.write(row, 0, 5, line_content_style)
        worksheet.write(row, 1, "Exports", line_content_style)
        worksheet.write(row, 2, self.export_sales, line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, '', line_content_style)
        row+=1
        worksheet.write(row, 0, 6, line_content_style)
        worksheet.write(row, 1, "Exempt sales", line_content_style)
        worksheet.write(row, 2, self.exempt_sales, line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, '', line_content_style)
        row+=1
        worksheet.write(row, 0, 7, line_content_style)
        worksheet.write(row, 1, "Total sales", line_content_style)
        worksheet.write(row, 2, self.total_sales_in_form, line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, self.sales_tax_in_form, line_content_style)
        row+=1
        worksheet.write(row, 0, 8, line_content_style)
        worksheet.write(row, 1, "Standard rated domestic purchases", line_content_style)
        worksheet.write(row, 2, self.total_purchase_without_import, line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, self.total_purchase_tax_without_import, line_content_style)
        row+=1
        worksheet.write(row, 0, 9, line_content_style)
        worksheet.write(row, 1, "Import subject to VAT either paid at customs or deferred", line_content_style)
        worksheet.write(row, 2, self.total_reverse_charge_goods_declared, line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, self.total_reverse_charge_goods, line_content_style)
        row+=1
        worksheet.write(row, 0, 10, line_content_style)
        worksheet.write(row, 1, "Import subject to VAT accounted for through reverse charge mechanism", line_content_style)
        worksheet.write(row, 2, '', line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, '', line_content_style)
        row+=1
        worksheet.write(row, 0,11, line_content_style)
        worksheet.write(row, 1, "Purchase subject to domestic reverse charge mechanism", line_content_style)
        worksheet.write(row, 2, self.domestic_purchases, line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, self.domestic_purchases_tax, line_content_style)
        row+=1
        worksheet.write(row, 0, 12, line_content_style)
        worksheet.write(row, 1, "Purchase from non registered suppliers, zero rated/ exempt purchases", line_content_style)
        worksheet.write(row, 2, '', line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, '', line_content_style)
        row+=1
        worksheet.write(row, 0, 13, line_content_style)
        worksheet.write(row, 1, "Total Purchases", line_content_style)
        worksheet.write(row, 2, self.total_purchase_in_form, line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, self.total_purchase_tax_in_form, line_content_style)
        row+=1
        worksheet.write(row, 0, 14, line_content_style)
        worksheet.write(row, 1, "Total VAT due for current periods", line_content_style)
        worksheet.write(row, 2, '', line_content_style)
        worksheet.write(row, 3, '', line_content_style)
        worksheet.write(row, 4, self.total_payable, line_content_style)
        # row+=1
        # worksheet.write(row, 0, 2, line_content_style)
        # worksheet.write(row, 1, 'Total taxable sales in period, before tax', line_content_style)
        # worksheet.write(row, 2, self.total_taxable_sales_in_period_before_tax, line_content_style)
        # worksheet.merge_range('C8:D8', '', line_content_style)
        # row += 1
        # worksheet.write(row, 0, 3, line_content_style)
        # worksheet.write(row, 1, 'Tax collected on sales', line_content_style)
        # worksheet.write(row, 2, self.total_collected_on_sales, line_content_style)
        # worksheet.merge_range('C9:D9', '', line_content_style)
        # row += 1
        #
        # worksheet.write(row, 0, 4, line_content_style)
        # worksheet.write(row, 1, 'Adjustments to tax on sales', line_content_style)
        # worksheet.write(row, 2, self.total_sale_adjustment_amount , line_content_style)
        # worksheet.merge_range('C10:D10', '', line_content_style)
        # row += 1
        # worksheet.write(row, 0, 5, line_content_style)
        # worksheet.write(row, 1, 'Subtotal of tax on sales', line_content_style)
        # worksheet.write(row, 2, self.total_collected_on_sales, line_content_style)
        # worksheet.merge_range('C11:D11', '', line_content_style)
        # row += 1
        # worksheet.write(row, 0,'', cell_format)
        # worksheet.write(row, 1, 'Purchase', cell_format)
        # worksheet.write(row, 2, '', cell_format)
        # worksheet.merge_range('C12:D12', '', cell_format)
        # row+=1
        # worksheet.write(row, 0, 6, line_content_style)
        # worksheet.write(row, 1, 'Total purchases in period, before tax', line_content_style)
        # worksheet.write(row, 2, self.total_purchase, line_content_style)
        # worksheet.merge_range('C13:D13', '', line_content_style)
        # row += 1
        # worksheet.write(row, 0, 7, line_content_style)
        # worksheet.write(row, 1, 'Total taxable purchases in period, before tax', line_content_style)
        # worksheet.write(row, 2, self.total_taxable_purchase_in_period_before_tax, line_content_style)
        # worksheet.merge_range('C14:D14', '', line_content_style)
        # row += 1
        # worksheet.write(row, 0, 8, line_content_style)
        # worksheet.write(row, 1, 'Tax reclaimable on purchases', line_content_style)
        # worksheet.write(row, 2, abs(self.total_payable), line_content_style)
        # worksheet.merge_range('C15:D15', '', line_content_style)
        # row += 1
        # worksheet.write(row, 0, 9, line_content_style)
        # worksheet.write(row, 1, 'Adjustments to reclaimable tax on purchases', line_content_style)
        # worksheet.write(row, 2, self.total_purchase_adjustment_amount, line_content_style)
        # worksheet.merge_range('C16:D16', '', line_content_style)
        # row += 1
        # worksheet.write(row, 0, 10, line_content_style)
        # worksheet.write(row, 1, 'Subtotal of tax on purchases', line_content_style)
        # worksheet.write(row, 2, self.total_collected_on_purchase, line_content_style)
        # row += 1
        # worksheet.write(row, 0,'', cell_format)
        # worksheet.write(row, 1, 'Reverse Charges', cell_format)
        # worksheet.write(row, 2, 'Declared Amount', cell_format)
        # worksheet.write(row, 3, 'Reverse Charge Amount', cell_format)
        # row += 1
        # worksheet.write(row, 0, 11, line_content_style)
        # worksheet.write(row, 1, 'Goods imported', line_content_style)
        # worksheet.write(row, 2, self.total_reverse_charge_goods_declared, line_content_style)
        # worksheet.write(row, 3, self.total_reverse_charge_goods, line_content_style)
        # row += 1
        # worksheet.write(row, 0, 12, cell_format)
        # worksheet.write(row, 1, 'Net Amount', cell_format)
        # worksheet.write(row, 2, '', cell_format)
        # worksheet.merge_range('C19:D19', self.total_payable, cell_format)

        workbook.save(fp)
        out = base64.encodestring(fp.getvalue())
        self.write({'report': out, 'name_r': 'VAT Report.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'uae.vat.return',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
        }

        # workbook.close()
        # data = base64.b64encode(open('/tmp/' + file_path, 'rb+').read())
        #
        # # open_data = open("/tmp/VATReport.xlsx", 'rb')
        # # data = open_data.read()
        # values = {
        #     'name': "VATReport.xlsx",
        #     'datas_fname': 'VATReport.xlsx',
        #     'res_model': 'ir.ui.view',
        #     'res_id': False,
        #     'type': 'binary',
        #     'public': True,
        #
        #     'datas': base64.b64encode(data),
        #
        # }
        # # open_data.close()
        #
        # attachment_id = self.env['ir.attachment'].sudo().create(values)
        # # Prepare your download URL
        # download_url = '/web/content/' + str(attachment_id.id) + '?download=True'
        # base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        #
        # return {
        #     "type": "ir.actions.act_url",
        #     "url": str(base_url) + str(download_url),
        #     "target": "new",
        # }

    @api.multi
    def set_to_paid(self):
        self.write({'state': 'paid'})

    @api.depends('return_line_ids')
    def compute_zero_rate_tax(self):
        zero_rated = 0.0
        for vat in self:
            for line in vat.return_line_ids:
                if line.zero_rated and line.scope == 'Sale':
                    zero_rated+=line.base_amount
            vat.zero_rated_total = zero_rated

    @api.depends('return_line_ids')
    def compute_state_wise_tax(self):
        dubai_tax = 0.0
        dubai_sales = 0.0
        fujaira_tax = 0.0
        fujaira_sales = 0.0
        abhu_dabhi_tax = 0.0
        abhu_dabhi_sales = 0.0
        umm_al_quwain_tax = 0.0
        umm_al_quwain_sales = 0.0
        ras_al_khaima_tax = 0.0
        ras_al_khaima_sales = 0.0
        ajman_tax = 0.0
        ajman_sales = 0.0
        sharjah_tax = 0.0
        sharjah_sales = 0.0
        for vat in self:
            for line in vat.return_line_ids:
                if line.scope == 'Sale':
                    dubai_tax+=line.tax_amount
                    dubai_sales+=line.base_amount

            vat.fujaira_tax_total = fujaira_tax
            vat.fujaira_sales_total = fujaira_sales
            vat.dubai_tax_total = dubai_tax
            vat.dubai_sales_total = dubai_sales
            vat.abu_dhabi_tax_total = abhu_dabhi_tax
            vat.abu_dhabi_sales_total = abhu_dabhi_sales
            vat.sharjah_tax_total = sharjah_tax
            vat.sharjah_sales_total = sharjah_sales
            vat.ras_al_khaimah_tax_total = ras_al_khaima_tax
            vat.ras_al_khaimah_sales_total = ras_al_khaima_sales
            vat.umm_al_quwain_tax_total = umm_al_quwain_tax
            vat.umm_al_quwain_sales_total = umm_al_quwain_sales
            vat.ajman_tax_total = ajman_tax
            vat.ajman_sales_total = ajman_sales

    # @api.depends('total_collected_on_sales','total_collected_on_purchase')
    # def compute_total_payable(self):
    #     for line in self:
    #         line.total_payable = line.sales_tax_in_form - line.total_purchase_tax_in_form
    #         if line.total_payable < 0:
    #             line.total_minus = True
    
    @api.depends('total_collected_on_sales','total_collected_on_purchase')
    def compute_total_payable(self):
        for line in self:
            line.total_payable = line.total_collected_on_purchase - line.total_collected_on_sales
            if line.total_payable < 0:
                line.total_minus = True

    @api.multi
    def unlink(self):
        for document in self:
            if document.state not in ('new','validate'):
                raise Warning(_('You cannot delete an document which is not new state'))
        return models.Model.unlink(self)

    @api.multi
    def tax_adjustment(self):
        adjustment_form_id = self.env.ref('sit_saudi_vat.tax_adjustment_wizard').id
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tax.adjustment.wizard',
            'views': [(adjustment_form_id, 'form')],
            'view_id': adjustment_form_id,
            'target': 'new',
        }

    @api.multi
    def sales_domestic_charge(self):
        for line in self:
            reverse_charge_invoice_ids = self.env['account.invoice'].search([
                ('type', 'in', ['out_invoice']),
                ('state', 'not in', ['draft', 'cancel']),
                ('date_invoice', '>=', line.start_date),
                ('date_invoice', '<=', line.end_date),
                ('domestic', '=', True),
            ])
            views = [(self.env.ref('account.invoice_supplier_tree').id, 'tree'),
                     (self.env.ref('account.invoice_supplier_form').id, 'form')]
            return {
                'name': _('Paid Invoices'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'view_id': False,
                'views': views,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', [x.id for x in reverse_charge_invoice_ids])],
            }

    @api.multi
    def purchases_domestic_charge(self):
        for line in self:
            reverse_charge_invoice_ids = self.env['account.invoice'].search([
                ('type', 'in', ['in_invoice']),
                ('state', 'not in', ['draft', 'cancel']),
                ('date_invoice', '>=', line.start_date),
                ('date_invoice', '<=', line.end_date),
                ('domestic', '=', True),
            ])
            views = [(self.env.ref('account.invoice_supplier_tree').id, 'tree'),
                     (self.env.ref('account.invoice_supplier_form').id, 'form')]
            return {
                'name': _('Paid Invoices'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'view_id': False,
                'views': views,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', [x.id for x in reverse_charge_invoice_ids])],
            }


    @api.multi
    def open_import_charge(self):
        for line in self:
            import_charge_invoice_ids = self.env['account.invoice'].search([
                ('type', 'in', ['in_invoice']),
                ('state', 'not in', ['draft', 'cancel']),
                ('date_invoice', '>=', line.start_date),
                ('date_invoice', '<=', line.end_date),
                ('import_charge', '=', True)
            ])
            views = [(self.env.ref('account.invoice_supplier_tree').id, 'tree'),
                     (self.env.ref('account.invoice_supplier_form').id, 'form')]
            return {
                'name': _('Paid Invoices'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'view_id': False,
                'views': views,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', [x.id for x in import_charge_invoice_ids])],
            }

    @api.multi
    def tax_compute(self):
        """ Return all account.tax ids for which there is at least
        one account.move.line in the context period
        for the user company.

        Caveat: this ignores record rules and ACL but it is good
        enough for filtering taxes with activity during the period.
        """
        return_lines = self.env['uae.vat.return.line'].sudo().search([('return_id','=',self.id)])
        return_lines.unlink()
        total_sales_tax = 0.0
        total_sales = 0.0
        total_purchase_tax = 0.0
        total_purchase = 0.0
        zero_rated = False
        for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
            if tax.amount < 0:
                zero_rated = True
            req = """select aml.tax_line_id, COALESCE(SUM(aml.debit-aml.credit), 0) FROM account_move_line aml
                    INNER JOIN account_tax tax on (aml.tax_line_id = tax.id)
                    WHERE aml.tax_exigible AND aml.date >= %s AND aml.date <= %s AND aml.company_id = %s AND tax.type_tax_use = 'sale' GROUP BY aml.tax_line_id;"""

            self.env.cr.execute(req, (self.start_date, self.end_date, self.company_id.id))
            lines = self.env.cr.fetchall()
            _logger.info('Tax Amount >>>>>>>>>>>>>>>>')
            _logger.info(lines)
            for line in lines:
                if tax.id == line[0]:
                    total_sales_tax += abs(line[1])
                    value = return_lines.create({'return_id': self.id,
                                     'tax_amount': abs(line[1]),
                                     'name': tax.name,
                                     'tax_per': tax.amount,
                                     'zero_rated':zero_rated,
                                     'reverse_charge': tax.reverse_charge,
                                     'scope': 'Sale'})

            sql = """SELECT  r.account_tax_id, COALESCE(SUM(aml.debit-aml.credit), 0)
                             FROM account_move_line aml
                             INNER JOIN account_move_line_account_tax_rel r ON (aml.id = r.account_move_line_id)
                             INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                             WHERE aml.date >= %s AND aml.date <= %s AND aml.tax_exigible AND aml.company_id = %s AND t.type_tax_use = 'sale' GROUP BY r.account_tax_id"""
            self.env.cr.execute(sql, (self.start_date, self.end_date, self.company_id.id))
            net_amounts = self.env.cr.fetchall()
            _logger.info('Base Amount >>>>>>>>>>>>>>>>')
            _logger.info(net_amounts)
            for line in net_amounts:
                if tax.id == line[0]:
                    if line[0] in (row[0] for row in lines):
                        total_sales += abs(line[1])
                        value.write({'base_amount':abs(line[1])})
                    else:
                        total_sales += abs(line[1])
                        return_lines.create({'return_id': self.id,
                                             'tax_amount': 0,
                                             'base_amount': abs(line[1]),
                                             'name': tax.name,
                                             'tax_per': tax.amount,
                                             'zero_rated': zero_rated,
                                             'reverse_charge': tax.reverse_charge,
                                             'scope': 'Sale'})

            purchase_taxs = """select aml.tax_line_id, COALESCE(SUM(aml.debit-aml.credit), 0) FROM account_move_line aml
                    INNER JOIN account_tax tax on (aml.tax_line_id = tax.id)
                    WHERE aml.tax_exigible AND aml.date >= %s AND aml.date <= %s AND aml.company_id = %s AND tax.type_tax_use = 'purchase' GROUP BY tax.id, aml.tax_line_id;"""

            self.env.cr.execute(purchase_taxs, (self.start_date, self.end_date, self.company_id.id))
            purchase_taxs_results = self.env.cr.fetchall()
            _logger.info(self.start_date)
            _logger.info(self.end_date)
            _logger.info(self.company_id.id)
            _logger.info(lines)
            _logger.info(purchase_taxs_results)
            for line in purchase_taxs_results:
                _logger.info(line)
                if tax.id == line[0]:
                    total_purchase_tax+=abs(line[1])
                    value = return_lines.create({'return_id': self.id,
                                     'tax_amount': abs(line[1]),
                                     'name': tax.name,
                                     'tax_per': tax.amount,
                                     'zero_rated': zero_rated,
                                     'reverse_charge': tax.reverse_charge,
                                     'scope': 'Purchase'})

            purchase_taxable = """SELECT  r.account_tax_id, COALESCE(SUM(aml.debit-aml.credit), 0)
                             FROM account_move_line aml
                             INNER JOIN account_move_line_account_tax_rel r ON (aml.id = r.account_move_line_id)
                             INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                             WHERE aml.date >= %s AND aml.date <= %s AND aml.tax_exigible AND aml.company_id = %s AND t.type_tax_use = 'purchase' GROUP BY r.account_tax_id"""

            self.env.cr.execute(purchase_taxable, (self.start_date, self.end_date, self.company_id.id))
            purchase_taxable_values = self.env.cr.fetchall()
            for line in purchase_taxable_values:
                if tax.id == line[0]:
                    if line[0] in (row[0] for row in purchase_taxs_results):
                        total_purchase+=abs(line[1])
                        value.write({'base_amount':abs(line[1])})
                    else:
                        total_purchase += abs(line[1])
                        return_lines.create({'return_id': self.id,
                                             'tax_amount': 0,
                                             'base_amount': abs(line[1]),
                                             'name': tax.name,
                                             'tax_per': tax.amount,
                                             'zero_rated': zero_rated,
                                             'reverse_charge': tax.reverse_charge,
                                             'scope': 'Purchase'})
            _logger.info("Total Sales and Purchase")
            _logger.info(total_sales)
            _logger.info(total_purchase)
        # reverse_charge_invoice_ids = self.env['account.invoice'].search([
        #     ('type', 'in', ['in_invoice']),
        #     ('state', 'not in', ['draft', 'cancel']),
        #     ('date_invoice', '>=', self.start_date),
        #     ('date_invoice', '<=', self.end_date),
        #     ('reverse_charge', '=', True),
        #     ('import_charge', '=', False)
        # ])
        import_charge_invoice_ids = self.env['account.invoice'].search([
            ('type', 'in', ['in_invoice']),
            ('state', 'not in', ['draft', 'cancel']),
            ('date_invoice', '>=', self.start_date),
            ('date_invoice', '<=', self.end_date),
            ('import_charge', '=', True)
        ])
        # total_declared_amount = 0.0
        # total_reverse_charge_amount = 0.0
        # for line in reverse_charge_invoice_ids:
        #     total_declared_amount+=line.reverse_charge_entry.amount
        #     total_reverse_charge_amount+=line.reverse_charge_entry.reverse_charge_amount

        if self.reverse_charge_line_ids:
            self.reverse_charge_line_ids.unlink()

        # reverse_charge = {
        #     'type': 'reverse',
        #     'return_id': self.id,
        #     'amount': total_declared_amount,
        #     'reverse_charge_amount': total_reverse_charge_amount,
        # }
        # if reverse_charge:
        #     self.env['vat.reverse.charge.line'].create(reverse_charge)
        total_import_declared_amount = 0.0
        total_import_reverse_charge_amount = 0.0
        total_custom_amount = 0.0
        for line in import_charge_invoice_ids:
            for charge in line.bill_of_entry:
                if charge.state not in ['draft','cancel']:
                    total_import_declared_amount+=charge.amount
                    total_import_reverse_charge_amount+=charge.reverse_charge_amount
                    total_custom_amount+= charge.custom_amount

        import_charge = {
            'type': 'import',
            'return_id': self.id,
            'amount': total_import_declared_amount,
            'custom_amount': total_custom_amount,
            'reverse_charge_amount': total_import_reverse_charge_amount,
        }

        if import_charge:
            self.env['vat.reverse.charge.line'].create(import_charge)
        self.return_line_ids.write({})

        #domestic Reverse Charge
        sales_domestic_charge = self.env['account.invoice'].search([
            ('type', 'in', ['out_invoice']),
            ('state', 'not in', ['draft', 'cancel']),
            ('date_invoice', '>=', self.start_date),
            ('date_invoice', '<=', self.end_date),
            ('domestic', '=', True),
        ])
        purchase_domestic_charge = self.env['account.invoice'].search([
            ('type', 'in', ['in_invoice']),
            ('state', 'not in', ['draft', 'cancel']),
            ('date_invoice', '>=', self.start_date),
            ('date_invoice', '<=', self.end_date),
            ('domestic', '=', True),
        ])
        total_domestic_amount = 0.0
        total_domestic_reverse_charge_amount = 0.0
        for line in sales_domestic_charge:
            total_domestic_amount+=line.amount_untaxed
            total_domestic_reverse_charge_amount+=line.amount_tax

        domestic_charge = {
            'type': 'domestic_sales',
            'return_id': self.id,
            'amount': total_domestic_amount,
            'reverse_charge_amount': total_domestic_reverse_charge_amount,
        }

        if domestic_charge:
            self.env['vat.reverse.charge.line'].create(domestic_charge)
        total_purchase_domestic_declared_amount = 0.0
        total_purchase_domestic_reverse_charge_amount = 0.0
        for line in purchase_domestic_charge:
            total_purchase_domestic_declared_amount+=line.amount_untaxed
            total_purchase_domestic_reverse_charge_amount+=line.amount_tax

        pruchase_domestic = {
            'type': 'domestic_purchases',
            'return_id': self.id,
            'amount': total_purchase_domestic_declared_amount,
            'reverse_charge_'
            'amount': total_purchase_domestic_reverse_charge_amount,
        }

        if pruchase_domestic:
            self.env['vat.reverse.charge.line'].create(pruchase_domestic)
        purchase_base_amount = 0.0
        purchase_tax_amount = 0.0
        vendor_invoice_ids = self.env['account.invoice'].search([
            ('type', 'in', ['in_invoice']),
            ('state', 'not in', ['draft', 'cancel']),
            ('date_invoice', '>=', self.start_date),
            ('date_invoice', '<=', self.end_date),
            ('import_charge', '=', False)
        ])
        for invoice in vendor_invoice_ids:
            for line in invoice.invoice_line_ids:
                if line.invoice_line_tax_ids:
                    for tax in line.invoice_line_tax_ids:
                        purchase_tax_amount+=line.price_subtotal*(tax.amount/100)
                    purchase_base_amount+=line.price_subtotal
        total_purchase_without_import = purchase_base_amount
        total_purchase_tax_without_import = purchase_tax_amount

        export_invoices = self.env['account.invoice'].search([
            ('type', 'in', ['out_invoice']),
            ('state', 'not in', ['draft', 'cancel']),
            ('date_invoice', '>=', self.start_date),
            ('date_invoice', '<=', self.end_date),
            ('export', '=', True),
        ])
        total_export_amount = 0.0

        for line in export_invoices:
            total_export_amount+=line.amount_untaxed

        export_amount = {
            'type': 'export',
            'return_id': self.id,
            'amount': total_export_amount,
        }

        if export_amount:
            self.env['vat.reverse.charge.line'].create(export_amount)

        self.write({'name':"VR/"+str(self.start_date)+"/"+str(self.end_date),'total_purchase_tax_without_import':total_purchase_tax_without_import,'total_purchase_without_import':total_purchase_without_import,'total_purchase_in_period_before_tax':total_purchase,'total_sales_in_period_before_tax':total_sales,'total_collected_on_sales':total_sales_tax,'total_taxable_sales_in_period_before_tax':total_sales,'total_taxable_purchase_in_period_before_tax':total_purchase, 'total_collected_on_purchase':total_purchase_tax})

    @api.multi
    def action_validate_new(self):
        for tax_return in self:
            amount = tax_return.total_payable
            if tax_return.total_payable == 0:
                return tax_return.write({'state':'filed'})
            if amount > 0:
                tax_return.tax_validate()
            else:
                roll_form_id = self.env.ref('sit_saudi_vat.rollforward_wizard').id
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'roll.over.wizard',
                    'views': [(roll_form_id, 'form')],
                    'view_id': roll_form_id,
                    'target': 'new',
                }

    @api.multi
    def roll_over(self):
        precision = self.env['decimal.precision'].precision_get('TaxReturn')

        for tax_return in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = fields.Datetime.now()

            name = _('VAT Return')
            move_dict = {
                'narration': name,
                'ref': tax_return.name,
                'journal_id': 3,
                'date': date,
            }
            amount = abs(tax_return.total_payable)
            tax = self.env['account.tax'].search([('type_tax_use','=','sale')],limit=1)
            debit_account_id = tax.account_id.id
            credit_account_id = self.tax_suspense_account_id.id
            if debit_account_id:
                debit_line = (0, 0, {
                    'name': tax_return.name,
                    'partner_id': tax_return.partner_id.id,
                    'account_id': debit_account_id,
                    'journal_id': 3,
                    'date': date,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

            if credit_account_id:
                credit_line = (0, 0, {
                    'name': tax_return.name,
                    'partner_id': tax_return.partner_id.id,
                    'account_id': credit_account_id,
                    'journal_id': 3,
                    'date': date,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_id = tax_return.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (tax_return.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': tax_return.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_id = tax_return.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (tax_return.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': tax_return.journal_id.id,
                    'date': date,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            tax_return.write({'move_id': move.id})
            move.post()
            self.write({'state':'rollover'})

    @api.multi
    def tax_close(self):
        self.write({'state':'filed'})

    @api.multi
    def tax_validate(self):
        precision = self.env['decimal.precision'].precision_get('TaxReturn')

        for tax_return in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = fields.Date.today()

            name = _('VAT Return')
            move_dict = {
                'narration': name,
                'ref': tax_return.name,
                'journal_id': 3,
                'date': date
            }
            amount = tax_return.total_payable
            tax = self.env['account.tax'].search([('type_tax_use','=','sale')],limit=1)
            debit_account_id = tax.account_id.id
            credit_account_id = tax_return.partner_id.property_account_payable_id.id
            if debit_account_id:
                debit_line = (0, 0, {
                    'name': tax_return.name,
                    'partner_id': tax_return.partner_id.id,
                    'account_id': debit_account_id,
                    'journal_id': 3,
                    'date': date,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

            if credit_account_id:
                credit_line = (0, 0, {
                    'name': tax_return.name,
                    'partner_id': tax_return.partner_id.id,
                    'account_id': credit_account_id,
                    'journal_id': 3,
                    'date': date,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_id = tax_return.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (tax_return.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': tax_return.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_id = tax_return.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (tax_return.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': tax_return.journal_id.id,
                    'date': date,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            tax_return.write({'move_id': move.id})
            move.post()
            self.write({'state':'validate'})

    @api.multi
    def tax_close(self):
        self.write({'state':'filed'})

class VatImportChargeLine(models.Model):
    _name = "vat.reverse.charge.line"
    _description = 'VAT Reverse Charge Lines'

    return_id = fields.Many2one('uae.vat.return','Return ID')
    type = fields.Selection([('reverse', 'Supplies subject to the reverse charge provisions	'),('export', 'Export'), ('import', 'Goods imported'),('domestic_sales', 'Sales subject to domestic reverse charge mechanism'), ('domestic_purchases', 'Purchase subject to domestic reverse charge mechanism')], copy=False)
    amount = fields.Char('Declared Amount')
    reverse_charge_amount = fields.Float('Reverse Charge Amount')
    custom_amount = fields.Float('Custom Amount')

class UaeVatReturnLine(models.Model):
    _name = "uae.vat.return.line"
    _description = 'UAE VAT Lines'

    return_id = fields.Many2one('uae.vat.return','Return ID')
    name = fields.Char('Name of the Tax')
    tax_per = fields.Float('TAX Percentage')
    scope = fields.Char('Scope')
    tax_amount = fields.Float('Tax Amount')
    base_amount = fields.Float('Base Amount')
    zero_rated = fields.Boolean('Zero Rated Tax')
    reverse_charge = fields.Boolean('Reverse Charge')
    remaing_vat_line = fields.Boolean('Remaining Vat',default=False)

    def get_balance_domain(self, state_list, type_list):
        tax_ids = self.env['account.tax'].search([('name', '=', self.name)])
        for line in tax_ids:
            domain = [
                ('move_id.state', 'in', state_list),
                ('tax_line_id', '=', line.id),
                ('tax_exigible', '=', True)
            ]
            # if type_list:
            #     domain.append(('move_id.move_type', 'in', type_list))
            return domain

    def get_base_balance_domain(self, state_list, type_list):
        tax_ids = self.env['account.tax'].search([('name','=',self.name)])
        for line in tax_ids:
            domain = [
                ('move_id.state', 'in', state_list),
                ('tax_ids', 'in', line.id),
                ('tax_exigible', '=', True)
            ]
            # if type_list:
            #     domain.append(('move_id.move_type', 'in', type_list))
            return domain

    def get_target_type_list(self, move_type=None):
        if move_type == 'refund':
            return ['receivable_refund', 'payable_refund']
        elif move_type == 'regular':
            return ['receivable', 'payable', 'liquidity', 'other']
        return []

    def get_target_state_list(self, target_move="posted"):
        if target_move == 'posted':
            state = ['posted']
        elif target_move == 'all':
            state = ['posted', 'draft']
        else:
            state = []
        return state

    def get_context_values(self):
        context = self.env.context
        return (
            context.get('from_date', fields.Date.context_today(self)),
            context.get('to_date', fields.Date.context_today(self)),
            context.get('company_id', self.env.user.company_id.id),
            context.get('posted'),
        )

    @api.multi
    def view_tax_regular_lines(self):
        self.ensure_one()
        return self.get_lines_action(tax_or_base='tax', move_type='regular')

    def get_lines_action(self, tax_or_base='tax', move_type=None):
        domain = self.get_move_lines_domain(
            tax_or_base=tax_or_base, move_type=move_type)
        action = self.env.ref('account.action_account_moves_all_tree')
        vals = action.read()[0]
        vals['context'] = {}
        vals['domain'] = domain
        _logger.info(vals)
        return vals

    def get_move_lines_domain(self, tax_or_base='tax', move_type=None):
        state_list = ['posted']
        type_list = ['receivable', 'payable', 'liquidity', 'other']
        domain = [('date', '<=', self.return_id.end_date),('date', '>=', self.return_id.start_date),('company_id', '=', self.return_id.company_id.id)]
        balance_domain = []
        if tax_or_base == 'tax':
            balance_domain = self.get_balance_domain(state_list, type_list)
        elif tax_or_base == 'base':
            balance_domain = self.get_base_balance_domain(
                state_list, type_list)
        domain.extend(balance_domain)
        _logger.info("Domain Value >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        _logger.info(domain)
        return domain

    @api.multi
    def view_base_regular_lines(self):
        self.ensure_one()
        return self.get_lines_action(tax_or_base='base', move_type='regular')

class VatPlace(models.Model):
    _name = "vat.place"

    name = fields.Char('Name')

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    date_of_supply = fields.Date('Date of Supply',readonly=True, states={'draft': [('readonly', False)]})
    date_of_issue = fields.Date('Date of Issue',readonly=True, states={'draft': [('readonly', False)]})
    trn = fields.Char('VAT', related='partner_id.vat', states={'draft': [('readonly', False)]})
    bill_of_entry = fields.One2many('reverse.charge', 'vendor_bill')
    reverse_charge_entry = fields.Many2one('reverse.charge.service', 'Reverse Charge Entry',readonly=True)
    import_charge = fields.Boolean('Import', readonly=True, states={'draft': [('readonly', False)]})
    reverse_charge = fields.Boolean('Reverse Charge', readonly=True, states={'draft': [('readonly', False)]})
    domestic = fields.Boolean('Reverse Charge Mechanism')
    export = fields.Boolean('Export')

    @api.multi
    def action_invoice_open(self):
        for invoice in self:
            if invoice.reverse_charge_entry:
                invoice.reverse_charge_entry.action_move_create()
        return super(AccountInvoice, self).action_invoice_open()

class AccountTax(models.Model):
    _inherit = "account.tax"

    reverse_charge = fields.Boolean('Is This Reverse Charge Tax')

class ResPartner(models.Model):
    _inherit = "res.partner"

    product_ids = fields.Many2many('product.product', 'customer_product_rel', 'partner_id', 'product_id',
                                        string="Visible Products", help='Vendor can view the selected products only')