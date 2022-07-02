# -*- coding: utf-8 -*-

import logging

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ReportTaxUae(models.AbstractModel):
    _name = 'report.uae_vat.report_tax_uae'
    _inherit = 'report.account_financial_report.abstract_report_xlsx'

    def _get_report_name(self):
        return _('VAT Report')

    @api.model
    def get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        return {
            'data': data['form'],
            'places': self.get_lines(data.get('form')),
            'totals': self.get_lines_total(data.get('form')),
        }

    def _get_col_count_filter_name(self):
        return 2

    def _get_col_count_filter_value(self):
        return 3

    def _get_report_columns(self, report):
        return {
            0: {'header': _('Code'), 'field': 'code', 'width': 5},
            1: {'header': _('Name'), 'field': 'name', 'width': 100},
            2: {'header': _('Net'),
                'field': 'net',
                'type': 'amount',
                'width': 14},
            3: {'header': _('Tax'),
                'field': 'tax',
                'type': 'amount',
                'width': 14},
        }

    def _get_report_filters(self, report):
        return [
        ]

    def _sql_from_amls_one(self):
        sql = """SELECT "account_move_line".vat_place, "account_move_line".tax_line_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                    FROM %s
                    WHERE %s AND "account_move_line".tax_exigible GROUP BY "account_move_line".tax_line_id, "account_move_line".vat_place"""
        return sql

    def _sql_from_amls_two(self):
        sql = """SELECT "account_move_line".vat_place, r.account_tax_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                 FROM %s
                 INNER JOIN account_move_line_account_tax_rel r ON ("account_move_line".id = r.account_move_line_id)
                 INNER JOIN vat_place vp ON (vp.id = "account_move_line".vat_place)                 
                 INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                 WHERE %s AND "account_move_line".tax_exigible GROUP BY "account_move_line".vat_place, r.account_tax_id"""
        return sql

    def _compute_from_amls(self, options, taxes, place):
        _logger.info("Compute AML is Working >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        #compute the tax amount
        sql = self._sql_from_amls_one()
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            _logger.info("Total Results")
            _logger.info(results)
            _logger.info("One Results")
            _logger.info(result[0])
            _logger.info("Places in Taxes >>>>>>>>>")
            if place == result[0]:
                if result[1] in taxes:
                    _logger.info("Inside loop One Results")
                    _logger.info(result[1])
                    taxes[result[1]]['tax'] = abs(result[2])
                    result

        #compute the net amount
        sql2 = self._sql_from_amls_two()
        query = sql2 % (tables, where_clause)    
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if place == result[0]:
                if result[1] in taxes:
                    taxes[result[1]]['net'] = abs(result[2])

    @api.model
    def get_lines_total(self, options):
        taxes = {}
        totals = []
        places = []
        total_sales_tax_amount = 0.0
        total_sales_taxable_amount = 0.0
        total_purchase_tax_amount = 0.0
        total_purchase_taxable_amount = 0.0
        _logger.info("Get Line total is Working >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        for place in self.env['vat.place'].search([]):
            for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
                if tax.children_tax_ids:
                    for child in tax.children_tax_ids:
                        if child.type_tax_use != 'none':
                            continue
                        taxes[child.id] = {'tax': 0, 'net': 0, 'name': child.name, 'type': tax.type_tax_use, 'place': place.id, 'place_name':place.name}
                else:
                    taxes[tax.id] = {'tax': 0, 'net': 0, 'name': tax.name, 'type': tax.type_tax_use, 'place': place.id, 'place_name':place.name}
            self.with_context(date_from=options['date_from'], date_to=options['date_to'], strict_range=True)._compute_from_amls(options, taxes, place.id)
            groups = dict((tp, []) for tp in ['sale', 'purchase'])
            for tax in taxes.values():
                _logger.info(tax)
                if tax['tax']:
                    groups[tax['type']].append(tax)
            _logger.info("Total Dictionary")
            _logger.info(groups)
            places.append(groups)
            _logger.info(places)
        for record in places:
            for line in record['sale']:
                total_sales_tax_amount+=line['tax']
                total_sales_taxable_amount+=line['net']
        for record in places:
            for line in record['purchase']:
                total_purchase_tax_amount+=line['tax']
                total_purchase_taxable_amount+=line['net']
        totals.append({'total_sales_tax_amount':total_sales_tax_amount,
                       'total_sales_taxable_amount': total_sales_taxable_amount,
                       'total_purchase_tax_amount': total_purchase_tax_amount,
                       'total_purchase_taxable_amount':total_purchase_taxable_amount})
        return totals

    @api.model
    def get_lines(self, options):
        taxes = {}
        places = []
        _logger.info("Get Line is Working >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        for place in self.env['vat.place'].search([]):
            for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
                if tax.children_tax_ids:
                    for child in tax.children_tax_ids:
                        if child.type_tax_use != 'none':
                            continue
                        taxes[child.id] = {'tax': 0, 'net': 0, 'name': child.name, 'type': tax.type_tax_use, 'place': place.id, 'place_name':place.name}
                else:
                    taxes[tax.id] = {'tax': 0, 'net': 0, 'name': tax.name, 'type': tax.type_tax_use, 'place': place.id, 'place_name':place.name}
            self.with_context(date_from=options['date_from'], date_to=options['date_to'], strict_range=True)._compute_from_amls(options, taxes, place.id)
            groups = dict((tp, []) for tp in ['sale', 'purchase'])
            for tax in taxes.values():
                _logger.info(tax)
                if tax['tax']:
                    groups[tax['type']].append(tax)
            _logger.info("Total Dictionary")
            _logger.info(groups)
            places.append(groups)
            _logger.info(places)
        return places

    def _generate_report_content(self, workbook, report):
        # For each taxtag
        self.write_array_header()
        # Write taxtag line
        totals = []
        totals.append({'total_sales_tax_amount':50,
                       'total_sales_taxable_amount': 50,
                       'total_purchase_tax_amount': 50,
                       'total_purchase_taxable_amount':50})
        self.write_line(totals)