# -*- coding: utf-8 -*-
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import _,models
DAYS_OF_WEEK = [('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday')]

from dateutil import tz
from odoo.tools import __


class SheetReportExcel(models.AbstractModel):

    _name = 'report.overtime_late.report_sheet'
    _inherit = 'report.report_xlsx.abstract'
    def generate_xlsx_report(self, workbook, data, wizard):
        sheet = workbook.add_worksheet('Excuses')
        sheet.set_column(0, 0, 20)
        sheet.set_column(0, 2, 20)
        sheet.write(0, 0, _('Day'))
        sheet.write(0, 1, _('Time'))
        sheet.write(0, 2, _('Action'))
        sheet.write(0, 3, _('Employee department'))
        # sheet.write(0, 4, _('Is external labour'))
        days = dict(DAYS_OF_WEEK)

        row_no = 0
        for employee_report in wizard.employee_report_ids:
            employee = employee_report.employee_id
            working_days = self.env['working.days'].search(
                [('employee_id', '=', employee.id),
                 ('date', '>=', __(employee_report.delay_date_from)),
                 ('date', '<=', __(employee_report.delay_date_to))],
                order='date')
            if working_days:
                row_no += 2
                sheet.merge_range('A%s:D%s' % (row_no + 1, row_no + 1), employee.display_name)
                row_no += 1
                for day in working_days:
                    sheet.write(row_no, 0, days[day.dayofweek])
                    for action in day.att_ids:
                        sheet.write(row_no, 1, self.localize_dt(action.name, self.env.user.tz))
                        sheet.write(row_no, 2, action.action_compute)
                        sheet.write(row_no, 3, employee.department_id.display_name)
                        sheet.write(row_no, 4, employee.is_external_labour and 'True' or 'False')
                        row_no += 1

    def localize_dt(self, date, to_tz):
        from_zone = tz.gettz('UTC')
        to_zone = tz.gettz(to_tz)
        # utc = datetime.utcnow()
        utc = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        # Tell the datetime object that it's in UTC time zone since
        # datetime objects are 'naive' by default
        utc = utc.replace(tzinfo=from_zone)
        # Convert time zone
        res = utc.astimezone(to_zone)
        return res.strftime('%Y-%m-%d %H:%M:%S')
