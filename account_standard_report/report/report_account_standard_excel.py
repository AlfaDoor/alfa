# -*- coding: utf-8 -*-
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import _
from odoo import models
from odoo.tools import __


class AccountStandardExcel(models.AbstractModel):
    _name = 'report.account_standard_report.report_account_standard_excel'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizard):
        if wizard.type_ledger == 'general' and wizard.summary:
            workbook = wizard.get_account_trial_balance(workbook)
            return

        num_format = wizard.company_currency_id.excel_format
        bold = workbook.add_format({'bold': True})
        middle = workbook.add_format({'bold': True, 'top': 1})
        left = workbook.add_format({'left': 1, 'top': 1, 'bold': True})
        right = workbook.add_format({'right': 1, 'top': 1})
        top = workbook.add_format({'top': 1})
        currency_format = workbook.add_format({'num_format': num_format})
        c_middle = workbook.add_format({'bold': True, 'top': 1, 'num_format': num_format})
        report_format = workbook.add_format({'font_size': 24})
        rounding = self.env.user.company_id.currency_id.decimal_places or 2
        lang_code = self.env.user.lang or 'en_US'
        lang_id = self.env['res.lang']._lang_get(lang_code)
        date_format = lang_id.date_format
        report_name_format = workbook.add_format(
            {
                'font_size': 14,
                'align': 'center',
                'valign': 'center',
                'bg_color': '#cccccc',
            }
        )
        gray_format = workbook.add_format(
            {
                'font_size': 9,
                'bg_color': '#cccccc',
                'bold': True,
                'border': 1,
                'border_color': '#000000',
            }
        )
        workbook.formats[0].set_font_size(9)

        report = wizard.report_id

        def _get_data_float(data):
            if data == None or data == False:
                return 0.0
            else:
                return wizard.company_currency_id.round(data) + 0.0

        def get_date_format(date):
            if date:
                date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
                date = date.strftime(date_format)
            return date

        def _header_sheet(sheet):
            # sheet.write(0, 4, report.name, report_format)
            sheet.merge_range('A1:J1', report.name, report_name_format)
            for r in range(7):
                sheet.set_row(r, 20)
            sheet.write(2, 0, _('Company:'), gray_format)
            sheet.write(2, 1, wizard.company_id.name, )
            sheet.write(3, 0, _('Print on '), gray_format)
            sheet.write(3, 1, report.print_time)

            sheet.write(4, 6, _('Start Date : '), gray_format)
            sheet.write(4, 7, __(wizard.date_from) if __(wizard.date_from) else '')
            sheet.write(4, 8, _('End Date :'), gray_format)
            sheet.write(4, 9, __(wizard.date_to) if __(wizard.date_to) else '')

            sheet.write(2, 3, _('Target Moves:'), gray_format)
            sheet.write(2, 4, _('All Entries') if wizard.target_move == 'all' else _('All Posted Entries'))
            sheet.merge_range('D4:E4', _('Only UnReconciled Entries') if wizard.reconciled is False else _('With Reconciled Entries'), bold)
            sheet.merge_range('D5:E5', _('Initial balance with history : %s') % 'True' if wizard.summary is True else 'False')

            sheet.merge_range('G3:G4', _('Filter by account \n Filter = %s ') % wizard.account_methode, gray_format)
            accounts_str = ''.join([a.name + ' / \n' for a in wizard.account_in_ex_clude])
            sheet.merge_range('H3:H4', accounts_str)

        if wizard.type_ledger == 'aged':

            if wizard.summary:
                sheet = workbook.add_worksheet(report.name)
                _header_sheet(sheet)

                head = [
                    {'name': 'Code',
                     'larg': 10,
                     'col': {}},
                    {'name': 'Name',
                     'larg': 30,
                     'col': {}},
                    {'name': _('Not Due'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('0-30'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('30-60'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('60-90'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('90-120'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('Older'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('Total'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                ]

                all_lines = wizard._sql_get_line_for_report(type_l=('4_total',))
                if all_lines:

                    row = 7
                    row += 1
                    start_row = row
                    for i, line in enumerate(all_lines):
                        i += row
                        sheet.write(i, 0, line.get('code', ''))
                        sheet.write(i, 1, line.get('name', ''))
                        sheet.write(i, 2, _get_data_float(line.get('current')), currency_format)
                        sheet.write(i, 3, _get_data_float(line.get('age_30_days')), currency_format)
                        sheet.write(i, 4, _get_data_float(line.get('age_60_days')), currency_format)
                        sheet.write(i, 5, _get_data_float(line.get('age_90_days')), currency_format)
                        sheet.write(i, 6, _get_data_float(line.get('age_120_days')), currency_format)
                        sheet.write(i, 7, _get_data_float(line.get('older')), currency_format)
                        sheet.write(i, 8, _get_data_float(line.get('balance')), currency_format)
                    row = i

                    for j, h in enumerate(head):
                        sheet.set_column(j, j, h['larg'])

                    table = []
                    for h in head:
                        col = {}
                        col['header'] = h['name']
                        col.update(h['col'])
                        table.append(col)

                    sheet.add_table(start_row - 1, 0, row + 1, len(head) - 1,
                                    {'total_row': 1,
                                     'columns': table,
                                     'style': 'Table Style Light 9',
                                     })

            else:  # aged not summary
                head = [
                    {'name': _('Date'),
                     'larg': 10,
                     'col': {}},
                    {'name': _('JRNL'),
                     'larg': 10,
                     'col': {}},
                    {'name': _('Account'),
                     'larg': 10,
                     'col': {}},
                    {'name': _('Account Name'),
                     'larg': 15,
                     'col': {}},
                    {'name': _('Journal entries'),
                     'larg': 20,
                     'col': {}},
                    {'name': _('Ref'),
                     'larg': 40,
                     'col': {}},
                    {'name': _('Partner'),
                     'larg': 20,
                     'col': {}},
                    {'name': _('Due Date'),
                     'larg': 10,
                     'col': {}},
                    {'name': _('Not Due'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('0-30'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('30-60'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('60-90'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('90-120'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('Older'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('Total'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('Match.'),
                     'larg': 10,
                     'col': {}},
                ]
                table = []
                for h in head:
                    col = {'header': h['name']}
                    col.update(h['col'])
                    table.append(col)

                def _set_line(line):
                    sheet.write(i, 0, get_date_format(__(line.get('date', ''))))
                    sheet.write(i, 1, line.get('j_code', ''))
                    sheet.write(i, 2, line.get('a_code', ''))
                    sheet.write(i, 3, line.get('a_name', ''))
                    sheet.write(i, 4, line.get('move_name', ''))
                    sheet.write(i, 5, line.get('displayed_name', ''))
                    sheet.write(i, 6, line.get('partner_name', ''))
                    sheet.write(i, 7, get_date_format(__(line.get('date_maturity', ''))))
                    sheet.write(i, 8, _get_data_float(line.get('current')), currency_format)
                    sheet.write(i, 9, _get_data_float(line.get('age_30_days')), currency_format)
                    sheet.write(i, 10, _get_data_float(line.get('age_60_days')), currency_format)
                    sheet.write(i, 11, _get_data_float(line.get('age_90_days')), currency_format)
                    sheet.write(i, 12, _get_data_float(line.get('age_120_days')), currency_format)
                    sheet.write(i, 13, _get_data_float(line.get('older')), currency_format)
                    sheet.write(i, 14, _get_data_float(line.get('balance')), currency_format)
                    sheet.write(i, 15, line.get('matching_number', ''))

                def _set_table(start_row, row):
                    sheet.add_table(start_row - 1, 0, row + 1, len(head) - 1,
                                    {'total_row': 1,
                                     'columns': table,
                                     'style': 'Table Style Light 9',
                                     })
                    # sheet.write(row + 1, 10, "=I%s-J%s" % (row + 2, row + 2), currency_format)

                # With total workbook
                sheet = workbook.add_worksheet(report.name + _(' Totals'))
                _header_sheet(sheet)

                row = 6
                all_lines = wizard._sql_get_line_for_report(type_l=('1_init_line', '2_line'))
                for obj in report.report_object_ids:

                    lines_obj = []
                    obj_id = obj.id
                    for line in all_lines:
                        if line.get('report_object_id') == obj_id:
                            lines_obj.append(line)
                    if lines_obj:
                        row += 1
                        sheet.write(row, 0, obj.partner_id.name, left)  # obj.partner_id.name
                        sheet.write(row, 1, '', top)
                        sheet.write(row, 2, '', top)
                        sheet.write(row, 3, '', top)
                        sheet.write(row, 4, '', top)
                        sheet.write(row, 5, '', top)
                        sheet.write(row, 6, '', c_middle)
                        sheet.write(row, 7, '', c_middle)
                        sheet.write(row, 8, '', c_middle)
                        sheet.write(row, 9, '', c_middle)
                        sheet.write(row, 10, '', c_middle)
                        sheet.write(row, 11, '', c_middle)
                        sheet.write(row, 12, '', c_middle)
                        sheet.write(row, 13, '', c_middle)
                        sheet.write(row, 14, '', c_middle)
                        sheet.write(row, 15, '', right)

                        row += 2
                        start_row = row
                        for i, line in enumerate(lines_obj):
                            i += row
                            _set_line(line)

                        row = i

                        for j, h in enumerate(head):
                            sheet.set_column(j, j, h['larg'])

                        _set_table(start_row, row)
                        row += 2

                # Pivot
                sheet = workbook.add_worksheet(report.name)
                _header_sheet(sheet)

                # for group_by in data['group_by_data']['ids']:
                #     for line in data['lines_group_by'][group_by]['new_lines']:
                #         if line['type_line'] != 'total':
                #             all_lines.append(line)
                # Head
                if all_lines:
                    row = 6
                    row += 1
                    start_row = row
                    for i, line in enumerate(all_lines):
                        i += row
                        _set_line(line)
                    row = i

                    for j, h in enumerate(head):
                        sheet.set_column(j, j, h['larg'])

                    _set_table(start_row, row)

        else:  # standard report

            if wizard.summary:
                sheet = workbook.add_worksheet(report.name)
                _header_sheet(sheet)

                all_lines = wizard._sql_get_line_for_report(type_l=('4_total',))
                # for group_by in data['group_by_data']['ids']:
                #     all_lines.append(data['lines_group_by'][group_by])
                if all_lines:
                    # Head
                    head = [
                        {'name': 'Code',
                         'larg': 10,
                         'col': {}},
                        {'name': 'Name',
                         'larg': 30,
                         'col': {}},
                        {'name': 'Level',
                         'larg': 10,
                         'col': {}},
                        {'name': 'Initial Debit',
                         'larg': 15,
                         'col': {'total_function': 'sum', 'format': currency_format}},
                        {'name': 'Initial Credit',
                         'larg': 15,
                         'col': {'total_function': 'sum', 'format': currency_format}},
                        {'name': 'Debit',
                         'larg': 15,
                         'col': {'total_function': 'sum', 'format': currency_format}},
                        {'name': 'Credit',
                         'larg': 15,
                         'col': {'total_function': 'sum', 'format': currency_format}},
                        {'name': 'Total Debit',
                         'larg': 15,
                         'col': {'total_function': 'sum', 'format': currency_format}},
                        {'name': 'Total Credit',
                         'larg': 15,
                         'col': {'total_function': 'sum', 'format': currency_format}},
                        {'name': 'Balance Debit',
                         'larg': 15,
                         'col': {'total_function': 'sum', 'format': currency_format}},
                        {'name': 'Balance Credit',
                         'larg': 15,
                         'col': {'total_function': 'sum', 'format': currency_format}},
                    ]

                    row = 7
                    row += 1
                    start_row = row
                    i = row - 1
                    for x, line in enumerate(all_lines):
                        init_debit = line.get('init_debit', '')
                        init_credit = line.get('init_credit', '')

                        debit = line.get('debit', 0) - line.get('init_debit', 0)
                        credit = line.get('credit', 0) - line.get('init_credit', 0)
                        total_debit = line.get('debit', 0)
                        total_credit = line.get('credit', 0)
                        balance_debit = total_debit > total_credit and (total_debit - total_credit) or 0
                        balance_credit = total_credit > total_debit and (total_credit - total_debit) or 0
                        if not (balance_debit or balance_credit):
                            continue

                        i += 1
                        # if line.get('level', '') > wizard.level:
                        #     sheet.set_row(i, None, None, {'hidden': True})
                        sheet.write(i, 0, line.get('code', ''))
                        sheet.write(i, 1, line.get('name', ''))
                        sheet.write(i, 2, line.get('level', ''))

                        sheet.write(i, 3, init_debit, currency_format)
                        sheet.write(i, 4, init_credit, currency_format)

                        sheet.write(i, 5, debit, currency_format)
                        sheet.write(i, 6, credit, currency_format)

                        sheet.write(i, 7, total_debit, currency_format)
                        sheet.write(i, 8, total_credit, currency_format)
                        sheet.write(i, 9, balance_debit, currency_format)
                        sheet.write(i, 10, balance_credit, currency_format)

                    row = i

                    for j, h in enumerate(head):
                        sheet.set_column(j, j, h['larg'])

                    table = []
                    for h in head:
                        col = {}
                        col['header'] = h['name']
                        col.update(h['col'])
                        table.append(col)

                    sheet.add_table(start_row - 1, 0, row + 1, len(head) - 1,
                                    {'total_row': 1,
                                     'columns': table,
                                     'style': 'Table Style Light 9',
                                     })
                    code_col_format = workbook.add_format(
                        {'font_size': 11, 'bg_color': '#f48024', 'align': 'center'}
                    )
                    sheet.write(6, 0, 'الكود', code_col_format)
                    name_col_format = workbook.add_format({'font_size': 11, 'bg_color': '#cccccc', 'align': 'center'})
                    sheet.write(6, 1, 'إسم الحساب', name_col_format)
                    level_col_format = workbook.add_format({'font_size': 11, 'bg_color': '#ecc6ec', 'align': 'center'})
                    sheet.write(6, 2, 'المستوى', level_col_format)
                    init_col_format = workbook.add_format({'font_size': 11, 'bg_color': '#fbe54e', 'align': 'center'})
                    sheet.merge_range('D7:E7', 'Opening Balance الأرصده الافتتاحيه', init_col_format)
                    trans_col_format = workbook.add_format({'font_size': 11, 'bg_color': '#5bc0de', 'align': 'center'})
                    sheet.merge_range('F7:G7', 'Transactions الحركات', trans_col_format)
                    total_col_format = workbook.add_format({'font_size': 11, 'bg_color': '#9fe89f', 'align': 'center'})
                    sheet.merge_range('H7:I7', 'Totals المجاميع ', total_col_format)
                    balance_col_format = workbook.add_format({'font_size': 11, 'bg_color': '#cccccc', 'align': 'center'})
                    sheet.merge_range('J7:K7', 'Balance الأرصده', balance_col_format)

            else:  # not summary

                head = [
                    {'name': _('Date'),
                     'larg': 10,
                     'col': {}},
                    {'name': _('JRNL'),
                     'larg': 10,
                     'col': {}},
                    {'name': _('Account'),
                     'larg': 10,
                     'col': {}},
                    {'name': _('Account Name'),
                     'larg': 15,
                     'col': {}},
                    {'name': _('Analytic account'),
                     'larg': 20,
                     'col': {}},
                    {'name': _('Journal entries'),
                     'larg': 20,
                     'col': {}},
                    {'name': _('Description'),
                     'larg': 20,
                     'col': {}},
                    {'name': _('Ref'),
                     'larg': 40,
                     'col': {}},
                    {'name': _('Document type'),
                     'larg': 20,
                     'col': {}},
                    {'name': _('Analytical tag'),
                     'larg': 15,
                     'col': {}},
                    {'name': _('Taxes'),
                     'larg': 15,
                     'col': {}},
                    {'name': _('Partner'),
                     'larg': 20,
                     'col': {}},
                    {'name': _('Due Date'),
                     'larg': 0,
                     'col': {}},
                    {'name': _('Debit'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('Credit'),
                     'larg': 15,
                     'col': {'total_function': 'sum', 'format': currency_format}},
                    {'name': _('Balance'),
                     'larg': 15,
                     'col': {'format': currency_format}},
                    {'name': _('Amount Currency'),
                     'larg': 15,
                     'col': {}},
                    {'name': _('Match.'),
                     'larg': 10,
                     'col': {}},
                ]
                table = []
                for h in head:
                    col = {'header': h['name']}
                    col.update(h['col'])
                    table.append(col)

                def _set_line(line):
                    doctype = {
                        'out_invoice': 'Customer Invoice',
                        'in_invoice': 'Vendor Bill',
                        'out_refund': 'Customer Refund',
                        'in_refund': 'Vendor Refund',
                        'outbound': 'Send Money',
                        'inbound': 'Receive Money',
                        'transfer': 'Internal Transfer',
                        'manual': 'Manual journal entry'
                    }
                    doctype = doctype[line.get('doctype', 'manual') or 'manual']
                    sheet.write(i, 0, get_date_format(__(line.get('date', ''))) if line.get('type_view') != 'init' else 'INIT')
                    sheet.write(i, 1, line.get('j_code', ''))
                    sheet.write(i, 2, line.get('a_code', ''))
                    sheet.write(i, 3, line.get('a_name', ''))
                    sheet.write(i, 4, "%s - %s" % (line.get('an_code', ''), line.get('an_name', '')) if line.get('an_code', '') else line.get('an_name', ''))
                    sheet.write(i, 5, line.get('move_name', ''))
                    sheet.write(i, 6, line.get('label', ''))
                    sheet.write(i, 7, line.get('displayed_name', ''))
                    sheet.write(i, 8, doctype)
                    sheet.write(i, 9, line.get('tags', ''))
                    sheet.write(i, 10, line.get('tax', ''))
                    sheet.write(i, 11, line.get('partner_name', ''))
                    sheet.write(i, 12, get_date_format(__(line.get('date_maturity', ''))))
                    sheet.write(i, 13, _get_data_float(line.get('debit', '')), currency_format)
                    sheet.write(i, 14, _get_data_float(line.get('credit', '')), currency_format)
                    sheet.write(i, 15, _get_data_float(line.get('cumul_balance', '')), currency_format)
                    # if line.get('amount_currency', ''):
                    #     sheet.write(i, 12, _get_data_float(line.get('amount_currency', '')), workbook.add_format({'num_format': line.get('currency')}))
                    # sheet.write(i, 13, line.get('matching_number', ''))

                def _set_table(start_row, row):
                    sheet.add_table(start_row - 1, 0, row + 1, len(head) - 1,
                                    {'total_row': 1,
                                     'columns': table,
                                     'style': 'Table Style Light 9',
                                     })

                # With total workbook
                sheet = workbook.add_worksheet(report.name + _(' Totals'))
                _header_sheet(sheet)

                row = 6

                all_lines = wizard._sql_get_line_for_report(type_l=('0_init', '1_init_line', '2_line'))
                for obj in report.report_object_ids:
                    lines_obj = []
                    obj_id = obj.id
                    for line in all_lines:
                        if line.get('report_object_id') == obj_id:
                            lines_obj.append(line)
                    if lines_obj:
                        row += 1
                        name_view = ''
                        if wizard.type == 'account':
                            name_view = obj.account_id.display_name
                        if wizard.type == 'partner':
                            name_view = obj.partner_id.display_name
                        if wizard.type == 'journal':
                            name_view = obj.journal_id.display_name
                        if wizard.type == 'analytic':
                            name_view = obj.analytic_account_id.display_name
                        if wizard.type == 'sub_account':
                            name_view = obj.analytic_id.name
                        if wizard.type == 'employees':
                            name_view = obj.employee_id.display_name

                        sheet.write(row, 0, name_view, left)
                        sheet.write(row, 1, '', top)
                        sheet.write(row, 2, '', top)
                        sheet.write(row, 3, '', top)
                        sheet.write(row, 4, '', top)
                        sheet.write(row, 5, '', top)
                        sheet.write(row, 6, '', top)
                        sheet.write(row, 7, '', top)
                        sheet.write(row, 8, '', top)
                        sheet.write(row, 9, '', top)
                        sheet.write(row, 10, '', top)
                        sheet.write(row, 11, '', top)
                        sheet.write(row, 12, '', top)
                        sheet.write(row, 13, '', right)

                        row += 2
                        start_row = row
                        for i, line in enumerate(lines_obj):
                            i += row
                            _set_line(line)

                        row = i

                        for j, h in enumerate(head):
                            sheet.set_column(j, j, h['larg'])

                        _set_table(start_row, row)
                        row += 2

                # Pivot workbook
                sheet = workbook.add_worksheet(report.name)
                _header_sheet(sheet)

                # Head
                if all_lines:
                    row = 6
                    row += 1
                    start_row = row
                    for i, line in enumerate(all_lines):
                        i += row
                        _set_line(line)
                    row = i

                    for j, h in enumerate(head):
                        sheet.set_column(j, j, h['larg'])

                    _set_table(start_row, row)

        if wizard.type_ledger == 'custom':
            workbook = wizard.custom_report.get_workbook()
