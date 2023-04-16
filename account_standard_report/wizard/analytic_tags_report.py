# -*- coding: utf-8 -*-

import calendar

import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta
from odoo import api, models, fields, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import AccessError, UserError
from odoo.tools import __


class AccountStandardLedger(models.TransientModel):
    _inherit = 'account.report.standard.ledger'

    def _sql_report_object_tags(self):
        analytic_tags = self.analytic_ids and (
                len(self.analytic_ids) > 1 and str(tuple(self.analytic_ids.ids)) or '(%s)' % self.analytic_ids.ids[0]) or '(0)'
        there_is_tags = bool(self.analytic_ids)
        query = """INSERT INTO  account_report_standard_ledger_report_object (report_id, create_uid, create_date, object_id, name, analytic_id)
            SELECT DISTINCT 
                %s AS report_id,
                %s AS create_uid,
                NOW() AS create_date,
                tag.id AS object_id,
                tag.name AS name,
                tag.id  AS analytic_id
            FROM
                account_analytic_tag tag
            WHERE 
            CASE WHEN %s = True THEN  
            id IS NOT NULL and id IN %s 
            ELSE  id IN %s  END """ % (
            self.report_id.id,
            self.env.uid,
            bool(analytic_tags), analytic_tags, analytic_tags
        )
        # params =
        self.env.cr.execute(query)
        # res = self.env.cr.dictfetchall()
        pass

    def _sql_init_balance_tags(self):
        company = self.company_id
        # initial balance partner
        query = """INSERT INTO account_report_standard_ledger_line(report_id, create_uid, create_date, account_id, partner_id, analytic_id, employee_id,  analytic_account_id, type, type_view, date, debit, credit, balance, cumul_balance, company_currency_id, reconciled, report_object_id)

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
            CASE WHEN %s = 'sub_account' THEN MIN(tag.id) ELSE NULL END,
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
            JOIN account_move_line aml ON (ro.report_id ilike aml.tags_str)
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
            # self.type, self.type,  self.analytic_recursive, self.type, self.type,
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


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    analytic_id = fields.Many2one('account.analytic.tag', 'Analytic tag')
    tags_str = fields.Char('Tags ids str', compute='get_tag_ids_str', store=True)
    taxs_str = fields.Char('Tax ids str', compute='get_tax_ids_str', store=True)

    # @api.one
    # def write(self, vals):
    #     res = super(AccountMoveLine, self).write(vals)
    #     if 'analytic_tag_ids' in vals:
    #         self.
    #     return res

    @api.one
    @api.depends('analytic_tag_ids')
    def get_tag_ids_str(self):
        tags_str = ''
        if self.analytic_tag_ids:
            tags_str = ';'.join([str(i) for i in self.analytic_tag_ids.ids])
            tags_str = ";%s;" % tags_str
        self.tags_str = tags_str

    @api.one
    @api.depends('tax_ids')
    def get_tax_ids_str(self):
        taxs_str = ''
        if self.tax_ids:
            taxs_str = ';'.join([str(i) for i in self.tax_ids.ids])
            taxs_str = ";%s;" % taxs_str
        self.taxs_str = taxs_str

