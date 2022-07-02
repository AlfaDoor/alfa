# -*- coding: utf-8 -*-
from datetime import datetime
from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsxAbstract
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import _
from odoo import models
from odoo.tools import __


class ExcuseReportExcel(models.AbstractModel):
    _name = 'report.overtime_late.overtime_late'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizard):
        sheet = workbook.add_worksheet('Excuses')
        delay_date_from = __(wizard.delay_date_from)
        delay_date_to = __(wizard.delay_date_to)
        sheet.set_column(0, 0, 40)
        sheet.write(0, 0, _('Employee'))
        sheet.write(0, 1, _('Total'))
        sheet.write(0, 2, _('Excuses number'))

        row_no = 1
        for employee_report in wizard.employee_report_ids:
            excuses = wizard.env['hr.excuse'].search([('employee_id', '=', employee_report.employee_id.id), ('date', '>=', delay_date_from),
                                                      ('date', '<=', delay_date_to), ('state', '=', 'confirmed'), ('excuse_hours', '!=', 0)])
            total_excuse = 0
            for e in excuses:
                total_excuse += e.excuse_hours
            if total_excuse:
                sheet.write(row_no, 0, employee_report.employee_id.display_name)
                sheet.write(row_no, 1, round(total_excuse, 2))
                sheet.write(row_no, 2, len(excuses))
                # x=
                row_no += 1
