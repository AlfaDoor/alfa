
# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
import time
from datetime import datetime, date, timedelta
import copy
import pytz
from .base_tech import *
from dateutil.relativedelta import relativedelta
from .overtime_calc import over_time_calc
from odoo.exceptions import UserError, ValidationError, QWebException
from odoo.tools import  __



class overtime_late_report(models.Model):
    _name = 'overtime.late.report'
    _inherit = 'mail.thread'
    _rec_name = 'employee_id'

    date_from = fields.Date('Date Form')
    date_to = fields.Date('Date To')
    employee_id = fields.Many2one('hr.employee', 'Employee')
    lines = fields.One2many('overtime.late', 'report_id', 'Lines')

    @api.one
    def update_lines(self):
        start_date = datetime.strptime(__(self.date_from), '%Y-%m-%d')
        end_date = datetime.strptime(__(self.date_to), '%Y-%m-%d')
        day = timedelta(days=1)
        lines = []
        while start_date <= end_date:
            lines.append({
                'report_id': self.id,
                'employee_id': self.employee_id.id,
                'year': start_date.year,
                'month': start_date.strftime("%m"),
                'day': start_date.day,
            })
            start_date = start_date + day

        self.lines = [(5,)]
        for l in lines:
            line = self.env['overtime.late'].create(l)
            line.update_record()


class overtime_late(models.Model):
    _name = 'overtime.late'
    _inherit = 'mail.thread'

    report_id = fields.Many2one('overtime.late.report', 'Report')
    employee_id = fields.Many2one('hr.employee', 'Employee')
    _PERIOD = [
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ]

    day = fields.Integer('Day')
    month = fields.Selection(_PERIOD, 'Month', default=lambda s: time.strftime("%m"))
    year = fields.Integer('Year', default=lambda s: float(time.strftime('%Y')))
    overtime_hours = fields.Float('Overtime Hours')
    late_hours = fields.Float('Late Hours')
    attendance_ids = fields.Many2many('hr.attendance', 'overtime_attend_rel', 'overtime_id', 'attend_id', 'Attendances')
    working_time_ids = fields.Many2many('resource.calendar.attendance', 'overtime_work_rel', 'overtime_id', 'work_id', 'Working Time')

    @api.one
    def update_record(self):
        # //////////// Get User Timezone ///////////////////
        user_time_zone = pytz.UTC
        if self.env.user.partner_id.tz:
            # change the timezone to the timezone of the user
            user_time_zone = pytz.timezone(self.env.user.partner_id.tz)

        record_date = date(year=self.year, month=int(self.month), day=self.day)
        d1 = datetime.strftime(record_date, "%Y-%m-%d %H:%M:%S")
        d1_date = datetime.strptime(d1, '%Y-%m-%d %H:%M:%S')
        d1_date = user_time_zone.localize(d1_date)
        d1 = d1_date.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')

        d2 = datetime.strftime(record_date, "%Y-%m-%d 23:59:59")
        d2_date = datetime.strptime(d2, '%Y-%m-%d %H:%M:%S')
        d2_date = user_time_zone.localize(d2_date)
        d2 = d2_date.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
        attendance_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id), ('name', '>=', d1), ('name', '<=', d2)], order='name asc')
        self.attendance_ids = [(5,)]
        self.attendance_ids = [(4, a.id) for a in attendance_ids]
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('active', '=', True)])
        if not len(contracts):
            raise exceptions.ValidationError("Employee has no Contract")
        contract = contracts[0]
        if not contract.resource_calendar_id:
            raise exceptions.ValidationError("Employee Contract has no Working Schedule")
        week_day = record_date.weekday()
        working_time_ids = self.env['resource.calendar.attendance'].search(
            [('calendar_id', '=', contract.resource_calendar_id.id), ('dayofweek', '=', str(week_day))])
        self.working_time_ids = [(5,)]
        self.working_time_ids = [(4, w.id) for w in working_time_ids]

        # ----------- Compute Overtime hours and late hours --------------------
        att_periods = []
        att_period = {}
        for att in attendance_ids:
            if att.action == 'sign_in' and not att_period.has_key('start'):
                att_period['start'] = att.name
            if att.action == 'sign_out' and not att_period.has_key('end'):
                att_period['end'] = att.name
                if not att_period.has_key('start'):
                    att_period['start'] = d1
                att_periods.append(copy.deepcopy(att_period))
                att_period.clear()
        if att_period.has_key('start') and not att_period.has_key('end'):
            att_period['end'] = d2
            att_periods.append(copy.deepcopy(att_period))
            att_period.clear()

        work_time_periods = []
        for w in working_time_ids:
            time_from = '{0:02.0f}:{1:02.0f}:00'.format(*divmod(w.hour_from * 60, 60))
            from_date_format = str(self.year) + '-' + str(self.month) + '-' + str(self.day) + ' ' + time_from
            form_date_time = datetime.strptime(from_date_format, '%Y-%m-%d %H:%M:%S')
            form_date_time_zone = user_time_zone.localize(form_date_time)
            from_date_format = form_date_time_zone.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')

            time_to = '{0:02.0f}:{1:02.0f}:00'.format(*divmod(w.hour_to * 60, 60))
            to_date_format = str(self.year) + '-' + str(self.month) + '-' + str(self.day) + ' ' + time_to
            to_date_time = datetime.strptime(to_date_format, '%Y-%m-%d %H:%M:%S')
            to_date_time_zone = user_time_zone.localize(to_date_time)
            to_date_format = to_date_time_zone.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')

            work_time_periods.append({
                'start': from_date_format,
                'end': to_date_format,
            })
        # ////////// Get overtime hours ////////////////////////////
        total_overtime_seconds = 0
        for a_period in att_periods:
            conflect_seconds = 0
            for w_period in work_time_periods:
                if w_period['start'] <= a_period['end'] and w_period['end'] >= a_period['start']:
                    if w_period['start'] > a_period['start']:
                        intersection_start = w_period['start']
                    else:
                        intersection_start = a_period['start']
                    if w_period['end'] < a_period['end']:
                        intersection_end = w_period['end']
                    else:
                        intersection_end = a_period['end']

                    intersection_start_time = datetime.strptime(intersection_start, '%Y-%m-%d %H:%M:%S')
                    intersection_end_time = datetime.strptime(intersection_end, '%Y-%m-%d %H:%M:%S')
                    intersection_duration = intersection_end_time - intersection_start_time
                    conflect_seconds += intersection_duration.total_seconds()
            # ///////////////////////////////////////////////////////////////////////
            a_period_start_time = datetime.strptime(a_period['start'], '%Y-%m-%d %H:%M:%S')
            a_period_end_time = datetime.strptime(a_period['end'], '%Y-%m-%d %H:%M:%S')
            a_period_duration = a_period_end_time - a_period_start_time
            a_period_overtime_seconds = a_period_duration.total_seconds() - conflect_seconds
            total_overtime_seconds += a_period_overtime_seconds
        # /////////////////////////////////////////////////////////////////////
        overtime_min, overtime_sec = divmod(total_overtime_seconds, 60)
        overtime_hours, overtime_min = divmod(overtime_min, 60)
        self.overtime_hours = (overtime_hours + (overtime_min / 100)) * 1.0

        # ////////// Get Late hours ////////////////////////////
        total_late_seconds = 0
        for w_period in work_time_periods:
            conflect_seconds = 0
            for a_period in att_periods:
                if a_period['start'] <= w_period['end'] and a_period['end'] >= w_period['start']:
                    if a_period['start'] > w_period['start']:
                        intersection_start = a_period['start']
                    else:
                        intersection_start = w_period['start']
                    if a_period['end'] < w_period['end']:
                        intersection_end = a_period['end']
                    else:
                        intersection_end = w_period['end']

                    intersection_start_time = datetime.strptime(intersection_start, '%Y-%m-%d %H:%M:%S')
                    intersection_end_time = datetime.strptime(intersection_end, '%Y-%m-%d %H:%M:%S')
                    intersection_duration = intersection_end_time - intersection_start_time
                    conflect_seconds += intersection_duration.total_seconds()
            # ///////////////////////////////////////////////////////////////////////
            w_period_start_time = datetime.strptime(w_period['start'], '%Y-%m-%d %H:%M:%S')
            w_period_end_time = datetime.strptime(w_period['end'], '%Y-%m-%d %H:%M:%S')
            w_period_duration = w_period_end_time - w_period_start_time
            w_period_late_seconds = w_period_duration.total_seconds() - conflect_seconds
            total_late_seconds += w_period_late_seconds
        # /////////////////////////////////////////////////////////////////////
        late_min, late_sec = divmod(total_late_seconds, 60)
        late_hours, late_min = divmod(late_min, 60)
        self.late_hours = (late_hours + (late_min / 100)) * 1.0
