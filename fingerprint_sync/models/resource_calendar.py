# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from . base_tech import *
from datetime import datetime
from dateutil.relativedelta import relativedelta

import logging
from odoo.tools import __
_logger = logging.getLogger(__name__)


# _logger.info(error_msg)


class resource_calendar(models.Model):
    _inherit = "resource.calendar"

    attendance_config_ids = o2m_field('attendance.config', 'calender_id', 'Attendance configuration', copy=True)

    @api.model
    def get_action_by_time(self, date_time, ):
        if type(date_time) == str:
            date_time = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
        day_of_week = date_time.weekday()
        time_ = self.localize_dt(date_time, self.env.user.tz).strftime("%H:%M")

        float_minutes = self.minute_to_float(time_)
        conf = self.env['attendance.config'].search(['|', ('dayofweek', '=', day_of_week), ('dayofweek', '=', str(day_of_week)),
                                                     ('hour_from', '<=', float_minutes), ('hour_to', '>=', float_minutes), ('calender_id', '=', self.id)])
        action = 'action'
        if conf:
            action = conf[0].action
        return action

    @api.model
    def minute_to_float(self, m):
        h, m = m.split(':')
        float_ = float(h) + (float(m) / 60.0)
        return float_

    def localize_dt(self, utc, to_tz):
        from dateutil import tz
        from_zone = tz.gettz('UTC')
        to_zone = tz.gettz(to_tz)
        utc = utc.replace(tzinfo=from_zone)
        res = utc.astimezone(to_zone)
        return res

    @api.model
    def float_to_time(self, f):
        t = datetime.strptime('00:00', "%H:%M") + relativedelta(hours=f)
        return t.strftime("%H:%M")

    @api.model
    def get_official_workings(self, day_number):
        official_working = []
        days = self.env['resource.calendar.attendance'].search([('calendar_id', '=', self.id), ('dayofweek', '=', day_number)])
        for day in days:
            hour_from = self.float_to_time(day.hour_from)
            hour_to = self.float_to_time(day.hour_to)
            official_working.append({
                'work_start': hour_from,
                'work_end': hour_to,
                'allow_late': 0,
                'allow_previous': 0
            })
        return official_working

    @api.model
    def check_day_is_official_day(self, day):
        # day = day is datetime and day or datetime.strptime(day, "%Y-%m-%d")
        day = type(day) == str and datetime.strptime(day, "%Y-%m-%d") or day
        week_day = day.weekday()
        week_day = week_day and week_day or '0'
        resource_calendar_attendance = self.env['resource.calendar.attendance'].search([('dayofweek', '=', week_day), ('calendar_id', '=', self.id)])
        if resource_calendar_attendance:
            return True
        else:
            return False


class attendance_config(models.Model):
    _name = "attendance.config"

    calender_id = m2o_field('resource.calendar', 'Calender')
    name = char_field('Name')
    dayofweek = selection_field([('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday')],
                                string='Day of Week')
    hour_from = float_field('time from')
    hour_to = float_field('time to')
    action = selection_field([('sign_in', 'Sign in'), ('sign_out', 'Sign out')], string="Action")
