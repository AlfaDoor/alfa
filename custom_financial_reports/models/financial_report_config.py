# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError
import xlwt
import base64
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from PIL import Image
import io
from odoo.tools import __

class FinancialReportConfig(models.Model):
    _name = "financial.report.config"
    _description = "Account Report Configuration"

    name = fields.Char(translate=True)
    debit_credit = fields.Boolean('Show Credit and Debit Columns')
    line_ids = fields.One2many('financial.report.config.line', 'financial_report_config_id', string='Lines')
    type = fields.Selection([('date_range', 'Based on date ranges'),
                             # ('date_range_extended', "Based on date ranges with 'older' and 'total' columns and last 3 months"),
                             ('no_date_range', 'Based on a single date'),
                             # ('date_range_cash', 'Bases on date ranges and cash basis method')
                             ],
                            string='Period Type', default=False,
                            help='For report like the balance sheet that do not work with date ranges')
    company_id = fields.Many2one('res.company', string='Company')
    direction = fields.Selection([('rtl', 'Right to left'), ('ltr', 'Left tp right'), ], 'direction', default='rtl')
    margin = fields.Integer('Margin')
    use_analytic_account_in_name = fields.Boolean('Use analytic account in nam')
    orientation = fields.Selection([('portrait', 'portrait'), ('landscape', 'landscape'), ], string='Orientation')

    @api.multi
    def open_lines(self):
        return {
            'domain': [],
            'name': _('All Report lines'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            # 'view_id': self.env.ref('custom_financial_reports.view_financial_report_config_line_open_tree'),
            'res_model': 'financial.report.config.line',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'search_default_report_id': self.id},
        }

    @api.multi
    def calc_lines(self):
        for report in self:
            tree = []
            for line in report.line_ids:
                tree += (self.calc_line(line))
            return tree

    @api.multi
    def get_workbook(self):
        # image = Image.open(io.BytesIO(self.env.user.company_id.logo.decode('base64')))
        tree_list = self.calc_lines()
        workbook = xlwt.Workbook()
        filename = '%s.xls' % (self.name)
        sheet1 = workbook.add_sheet(filename)
        # sheet1.insert_bitmap(image,0,0)

        sheet1.cols_right_to_left = self.direction and 1 or 0
        row_num = 3
        col_num = 1
        font_height = 300
        sheet1.col(col_num).width = 12000
        style = xlwt.XFStyle()
        align = xlwt.Alignment()
        font = xlwt.Font()
        align.horz = xlwt.Alignment.HORZ_RIGHT
        font.height = font_height
        font.underline = True
        style.alignment = align
        style.font = font
        val_col_num = col_num
        row = sheet1.row(row_num)
        comparison_names = self._context.get('comparison_names', False)
        report_name = self._context.get('custom_report', False)
        sheet1.row(1).height_mismatch = True
        sheet1.row(1).height = 256 * 8
        sheet1.write_merge(1, 1, 1, 2, "شركة معارض الظهران الدوليه\n\n(شركة مساهمة سعوديه مقفله)\n\n%s\n" % report_name.name, style)
        for name in comparison_names:
            if self.debit_credit:
                sheet1.write_merge(row_num, row_num, col_num + 1, val_col_num + 3, comparison_names[name], style)
                val_col_num += 3
            else:
                row.write(val_col_num + 1, name, style)
                sheet1.col(val_col_num + 1).width = 5000
                row.height = 256 * 2
                val_col_num += 1
        row_num += 1

        for line in tree_list:
            val_col_num = col_num
            style = xlwt.XFStyle()
            font = xlwt.Font()
            font.bold = line['bold']
            font.height = font_height
            font.underline = line['underline']
            style.font = font
            row = sheet1.row(row_num)
            row.height_mismatch = True
            row.height = 256 * 2
            row.write(val_col_num, line['name'], style)
            style.alignment.horz = xlwt.Alignment.HORZ_RIGHT
            style.num_format_str = '#,##0.00'
            comparison_names = self._context.get('comparison_names', False)
            for name in comparison_names:
                line_vals = line['vals'][name]
                if self.debit_credit:
                    row.write(val_col_num, line_vals['debit'], style)
                    row.write(val_col_num + 1, line_vals['credit'], style)
                    row.write(val_col_num + 2, line_vals['balance'], style)
                    val_col_num += 3
                else:
                    val_col_num += 1
                    balance = line_vals['balance']
                    balance = balance if balance >= 0 else "(%s)" % abs(balance)
                    row.write(val_col_num, balance, style)
            row_num += 1
        return workbook

    @api.multi
    def print_xls(self):
        for report in self:
            filename = '%s.xls' % (self.name)
            workbook = report.get_workbook()

            fp = io.BytesIO()
            workbook.save(fp)
            export_id = self.env['custom.report.file'].create(
                {'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename})
            fp.close()

            fp = io.BytesIO()
            workbook.save(fp)
            file_data = base64.b64encode(fp.getvalue())

            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': file_data,
                'datas_fname': filename,
                'res_model': self._name,
                'res_id': self.id,
                'type': 'binary'})

            base_url = self.env['ir.config_parameter'].get_param('web.base.url')

            # return {'type': 'ir.actions.act_url',
            #         'url': base_url + '/web/content/%s/%s' % (attachment.id, filename),
            #         'target': 'self',
            #         }
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'res_model': 'custom.report.file',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    def calc_line(self, line):
        line_tree = []
        line_calc = line.calc_()
        print(line_calc)
        vals = {}
        for name in line_calc:
            vals[name] = {
                'balance': line_calc[name].balance,
            }
        if line.label_top:
            line_tree.append({
                'name': line.name,
                'level': line.level,
                'vals': vals,
                "bold": line.label_top_bold,
                'underline': line.label_top_underline,
                'show_val': line.has_total_line,
            })
        if line.children_ids:
            for child in line.children_ids:
                line_tree += self.calc_line(child)
        if line.has_total_end:
            line_tree.append({
                'name': line.total_end_name,
                'level': line.level,
                'vals': vals,
                "bold": line.label_top_bold,
                'underline': True,
                'show_val': True,
            })

        if line.domain and line.groupby:
            line_tree += line.get_groupby()
        return line_tree


class CustomReportFile(models.TransientModel):
    _name = "custom.report.file"

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)


def get_variance(basic_num, comparisom_num):
    balance = 0
    if basic_num and comparisom_num:
        balance = round((comparisom_num - basic_num) / basic_num * 100, 2)
    if comparisom_num and not basic_num:
        balance = 100
    if basic_num and not comparisom_num:
        balance = -100
    return balance


GLOBAL_DOMAIN = [('balanced', '=', True)]


class FinancialReportConfigLine(models.Model):
    _name = "financial.report.config.line"
    _description = "Account Report Configuration Line"
    _order = "sequence"

    name = fields.Char('Section Name', translate=True)
    code = fields.Char('Code')
    report_id = fields.Many2one('financial.report.config', 'Report', compute='get_report', store=True)
    financial_report_config_id = fields.Many2one('financial.report.config', 'Financial Report Configuration')
    parent_id = fields.Many2one('financial.report.config.line', string='Parent')
    children_ids = fields.One2many('financial.report.config.line', 'parent_id', string='Children')
    sequence = fields.Integer()

    domain = fields.Char(default=None)
    formula = fields.Text('Formula', default="""# Python code\n# _('code') : other formulas\n# sum : to get current formula sums\n\n""")
    groupby = fields.Char("Group by", default=False)
    level = fields.Integer('Level', default=1)
    label_top = fields.Boolean('Label at the top ?', default=True)
    label_top_bold = fields.Boolean('label at the top Bold ?')
    label_top_underline = fields.Boolean('label at the top underline ?')
    has_total_line = fields.Boolean('has total at line', default=True)
    has_total_end = fields.Boolean('has total at the end')
    total_end_name = fields.Char('Total name')
    separate_after_section = fields.Boolean('Separate after this section')
    budget_item_ids = fields.Many2many('account.budget.post', string='Budget positions')
    distribute = fields.Boolean('use distribution', default=False)
    date_type = fields.Selection([('default', 'Use default date rang'), ('begin', 'At the begining'), ], string='Date range type', default='default')

    @api.model_cr
    def _init(self):
        for line in self.search([('report_id', '=', False)]):
            line.get_report()

    @api.one
    @api.depends('parent_id', 'financial_report_config_id')
    def get_report(self):
        self.report_id = self.financial_report_config_id.id or self.parent_id.financial_report_config_id.id or False

    @api.onchange('name', 'has_total_end')
    def _get_level(self):
        self.level = self.parent_id and (self.parent_id.level + 1) or 1

    def get_sum(self):
        sum = {'credit': 0, 'debit': 0, 'balance': 0.0, 'budgeted': 0.0}
        if not self.domain:
            return Dict2Obj(sum)
        domain = safe_eval(self.domain)
        report_config = self._context.get('report_config', False)
        a_ids = []
        for a in report_config.analytic_account_select_ids:
            a_ids += a.get_all_child_ids()
        analytic_accounts = self.env['account.analytic.account'].browse(a_ids)
        total_percentage = 0
        for analytic in analytic_accounts:
            total_percentage += analytic.distribute_percentage
        if self._context.get('analytic_to_dist', False):
            total_percentage += self._context.get('analytic_to_dist').distribute_percentage
        filter_domain = report_config.get_custom_report_domain(analytic_domain=not self.distribute)
        if self.date_type == 'begin':
            filter_domain = report_config.get_custom_report_domain_begining(analytic_domain=not self.distribute)
        if report_config.per_profit_center and self._context.get('profit_domain', False) and not self.distribute:
            filter_domain += self._context.get('profit_domain')
        domain += filter_domain
        if self._context.get('current_comparison_domain', False):
            domain += self._context.get('current_comparison_domain', False)
        lines = self.env['account.move.line'].search(domain + GLOBAL_DOMAIN)
        print
        self.name, self._context.get('profit_domain')
        for line in lines:
            sum['debit'] += line.debit
            sum['credit'] += line.credit
        if self.distribute and (report_config.analytic_account_select_ids or self._context.get('analytic_to_dist', False)):  #
            debit = 0
            credit = 0
            if total_percentage:
                debit = round(sum['debit'] * (total_percentage / 100.0), 2)
                credit = round(sum['credit'] * (total_percentage / 100.0), 2)
            sum['debit'] = debit
            sum['credit'] = credit
        sum['balance'] = sum['debit'] - sum['credit']
        sum['budgeted'] = self.get_budget_value()
        return Dict2Obj(sum)

    def _calc(self):
        localdict = {}
        localdict['sum'] = self.get_sum()
        localdict['_'] = self.get_line_sums
        vals = self.get_sum()
        localdict['debit'] = vals.debit
        localdict['credit'] = vals.credit
        localdict['balance'] = 0
        localdict['budgeted'] = 0
        localdict['budget_v'] = 0
        safe_eval(self.formula, localdict, mode='exec', nocopy=True)
        return Dict2Obj({'balance': localdict['balance'], 'debit': localdict['debit'], 'credit': localdict['credit'], 'budgeted': localdict['budgeted'],
                         'budget_v': localdict['budget_v']})

    def calc_(self):
        report_config = self._context.get('report_config')
        if not report_config.per_profit_center:
            _calc = self._calc()
            res = {1: _calc}
            if self._context.get('budget_comparison', False):
                res[2] = Dict2Obj({'debit': 0, 'credit': 0, 'balance': _calc.budgeted})
                res[3] = Dict2Obj({'debit': 0, 'credit': 0, 'balance': _calc.budget_v})
            if self._context.get('is_comparison', False):
                comparison_names = self._context.get('comparison_names', False)
                comparison_domains = self._context.get('comparison_domains', False)
                for name in comparison_names:
                    name_domain = name in comparison_domains and comparison_domains[name] or False
                    if name >= 6 and name_domain:
                        vals = self.with_context(self._context, current_comparison_domain=name_domain)._calc()
                        res[name] = vals
                        if report_config.comparison_var:
                            balance = get_variance(vals.balance, res[1].balance)
                            # if vals.balance and res[1].balance:
                            #     balance = round((res[1].balance - vals.balance) / vals.balance * 100, 2)
                            # if res[1].balance and not vals.balance:
                            #     balance = 100
                            # if vals.balance and not res[1].balance:
                            #     balance = -100
                            new_vals = {'balance': balance}
                            res[name + 1] = Dict2Obj(new_vals)
        else:
            res = {}
            profit_centers = self.env['account.analytic.account'].search([['is_profit_center', '=', True]])
            names = self._context.get('comparison_names', False) or {}
            reversed_names = {}
            for name in names:
                reversed_names[names[name]] = name
            total = 0
            for profit_center in profit_centers:
                profit_domain = [['analytic_account_id', 'in', profit_center.get_all_child_ids()]]
                _calc = self.with_context(dict(self._context, profit_domain=profit_domain, analytic_to_dist=profit_center))._calc()
                res.update({reversed_names[profit_center.name]: _calc})
                print( ">>>>>>>>>total: %s,  balance: %s" % (total, _calc.balance))
                total += _calc.balance
            res[reversed_names[u'الإجــمــالــى']] = Dict2Obj({'balance': total})

        return res

    @api.multi
    def get_line_sums(self, code):
        line = self.search([['code', '=', code]])
        if not line:
            return
        calc = line[0]._calc()
        return calc

    def get_budget_value(self):
        ctx = self._context.get
        analytic_ids = ctx('budget_analytic_ids', [])
        domain = [('general_budget_id', 'in', self.budget_item_ids.ids)]
        if ctx('date_from', False):
            domain.append(('date_from', '>=', ctx('date_from')))
        if ctx('date_to', False):
            domain.append(('date_from', '<=', ctx('date_to')))
        if analytic_ids:
            domain.append(('analytic_account_id', 'in', analytic_ids))
        if not ctx('report_config').analytic_account_select_ids:
            domain.append(('analytic_account_id.is_profit_center', '=', True))
        budget_items = self.env['crossovered.budget.lines'].search(domain)
        total = sum([abs(i.planned_amount) for i in budget_items])
        return total

    def get_groupby(self):
        if not (self.domain and self.groupby):
            return []
        if self.groupby not in self.env['account.move.line']._columns:
            raise ValueError('Group by should be a field from account.move.line')
        if not self._context.get('is_comparison', False):
            aml_obj = self.env['account.move.line']
            domain = safe_eval(self.domain)
            if self._context.get('filter_domain', False):
                domain += self._context.get('filter_domain', False)
            aml_ids = aml_obj.search(domain + GLOBAL_DOMAIN).ids
            select = 'COALESCE(SUM(aml.debit-aml.credit), 0) balance, SUM(aml.amount_residual) amount_residual, SUM(aml.debit) debit, SUM(aml.credit) credit'
            groupby_table = getattr(aml_obj, self.groupby)._table
            sql = "SELECT " + select + ", aml." + self.groupby + " groupby " + \
                  " FROM account_move_line aml LEFT JOIN  " + groupby_table + " groupby_table ON aml." + self.groupby + " = groupby_table.id" + \
                  " WHERE  aml.id in " + str(tuple(aml_ids)) + \
                  " GROUP BY aml." + self.groupby
            self.env.cr.execute(sql)
            results = self.env.cr.dictfetchall()
            groupby_list = []
            for row in results:
                groupby_list.append({
                    'name': getattr(aml_obj, self.groupby).browse(row['groupby']).display_name,
                    'level': self.level + 1,
                    'vals': row,
                })
            return groupby_list
        else:
            comparison_names = self._context.get('comparison_names', False)
            comparison_domains = self._context.get('comparison_domains', False)
            comparison_vals = {}
            for comparison_name in comparison_names:
                if comparison_name < 6: continue
                aml_obj = self.env['account.move.line']
                domain = safe_eval(self.domain)
                if self._context.get('filter_domain', False):
                    domain += self._context.get('filter_domain', False)
                if comparison_domains[comparison_name]:
                    domain += comparison_domains[comparison_name]
                aml_ids = aml_obj.search(+ GLOBAL_DOMAIN).ids
                select = 'COALESCE(SUM(aml.debit - aml.credit), 0) balance,SUM(aml.amount_residual) amount_residual,SUM(aml.debit) debit,SUM(aml.credit) credit'
                groupby_table = getattr(aml_obj, self.groupby)._table
                sql = "SELECT " + select + ", aml." + self.groupby + " groupby " + \
                      " FROM account_move_line aml LEFT JOIN  " + groupby_table + " groupby_table ON aml." + self.groupby + " = groupby_table.id" + \
                      " WHERE  aml.id in " + str(tuple(aml_ids)) + \
                      " GROUP BY aml." + self.groupby
                self.env.cr.execute(sql)
                results = self.env.cr.dictfetchall()
                for row in results:
                    if row['groupby'] in comparison_vals:
                        comparison_vals[row['groupby']][comparison_name] = row
                    else:
                        comparison_vals[row['groupby']] = {}
                        comparison_vals[row['groupby']][comparison_name] = row
                    comparison_vals[row['groupby']][comparison_name] = row
            groupby_list = []
            for vals in comparison_vals:
                row = comparison_vals[vals]
                groupby_list.append({
                    'name': getattr(aml_obj, self.groupby).browse(row[comparison_name]['groupby']).display_name,
                    'level': self.level + 1,
                    'vals': comparison_vals[vals],
                })
            return groupby_list


class Dict2Obj(object):
    def __init__(self, dictionary):
        """Constructor"""
        for key in dictionary:
            setattr(self, key, dictionary[key])

    def __getitem__(self, key):
        return getattr(self, key)


class AccountStandardLedger(models.TransientModel):
    _inherit = "account.report.standard.ledger"
    type_ledger = fields.Selection(
        selection_add=[
            ('analytic_analysis', 'project Analysis'),
            ('custom', 'Custom')
        ],
        string='Type', default='general', required=True,
        help=' * General Ledger : Journal entries group by account\n'
             ' * Partner Leger : Journal entries group by partner, with only payable/recevable accounts\n'
             ' * Journal Ledger : Journal entries group by journal, without initial balance\n'
             ' * Open Ledger : Openning journal at Start date\n'
             ' * Analytic Ledger : Journal entries group by analytic account\n')
    custom_report = fields.Many2one('financial.report.config', 'Custom Report')
    custom_report_type = fields.Selection(related='custom_report.type')
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='all')
    fiscal_year = fields.Many2one('fiscal.year', 'Fiscal Year')
    is_comparison = fields.Boolean('Comparison')
    number_of_periods = fields.Integer('Number Of Periods')
    same_period_last_year = fields.Integer('Same Period Last Year')
    comparison_line_ids = fields.One2many('comparison.line', 'report_wizard_id', 'Custom comparison')
    original_name = fields.Char('Column name')
    budget_comparison = fields.Boolean('Budget comparison')
    budget_comparison_name = fields.Char('Budget comparison name')
    variance_name = fields.Char('Variance name')
    comparison_var = fields.Boolean('Show comparison Variation')
    per_profit_center = fields.Boolean('Report per profit center')

    @api.onchange('same_period_last_year', 'date_from', 'date_to')
    def onchange_same_period_last_year(self):
        if self.same_period_last_year:
            if not __(self.date_to):
                raise UserError('You must select End Date')
            if __(self.date_from):
                date_from = datetime.strptime(__(self.date_from), DEFAULT_SERVER_DATE_FORMAT)
            date_to = datetime.strptime(__(self.date_to), DEFAULT_SERVER_DATE_FORMAT)
            period_vals = []
            for n in range(self.same_period_last_year):
                if __(self.date_from):
                    las_date_from = date_from - relativedelta(years=n + 1)
                las_date_to = date_to - relativedelta(years=n + 1)
                period_vals.append({
                    'name': 'From (%s) To (%s)' % (
                        __(self.date_from) and las_date_from.strftime(DEFAULT_SERVER_DATE_FORMAT) or 'Beginning',
                        las_date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                    'date_from': __(self.date_from) and las_date_from.strftime(DEFAULT_SERVER_DATE_FORMAT) or False,
                    'date_to': las_date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
                })
            self.comparison_line_ids = [(5)]
            self.comparison_line_ids = [(0, 0, vals) for vals in period_vals]

    @api.onchange('number_of_periods', 'periode_date', 'fiscal_year')
    def onchange_number_of_periods(self):
        if self.periode_date and self.number_of_periods:
            periods = self.env['periods'].search([('date_start', '<', __(self.periode_date.date_start))],
                                                 limit=self.number_of_periods, order="date_start desc")
            period_vals = []
            for period in periods:
                period_vals.append({
                    'name': 'From (%s) To (%s)' % (
                        self.date_from and period.date_start or 'beginning', period.date_end),
                    'date_from': self.date_from and period.date_start or False,
                    'date_to': period.date_end,
                })
            self.comparison_line_ids = [(5)]
            self.comparison_line_ids = [(0, 0, vals) for vals in period_vals]
        elif self.fiscal_year and self.number_of_periods:
            periods = self.env['fiscal.year'].search([('start_date', '<', self.fiscal_year.start_date)],
                                                     limit=self.number_of_periods, order="start_date desc")
            period_vals = []
            for period in periods:
                period_vals.append({
                    'name': 'From (%s) To (%s)' % (
                        self.date_from and period.start_date or 'beginning', period.start_end),
                    'date_from': self.date_from and period.start_date or False,
                    'date_to': period.start_end,
                })
            self.comparison_line_ids = [(5)]
            self.comparison_line_ids = [(0, 0, vals) for vals in period_vals]

    @api.onchange('custom_report')
    def onchange_custom_report(self):
        if self.custom_report_type == 'no_date_range':
            self.date_from = False

    @api.onchange('fiscal_year')
    def on_fiscal_year(self):
        if self.fiscal_year:
            self.periode_date = False
            if self.custom_report_type == 'no_date_range':
                self.date_from = False
            else:
                self.date_from = self.fiscal_year.start_date
            self.date_to = self.fiscal_year.start_end

    @api.multi
    def print_pdf_report(self):
        if not self.type_ledger in ['custom', 'analytic_analysis']:
            return super(AccountStandardLedger, self).print_pdf_report()
        if self.type_ledger == 'analytic_analysis':
            return self.get_analytic_analysis()
        ctx = self.report_ctx()
        data = {'col_names': self.with_context(ctx).get_comparison_names()}
        data['lines'] = self.with_context(ctx).custom_report.calc_lines()
        data['report_name'] = self.custom_report.name
        if self.per_profit_center and self.original_name:
            data['report_name'] += " %s" % (self.original_name)
        data['sorted_x'] = sorted(data['col_names'])
        if self.custom_report.use_analytic_account_in_name and self.analytic_account_select_ids:
            data['report_name_analytic'] = '( %s )' % (', '.join([a.name for a in self.analytic_account_select_ids]))
        data['t_width'] = 'width:%s %'
        report_tem = self.custom_report.orientation == 'landscape' and 'custom_financial_reports.custom_financial_report_landscape' or 'custom_financial_reports.custom_financial_report_portrait'
        return self.env.ref(report_tem).report_action(self.custom_report.id, data=data)
        # return self.env['report'].get_action(self.custom_report, report_tem, data=data)

    @api.multi
    def func(self, b):
        balance = b if b >= 0 else abs(b)
        balance = '{0:,}'.format(balance)
        return b >= 0 and '%s' % balance or '(%s)' % balance

    @api.model
    def report_ctx(self):
        comparison_domains = {}
        filters_domain = self.get_custom_report_domain()
        if self.is_comparison:
            comparison_domains = self.get_comparison_domains()
        comparison_names = self.get_comparison_names()
        if not self.custom_report:
            raise UserError('You must select custom report')
        return dict(self._context or {}, filter_domain=filters_domain,
                    is_comparison=self.is_comparison,
                    comparison_domains=comparison_domains,
                    comparison_names=comparison_names,
                    budget_comparison=self.budget_comparison,
                    budget_comparison_name=self.budget_comparison_name,
                    budget_analytic_ids=self.analytic_account_select_ids.ids,
                    date_from=self.date_from,
                    date_to=self.date_to,
                    variance_name=self.variance_name,
                    custom_report=self.custom_report,
                    original_name=self.original_name,
                    report_config=self,
                    )

    @api.multi
    def get_analytic_analysis(self):
        domain = self.get_custom_report_domain(analytic_domain=False)
        projects = []
        for analytic in self.analytic_account_select_ids or self.env['account.analytic.account'].search([]):
            for project in analytic.get_all_child_ids():
                if self.env['account.analytic.account'].browse(project).is_project:
                    projects.append(self.env['account.analytic.account'].browse(project))
        domain.append(['analytic_account_id', 'in', [p.id for p in projects]])
        domain.append(['account_id.user_type_id.location', 'in', ['income', 'expense']])
        amls = self.env['account.move.line'].search(domain + GLOBAL_DOMAIN)
        names = {
            1: 'ايراد فعلى',
            2: 'ايراد تقديرى',
            3: 'الانحراف',
            4: 'تكلفة فعليه',
            5: 'تكلفة تقدريه',
            6: 'الانحراف',
        }
        report_lines = {}
        total_line = {'total': {'name': u'الإجـــمـــالـــى', 'level': 1, 'vals': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, }}}
        for line in amls:
            if line.analytic_account_id.id not in report_lines:
                report_lines[line.analytic_account_id.id] = {'name': line.analytic_account_id.name, 'level': 1, 'show_val': True, 'bold': False,
                                                             'underline': False, 'vals':
                                                                 {1: {'balance': 0},
                                                                  4: {'balance': 0},
                                                                  2: {'balance': 0},
                                                                  3: {'balance': 0},
                                                                  5: {'balance': 0},
                                                                  6: {'balance': 0},
                                                                  }}
            if line.account_id.user_type_id.location == 'income':
                report_lines[line.analytic_account_id.id]['vals'][1]['balance'] += line.credit - line.debit
                total_line['total']['vals'][1] += line.credit - line.debit
            if line.account_id.user_type_id.location == 'expense':
                report_lines[line.analytic_account_id.id]['vals'][4]['balance'] += line.debit - line.credit
                total_line['total']['vals'][4] += line.debit - line.credit
        lines = []
        for line in report_lines:
            budgeted_income = self.get_budgeted_for_project(line, 'income')
            budgeted_expense = self.get_budgeted_for_project(line, 'expense')
            report_lines[line]['vals'][2]['balance'] = budgeted_income
            report_lines[line]['vals'][5]['balance'] = budgeted_expense
            income_var = get_variance(budgeted_income, report_lines[line]['vals'][1]['balance'])
            expense_var = get_variance(budgeted_expense, report_lines[line]['vals'][4]['balance'])
            report_lines[line]['vals'][3]['balance'] = income_var
            report_lines[line]['vals'][6]['balance'] = expense_var
            print(">>>>>>>>>>>>>>>>>", expense_var)
            print(">>>>>>>>>>>>>>>>>", income_var)
            # report_lines[line]['vals'][3]['balance'] = income
            # report_lines[line]['vals'][6]['balance'] = expense
            # totals['income'] += income
            # totals['budgeted_income'] += budgeted_income
            # totals['expense'] += expense
            # totals['budgeted_expense'] += budgeted_expense
            lines.append(report_lines[line])

        data = {}
        data['col_names'] = names
        data['lines'] = lines
        data['report_name'] = u'تحليل مراكز التكلفه'
        data['sorted_x'] = sorted(data['col_names'])
        return self.env.ref('custom_financial_reports.custom_financial_report_landscape').report_action(self.custom_report.id, data=data)
        # return self.env['report'].get_action(self.custom_report, 'custom_financial_reports.rcf_landscape', data=data)

    @api.model
    def get_budgeted_for_project(self, analytic_account_id, type='expense', date_from=False, date_to=False):
        date_from = date_from or self.date_from
        date_to = date_to or self.date_to
        domain = [('analytic_account_id', '=', analytic_account_id)]
        if date_from:
            domain.append(('date_from', '>=', date_from))
        if date_to:
            domain.append(('date_from', '<=', date_to))
        budget_positions = self.env['crossovered.budget.lines'].search(domain)
        cost = income = 0
        for line in budget_positions:
            if line.general_budget_id.type == 'income':
                income += line.planned_amount
            if line.general_budget_id.type == 'expense':
                cost += line.planned_amount
        return cost if type == 'expense' else income

    @api.multi
    def print_excel_report(self):
        if self.type_ledger == 'custom':
            ctx = self.report_ctx()
            return self.with_context(ctx).custom_report.print_xls()
        elif self.type_ledger == 'analytic_analysis':
            self.get_analytic_analysis()
        else:
            self.ensure_one()
            self._compute_data()
            return self.env.ref('account_standard_report.action_standard_excel').report_action(self.custom_report.id, data={})
            return self.env['report'].get_action(self, 'account_standard_report.report_account_standard_excel')

    def get_comparison_names(self):
        names = {1: self.original_name}
        if self.budget_comparison:
            names.update({2: self.budget_comparison_name})
            names.update({3: self.variance_name})
        name_no = 6
        if self.is_comparison:
            for comparison in self.comparison_line_ids:
                names.update({name_no: comparison.name})
                name_no += 1
                if comparison.report_wizard_id.comparison_var:
                    names.update({name_no: u'الـتغير'})
                name_no += 3
        if self.per_profit_center:
            names = {}
            profit_centers = self.env['account.analytic.account'].search([['is_profit_center', '=', True]])
            name_no = 1
            for profit_center in profit_centers:
                names.update({name_no: profit_center.name})
                name_no += 1
            names[name_no] = u'الإجــمــالــى'
        return names

    def get_comparison_domains(self):
        comparison_dict = {}
        if self.custom_report_type == 'date_range':
            comparison_dict[1] = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        else:
            comparison_dict[1] = [('date', '<=', self.date_to)]
        name_no = 6
        for comparison in self.comparison_line_ids:
            if self.custom_report_type == 'date_range':
                comparison_dict[name_no] = [('date', '>=', comparison.date_from), ('date', '<=', comparison.date_to)]
            else:
                comparison_dict[name_no] = [('date', '<=', comparison.date_to)]
            name_no += 4
        return comparison_dict

    def get_custom_report_domain(self, analytic_domain=True):
        domain = []
        if self.date_from and self.custom_report_type == 'date_range':
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.target_move == 'posted':
            domain.append(('move_id.state', '=', 'posted'))
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.partner_select_ids:
            domain.append(('partner_id', 'in', self.partner_select_ids.ids))
        if self.account_in_ex_clude:
            if self.account_methode == 'include':
                domain.append(('account_id', 'in', self.account_in_ex_clude.ids))
            if self.account_methode == 'exclude':
                domain.append(('account_id', 'not in', self.account_in_ex_clude.ids))
        if self.analytic_account_select_ids and analytic_domain:
            ids = []
            for a in self.analytic_account_select_ids:
                ids += a.get_all_child_ids()
            domain.append(('analytic_account_id', 'in', ids))
        # if self.project_ids:
        #     domain.append(('journal_id', 'in', self.project_ids.ids))
        return domain

    def get_custom_report_domain_begining(self, analytic_domain=True):
        domain = []
        if self.date_from:
            domain.append(('date', '<', self.date_from))
        if self.target_move == 'posted':
            domain.append(('move_id.state', '=', 'posted'))
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.partner_select_ids:
            domain.append(('partner_id', 'in', self.partner_select_ids.ids))
        if self.account_in_ex_clude:
            if self.account_methode == 'include':
                domain.append(('account_id', 'in', self.account_in_ex_clude.ids))
            if self.account_methode == 'exclude':
                domain.append(('account_id', 'not in', self.account_in_ex_clude.ids))
        if self.analytic_account_select_ids and analytic_domain:
            ids = []
            for a in self.analytic_account_select_ids:
                ids += a.get_all_child_ids()
            domain.append(('analytic_account_id', 'in', ids))
        # if self.project_ids:
        #     domain.append(('journal_id', 'in', self.project_ids.ids))
        return domain


class ComparisonLine(models.TransientModel):
    _name = 'comparison.line'
    _order = 'sequence, id'

    report_wizard_id = fields.Many2one('account.report.standard.ledger', 'Wizard')
    sequence = fields.Integer('Sequence', default=10)
    name = fields.Char('Name')
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    comparison_with_original = fields.Boolean('show comparison column')


class CustomFinancialReport(models.TransientModel):
    _name = "report.custom_financial_reports.report_custom_financial"

    @api.multi
    def _get_report_values(self, docids, data=None):
        data['func'] = self.env['account.report.standard.ledger'].func
        data .update({
            'doc_ids': docids,
            'doc_model': 'financial.report.config',
            'docs': self.env['financial.report.config'].browse(docids),
        })
        return data
        return self.env['report'].render('custom_financial_reports.report_custom_financial', data)


class CustomFinancialReport_portrait(models.TransientModel):
    _name = "report.custom_financial_reports.rcf_portrait"

    @api.multi
    def _get_report_values(self, docids, data=None):
        data['func'] = self.env['account.report.standard.ledger'].func
        data .update({
            'doc_ids': docids,
            'doc_model': 'financial.report.config',
            'docs': self.env['financial.report.config'].browse(docids),
        })
        return data


class CustomFinancialReport_landscape(models.TransientModel):
    _name = "report.custom_financial_reports.rcf_landscape"

    @api.multi
    def _get_report_values(self, docids, data=None):
        data['func'] = self.env['account.report.standard.ledger'].func
        data .update({
            'doc_ids': docids,
            'doc_model': 'financial.report.config',
            'docs': self.env['financial.report.config'].browse(docids),
        })
        return data
        return self.env['report'].render('custom_financial_reports.rcf_landscape', data)


class account_analytic_account(models.Model):
    _inherit = "account.analytic.account"

    is_profit_center = fields.Boolean('Is Profit center')
    is_project = fields.Boolean('is project')


class crossovered_budget_lines(models.Model):
    _inherit = "account.budget.post"
    type = fields.Selection([('income', 'Income'), ('expense', 'Expense'), ], string="Type", default='expense')
