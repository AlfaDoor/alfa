# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import time
from datetime import datetime
from .base_tech import *
from dateutil.relativedelta import relativedelta
from .overtime_calc import over_time_calc
from odoo.tools import __

DAYS_OF_WEEK = [
    ('0', 'Monday'),
    ('1', 'Tuesday'),
    ('2', 'Wednesday'),
    ('3', 'Thursday'),
    ('4', 'Friday'),
    ('5', 'Saturday'),
    ('6', 'Sunday'),
]


class hr_attendance(models.Model):
    _inherit = "hr.attendance"
    _order = 'id'

    action_compute = fields.Selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'), ('action', 'Action')], string='Action computed')
    dayofweek = selection_field(DAYS_OF_WEEK, string='Day of week', compute='get_dayofweek')
    working_day_id = m2o_field('working.days', 'Working day')
    is_different_day = bool_field('is different day', compute='get_is_different_day')
    date_str = char_field('Date string', compute="get_date_str")
    name = fields.Datetime('Date', default=fields.Datetime.now, required=True)
    action = selection_field([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'), ('action', 'Action')],
                             required=True, string='Action')
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=False)

    def localize_dt(self, date, to_tz):
        from dateutil import tz
        from_zone = tz.gettz('UTC')
        to_zone = tz.gettz(to_tz)
        utc = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        utc = utc.replace(tzinfo=from_zone)
        res = utc.astimezone(to_zone)
        return res.strftime('%Y-%m-%d %H:%M:%S')

    @api.one
    @api.depends('name')
    def get_date_str(self):
        self.date_str = __(self.name, True, True, self.env.user.tz)

    @api.one
    @api.depends()
    def get_is_different_day(self):
        action_time = datetime.strptime(__(self.name, True, True, self.env.user.tz), "%Y-%m-%d %H:%M:%S")
        if action_time.hour < 6 and self.action_compute == 'sign_out':
            self.is_different_day = True
            return
        self.is_different_day = False

    @api.one
    @api.depends('name')
    def get_dayofweek(self):
        if self.name:
            self.dayofweek = str(datetime.strptime(__(self.name), '%Y-%m-%d').weekday())

    @api.one
    @api.depends()
    def _get_action(self):
        self.action_compute = self.employee_id.contract_id.resource_calendar_id.get_action_by_time(__(__(self.name, True), True))

    @api.multi
    @api.constrains('action')
    def _altern_si_so(self):
        return True

    _constraints = [(_altern_si_so, 'Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]

    @api.one
    @api.depends('name')
    def get_date(self):
        if __(self.name, True):
            self.date = datetime.strptime(__(self.name, True), "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")

    @api.one
    def set_working_day(self):
        if self._context.get('dont_set_again', False):
            return
        ctx = dict(self._context.copy(), dont_set_again=True)
        action_time = datetime.strptime(__(self.name, True, True, self.env.user.tz), "%Y-%m-%d %H:%M:%S")
        day = action_time.strftime("%Y-%m-%d")
        in_action_before = len(self.env['hr.attendance'].search(
            [('employee_id', '=', self.employee_id.id), ('name', '<', __(self.name, True)), ('name', '>', day),
             ('action_compute', '=', 'sign_in')])) > 0
        if action_time.hour < 6 and self.action_compute == 'sign_out' and not in_action_before:
            action_time = action_time + relativedelta(days=-1)
        day = action_time.strftime("%Y-%m-%d")
        working_day = self.env['working.days'].search([('employee_id', '=', self.employee_id.id), ('date', '=', day)])
        if working_day:
            self.with_context(ctx).working_day_id = working_day[0].id
        else:
            working_day = self.sudo().env['working.days'].create({
                'employee_id': self.employee_id.id,
                'date': day,
                'absence': False,
            })
            self.with_context(ctx).working_day_id = working_day.id

    @api.model
    def create(self, vals):
        if not vals.get('name', False):
            vals['name'] = time.strftime('%Y-%m-%d %H:%M:%S')
        employee = self.env['hr.employee'].browse(vals['employee_id'])
        working_time = self.env['working.days'].get_employee_working_hours(employee, vals['name'].split(' ')[0])
        if not vals.get('action_compute', False):
            vals['action_compute'] = working_time.get_action_by_time(vals['name'])
        res = super(hr_attendance, self).create(vals)
        res.set_working_day()
        res.working_day_id.get_is_ok()
        res.working_day_id.get_ded_ovt()
        return res

    @api.multi
    def write(self, vals):
        res = super(hr_attendance, self).write(vals)
        self.set_working_day()
        self.working_day_id.get_is_ok()
        self.working_day_id.get_ded_ovt()
        return res

    @api.one
    def unlink(self):
        working_day_id = self.working_day_id
        res = super(hr_attendance, self).unlink()
        working_day_id.get_is_ok()
        working_day_id.get_ded_ovt()
        return res

    @api.model_cr
    def init(self):
        try:
            self.env.cr.execute("ALTER TABLE hr_attendance ALTER COLUMN check_in DROP NOT NULL")
        except:
            pass

    @api.one
    def name_get(self):
        return (self.id,__(self.name, True, True, self.env.user.tz))

    # Ignore hr_attendance validations
    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        return True

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        return True


Time_digits = (20, 12)


class WorkingDays(models.Model):
    _name = "working.days"
    _order = "employee_id, date"

    @api.model
    def create(self, vals):
        res = super(WorkingDays, self).create(vals)
        res.get_ded_ovt()
        return res

    employee_id = m2o_field('hr.employee', 'Employee')
    employee_number = fields.Char(related='employee_id.employee_number')
    employee_status = fields.Many2one(related='employee_id.employee_status')
    date = date_field('Date')
    att_ids = o2m_field('hr.attendance', 'working_day_id', 'Attendances')
    att_count = integer_field('Number of actions', compute='get_ded_ovt', multi=True, store=True)
    not_ok = bool_field('Isn\'t OK', compute='get_ded_ovt', multi=True, store=True)
    reason = char_field('Reason', compute='get_ded_ovt', multi=True, store=True)
    dayofweek = selection_field(DAYS_OF_WEEK, string='Day of week', compute='get_dayofweek', store=True)
    overtime_minutes = float_field('Overtime Hours', compute='get_ded_ovt', multi=True, store=True)
    delay_minutes = float_field('Delay Hours', compute='get_ded_ovt', store=True, multi=True, digits=Time_digits)
    working_minutes = float_field('Working Hours', compute='get_ded_ovt', multi=True, store=True, digits=Time_digits)
    total_working_minutes = float_field('Total working Hours', compute='get_ded_ovt', multi=True, store=True, digits=Time_digits)
    excuse_id = m2o_field('hr.excuse', 'Excuse', compute='get_net_delay', multi=True)
    excuse_minutes = float_field('Excuse minutes', compute='get_net_delay', multi=True)
    net_delay = float_field('Final delay', compute='get_ded_ovt', store=True, multi=True, digits=Time_digits)
    overtime_assignment_id = m2o_field('overtime.assignment', 'Overtime assignment', compute='get_overtime_assignment_id', multi=True)
    overtime_assigned_hours = float_field('Assigned overtime hours', compute='get_overtime_assignment_id', multi=True, digits=Time_digits)
    assignment_state = selection_field(related='overtime_assignment_id.state')
    excuse_state = selection_field(related='excuse_id.state')
    absence = bool_field('is absence that day', compute='get_ded_ovt', multi=True, store=True, default=True)
    absence_excuse = bool_field('Has absence excuse', compute='get_ded_ovt', multi=True, store=True)
    is_national_holiday = bool_field('Is national holiday', compute='get_ded_ovt', multi=True, store=True)
    in_leave = bool_field('In Leave', compute='get_ded_ovt', multi=True, store=True)
    is_manipulate = bool_field('Manipulation', compute='get_ded_ovt', multi=True, store=True)
    overtime_amount = float_field('overtime (amount)', related="overtime_assignment_id.overtime_calc")
    morning_delay = fields.Float('Morning delay', compute='get_ded_ovt', multi=True, store=True, digits=Time_digits)
    exit_delay = fields.Float('Exit delay', compute='get_ded_ovt', multi=True, store=True, digits=Time_digits)
    morning_delay_ = fields.Char('Morning delay', compute='minute_to_string', multi=True, )
    exit_delay_ = fields.Char('Exit delay', compute='minute_to_string', multi=True, )

    enter_date = fields.Datetime('Enter date', compute='get_enter_exit_dates')
    exit_date = fields.Datetime('Enter date', compute='get_enter_exit_dates')
    total_working_minutes_ = fields.Char('Total working minute', compute='minute_to_string', multi=True, )
    is_weekend = fields.Boolean('Is week end', compute='get_is_weekend')

    @api.one
    @api.depends('date')
    def get_is_weekend(self):
        self.is_weekend = not self.employee_id.contract_id.resource_calendar_id.check_day_is_official_day(__(self.date))

    @api.one
    @api.depends()
    def get_enter_exit_dates(self):
        fingerprints = self.env['hr.attendance'].search([('working_day_id', '=', self.id)], order='name')
        enter_date = exit_date = False
        for f in fingerprints:
            if f.action_compute == 'sign_in':
                if not enter_date:
                    enter_date = __(f.name, True)
            if f.action_compute == 'sign_out':
                exit_date = __(f.name, True)
        self.enter_date = enter_date
        self.exit_date = exit_date

    @api.model
    def to_minute(self, float_min):
        s = str(float_min).split('.')
        minutes = int(s[1]) / (10.0 ** len(s[1])) * 60
        return "%s:%s" % (s[0], int(round(minutes)))

    @api.one
    @api.depends('morning_delay', 'exit_delay', 'total_working_minutes')
    def minute_to_string(self):
        self.morning_delay_ = self.to_minute(self.morning_delay)
        self.exit_delay_ = self.to_minute(self.exit_delay)
        self.total_working_minutes_ = self.to_minute(self.total_working_minutes)

    @api.one
    @api.depends()
    def get_is_manipulate(self):
        if len(self.att_ids) == 1:
            self.is_manipulate = True
            self.not_ok = False
            self.reason = ''
        else:
            self.is_manipulate = False

    @api.one
    @api.depends()
    def get_in_leave(self):
        leave = self.env['hr.leave'].search(
            [('employee_id', '=', self.employee_id.id), ('date_from', '<=', __(self.date)), ('date_to', '>=', __(self.date)),
             ('state', '=', 'validate'), ])
        in_leave = False
        if len(leave) != 0 and leave[0].holiday_status_id.non_annual_type != 'Unpaid Leave':
            in_leave = True
        self.in_leave = in_leave

    @api.one
    @api.depends()
    def get_overtime_assignment_id(self):
        assignment = self.env['overtime.assignment'].search([('employee_id', '=', self.employee_id.id), ('date', '=', __(self.date)), ])
        if assignment:
            self.overtime_assignment_id = assignment[0].id
            self.overtime_assigned_hours = self.overtime_assignment_id.overtime_hours_assigned

    @api.one
    @api.depends()
    def get_net_delay(self):
        if self.in_leave:
            self.net_delay = 0
            return
        net_delay = self.delay_minutes
        excuses = self.env['hr.excuse'].search([('employee_id', '=', self.employee_id.id), ('date', '=', __(self.date)), ])
        total_excuse = excuse_minutes = 0
        for excuse in excuses:
            self.excuse_id = excuse.id
            excuse_minutes += self.excuse_id.excuse_hours
            total_excuse += (excuse.state == 'confirmed' and excuse.excuse_hours or 0)
        net_delay = net_delay - total_excuse
        self.excuse_minutes = excuse_minutes
        self.net_delay = net_delay >= 0 and net_delay or 0

    @api.one
    @api.depends()
    def get_excuse(self):
        if self.in_leave:
            self.net_delay = 0
            return
        net_delay = self.delay_minutes
        excuse = self.env['hr.excuse'].search([('employee_id', '=', self.employee_id.id), ('date', '=', __(self.date)), ])
        if excuse:
            self.excuse_id = excuse[0].id
            self.excuse_minutes = self.excuse_id.excuse_hours
            net_delay = net_delay - (self.excuse_id.state == 'confirmed' and self.excuse_id.excuse_hours or 0)
        self.net_delay = net_delay >= 0 and net_delay or 0

    @api.model
    def get_employee_working_hours(self, employee, date):
        working_hours = employee.contract_id.resource_calendar_id or employee.working_time_id
        change_obj = self.env['change.working.hours']
        change_WH = change_obj.search([('date_from', '<=', date), ('date_to', '>=', date)])
        if change_WH:
            sql = """
            SELECT change.date_from AS d1, change.date_to AS d2 , rel.change_working_hours_id as xx, rel.hr_employee_id
            FROM change_working_hours_hr_employee_rel rel
             LEFT JOIN change_working_hours change ON (rel.change_working_hours_id = change.id)
             WHERE change.date_from <= %s AND change.date_to >= %s AND rel.hr_employee_id = %s
            """
            params = [date, date, employee.id]
            self.env.cr.execute(sql, params)
            rows = self.env.cr.dictfetchall()
            if rows:
                working_hours = change_obj.browse(rows[0]['xx']).calender_id
        return working_hours

    @api.one
    @api.depends()
    def get_ded_ovt(self):
        self.att_count = len(self.att_ids)
        self.get_in_leave()
        self.get_is_ok()
        # self.get_excuse()
        self.get_net_delay()
        self.get_is_manipulate()
        clear_day = False
        if self.not_ok:
            self.absence = False
            self.clear_day()
            return
        actual_workings = []
        actual_working = {}
        atts = self.env['hr.attendance'].search([('id', 'in', self.att_ids.ids), ('action_compute', 'in', ['sign_in', 'sign_out'])], order='name')
        last_action = False
        for att in atts:
            att_time = datetime.strptime(__(att.name, True, True, self.env.user.tz), "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
            if (att.action_compute == 'sign_in' and last_action in [False, 'sign_out']) or (
                    att.action_compute == 'sign_out' and last_action == 'sign_in'):
                actual_working[att.action_compute] = att_time
                last_action = att.action_compute
                if att.is_different_day:
                    actual_working['sign_out'] = "23:59"
                    actual_workings.append(actual_working)
                    actual_working = {'sign_in': "00:00", 'sign_out': att_time}
                    last_action = 'sign_out'
                if att.action_compute == 'sign_out':
                    actual_workings.append(actual_working)
                    actual_working = {}
            if last_action == 'sign_out' and att.action_compute == 'sign_out':
                actual_workings[-1]['sign_out'] = att_time
        working_hours = self.get_employee_working_hours(self.employee_id, __(self.date))
        official_workings = working_hours.get_official_workings(self.dayofweek)
        self.absence = False
        is_official_day = self.employee_id.contract_id.resource_calendar_id.check_day_is_official_day(__(self.date))
        if not atts and is_official_day and not self.in_leave:
            self.absence = True
        self.is_national_holiday = False
        if self.env['hr.national.holiday'].day_in_national_holiday(__(self.date)):
            self.is_national_holiday = True
            self.absence = False
            self.clear_day()
        dic = over_time_calc(official_workings, actual_workings)
        self.overtime_minutes = self.minute_to_float(dic['overtime'])
        self.delay_minutes = self.minute_to_float(dic['deduction'])
        self.working_minutes = self.minute_to_float(dic['working_minutes'])
        self.total_working_minutes = self.minute_to_float(dic['working_minutes_to'])
        self.morning_delay = self.minute_to_float(dic['delay_minutes'])
        self.exit_delay = self.minute_to_float(dic['exit_minutes'])
        if self.absence or self.is_manipulate or self.is_national_holiday or (
                self.excuse_id.ignore_deduction and self.excuse_id.state == 'confirmed') or self.in_leave:
            self.clear_day()
        absence_excuse = self.env['hr.excuse'].search(
            [('employee_id', '=', self.employee_id.id), ('date', '=', __(self.date)), ('for_absence', '=', True), ('state', '=', 'confirmed')],
            limit=1)
        if absence_excuse:
            self.absence_excuse = True

    @api.one
    def clear_day(self):
        self.delay_minutes = self.net_delay = self.overtime_minutes = self.working_minutes = self.total_working_minutes = self.morning_delay = self.exit_delay = 0

    @api.multi
    def new_excuse(self):

        return {
            'domain': [],
            'name': _('Excuse'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.excuse',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'default_employee_id': self.employee_id.id, 'default_date': __(self.date), 'default_for_absence': self.absence},
        }

    def localize_dt(self, utc, to_tz):
        to_tz = to_tz or self.env.user.tz
        from dateutil import tz
        from_zone = tz.gettz('UTC')
        to_zone = tz.gettz(to_tz)
        utc = utc.replace(tzinfo=from_zone)
        res = utc.astimezone(to_zone)
        return res

    @api.model
    def minute_to_float(self, m):
        h, m = m.split(':')
        float_ = float(h) + (float(m) / 60.0)
        return float_

    @api.one
    @api.depends('date')
    def get_dayofweek(self):
        if self.date:
            self.dayofweek = str(datetime.strptime(__(self.date), '%Y-%m-%d').weekday())

    @api.one
    @api.depends('att_ids')
    def get_is_ok(self):
        if self.in_leave:
            self.not_ok = False
            self.reason = False
            return
        last_action = False
        last_att_time = False
        reason = ''
        not_ok = False
        atts = self.env['hr.attendance'].search([('working_day_id', '=', self.id), ('action_compute', 'in', ['sign_in', 'sign_out'])], order='name')
        for att in atts:
            action = att.action_compute
            if not last_action and action == 'sign_out':
                not_ok = True
                reason = "first action is Sign out Please make first action is Sign in"
                break
            if last_action and last_action == action:
                d1 = datetime.strptime(__(att.name, True, True, self.env.user.tz), "%Y-%m-%d %H:%M:%S")
                d2 = datetime.strptime(last_att_time, "%Y-%m-%d %H:%M:%S")
                diff = relativedelta(d2, d1)
                big_diff = diff.days or diff.hours or diff.minutes > 6
                if big_diff:
                    not_ok = True
                    reason = 'There are two %s behind each other' % {'sign_in': 'Sign in', 'sign_out': 'Sign out'}[action]
                    break
            last_action = action
            last_att_time = __(att.name, True, True, self.env.user.tz)
        if not not_ok and last_action == 'sign_in':
            not_ok = True
            reason = 'Last action is Sign in ,It should be sign out'
        self.not_ok = not_ok
        self.reason = reason

    @api.one
    def name_get(self):
        lang = self._context.get('lang', False)
        name = self.employee_id.employee_english_name or self.employee_id.name
        if lang == 'ar_SY':
            name = self.employee_id.name or self.employee_id.employee_english_name
        return (self.id, "%s [%s]" % (name, __(self.date)))

    @api.one
    def get_overtime_delay_minutes(self):
        if not self.not_ok:
            atts = self.env['hr.attendance'].search([('working_day_id', '=', self.id), ('action_compute', 'in', ['sign_in', 'sign_out'])],
                                                    order='name')

    @api.multi
    def set_non_action_working_days(self, date_from=False, date_to=False):
        date_from = date_from or datetime.today()
        date_to = type(date_to) == datetime and date_to or type(date_from) == str and datetime.strptime("%Y-%m-%d") or False
        all_employees = self.env['hr.employee'].search(
            [['contract_id', '!=', False], ['contract_id.state', '=', 'open'], ['exclude_from_fingerprint', '=', False],
             ['active', '=', True]])
        for employee in all_employees:
            for day_before in range(1, 35):
                day = datetime.today() - relativedelta(days=day_before)
                working_day = self.search([['employee_id', '=', employee.id], ['date', '=', day.strftime("%Y-%m-%d")]])
                if not working_day:
                    self.create({
                        'employee_id': employee.id,
                        'date': day.strftime("%Y-%m-%d")
                    })

    # @api.multi
    # def init(self):
    #     for day in self.search([]):
    #         day.get_ded_ovt()

    @api.one
    def rest_action_days(self):
        # self.att_ids.set_working_day()
        self.env['hr.attendance'].search(
            ['|', '&', '&', ('name', '>=', __(self.date)), ('employee_id', '=', self.employee_id.id), ('name', '<=', __(self.date)),
             ('id', 'in', self.att_ids.ids)],
            order='name').set_working_day()

    @api.one
    def set_weekend_absence(self, employee_id=False, date_from=False, date_to=False):
        def proceed(_thursday, employee_id):
            d = [(_thursday + relativedelta(days=_diff)).strftime("%Y-%m-%d") for _diff in range(1, 3)]
            xx = self.search([('employee_id', '=', employee_id), ('date', 'in', d)])
            for x in xx:
                x.absence = True

        domain = [('dayofweek', 'in', ['3']), ('absence', '=', True), ('date', '>=', '2018-10-14')]
        absence_thursdays = self.search(domain)
        for thursday in absence_thursdays:
            thursday_date = datetime.strptime(thursday.date, "%Y-%m-%d")
            # Next Sunday
            # next_sunday_date = (thursday_date + relativedelta(days=3)).strftime("%Y-%m-%d")
            # next_sunday = self.search([('employee_id', '=', thursday.employee_id.id), ('date', '=', next_sunday_date)])
            # if next_sunday.absence:
            #     proceed(thursday_date, thursday.employee_id.id)
            #     continue

            # Previous week
            dates = [(thursday_date + relativedelta(days=-diff)).strftime("%Y-%m-%d") for diff in range(1, 5)]
            absence_pre_week = self.search([('employee_id', '=', thursday.employee_id.id), ('date', 'in', dates), ('absence', '=', True)])
            if len(absence_pre_week) == 4:
                proceed(thursday_date, thursday.employee_id.id)

    @api.multi
    def open_new_excuse(self):
        return {
            'name': _('Excuse'),
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'hr.excuse',
            'type': 'ir.actions.act_window',
            'context': {'default_employee_id': self.employee_id.id, 'default_date': __(self.date)},
        }

class Payslip(models.Model):
    _inherit = "hr.payslip"

    overtime_h = float_field("Overtime hours", compute='get_sheet_details', multi=True)
    absence_excuse = float_field('Absence with excuse', compute='get_sheet_details', multi=True)
    absence_no_excuse = float_field('Absence without excuse', compute='get_sheet_details', multi=True)
    delay = float_field('Attendance Delay(Min)', compute='get_sheet_details', multi=True)
    sheet_report_id = m2o_field('payroll.sheet.report', 'Payroll sheet report')
    absence_excuse_amount = float_field('Absence with excuse amount', compute='_get_delay_amounts', multi=True)
    absence_no_excuse_amount = float_field('Absence without excuse amount', compute='_get_delay_amounts', multi=True)
    delay_amount = float_field('Delay amount', compute='_get_delay_amounts', multi=True)

    @api.one
    # @api.depends('employee_id', 'payslip_run_id','sheet_report_id')
    def get_sheet_details(self):
        report = self.sheet_report_id or self.payslip_run_id.sheet_report_id
        employee_report = self.env['employee.sheet.report'].search(
            [('employee_id', '=', self.employee_id.id), ('payroll_report_sheet_id', '=', report.id), ('payroll_report_sheet_id', '!=', False)],
            limit=1)

        self.delay = employee_report.total_delay
        self.overtime_h = employee_report.total_overtime
        self.absence_excuse = employee_report.total_absence_with_ex
        self.absence_no_excuse = employee_report.total_absence_without_ex

    rule_overtime = fields.Float('Overtime')
    rule_absence = fields.Float('Absence / Delay')

    @api.one
    def compute_sheet(self):
        self.get_sheet_details()
        return super(Payslip, self).compute_sheet()

    @api.one
    def _compute_rules_fields(self):
        super(Payslip, self)._compute_rules_fields()
        for line in self.line_ids:
            if line.code == 'OVT':
                self.rule_overtime = line.total
            if line.code == 'ABS':
                self.rule_absence = line.total
    @api.model
    def RULE_overtime(self):
        OVT = 0
        if self.employee_id.overtime_eligible == True:
            if self.overtime_h:
                OVT = self.contract_id.basic_salary / 240 * self.overtime_h
        else:
            OVT = 0
        return OVT

    @api.multi
    def _get_delay_amounts(self):

        for rec in self:
            contract = rec.employee_id.contract_id
            basic = contract.basic_salary
            transportation = contract.transportation_allowance_amount
            # food = contract.food_allowance_amount
            x = (basic + transportation) / 30
            xx = (basic / 30 * 1.5) + ((transportation) / 30)
            rec.absence_excuse_amount = rec.absence_excuse * x
            rec.absence_no_excuse_amount = rec.absence_no_excuse * xx
            rec.delay_amount = basic / 14400 * rec.delay * 60

    @api.model
    def RULE_absence(self):
        ABS = self.absence_excuse_amount + self.absence_no_excuse_amount + self.delay_amount
        return ABS * -1

    # @api.model
    # def net_gross(self):
    #     res = super(Payslip, self).net_gross()
    #     return res + self.RULE_overtime()

    @api.model
    def total_deductions(self):
        res = super(Payslip, self).total_deductions()
        return res + self.RULE_absence()

    @api.multi
    def open_att_sheet(self):
        report = self.sheet_report_id or self.payslip_run_id.sheet_report_id
        employee_report = self.env['employee.sheet.report'].search(
            [('employee_id', '=', self.employee_id.id), ('payroll_report_sheet_id', '=', report.id), ('payroll_report_sheet_id', '!=', False)],
            limit=1)
        res_id = employee_report.id
        if res_id:
            return {
                'domain': [],
                'name': _('Employee report'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'employee.sheet.report',
                'res_id': res_id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {},
            }
        raise ValidationError(_("No report selected !!"))


class validate_working_days(models.TransientModel):
    _name = "validate.working.days"

    @api.one
    def calc_days(self):
        ids = self._context.get('active_ids', [])
        self.env['working.days'].browse(ids).get_ded_ovt()
        return {'type': 'ir.actions.act_window_close'}

    @api.one
    def rest_action_days(self):
        ids = self._context.get('active_ids', [])
        self.env['working.days'].browse(ids).rest_action_days()
        return {'type': 'ir.actions.act_window_close'}


class hr_excuse(models.Model):
    _name = 'hr.excuse'
    _description = "Employee excuse"
    _rec_name = 'code'
    _inherit = "mail.thread"
    _order = "id desc"

    employee_id = m2o_field('hr.employee', 'Employee')
    excuse_hours = float_field('Excuse hours')
    date = date_field('Day')
    day_sheet_id = m2o_field('working.days', 'Day', compute='get_day')
    delay = float_field('Delay in that day', related='day_sheet_id.delay_minutes')
    net_delay = float_field('Net delay after excuse')
    state = selection_field([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('refused', 'Refused')], string='Statue', default='draft',
                            track_visibility='onchange')
    responsible_id = m2o_field('hr.employee', 'Responsible', help="Who will confirm that excuse")
    for_absence = bool_field('For absence')
    ignore_deduction = bool_field('Ignore deduction')
    note = text_field('Notes')
    code = char_field('Code', default='EXCUSE')
    can_confirm = bool_field('Can confirm', compute='get_can_confirm')

    @api.one
    @api.depends('responsible_id')
    def get_can_confirm(self):
        can_confirm = False
        employee = self.sudo().env['hr.employee'].search([('id', '=', self.employee_id.id)])
        responsible = self.sudo().env['hr.employee'].search([('id', '=', self.responsible_id.id)])
        if (self.env.user.id in [responsible.user_id.id, employee.parent_id.user_id.id,
                                 employee.department_id.manager_id.user_id.id,
                                 employee.management_id.manager_id.user_id.id]) or \
                self.env.user.has_group('overtime_late.confirm_excuse'):
            can_confirm = True
        self.can_confirm = can_confirm

    @api.onchange('employee_id')
    def get_manager(self):
        employee = self.sudo().env['hr.employee'].search([('id', '=', self.employee_id.id)])
        self.responsible_id = employee.parent_id.id or employee.department_id.manager_id.id or employee.management_id.manager_id.id

    @api.constrains('employee_id', 'date')
    def set_excuse(self):
        self.day_sheet_id.get_ded_ovt()

    # @api.constrains('employee_id', 'excuse_hours', 'date', 'state')
    # def check_minutes(self):
    #     if self.state == 'confirmed' and self.excuse_hours > self.delay:
    #         raise ValidationError(_("Excuse hours can not be greater than delay in that day"))

    @api.one
    @api.depends('employee_id', 'date')
    def get_day(self):
        for rec in self:
            day = self.env['working.days'].search([('date', '=', __(self.date)), ('employee_id', '=', self.employee_id.id), ], limit=1)
            if len(day) != 0:
                rec.day_sheet_id = day.id
                rec.excuse_hours = day.read(['delay_minutes'])[0]['delay_minutes']

    @api.one
    def confirm(self):
        self.state = 'confirmed'

    @api.one
    def refuse(self):
        self.state = 'refused'

    @api.one
    def reset(self):
        self.state = 'draft'

    @api.one
    def cancel(self):
        self.state = 'cancel'

    @api.model
    def create(self, vals):
        self.check_valid_period(vals['date'])
        res = super(hr_excuse, self).create(vals)
        res.code = self.env['ir.sequence'].next_by_code(self._name)
        return res

    @api.one
    def write(self, vals):
        self.check_valid_period()
        res = super(hr_excuse, self).write(vals)
        self.day_sheet_id.get_ded_ovt()
        return res

    def check_valid_period(self, date=False):
        date = date or self.date
        confirmed_report_sheet = self.env['employee.sheet.report'].search(
            [('delay_date_from', '<=', date), ('delay_date_to', '>=', date), ('state', 'in', ['confirmed', 'reviewed']), ])
        if confirmed_report_sheet:
            confirmed_report_sheet = confirmed_report_sheet[0]
            raise ValidationError(_("Sorry you can't made any changes on excuses in this period\nfrom %s to %s\nBecause it's closed" % (
                confirmed_report_sheet.delay_date_from, confirmed_report_sheet.delay_date_to)))


class overtime_asignment(models.Model):
    _name = 'overtime.assignment'
    _description = "Overtime assignment"
    _rec_name = 'code'
    _inherit = "mail.thread"
    _order = "id desc"

    employee_id = m2o_field('hr.employee', 'Employee')
    date = date_field('Day')
    overtime_hours_assigned = float_field('Assigned overtime hours')
    state = selection_field([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('cancel', 'Cancelled from HR')], string='Statue', default='draft',
                            track_visibility='onchange')
    day_sheet_id = m2o_field('working.days', 'Day', compute='get_day')
    overtime_hours_sheet = float_field('Sheet overtime hours', compute='get_day')
    responsible_id = m2o_field('hr.employee', 'Responsible', help="How will confirm that Overtime")
    code = char_field('Code', default='OVT')
    note = text_field('Description')
    can_confirm = bool_field('Can confirm', compute='get_can_confirm')
    analytic_account_id = m2o_field('account.analytic.account', 'Analytic account')
    overtime_calc = float_field('Overtime calculation', compute="get_overtime_calc")
    type = selection_field([
        ('delay_at_morning', ''),
        ('get_out_early', ''),
        ('absence', ''),
        ('forget_fingerprint', ''),
        ('add_action', ''),
    ], string='Excuse type')


    is_external_labour = fields.Boolean('External labour', related='employee_id.is_external_labour', store=True)
    vendor_id = fields.Many2one('res.partner', 'Vendor', related="employee_id.vendor_id", store=True)
    working_time_id = fields.Many2one('resource.calendar', 'Working Schedule', related="employee_id.working_time_id", store=True)

    @api.one
    def get_overtime_calc(self):
        OVT = 0
        if self.state == 'confirmed':
            if self.employee_id.is_external_labour:
                OVT = self.employee_id.rate * self.overtime_hours_assigned
            else:
                basic_salary = self.employee_id.contract_id.basic_salary
                if basic_salary:
                    OVT = basic_salary / 160 * self.overtime_hours_assigned
        self.overtime_calc = round(OVT, 2)

    @api.one
    def reset(self):
        self.state = 'draft'

    @api.one
    def cancel(self):
        self.state = 'cancel'

    @api.one
    @api.depends('responsible_id')
    def get_can_confirm(self):
        can_confirm = False
        employee = self.sudo().env['hr.employee'].search([('id', '=', self.employee_id.id)])
        responsible = self.sudo().env['hr.employee'].search([('id', '=', self.responsible_id.id)])
        if (self.env.user.id in [responsible.user_id.id, employee.parent_id.user_id.id,
                                 employee.department_id.manager_id.user_id.id,
                                 employee.management_id.manager_id.user_id.id]) or \
                self.env.user.has_group('overtime_late.confirm_excuse'):
            can_confirm = True
        self.can_confirm = can_confirm

    @api.onchange('employee_id')
    def get_manager(self):
        self.responsible_id = self.employee_id.parent_id.id or self.employee_id.department_id.manager_id.id or self.employee_id.management_id.manager_id.id

    @api.one
    @api.depends('employee_id', 'date')
    def get_day(self):
        day = self.env['working.days'].search([('date', '=', __(self.date)), ('employee_id', '=', self.employee_id.id), ], limit=1)
        if len(day) != 0:
            self.day_sheet_id = day.id
            self.overtime_hours_sheet = day.read(['overtime_minutes'])[0]['overtime_minutes']
            self.overtime_hours_assigned = day.read(['overtime_minutes'])[0]['overtime_minutes']

    @api.one
    def confirm(self):
        self.state = 'confirmed'

    @api.model
    def create(self, vals):
        res = super(overtime_asignment, self).create(vals)
        res.check_valid_period(vals['date'])
        res.code = self.env['ir.sequence'].next_by_code(self._name)
        if not res.responsible_id:
            res.get_manager()
        return res

    @api.one
    def write(self, vals):
        self.check_valid_period()
        res = super(overtime_asignment, self).write(vals)
        return res

    def check_valid_period(self, date=False):
        if self.employee_id.is_external_labour:
            return
        date = date or __(self.date)
        confirmed_report_sheet = self.env['employee.sheet.report'].search(
            [('overtime_date_from', '<=', date), ('overtime_date_to', '>=', date), ('state', 'in', ['confirmed', 'reviewed']), ])
        if confirmed_report_sheet:
            confirmed_report_sheet = confirmed_report_sheet[0]
            raise ValidationError(
                _("Sorry you can't made any changes on Overtime in this period\n- from %s to %s\nBecause Payroll sheet is closed" % (
                    __(confirmed_report_sheet.delay_date_from), __(confirmed_report_sheet.delay_date_to))))


PAYROLL_STATUS = [
    ('new', 'new'),
    ('sent_emails', 'Emails sent'),
    ('reviewed', 'Reviewed'),
    ('confirmed', 'Confirmed'),
]


class Employee_report(models.Model):
    _name = "employee.sheet.report"
    _description = "Employee sheet report"
    _inherit = "mail.thread"

    employee_id = m2o_field('hr.employee', 'Employee')
    overtime_date_from = date_field('overtime date from')
    overtime_date_to = date_field('overtime date to')
    delay_date_from = date_field('delay date from')
    delay_date_to = date_field('delay date to')

    total_delay = float_field('Total delay', compute='get_totals', multi=True)
    total_delay_round = float_field('Total delay', compute='get_totals', multi=True)
    total_overtime = float_field('Total overtime', compute='get_totals', multi=True)
    total_overtime_round = float_field('Total overtime', compute='get_totals', multi=True)
    total_overtime_amount = float_field('Total overtime (amount)', compute='get_totals', multi=True)
    total_absence_with_ex = integer_field('Absence with excuse', compute='get_totals', multi=True)
    total_absence_without_ex = integer_field('Absence without excuse', compute='get_totals', multi=True)
    delay_day_ids = m2m_field('working.days', string='Delay Days', compute='get_totals', multi=True)
    overtime_day_ids = m2m_field('working.days', string='Delay Days', compute='get_totals', multi=True)
    payroll_report_sheet_id = m2o_field('payroll.sheet.report', string='Payroll report sheet')
    state = selection_field(PAYROLL_STATUS, string='Status', store=True, related="payroll_report_sheet_id.state")
    send = bool_field('send email')

    @api.one
    @api.depends('employee_id', 'overtime_date_from', 'overtime_date_to', 'delay_date_from', 'delay_date_to', )
    def get_totals(self):
        if __(self.delay_date_from) and __(self.delay_date_to):
            domain = [
                ('employee_id', '=', self.employee_id.id),
                ('date', '>=', __(self.delay_date_from)),
                ('date', '<=', __(self.delay_date_to)),
            ]
            delay_days = self.env['working.days'].search(domain)
            total_delay = 0
            for att in delay_days:
                total_delay += att.net_delay
            self.total_delay = total_delay
            # self.total_delay = sum([ ])
            self.delay_day_ids = delay_days.ids
            total_absence = self.env['working.days'].search(domain + [('absence', '=', True)])
            total_absence_with_ex = total_absence_without_ex = 0
            for abc in total_absence:
                if not abc.excuse_id.ignore_deduction:
                    if abc.excuse_id.state == 'confirmed':
                        total_absence_with_ex += 1
                    else:
                        total_absence_without_ex += 1
            self.total_absence_with_ex = total_absence_with_ex
            self.total_absence_without_ex = total_absence_without_ex
        if __(self.overtime_date_from) and __(self.overtime_date_to):
            overtime_days = self.env['working.days'].search([
                ('employee_id', '=', self.employee_id.id),
                ('date', '>=', __(self.overtime_date_from)),
                ('date', '<=', __(self.overtime_date_to)),
            ])
            total_overtime = 0
            for att_over in overtime_days:
                total_overtime += att_over.overtime_minutes
            self.total_overtime = total_overtime
            # self.total_overtime = sum([att.overtime_assigned_hours for att in overtime_days if att.overtime_assignment_id.state == 'confirmed'])
            # self.total_overtime_amount = sum(
            #     [att.overtime_assignment_id.overtime_calc for att in overtime_days if att.overtime_assignment_id.state == 'confirmed'])
            self.overtime_day_ids = overtime_days.ids
        self.total_delay_round = round(self.total_delay, 2)
        self.total_overtime_round = round(self.total_overtime, 2)

    @api.one
    def deep_update(self):
        days = self.env['working.days'].search(
            [('employee_id', '=', self.employee_id.id), ('date', '>=', __(self.delay_date_from)), ('date', '<=', __(self.delay_date_to))])
        days.get_ded_ovt()


class PayrollSheetReport(models.Model):
    _name = "payroll.sheet.report"
    _description = "Payroll sheet report"
    _inherit = "mail.thread"
    _order = "id desc"

    name = char_field('Name', default='/')
    overtime_date_from = date_field('overtime date from')
    overtime_date_to = date_field('overtime date to')
    delay_date_from = date_field('delay date from')
    delay_date_to = date_field('delay date to')
    employee_report_ids = o2m_field('employee.sheet.report', 'payroll_report_sheet_id', string='Employees reports')
    state = selection_field(PAYROLL_STATUS, string='Status', default='new')
    emails_sent = bool_field('Emails sent', default=False)

    @api.one
    def update(self):
        self.employee_report_ids.unlink()
        all_emp = self.env['hr.employee'].search([('contract_id', '!=', False), ('exclude_from_fingerprint', '=', False)])
        for emp in all_emp:
            vals = {
                'employee_id': emp.id,
                'overtime_date_from': __(self.overtime_date_from),
                'overtime_date_to': __(self.overtime_date_to),
                'delay_date_from': __(self.delay_date_from),
                'delay_date_to': __(self.delay_date_to),
                'payroll_report_sheet_id': self.id,
            }
            self.env['employee.sheet.report'].create(vals)

    @api.one
    def deep_update(self):
        emp_ids = [e.employee_id.id for e in self.employee_report_ids]
        days = self.env['working.days'].search(
            [('employee_id', 'in', emp_ids), ('date', '>=', __(self.delay_date_from)), ('date', '<=', __(self.delay_date_to))])
        days.get_ded_ovt()

    @api.one
    def action_confirm(self):
        # self.deep_update()
        self.state = 'confirmed'

    @api.one
    def action_sent_emails(self):
        if not self.emails_sent:
            self.state = 'sent_emails'
            for e in self.employee_report_ids:
                if not e.employee_id.is_external_labour:
                    e.send = not e.send
            self.emails_sent = True
        else:
            self.state = 'reviewed'

    @api.one
    def action_review(self):
        self.state = 'reviewed'

    @api.one
    def action_reset(self):
        self.state = 'new'


class hr_payslip_run(models.Model):
    _inherit = 'hr.payslip.run'

    sheet_report_id = m2o_field('payroll.sheet.report', 'Payroll sheet report')


class Employee(models.Model):
    _inherit = "hr.employee"

    exclude_from_fingerprint = bool_field('Exclude from Fingerprint')
    working_time_id = m2o_field('resource.calendar', 'Working Schedule')

    @api.multi
    def _inverse_manual_attendance(self):
        pass

class Holidays(models.Model):
    _inherit = "hr.leave"

    @api.one
    def write(self, vals):
        # self.check_valid_period(vals.get('date_from', False), vals.get('date_to', False))
        res = super(Holidays, self).write(vals)
        days = self.env['working.days'].search(
            [('employee_id', '=', self.employee_id.id), ('date', '>=', __(self.date_from)), ('date', '<=', __(self.date_to))])
        days.get_ded_ovt()
        return res

    @api.model
    def create(self, vals):
        self.check_valid_period(vals.get('date_from', False), vals.get('date_to', False))
        return super(Holidays, self).create(vals)

    def check_valid_period(self, date_from=False, date_to=False):
        if self.employee_id.is_external_labour:
            return
        date_from = date_from or __(self.date_from)
        date_to = date_to or __(self.date_to)
        confirmed_report_sheet = self.env['employee.sheet.report'].search(
            ['|', '|',
             '&', ('delay_date_from', '<=', date_from), ('delay_date_to', '>=', date_from),
             '&', ('delay_date_from', '<=', date_to), ('delay_date_to', '>=', date_to),
             '&', ('delay_date_from', '>=', date_from), ('delay_date_to', '<=', date_to),
             ('state', 'in', ['confirmed', 'reviewed']), ])
        if confirmed_report_sheet:
            confirmed_report_sheet = confirmed_report_sheet[0]
            raise ValidationError(_("Sorry you can't made any changes on Leaves in this period\n- from %s to %s\nBecause Payroll sheet is closed" % (
                __(confirmed_report_sheet.delay_date_from), __(confirmed_report_sheet.delay_date_to))))
