# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, QWebException
from werkzeug import url_encode
from odoo.tools import float_compare
from datetime import datetime
from dateutil import relativedelta
import logging
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vat_status = fields.Boolean(string='Reconciliation VAT Method', readonly=False)
    vat_method = fields.Selection([('single_vat','Single VAT Account'),('multiple_vat','Multiple VAT Account')], readonly=False, default='single_vat')
    vat_calculation = fields.Boolean(string='VAT Calculation', readonly=False)
    vat_calculation_date = fields.Date("Vat Calculate From",default=fields.Date.today())


    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('sit_saudi_vat.vat_method', self.vat_method)
        self.env['ir.config_parameter'].sudo().set_param('sit_saudi_vat.vat_status', self.vat_status)
        self.env['ir.config_parameter'].sudo().set_param('sit_saudi_vat.vat_calculation', self.vat_calculation)
        self.env['ir.config_parameter'].sudo().set_param('sit_saudi_vat.vat_calculation_date', self.vat_calculation_date)


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ir_param = self.env['ir.config_parameter'].sudo()
        vat_status = ir_param.get_param(
            'sit_saudi_vat.vat_status') or False
        vat_method = ir_param.get_param(
            'sit_saudi_vat.vat_method') or "single_vat"
        vat_calculation_date = ir_param.get_param(
            'sit_saudi_vat.vat_calculation_date') or fields.Date.today()
        vat_calculation = ir_param.get_param(
            'sit_saudi_vat.vat_calculation') or False
        res.update(
            vat_status=bool(vat_status),
            vat_method=str(vat_method),
            vat_calculation=bool(vat_calculation),
            vat_calculation_date=str(vat_calculation_date),
        )
        return res


class AccountInherit(models.Model):
    _inherit = 'account.account'

    vat_account = fields.Boolean(string='VAT Account', readonly=False)

    @api.onchange('vat_account')
    def _check_vat_account_status(self):
    	config_vat_obj = self.env['res.config.settings']
    	vat_status = config_vat_obj.sudo().search([], limit=1, order="id desc").vat_status
    	vat_method = config_vat_obj.sudo().search([], limit=1, order="id desc").vat_method
    	# print(vat_status,vat_method)
    	if self.vat_account:
	    	if vat_status:
	    		vat_accounts = self.env['account.account'].search([('vat_account','=',True)])
	    		if vat_method == 'single_vat':
	    			if len(vat_accounts) >= 1:
	    				raise ValidationError(_("As per Company Policy, you can’t create more vat account !!"))
	    				return False



class AccountTaxInherit(models.Model):
    _inherit = 'account.tax'

    @api.onchange('account_id','refund_account_id')
    def onchange_check_vat_reconciliation(self):

        config_vat_obj = self.env['res.config.settings']
        vat_status = config_vat_obj.sudo().search([], limit=1, order="id desc").vat_status

        if vat_status:

            vat_accounts = self.env['account.account'].search([('vat_account','=',True)])
            vat_acc_list = []

            for acc in vat_accounts:
                vat_acc_list.append(acc.id)

            res = {}
            res['domain'] = {'account_id':[('id','in',vat_acc_list)],'refund_account_id':[('id','in',vat_acc_list)]}
            return res
            for rec in self:
                return {'domain': {'account_id': [('vat_account', '=', True)],'refund_account_id': [('vat_account', '=', True)]}}


class UaeVatReturn(models.Model):
    _inherit = "uae.vat.return"

    vat_payment = fields.Many2one('account.payment', string='Payment JV', default=None, readonly=True)
    vat_company_logo = fields.Binary("Image", attachment=True,
        help="This field holds the image used as avatar for this contact, limited to 1024x1024px")
    vat_report_14 = fields.Float("Corrections from previos period (between SAR ± 5,000 )")
    vat_report_15 = fields.Float(" VAT credit carried forward from previos period(s)")

    month_type = fields.Selection([('quarter', 'Quarter'), ('month', 'Month')], default='month', copy=False)
    no_of_months = fields.Float(string="Month", compute='compute_month', readonly=True, default="0")
    month_quarter = fields.Selection([
        ('first_quarter', 'First Quarter'),
        ('second_quarter', 'Second Quarter'),
        ('third_quarter', 'Third Quarter'),
        ('fourth_quarter', 'Fourth Quarter'),
        ('first_half_year', 'First Half Year'),
        ('second_half_year', 'Second Half Year'),
        ('full_year', 'Full Year')
        ], copy=False)

    @api.multi
    @api.depends('start_date','end_date')
    def compute_month(self):
        start = self.start_date
        end = self.end_date

        if start and end:

            date1 = datetime.strptime(str(start), '%Y-%m-%d')
            date2 = datetime.strptime(str(end), '%Y-%m-%d')
            r = relativedelta.relativedelta(date2, date1)
            self.no_of_months = r.months

    @api.multi
    def tax_calculate_remaining(self):


        """ Return all account.tax ids for which there is at least
        one account.move.line in the context period
        for the user company.

        Caveat: this ignores record rules and ACL but it is good
        enough for filtering taxes with activity during the period.
        """

        config_vat_obj = self.env['res.config.settings']
        vat_calculation = config_vat_obj.sudo().search([], limit=1, order="id desc").vat_calculation
        vat_calculation_date = config_vat_obj.sudo().search([], limit=1, order="id desc").vat_calculation_date

        return_lines = self.env['uae.vat.return.line'].sudo().search([('return_id','=',self.id)])
        remaining_return_lines = self.env['uae.vat.return.line'].sudo().search([('return_id','=',self.id),('remaing_vat_line','=',True)])
        remaining_return_lines.unlink()
        total_sales_tax = 0.0
        total_sales = 0.0
        total_purchase_tax = 0.0
        total_purchase = 0.0
        zero_rated = False
        for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
            if tax.amount < 0:
                zero_rated = True

            if vat_calculation and vat_calculation_date:
                # print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",vat_calculation_date)
                req = """select aml.tax_line_id, COALESCE(SUM(aml.debit-aml.credit), 0) FROM account_move_line aml
                        INNER JOIN account_tax tax on (aml.tax_line_id = tax.id)
                        INNER JOIN account_move am on (aml.move_id = am.id)
                        WHERE aml.tax_exigible AND aml.date >= %s AND aml.date < %s AND aml.company_id = %s AND am.vat_status = false AND tax.type_tax_use = 'sale' GROUP BY aml.tax_line_id;"""
                self.env.cr.execute(req, (vat_calculation_date, self.start_date, self.company_id.id))
            else:
                req = """select aml.tax_line_id, COALESCE(SUM(aml.debit-aml.credit), 0) FROM account_move_line aml
                        INNER JOIN account_tax tax on (aml.tax_line_id = tax.id)
                        INNER JOIN account_move am on (aml.move_id = am.id)
                        WHERE aml.tax_exigible AND am.vat_status = false AND tax.type_tax_use = 'sale' AND aml.company_id = %s GROUP BY aml.tax_line_id;"""
                self.env.cr.execute(req, [self.company_id.id])

            lines = self.env.cr.fetchall()
            print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",lines)
            # return False
            _logger.info('Tax Amount >>>>>>>>>>>>>>>>')
            _logger.info(lines)
            for line in lines:
                print("ppppppppppppppppppppppppppppppppppppppp",line)

                if tax.id == line[0]:
                    total_sales_tax += abs(line[1])
                    value = return_lines.create({'return_id': self.id,
                                     'tax_amount': abs(line[1]),
                                     'name': tax.name,
                                     'tax_per': tax.amount,
                                     'zero_rated':zero_rated,
                                     'reverse_charge': tax.reverse_charge,
                                     'remaing_vat_line': True,
                                     'scope': 'Sale'})



            if vat_calculation and vat_calculation_date:
                sql = """SELECT  r.account_tax_id, COALESCE(SUM(aml.debit-aml.credit), 0)
                             FROM account_move_line aml
                             INNER JOIN account_move_line_account_tax_rel r ON (aml.id = r.account_move_line_id)
                             INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                             INNER JOIN account_move am on (aml.move_id = am.id)
                             WHERE aml.date >= %s AND aml.date < %s AND am.vat_status = false AND aml.tax_exigible AND aml.company_id = %s AND t.type_tax_use = 'sale' GROUP BY r.account_tax_id"""
                self.env.cr.execute(sql, (vat_calculation_date, self.start_date, self.company_id.id))
            else:
                sql = """SELECT  r.account_tax_id, COALESCE(SUM(aml.debit-aml.credit), 0)
                             FROM account_move_line aml
                             INNER JOIN account_move_line_account_tax_rel r ON (aml.id = r.account_move_line_id)
                             INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                             INNER JOIN account_move am on (aml.move_id = am.id)
                             WHERE am.vat_status = false AND aml.tax_exigible AND aml.company_id = %s AND t.type_tax_use = 'sale' GROUP BY r.account_tax_id"""
                self.env.cr.execute(sql, [self.company_id.id])



            net_amounts = self.env.cr.fetchall()
            _logger.info('Base Amount >>>>>>>>>>>>>>>>')
            _logger.info(net_amounts)
            # return False
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
                                             'remaing_vat_line': True,
                                             'scope': 'Sale'})

            if vat_calculation and vat_calculation_date:

                purchase_taxs = """select aml.tax_line_id, COALESCE(SUM(aml.debit-aml.credit), 0) FROM account_move_line aml
                    INNER JOIN account_tax tax on (aml.tax_line_id = tax.id)
                    INNER JOIN account_move am on (aml.move_id = am.id)
                    WHERE am.vat_status = false AND aml.tax_exigible AND aml.date >= %s AND aml.date < %s AND aml.company_id = %s AND tax.type_tax_use = 'purchase' GROUP BY tax.id, aml.tax_line_id;"""
                self.env.cr.execute(purchase_taxs, (vat_calculation_date,self.start_date,self.company_id.id))
            else:
                purchase_taxs = """select aml.tax_line_id, COALESCE(SUM(aml.debit-aml.credit), 0) FROM account_move_line aml
                    INNER JOIN account_tax tax on (aml.tax_line_id = tax.id)
                    INNER JOIN account_move am on (aml.move_id = am.id)
                    WHERE am.vat_status = false AND aml.tax_exigible AND aml.company_id = %s AND tax.type_tax_use = 'purchase' GROUP BY tax.id, aml.tax_line_id;"""
                self.env.cr.execute(purchase_taxs, ([self.company_id.id]))

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
                                     'remaing_vat_line': True,
                                     'scope': 'Purchase'})

            if vat_calculation and vat_calculation_date:
                purchase_taxable = """SELECT  r.account_tax_id, COALESCE(SUM(aml.debit-aml.credit), 0)
                     FROM account_move_line aml
                     INNER JOIN account_move_line_account_tax_rel r ON (aml.id = r.account_move_line_id)
                     INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                     INNER JOIN account_move am on (aml.move_id = am.id)
                     WHERE aml.date >= %s AND aml.date < %s AND am.vat_status = false AND aml.tax_exigible AND aml.company_id = %s AND t.type_tax_use = 'purchase' GROUP BY r.account_tax_id"""
                self.env.cr.execute(purchase_taxable, (vat_calculation_date,self.start_date,self.company_id.id))
            else:
                purchase_taxable = """SELECT  r.account_tax_id, COALESCE(SUM(aml.debit-aml.credit), 0)
                     FROM account_move_line aml
                     INNER JOIN account_move_line_account_tax_rel r ON (aml.id = r.account_move_line_id)
                     INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                     INNER JOIN account_move am on (aml.move_id = am.id)
                     WHERE am.vat_status = false AND aml.tax_exigible AND aml.company_id = %s AND t.type_tax_use = 'purchase' GROUP BY r.account_tax_id"""
                self.env.cr.execute(purchase_taxable, ([self.company_id.id]))

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
                                             'remaing_vat_line': True,
                                             'scope': 'Purchase'})
            _logger.info("Total Sales and Purchase")
            _logger.info(total_sales)
            _logger.info(total_purchase)

        import_charge_invoice_ids = self.env['account.invoice'].search([
            ('type', 'in', ['in_invoice']),
            ('state', 'not in', ['draft', 'cancel']),
            ('date_invoice', '>=', vat_calculation_date),
            ('date_invoice', '<', self.start_date),
            ('vat_status', '=', False),
            ('import_charge', '=', True)
        ])
        if self.reverse_charge_line_ids:
            self.reverse_charge_line_ids.unlink()

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
            ('date_invoice', '>=', vat_calculation_date),
            ('date_invoice', '<', self.start_date),
            ('vat_status', '=', False),
            ('domestic', '=', True),
        ])
        purchase_domestic_charge = self.env['account.invoice'].search([
            ('type', 'in', ['in_invoice']),
            ('state', 'not in', ['draft', 'cancel']),
            ('date_invoice', '>=', vat_calculation_date),
            ('date_invoice', '<', self.start_date),
            ('vat_status', '=', False),
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
            ('date_invoice', '>=', vat_calculation_date),
            ('date_invoice', '<', self.start_date),
            ('vat_status', '=', False),
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
            ('date_invoice', '>=', vat_calculation_date),
            ('date_invoice', '<', self.start_date),
            ('vat_status', '=', False),
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
        self.write({
            'name':"VR/"+str(self.start_date)+"/"+str(self.end_date),
            'total_purchase_tax_without_import':self.total_purchase_tax_without_import+total_purchase_tax_without_import,
            'total_purchase_without_import':self.total_purchase_without_import+total_purchase_without_import,
            'total_purchase_in_period_before_tax':self.total_purchase_in_period_before_tax+total_purchase,
            'total_sales_in_period_before_tax':self.total_sales_in_period_before_tax+total_sales,
            'total_collected_on_sales':self.total_collected_on_sales+total_sales_tax,
            'total_taxable_sales_in_period_before_tax':self.total_taxable_sales_in_period_before_tax+total_sales,
            'total_taxable_purchase_in_period_before_tax':self.total_taxable_purchase_in_period_before_tax+total_purchase,
            'total_collected_on_purchase':self.total_collected_on_purchase+total_purchase_tax
            })


    @api.multi
    def set_all_inv_je_vat_status(self):

        invoice_ids_query = """SELECT id from account_invoice where move_id in (
                                 SELECT aml.move_id
                                 FROM account_move_line aml
                                 INNER JOIN account_move_line_account_tax_rel r ON (aml.id = r.account_move_line_id)
                                 INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                                 WHERE aml.date >= %s AND aml.date <= %s AND aml.tax_exigible AND aml.company_id = %s AND t.type_tax_use in ('purchase','sale') GROUP BY aml.move_id
                             )"""
        self.env.cr.execute(invoice_ids_query, (self.start_date, self.end_date, self.company_id.id))
        invoice_ids = self.env.cr.fetchall()
        invoice_ids_dict = []

        for iv in invoice_ids:
            invoice_ids_dict.append(iv[0])

        account_invoices = self.env['account.invoice'].browse(invoice_ids_dict)
        if account_invoices:
            for inv in account_invoices:
                inv.vat_status = True
                inv.vat_return_record = self.name
                inv.vat_return_id = self.id

        move_ids_query = """SELECT aml.move_id
                             FROM account_move_line aml
                             INNER JOIN account_move_line_account_tax_rel r ON (aml.id = r.account_move_line_id)
                             INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                             WHERE aml.date >= %s AND aml.date <= %s AND aml.tax_exigible AND aml.company_id = %s AND t.type_tax_use in ('purchase','sale')
                             GROUP BY aml.move_id"""
        self.env.cr.execute(move_ids_query, (self.start_date, self.end_date, self.company_id.id))
        move_ids = self.env.cr.fetchall()
        move_ids_dict = []

        for mv in move_ids:
            move_ids_dict.append(mv[0])

        account_moves = self.env['account.move'].browse(move_ids_dict)
        print(account_moves)
        if account_moves:
            for am in account_moves:
                am.vat_status = True
                am.vat_return_record = '( Upload to '+self.name+' )'
                am.vat_return_id = self.id


    @api.multi
    def tax_validate(self):

        precision = self.env['decimal.precision'].precision_get('TaxReturn')
        config_vat_obj = self.env['res.config.settings']
        vat_status = config_vat_obj.sudo().search([], limit=1, order="id desc").vat_status
        vat_method = config_vat_obj.sudo().search([], limit=1, order="id desc").vat_method
        # print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",vat_method)
        # return False
        if vat_status or vat_method == 'multiple_vat':

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
                    'date': date,
                    'vat_status':True,
                    'vat_return_id':tax_return.id
                }
                amount = tax_return.total_payable
                s_amount = tax_return.total_collected_on_sales
                p_amount = tax_return.total_collected_on_purchase

                sale_tax = self.env['account.tax'].search([('type_tax_use','=','sale')],limit=1)
                purchase_tax = self.env['account.tax'].search([('type_tax_use','=','purchase')],limit=1)
                sales_tax_account_id = sale_tax.account_id.id
                purchase_tax_account_id = purchase_tax.account_id.id
                payable_account_id = tax_return.partner_id.property_account_payable_id.id
                # print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",payable_account_id)
                # print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",sales_tax_account_id)
                # print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",purchase_tax_account_id)
                # return False
                if purchase_tax_account_id:
                    purchase_tax_line = (0, 0, {
                        'name': tax_return.name,
                        'partner_id': tax_return.partner_id.id,
                        'account_id': purchase_tax_account_id,
                        'journal_id': 3,
                        'date': date,
                        'debit': 0.0,
                        'credit': p_amount > 0.0 and p_amount or 0.0,
                    })
                    line_ids.append(purchase_tax_line)

                if payable_account_id:

                    payable_line_1 = (0, 0, {
                        'name': tax_return.name,
                        'partner_id': tax_return.partner_id.id,
                        'account_id': payable_account_id,
                        'journal_id': 3,
                        'date': date,
                        'debit': p_amount > 0.0 and p_amount or 0.0,
                        'credit': 0.0,
                    })
                    line_ids.append(payable_line_1)

                    payable_line_2 = (0, 0, {
                        'name': tax_return.name,
                        'partner_id': tax_return.partner_id.id,
                        'account_id': payable_account_id,
                        'journal_id': 3,
                        'date': date,
                        'debit': 0.0,
                        'credit': s_amount > 0.0 and s_amount or 0.0,
                    })
                    line_ids.append(payable_line_2)



                if sales_tax_account_id:
                    sales_tax_line = (0, 0, {
                        'name': tax_return.name,
                        'partner_id': tax_return.partner_id.id,
                        'account_id': sales_tax_account_id,
                        'journal_id': 3,
                        'date': date,
                        'debit': s_amount > 0.0 and s_amount or 0.0,
                        'credit': 0.0,
                    })
                    line_ids.append(sales_tax_line)

                move_dict['line_ids'] = line_ids
                move = self.env['account.move'].create(move_dict)
                tax_return.write({'move_id': move.id})
                move.post()
                self.write({'state':'validate'})
                self.set_all_inv_je_vat_status()
                # self.write({'state':'validate'})


        else:

            for tax_return in self:
                line_ids = []
                debit_sum = 0.0
                credit_sum = 0.0
                date = fields.Date.today()

                name = _('VAT Return')
                move_dict = {
                    'narration': name,
                    'ref': tax_return.name,
                    'journal_id': tax_return.journal_id.id,
                    'date': date,
                    'vat_status':True,
                    'vat_return_id':tax_return.id
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
                        'journal_id': tax_return.journal_id.id,
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
                        'journal_id': tax_return.journal_id.id,
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
                self.set_all_inv_je_vat_status()


class VatReturnPaymentInherit(models.TransientModel):
    _inherit = "vat.return.payment"

    @api.multi
    def expense_post_payment(self):
        self.ensure_one()
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        vat_return = self.env['uae.vat.return'].browse(active_ids)
        payment = self.env['account.payment'].create(self._get_payment_vals())
        payment.post()
        body = (_("A payment of %s %s with the reference <a href='/mail/view?%s'>%s</a> related to your expense %s has been made.") % (payment.amount, payment.currency_id.symbol, url_encode({'model': 'account.payment', 'res_id': payment.id}), payment.name, vat_return.name))
        vat_return.message_post(body=body)
        account_move_lines_to_reconcile = self.env['account.move.line']
        for line in payment.move_line_ids + vat_return.move_id.line_ids:
            if line.account_id.internal_type == 'payable':
                account_move_lines_to_reconcile |= line
        account_move_lines_to_reconcile.reconcile()
        vat_return.write({'state':'paid','vat_payment':payment.id})
        # Reconcile the payment, i.e. lookup on the payable account move lines
        return {'type': 'ir.actions.act_window_close'}



class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    vat_return_id = fields.Many2one('uae.vat.return', string='Vat Return', default=None, readonly=True)
    vat_status = fields.Boolean("Vat Return",default=False,readonly=True)
    vat_return_record = fields.Char(string='Vat Return', readonly=True)


    @api.multi
    def button_cancel(self):
        for move in self:
            j_entry_status = self.check_journal_entries_in_vat_return()
            if j_entry_status:
                    raise UserError(_('You cannot modify a posted entry of validated VAT return.\nFirst you should modify VAT return to draft state.'))

            if not move.journal_id.update_posted:
                raise UserError(_('You cannot modify a posted entry of this journal.\nFirst you should set the journal to allow cancelling entries.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()
        if self.ids:
            self.check_access_rights('write')
            self.check_access_rule('write')
            self._check_lock_date()
            self._cr.execute('UPDATE account_move '\
                       'SET state=%s '\
                       'WHERE id IN %s', ('draft', tuple(self.ids),))
            self.invalidate_cache()
        self._check_lock_date()
        return True


    @api.multi
    def unlink(self):
        for move in self:
            j_entry_status = self.check_journal_entries_in_vat_return()
            if j_entry_status:
                    raise UserError(_('You cannot modify a posted entry of validated VAT return.\nFirst you should modify VAT return to draft state.'))
            else:
                #check the lock date + check if some entries are reconciled
                move.line_ids._update_check()
                move.line_ids.unlink()
        return super(AccountMoveInherit, self).unlink()


    @api.multi
    def check_journal_entries_in_vat_return(self):
        vat_returns = self.env['uae.vat.return'].search([('state','in',['validate','paid','filed'])])
        if len(vat_returns) > 0:
            journal_entries = []
            for vat in vat_returns:

                move_ids_query = """SELECT aml.move_id
                             FROM account_move_line aml
                             INNER JOIN account_move_line_account_tax_rel r ON (aml.id = r.account_move_line_id)
                             INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                             WHERE aml.date >= %s AND aml.date <= %s AND aml.tax_exigible AND aml.company_id = %s AND t.type_tax_use in ('purchase','sale') GROUP BY aml.move_id"""
                self.env.cr.execute(move_ids_query, (vat.start_date, vat.end_date, self.company_id.id))
                move_ids = self.env.cr.fetchall()
                move_ids_dict = []

                for mv in move_ids:
                    journal_entries.append(mv[0])

            if self.id in journal_entries:
                return True
            else:
                return False


class AccountInvoiceInherit(models.Model):
    _inherit = "account.invoice"

    vat_status = fields.Boolean("Vat Status",default=False,readonly=True)
    vat_return_id = fields.Many2one('uae.vat.return', string='Vat Return', default=None, readonly=True)
    vat_return_record = fields.Char(string='Vat Return', readonly=True)

    @api.multi
    def action_invoice_cancel(self):
        print('action_invoice_cancel')
        invoice_status = self.check_invoices_in_vat_return_dates()
        if invoice_status:
            raise UserError(_('You cannot modify invoices which are in validated VAT return dates.\nFirst you should modify VAT return to draft state.'))

        return self.filtered(lambda inv: inv.state != 'cancel').action_cancel()


    @api.multi
    def action_invoice_open(self):
        print('action_invoice_open')
        invoice_status = self.check_invoices_in_vat_return_dates()
        if invoice_status:
            raise UserError(_('You cannot modify invoices which are in validated VAT return dates.\nFirst you should modify VAT return to draft state.'))
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: not inv.partner_id):
            raise UserError(_("The field Vendor is required, please complete it to validate the Vendor Bill."))
        if to_open_invoices.filtered(lambda inv: inv.state != 'draft'):
            raise UserError(_("Invoice must be in draft state in order to validate it."))
        if to_open_invoices.filtered(lambda inv: float_compare(inv.amount_total, 0.0, precision_rounding=inv.currency_id.rounding) == -1):
            raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead."))
        if to_open_invoices.filtered(lambda inv: not inv.account_id):
            raise UserError(_('No account was found to create the invoice, be sure you have installed a chart of account.'))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        return to_open_invoices.invoice_validate()

    @api.multi
    def action_invoice_paid(self):
        # print('action_invoice_paid')
        # invoice_status = self.check_invoices_in_vat_return_dates()
        # if invoice_status:
        #     raise UserError(_('You cannot modify invoices which are in validated VAT return dates.\nFirst you should modify VAT return to draft state.'))
        # lots of duplicate calls to action_invoice_paid, so we remove those already paid
        to_pay_invoices = self.filtered(lambda inv: inv.state != 'paid')
        if to_pay_invoices.filtered(lambda inv: inv.state not in ('open', 'in_payment')):
            raise UserError(_('Invoice must be validated in order to set it to register payment.'))
        if to_pay_invoices.filtered(lambda inv: not inv.reconciled):
            raise UserError(_('You cannot pay an invoice which is partially paid. You need to reconcile payment entries first.'))

        for invoice in to_pay_invoices:
            if any([move.journal_id.post_at_bank_rec and move.state == 'draft' for move in invoice.payment_move_line_ids.mapped('move_id')]):
                invoice.write({'state': 'in_payment'})
            else:
                invoice.write({'state': 'paid'})


    @api.multi
    def action_invoice_draft(self):
        print('action_invoice_draft')
        invoice_status = self.check_invoices_in_vat_return_dates()
        if invoice_status:
            raise UserError(_('You cannot modify invoices which are in validated VAT return dates.\nFirst you should modify VAT return to draft state.'))

        if self.filtered(lambda inv: inv.state != 'cancel'):
            raise UserError(_("Invoice must be cancelled in order to reset it to draft."))
        # go from canceled state to draft state
        self.write({'state': 'draft', 'date': False})
        # Delete former printed invoice
        try:
            report_invoice = self.env['ir.actions.report']._get_report_from_name('account.report_invoice')
        except IndexError:
            report_invoice = False
        if report_invoice and report_invoice.attachment:
            for invoice in self:
                with invoice.env.do_in_draft():
                    invoice.number, invoice.state = invoice.move_name, 'open'
                    attachment = self.env.ref('account.account_invoices').retrieve_attachment(invoice)
                if attachment:
                    attachment.unlink()
        return True

    @api.multi
    def unlink(self):
        invoice_status = self.check_invoices_in_vat_return_dates()
        if invoice_status:
            raise UserError(_('You cannot modify invoices which are in validated VAT return dates.\nFirst you should modify VAT return to draft state.'))

        for invoice in self:
            if invoice.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an invoice which is not draft or cancelled. You should create a credit note instead.'))
            elif invoice.move_name:
                raise UserError(_('You cannot delete an invoice after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))
        return super(AccountInvoiceInherit, self).unlink()


    @api.multi
    def check_invoices_in_vat_return_dates(self):
        vat_returns = self.env['uae.vat.return'].search([('state','in',['validate','paid','filed'])])
        # print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa vat_returns",vat_returns)
        if len(vat_returns) > 0:
            invoices = []
            for vat in vat_returns:

                invoice_ids_query = """SELECT id from account_invoice where id in (
                            SELECT aml.move_id
                             FROM account_move_line aml
                             INNER JOIN account_move_line_account_tax_rel r ON (aml.id = r.account_move_line_id)
                             INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                             WHERE aml.date >= %s AND aml.date <= %s AND aml.tax_exigible AND aml.company_id = %s AND t.type_tax_use in ('purchase','sale') GROUP BY aml.move_id
                             )"""
                self.env.cr.execute(invoice_ids_query, (vat.start_date, vat.end_date, vat.company_id.id))
                invoice_ids = self.env.cr.fetchall()
                invoice_ids_dict = []

                for iv in invoice_ids:
                    invoices.append(iv[0])

            # print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa invoices",invoices)
            if self.id in invoices:
                return True
            else:
                return False

    @api.multi
    def action_view_vat_return(self):
        view_id = self.env.ref('sit_saudi_vat.view_uae_vat_return_form').id
        context = self._context.copy()
        return {
            'name':'view_uae_vat_return_form',
            'view_type':'form',
            'view_mode':'tree,form',
            'views' : [(view_id,'form')],
            'res_model':'uae.vat.return',
            'view_id':view_id,
            'type':'ir.actions.act_window',
            'res_id':self.vat_return_id.id,
            'target':'self',
            'context':context,
        }

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default['vat_status'] = False
        default['vat_return_id'] = None
        default['vat_return_record'] = ''
        return super(AccountInvoiceInherit, self).copy(default)
