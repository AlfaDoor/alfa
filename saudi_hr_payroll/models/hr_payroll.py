# -*- coding: utf-8 -*-

from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
import time
import calendar
from dateutil.relativedelta import relativedelta
from odoo.tools import __
import logging

_logger = logging.getLogger(__name__)


class hr_payslip(models.Model):
    _name = "hr.payslip"
    _inherit = ["hr.payslip", 'mail.thread']
    _order = "id desc"

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

    month = fields.Selection(_PERIOD, _('Month'), default=lambda s: time.strftime("%m"))
    year = fields.Integer(_('Year'), default=lambda s: float(time.strftime('%Y')))

    total_loans = fields.Float('Total Loans', readonly=True)
    current_total_loans = fields.Float('Total Loans', readonly=True)

    total_paid_amount = fields.Float('Total paid', readonly=True)
    current_total_paid_amount = fields.Float('Total paid', readonly=True)

    remaining_amount = fields.Float('Remaining Amount', readonly=True)
    current_remaining_amount = fields.Float('Remaining Amount', readonly=True)

    deduct_this_month = fields.Float('Deduct this Month')
    sponsor = fields.Many2one(related='employee_id.coach_id', store=True)
    loans_data_reviewed = fields.Boolean('Other payments / Deduction reviewed')
    in_trial_period = fields.Boolean('In trail period', compute='in_trial_period_')
    conflict_trial_period = fields.Boolean('Conflict trail period', compute='in_trial_period_')
    number_of_days = fields.Integer('Number of days according to payslip date', compute='_compute_number_of_days')
    excluded_days_old = fields.Integer('Excluded days due to old payslip', compute='_compute_excluded_days_old')
    excluded_days_leaves = fields.Integer('Excluded days due to Leaves', compute='_compute_excluded_days_leaves')
    total_excluded_days = fields.Integer('Total days Excluded', compute='_compute_total_excluded_days')
    days_in_payslip = fields.Integer('Days included in payslip', compute='_compute_number_of_days')
    employee_english_name = fields.Char("Employee English Name", related="employee_id.employee_english_name", readonly=True)
    reviewed_by = fields.Many2one('res.users', 'Reviewed By')
    reviewed_date = fields.Date('Reviewed Date')
    final_reviewed_by = fields.Many2one('res.users', 'Final Review By')
    final_reviewed_date = fields.Date('Final Review Date')
    confirmed_by = fields.Many2one('res.users', 'Confirmed By')
    confirmation_date = fields.Date('Confirmation Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('Reviewed', 'Reviewed'),
        ('Final Reviewed', 'Final Reviewed'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], 'Status', index=True, readonly=True, copy=False, default='draft',
        help='* When the payslip is created the status is \'Draft\'.\
            \n* If the payslip is under verification, the status is \'Waiting\'. \
            \n* If the payslip is confirmed then status is set to \'Done\'.\
            \n* When user cancel payslip the status is \'Rejected\'.')
    # //////////////////////// Rules Fields ////////////////////////////////////////////////////////////////
    rule_basic = fields.Float('Basic Salary')
    rule_house_allowance = fields.Float('House Allowance')
    rule_transportation_allowance = fields.Float('Transportation Allowance')
    rule_food_allowance = fields.Float('Food allowance')
    rule_phone_allowance = fields.Float('Phone Allowance')
    rule_other_llowance = fields.Float('Other Allowance')
    rule_gross = fields.Float('Gross')
    rule_loan_deducted = fields.Float('Loan Deducted')
    rule_deductions_violations = fields.Float('Deductions / Violations')
    rule_employee_rewards = fields.Float('Employee Rewards')
    rule_absence_deducted = fields.Float('Absence Deductions')
    rule_gosi_employee_share = fields.Float('Gosi Employee share')
    rule_total_deductions = fields.Float('Total deductions')
    rule_net = fields.Float('Net')
    rule_gosi_company_share = fields.Float('Gosi Company share')
    payslip_error = fields.Boolean('incorrect payslip')
    branch_id = fields.Many2one('hr.branch', 'Branch', related="employee_id.branch_id", store=True, readonly=True)
    department_id = fields.Many2one('hr.department', 'Department', related="employee_id.department_id", store=True, readonly=True)
    trial_days = fields.Integer("Number Of Days In Trial Period", compute='_compute_conflict_days')
    after_trial_days = fields.Integer("Number Of Days In After Trial Period", compute='_compute_conflict_days')
    leaves_count = fields.Float('Current annual leave balance')
    negative_salary = fields.Boolean('Accept negative net salary')
    trial_excluded_days = fields.Integer('Trial days Excluded', compute='_compute_trial_excluded_days')
    trial_days_payslip = fields.Integer("Number Of Days In Trial Period In Payslip", compute='_compute_conflict_days')
    after_trial_days_payslip = fields.Integer("Number Of Days In After Trial Period  In Payslip", compute='_compute_conflict_days')
    # journal_id = fields.Many2one(required=False, default=lambda s: s.env['account.journal'].search([]) and s.env['account.journal'].search([])[0].id or False)

    # /////////////////// Smart Buttons /////////////////////////////////////////////////////////////
    count_old_payslips = fields.Float('Employee Old payslips', compute='get_count_old_payslips')
    payment_method = fields.Selection(related='employee_id.salary_paid', store=True)
    reviewed = fields.Boolean('Reviewed')
    join_date = fields.Date(related='contract_id.start_work')
    is_variance = fields.Boolean(default=False)

    def _check_dates(self):
        return True

    _constraints = [(_check_dates, "Payslip 'Date From' must be before 'Date To'.", [])]

    @api.one
    @api.depends('date_from', 'date_to', 'conflict_trial_period', 'contract_id')
    def _compute_conflict_days(self):
        if self.conflict_trial_period:
            start_date = __(self.date_from)
            end_date = __(self.contract_id.trial_date_end)
            periods_by_month = self.devide_period_by_month(start_date, end_date)
            if len(periods_by_month) == 1:
                number_of_days = self.get_slip_month_days(periods_by_month[0]['from'], periods_by_month[0]['to'])
            elif len(periods_by_month) > 1:
                number_of_days = self.get_slip_month_days(periods_by_month[0]['from'], periods_by_month[0]['to']) + self.get_slip_month_days(
                    periods_by_month[-1]['from'], periods_by_month[-1]['to']) + ((len(periods_by_month) - 2) * 30)
            else:
                number_of_days = 0
            self.trial_days = number_of_days
        elif self.in_trial_period:
            self.trial_days = self.number_of_days
        else:
            self.trial_days = 0
        self.after_trial_days = self.number_of_days - self.trial_days
        self.trial_days_payslip = self.trial_days - self.trial_excluded_days
        self.after_trial_days_payslip = self.days_in_payslip - self.trial_days_payslip

    @api.one
    def get_count_old_payslips(self):
        self.count_old_payslips = self.env['hr.payslip'].search_count([('employee_id', '=', self.employee_id.id), ('id', '!=', self.id)])

    @api.multi
    def open_old_payslips(self):
        return {
            'domain': [('employee_id', '=', self.employee_id.id), ('id', '!=', self.id)],
            'name': _('Employee Old payslips'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    # ///////////////////////////////////////////////////////////////////////////////////////////////////

    @api.onchange('employee_english_name')
    def set_leaves_count(self):
        self.leaves_count = self.employee_id.leaves_count

    @api.one
    def review_payslip(self):
        if not self.contract_id.hr_approval:
            raise ValidationError(
                'Not Allowed !!\n Dear HR team,\n You are not allowed to Review or Final Review or confirm this payslip because HR manager did not confirm employee ( %s ) contract.' % self.employee_id.name)
        # self.sudo().compute_sheet()
        self.write({'state': 'Reviewed','update_no':True,'reviewed_by': self.env.uid, 'reviewed_date': datetime.now().strftime('%Y-%m-%d')})
        body = "Document Reviewed"
        self.message_post(body=body, message_type='email')

    @api.one
    def final_review_payslip(self):
        if not self.contract_id.hr_approval:
            raise ValidationError(
                'Not Allowed !!\n Dear HR team,\n You are not allowed to Review or Final Review or confirm this payslip because HR manager did not confirm employee ( %s ) contract.' % self.employee_id.name)
        # self.sudo().compute_sheet()
        self.write({'state': 'Final Reviewed', 'final_reviewed_by': self.env.uid, 'final_reviewed_date': datetime.now().strftime('%Y-%m-%d')})
        body = "Document Final Reviewed"
        self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def _compute_rules_fields(self):
        self.rule_basic = sum([l.total for l in self.line_ids if l.salary_rule_id.category_id.id == self.env.ref('hr_payroll.BASIC').id])
        self.rule_house_allowance = sum([l.total for l in self.line_ids if l.salary_rule_id.category_id.id == self.env.ref('saudi_hr_payroll.HOUSEALL').id])
        self.rule_transportation_allowance = sum([l.total for l in self.line_ids if l.salary_rule_id.category_id.id == self.env.ref('saudi_hr_payroll.TRANSEALL').id])
        self.rule_phone_allowance = sum([l.total for l in self.line_ids if l.code == 'PHOALL'])
        self.rule_food_allowance = sum([l.total for l in self.line_ids if l.code == 'FODALL'])
        self.rule_other_llowance = sum([l.total for l in self.line_ids if l.code == 'OTHERALL'])
        self.rule_gross = sum([l.total for l in self.line_ids if l.code == 'GROSS'])
        self.rule_loan_deducted = sum([l.total for l in self.line_ids if l.code == 'LOAN'])
        self.rule_deductions_violations = sum([l.total for l in self.line_ids if l.code == 'DEDUCT'])
        self.rule_employee_rewards = sum([l.total for l in self.line_ids if l.code == 'REWARD'])
        self.rule_absence_deducted = sum([l.total for l in self.line_ids if l.code == 'ABSENCE'])
        self.rule_gosi_employee_share = sum([l.total for l in self.line_ids if l.code == 'GOSIE'])
        self.rule_total_deductions = sum([l.total for l in self.line_ids if l.code == 'DED'])
        self.rule_net = sum([l.total for l in self.line_ids if l.code == 'NET_RULE'])
        self.rule_gosi_company_share = sum([l.total for l in self.line_ids if l.code == 'GOSIC'])
        actual_net = self.rule_basic + self.rule_house_allowance + self.rule_transportation_allowance + self.rule_phone_allowance + self.rule_other_llowance + self.rule_food_allowance + \
                     self.rule_employee_rewards + self.rule_loan_deducted + self.rule_deductions_violations + self.rule_absence_deducted - self.rule_gosi_employee_share
        if abs(actual_net - self.rule_net) > .4:
            self.payslip_error = True
        else:
            self.payslip_error = False

    @api.onchange('month', 'year')
    def onchange_period(self):
        if self.month and self.year:
            start_end = calendar.monthrange(self.year, int(self.month))
            self.date_from = str(self.year) + '-' + self.month + '-01'
            self.date_to = str(self.year) + '-' + self.month + '-' + str(start_end[1])

    @api.multi
    def compute_sheet(self):
        if self._context.get('without_compute_sheet', False):
            return
        _logger.info("########### Compute sheet: %s #############################" % self.employee_id.display_name)
        for rec in self:
            rec.leaves_count = rec.employee_id.leaves_count
        res = super(hr_payslip, self).compute_sheet()
        ref = self.env.ref
        rules_to_update_rate = [
            'saudi_hr_payroll.basic_salary_rule',
            'saudi_hr_payroll.house_salary_rule',
            'saudi_hr_payroll.transportation_salary_rule',
            'saudi_hr_payroll.phone_salary_rule',
            'saudi_hr_payroll.food_salary_rule',
            'saudi_hr_payroll.other_salary_rule',
            'saudi_hr_payroll.hr_rule_gross',
            'asc_hr.Food_salary_rule',
            'asc_hr.work_salary_rule',
        ]
        rules_to_update_rate_ids = [ref(rule).id for rule in rules_to_update_rate if ref(rule, False)]

        for rec in self:
            if not rec.conflict_trial_period:
                rate = rec.get_moth_percentage() * 100
                for line in rec.line_ids:
                    if line.salary_rule_id.id in rules_to_update_rate_ids:
                        line.rate = rate
            rec._compute_rules_fields()
        return res

    def devide_period_by_month(self, date_from, date_to):
        DATE_FORMAT = "%Y-%m-%d"
        date_from_date = datetime.strptime(date_from.split(' ')[0], DATE_FORMAT)
        date_to_date = datetime.strptime(date_to.split(' ')[0], DATE_FORMAT)
        periods = []
        period = {}
        if date_from_date > date_to_date:
            return periods
        period['from'] = date_from_date.strftime(DATE_FORMAT)
        if date_from_date.month == date_to_date.month and date_from_date.year == date_to_date.year:
            period['to'] = date_to_date.strftime(DATE_FORMAT)
            periods.append(period)
            return periods
        else:
            start_end = calendar.monthrange(date_from_date.year, int(date_from_date.month))
            month_last_day = str(date_from_date.year) + '-' + str(date_from_date.month) + '-' + str(start_end[1])

            next_month = date_from_date + relativedelta(months=1)
            next_month_start = str(next_month.year) + '-' + str(next_month.month) + '-01'
            period['to'] = month_last_day
            periods.append(period)
            return periods + self.devide_period_by_month(next_month_start, date_to)

    def get_slip_month_days(self, date_from, date_to):

        start_date = datetime.strptime(date_from, "%Y-%m-%d")
        end_date = datetime.strptime(date_to, "%Y-%m-%d")
        duration = relativedelta(end_date, start_date)

        month_start = date(start_date.year, start_date.month, 1)
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        month_end = date(start_date.year, start_date.month, last_day)
        if duration.days in [27, 28, 30] and (start_date.month == end_date.month and start_date.day == month_start.day and end_date.day == month_end.day):
            duration_days = 29
        else:
            duration_days = duration.days
        number_of_days = (duration.years * 12 + duration.months) * 30 + duration_days + 1
        return number_of_days

    @api.one
    @api.depends('date_from', 'date_to', 'excluded_days_old', 'excluded_days_leaves')
    def _compute_number_of_days(self):
        start_work = __(self.employee_id.contract_id.first_effective_notice.payslip_date) or __(self.employee_id.contract_id.start_work)
        number_of_days = 0
        if start_work and start_work > __(self.date_to):
            self.number_of_days = self.days_in_payslip = 0
            return
        elif start_work and __(self.date_from) < start_work <= __(self.date_to):
            start_date = start_work
        else:
            start_date = __(self.date_from)

        end_date = __(self.date_to)
        if start_date and end_date:
            periods_by_month = self.devide_period_by_month(start_date, end_date)
            if len(periods_by_month) == 1:
                number_of_days = self.get_slip_month_days(periods_by_month[0]['from'], periods_by_month[0]['to'])
            elif len(periods_by_month) > 1:
                number_of_days = self.get_slip_month_days(periods_by_month[0]['from'], periods_by_month[0]['to']) + self.get_slip_month_days(
                    periods_by_month[-1]['from'], periods_by_month[-1]['to']) + ((len(periods_by_month) - 2) * 30)
            else:
                number_of_days = 0
        if self.is_variance == True:
            self.number_of_days = number_of_days + 2
        else:
            self.number_of_days = number_of_days
        self.days_in_payslip = self.number_of_days - self.total_excluded_days


    @api.one
    @api.depends('date_from', 'date_to', 'employee_id')
    def _compute_excluded_days_old(self):
        if self.employee_id and self.date_from and self.date_to:
            if self.id:
                domain = [
                    ('date_from', '<=', __(self.date_to)),
                    ('date_to', '>=', __(self.date_from)),
                    ('employee_id', '=', self.employee_id.id),
                    ('id', '!=', self.id),
                    ('state', '=', 'done'),
                ]
            else:
                domain = [
                    ('date_from', '<=', __(self.date_to)),
                    ('date_to', '>=', __(self.date_from)),
                    ('employee_id', '=', self.employee_id.id),
                    ('state', '=', 'done'),
                ]
            old_payslips = self.search(domain)
            conflicts = []
            intersections = []
            for old_payslip in old_payslips:
                vals = {'start': __(old_payslip.date_from), 'end': __(old_payslip.date_to)}
                conflicts.append(vals)

            for conflict in conflicts:
                if conflict['start'] > __(self.date_from):
                    intersection_start = conflict['start']
                else:
                    intersection_start = __(self.date_from)
                if conflict['end'] < __(self.date_to):
                    intersection_end = conflict['end']
                else:
                    intersection_end = __(self.date_to)
                is_merged = False
                for intersection in intersections:
                    if intersection['start'] <= intersection_end and intersection['end'] >= intersection_start:
                        if intersection['start'] > intersection_start:
                            intersection['start'] = intersection_start
                        if intersection['end'] < intersection_end:
                            intersection['end'] = intersection_end
                        is_merged = True
                if not is_merged:
                    intersections.append({'start': intersection_start, 'end': intersection_end})

            excluded_old_count = 0
            for intersection in intersections:
                number_of_days = self.get_slip_month_days(intersection['start'], intersection['end'])
                # start_date = datetime.strptime(intersection['start'], "%Y-%m-%d")
                # end_date = datetime.strptime(intersection['end'], "%Y-%m-%d")
                # /////////////////////////////////////////////////////////////////////////////////////
                # duration = relativedelta(end_date, start_date)
                # if duration.days == 30 :
                #     duration_days = 29
                # else:
                #     duration_days = duration.days
                # number_of_days = (duration.years * 12 + duration.months) * 30 + duration_days +1
                # /////////////////////////////////////////////////////////////////////////////////////
                excluded_old_count += number_of_days
            self.excluded_days_old = excluded_old_count

    @api.one
    @api.depends('date_from', 'date_to', 'employee_id')
    def _compute_excluded_days_leaves(self):
        if self.employee_id and self.date_from and self.date_to:
            domain = [
                ('date_from', '<=', __(self.date_to)),
                ('date_to', '>=', __(self.date_from)),
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'validate'),
            ]
            old_leaves = self.env['hr.leave'].search(domain)
            conflicts = []
            intersections = []
            for old_leave in old_leaves:
                if old_leave.reconciliation_method == 'Stop payslip during leave and use leave reconciliation':
                    start_datetime = datetime.strptime(__(old_leave.date_from, True), "%Y-%m-%d %H:%M:%S")
                    start_date = start_datetime.strftime('%Y-%m-%d')
                    end_datetime = datetime.strptime(__(old_leave.date_to, True), "%Y-%m-%d %H:%M:%S")
                    end_date = end_datetime.strftime('%Y-%m-%d')
                    vals = {'start': start_date, 'end': end_date}
                    conflicts.append(vals)

            for conflict in conflicts:
                if conflict['start'] > __(self.date_from):
                    intersection_start = conflict['start']
                else:
                    intersection_start = __(self.date_from)
                if conflict['end'] < __(self.date_to):
                    intersection_end = conflict['end']
                else:
                    intersection_end = __(self.date_to)
                is_merged = False
                for intersection in intersections:
                    if intersection['start'] <= intersection_end and intersection['end'] >= intersection_start:
                        if intersection['start'] > intersection_start:
                            intersection['start'] = intersection_start
                        if intersection['end'] < intersection_end:
                            intersection['end'] = intersection_end
                        is_merged = True
                if not is_merged:
                    intersections.append({'start': intersection_start, 'end': intersection_end})
            excluded_leaves_count = 0
            for intersection in intersections:
                number_of_days = self.get_slip_month_days(intersection['start'], intersection['end'])
                # start_date = datetime.strptime(intersection['start'], "%Y-%m-%d")
                # end_date = datetime.strptime(intersection['end'], "%Y-%m-%d")
                # # /////////////////////////////////////////////////////////////////////////////////////
                # duration = relativedelta(end_date, start_date)
                # if duration.days == 30 :
                #     duration_days = 29
                # else:
                #     duration_days = duration.days
                # number_of_days = (duration.years * 12 + duration.months) * 30 + duration_days +1
                # /////////////////////////////////////////////////////////////////////////////////////
                excluded_leaves_count += number_of_days
            self.excluded_days_leaves = excluded_leaves_count

    @api.one
    @api.depends('date_from', 'date_to', 'employee_id')
    def _compute_total_excluded_days(self):
        if self.employee_id and self.date_from and self.date_to:
            if self.id:
                domain = [
                    ('date_from', '<=', __(self.date_to)),
                    ('date_to', '>=', __(self.date_from)),
                    ('employee_id', '=', self.employee_id.id),
                    ('id', '!=', self.id),
                    ('state', '=', 'done'),
                ]
            else:
                domain = [
                    ('date_from', '<=', __(self.date_to)),
                    ('date_to', '>=', __(self.date_from)),
                    ('employee_id', '=', self.employee_id.id),
                    ('state', '=', 'done'),
                ]
            old_payslips = self.search(domain)
            # ////////////////////////////////////////////////////////////////////////////
            leaves_domain = [
                ('date_from', '<=', __(self.date_to)),
                ('date_to', '>=', __(self.date_from)),
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'validate'),
            ]
            old_leaves = self.env['hr.leave'].search(leaves_domain)
            # //////////////////////////////////////////////////////////////////////////////////
            conflicts = []
            intersections = []
            # /////////////////////////////////////////////////////////////////////////////////
            for old_payslip in old_payslips:
                vals = {'start': __(old_payslip.date_from), 'end': __(old_payslip.date_to)}
                conflicts.append(vals)
            # /////////////////////////////////////////////////////////////////////////////////
            for old_leave in old_leaves:
                if old_leave.reconciliation_method == 'Stop payslip during leave and use leave reconciliation':
                    start_datetime = datetime.strptime(__(old_leave.date_from, True), "%Y-%m-%d %H:%M:%S")
                    start_date = start_datetime.strftime('%Y-%m-%d')
                    end_datetime = datetime.strptime(__(old_leave.date_to, True), "%Y-%m-%d %H:%M:%S")
                    end_date = end_datetime.strftime('%Y-%m-%d')
                    vals = {'start': start_date, 'end': end_date}
                    conflicts.append(vals)
            # ////////////////////////////////////////////////////////////////////////////////////
            for conflict in conflicts:
                if conflict['start'] > __(self.date_from):
                    intersection_start = conflict['start']
                else:
                    intersection_start = __(self.date_from)
                if conflict['end'] < __(self.date_to):
                    intersection_end = conflict['end']
                else:
                    intersection_end = __(self.date_to)
                is_merged = False
                for intersection in intersections:
                    if intersection['start'] <= intersection_end and intersection['end'] >= intersection_start:
                        if intersection['start'] > intersection_start:
                            intersection['start'] = intersection_start
                        if intersection['end'] < intersection_end:
                            intersection['end'] = intersection_end
                        is_merged = True
                if not is_merged:
                    intersections.append({'start': intersection_start, 'end': intersection_end})
            excluded_total_count = 0
            for intersection in intersections:
                number_of_days = self.get_slip_month_days(intersection['start'], intersection['end'])
                # start_date = datetime.strptime(intersection['start'], "%Y-%m-%d")
                # end_date = datetime.strptime(intersection['end'], "%Y-%m-%d")
                # # /////////////////////////////////////////////////////////////////////////////////////
                # duration = relativedelta(end_date, start_date)
                # if duration.days == 30 :
                #     duration_days = 29
                # else:
                #     duration_days = duration.days
                # number_of_days = (duration.years * 12 + duration.months) * 30 + duration_days +1
                # /////////////////////////////////////////////////////////////////////////////////////
                excluded_total_count += number_of_days
            self.total_excluded_days = excluded_total_count

    @api.one
    @api.depends('date_from', 'contract_id', 'employee_id')
    def _compute_trial_excluded_days(self):
        if self.employee_id and self.date_from and self.contract_id.trial_date_end:
            if self.id:
                domain = [
                    ('date_from', '<=', __(self.contract_id.trial_date_end)),
                    ('date_to', '>=', __(self.date_from)),
                    ('employee_id', '=', self.employee_id.id),
                    ('id', '!=', self.id),
                    ('state', '=', 'done'),
                ]
            else:
                domain = [
                    ('date_from', '<=', __(self.contract_id.trial_date_end)),
                    ('date_to', '>=', __(self.date_from)),
                    ('employee_id', '=', self.employee_id.id),
                    ('state', '=', 'done'),
                ]
            old_payslips = self.search(domain)
            # ////////////////////////////////////////////////////////////////////////////
            leaves_domain = [
                ('date_from', '<=', __(self.contract_id.trial_date_end)),
                ('date_to', '>=', __(self.date_from)),
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'validate'),
            ]
            old_leaves = self.env['hr.leave'].search(leaves_domain)
            # //////////////////////////////////////////////////////////////////////////////////
            conflicts = []
            intersections = []
            # /////////////////////////////////////////////////////////////////////////////////
            for old_payslip in old_payslips:
                vals = {'start': __(old_payslip.date_from), 'end': __(old_payslip.date_to)}
                conflicts.append(vals)
            # /////////////////////////////////////////////////////////////////////////////////
            for old_leave in old_leaves:
                if old_leave.reconciliation_method == 'Stop payslip during leave and use leave reconciliation':
                    start_datetime = datetime.strptime(__(old_leave.date_from, True), "%Y-%m-%d %H:%M:%S")
                    start_date = start_datetime.strftime('%Y-%m-%d')
                    end_datetime = datetime.strptime(__(old_leave.date_to, True), "%Y-%m-%d %H:%M:%S")
                    end_date = end_datetime.strftime('%Y-%m-%d')
                    vals = {'start': start_date, 'end': end_date}
                    conflicts.append(vals)
            # ////////////////////////////////////////////////////////////////////////////////////
            for conflict in conflicts:
                if conflict['start'] > __(self.date_from):
                    intersection_start = conflict['start']
                else:
                    intersection_start = __(self.date_from)
                if conflict['end'] < __(self.date_to):
                    intersection_end = conflict['end']
                else:
                    intersection_end = __(self.date_to)
                is_merged = False
                for intersection in intersections:
                    if intersection['start'] <= intersection_end and intersection['end'] >= intersection_start:
                        if intersection['start'] > intersection_start:
                            intersection['start'] = intersection_start
                        if intersection['end'] < intersection_end:
                            intersection['end'] = intersection_end
                        is_merged = True
                if not is_merged:
                    intersections.append({'start': intersection_start, 'end': intersection_end})
            excluded_total_count = 0
            for intersection in intersections:
                number_of_days = self.get_slip_month_days(intersection['start'], intersection['end'])
                # start_date = datetime.strptime(intersection['start'], "%Y-%m-%d")
                # end_date = datetime.strptime(intersection['end'], "%Y-%m-%d")
                # # /////////////////////////////////////////////////////////////////////////////////////
                # duration = relativedelta(end_date, start_date)
                # if duration.days == 30 :
                #     duration_days = 29
                # else:
                #     duration_days = duration.days
                # number_of_days = (duration.years * 12 + duration.months) * 30 + duration_days +1
                # /////////////////////////////////////////////////////////////////////////////////////
                excluded_total_count += number_of_days
            self.trial_excluded_days = excluded_total_count

    @api.model
    def get_moth_percentage(self):
        return self.days_in_payslip / 30.00

    @api.one
    @api.depends('date_from', 'date_to', 'contract_id')
    def in_trial_period_(self):
        if __(self.contract_id.trial_date_end) and __(self.date_to) <= __(self.contract_id.trial_date_end):
            self.in_trial_period = True
        else:
            self.in_trial_period = False

        if __(self.contract_id.trial_date_end) and __(self.date_from) <= __(self.contract_id.trial_date_end) < __(self.date_to):
            self.conflict_trial_period = True
        else:
            self.conflict_trial_period = False

    @api.model
    def BSC_rule(self):
        if self.conflict_trial_period:
            res = (self.contract_id.trial_wage * self.trial_days_payslip / 30) + (self.contract_id.basic_salary * self.after_trial_days_payslip / 30)
            return res

        basic_salary = not self.in_trial_period and self.contract_id.basic_salary or self.contract_id.trial_wage
        res = basic_salary  # * self.get_moth_percentage()
        return res

    @api.model
    def HOUSEALL_rule(self):
        if self.conflict_trial_period:
            res = (self.contract_id.trial_house_allowance_amount * self.trial_days_payslip / 30) + (
                    self.contract_id.house_allowance_amount * self.after_trial_days_payslip / 30)
            return res

        house_allowance_amount = not self.in_trial_period and self.contract_id.house_allowance_amount or self.contract_id.trial_house_allowance_amount
        return house_allowance_amount  # * self.get_moth_percentage()

    @api.model
    def TRANSALL_rule(self):
        if self.conflict_trial_period:
            res = (self.contract_id.trial_transportation_allowance_amount * self.trial_days_payslip / 30) + (
                    self.contract_id.transportation_allowance_amount * self.after_trial_days_payslip / 30)
            return res

        transportation_allowance_amount = not self.in_trial_period and self.contract_id.transportation_allowance_amount or self.contract_id.trial_transportation_allowance_amount
        return transportation_allowance_amount  # * self.get_moth_percentage()

    @api.model
    def PHOALL_rule(self):
        if self.conflict_trial_period:
            res = (self.contract_id.trial_phone_allowance_amount * self.trial_days_payslip / 30) + (
                    self.contract_id.phone_allowance_amount * self.after_trial_days_payslip / 30)
            return res

        phone_allowance_amount = not self.in_trial_period and self.contract_id.phone_allowance_amount or self.contract_id.trial_phone_allowance_amount
        return phone_allowance_amount  # * self.get_moth_percentage()

    @api.model
    def FODALL_rule(self):
        if self.conflict_trial_period:
            res = (self.contract_id.trial_food_allowance_amount * self.trial_days_payslip / 30) + (
                    self.contract_id.food_allowance_amount * self.after_trial_days_payslip / 30)
            return res

        food_allowance_amount = not self.in_trial_period and self.contract_id.food_allowance_amount or self.contract_id.trial_food_allowance_amount
        return food_allowance_amount  # * self.get_moth_percentage()

    @api.model
    def OTHERALL(self):
        if self.conflict_trial_period:
            res = (self.contract_id.trial_other_allowance * self.trial_days_payslip / 30) + (
                    self.contract_id.other_allowance * self.after_trial_days_payslip / 30)
            return res

        other_allowance = not self.in_trial_period and self.contract_id.other_allowance or self.contract_id.trial_other_allowance
        return other_allowance  # * self.get_moth_percentage()

    @api.model
    def net_rule(self):
        if self.conflict_trial_period:
            net_gross = self.net_gross()
            print('1',net_gross)
        else:
            print(self.net_gross())
            print(self.get_moth_percentage())
            net_gross = self.net_gross() * self.get_moth_percentage()
            print('2',net_gross)
        total_deductions = self.total_deductions()
        print('3',total_deductions)
        return net_gross + total_deductions  # * self.get_moth_percentage()

    @api.model
    def total_deductions(self):
        return 0.0

    @api.model
    def net_gross(self):
        total_gross = self.BSC_rule() + self.HOUSEALL_rule() + self.TRANSALL_rule() + self.PHOALL_rule() + self.FODALL_rule() + self.OTHERALL()
        return total_gross  # * self.get_moth_percentage()

    @api.model
    def get_rule_code_dict(self):
        pass

    @api.multi
    def refund_sheet(self):
        for record in self:
            msg = _(
                "Attention !! \n If you created a refund for this payslip, your system will create a new payslip for the same employee and same period with negative values to reverse old payslip effect.Are you sure that you want to continue ")
            return self.env.user.show_dialogue(msg, 'hr.payslip', 'refund_sheet_modified', record.id)

    def refund_sheet_modified(self):
        raise UserError('( loan - deductions - rewards - leaves integration ) while reverse payslip still under development')
        res = super(hr_payslip, self).refund_sheet()
        return res

    @api.multi
    def action_draft(self):
        for record in self:
            record.write({'state': 'draft','update_no':False})
        return {}

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.payslip_run_id and not self._context.get('patch_delete', False):
                raise ValidationError(_(
                    "Not allowed !! \n Not allowed to delete this payslip, because it is automatically generated from payslip batch. you still have the option to refuse it (cancel payslip)."))
        return super(hr_payslip, self).unlink()

    @api.model
    def create(self, vals):
        if hasattr(self, 'journal_id'):
            vals['journal_id'] = self.env['account.journal'].search([])[0].id
        res = super(hr_payslip, self).create(vals)
        res.struct_id = res.contract_id.struct_id.id
        return res


class hr_payslip_run(models.Model):
    _name = 'hr.payslip.run'
    _inherit = ['hr.payslip.run', 'mail.thread']
    _order = "id desc"

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

    month = fields.Selection(_PERIOD, _('Month'), default=lambda s: time.strftime("%m"))
    year = fields.Integer(_('Year'), default=lambda s: float(time.strftime('%Y')))
    count_payslips = fields.Integer('Count payslips', compute='_compute_count_payslips')
    attachment_ids = fields.One2many('hr.payslip.run.attaches', 'batch_id', 'Attachments')

    # //////////////////////// Rules Fields ////////////////////////////////////////////////////////////////
    rule_basic = fields.Float('Total Basic Salary', compute='_compute_rules_fields')
    rule_house_allowance = fields.Float('Total House Allowance', compute='_compute_rules_fields')
    rule_transportation_allowance = fields.Float('Total Transportation Allowance', compute='_compute_rules_fields')
    rule_phone_allowance = fields.Float('Total Phone Allowance', compute='_compute_rules_fields')
    rule_other_llowance = fields.Float('Total Other Allowance', compute='_compute_rules_fields')
    rule_gross = fields.Float('Total Gross', compute='_compute_rules_fields')
    rule_loan_deducted = fields.Float('Total Loan Deducted', compute='_compute_rules_fields')
    rule_deductions_violations = fields.Float('Total Deductions / Violations', compute='_compute_rules_fields')
    rule_employee_rewards = fields.Float('Total Employee Rewards', compute='_compute_rules_fields')
    rule_gosi_employee_share = fields.Float('Total Gosi Employee share', compute='_compute_rules_fields')
    rule_total_deductions = fields.Float('Total Total deductions', compute='_compute_rules_fields')
    rule_net = fields.Float('Total Net', compute='_compute_rules_fields')
    rule_gosi_company_share = fields.Float('Total Gosi Company share', compute='_compute_rules_fields')
    reviewed_by = fields.Many2one('res.users', 'Reviewed By')
    reviewed_date = fields.Date('Reviewed Date')
    final_reviewed_by = fields.Many2one('res.users', 'Final Review By')
    final_reviewed_date = fields.Date('Final Review Date')
    confirmed_by = fields.Many2one('res.users', 'Confirmed By')
    confirmation_date = fields.Date('Confirmation Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('Reviewed', 'Reviewed'),
        ('Final Reviewed', 'Final Reviewed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], 'Status', index=True, readonly=True, copy=False)
    note = fields.Html('Notes')
    is_live = fields.Boolean('Is Live', compute='_compute_is_live')

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state == 'draft':
                if rec.slip_ids:
                    not_draft_payslips = self.env['hr.payslip'].search([('payslip_run_id', '=', rec.id), ('state', '!=', 'draft')])
                    if not_draft_payslips:
                        raise ValidationError(
                            "Not allowed !! \n Dear, you are not allowed to delete this payslip batch because your system found that there is some employee payslips which generated automatically through this batch. in order to delete this batch, ( batch status must be draft ) and ( all employee payslip generated through this batch must be draft).")
                    else:
                        for slip in rec.slip_ids:
                            ctx = dict(self._context.copy(), patch_delete=True)
                            slip.with_context(ctx).unlink()
            else:
                raise ValidationError("Not allowed !! \n You are allowed to delete ( Draft ) payslip batch.")
        return super(hr_payslip_run, self).unlink()

    @api.model
    def create(self, vals):
        res = super(hr_payslip_run, self).create(vals)

        # /////////////  send mail custom notification  /////////////////////////////////////////////
        # partners_ids = [6, 7]
        #
        # body_html = '''
        #     <p style="margin-block-start:0px;direction: rtl;"><b><font style="font-size: 18px;">تم اصدار الرواتب عن&nbsp;شهر</font><font style="color: rgb(0, 0, 255); font-size: 18px;">&nbsp;</font><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.month}</span><span style="font-family: Arial; font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;"></span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;لسنة</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.year}</span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;"> .. نأمل منكم الدخول على النظام ومراجعة وإعتماد مسير الرواتب.</span></b></p><p style="margin-block-start:0px;"></p><p style="margin-block-start:0px;"></p><p></p><div style="direction: ltr;"><b><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;Payroll has been created for month =</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;</span><span style="color: initial; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;"><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.month}</span><span style="color: rgb(0, 0, 255); font-family: Arial; font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;"></span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;</span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">Year =&nbsp;</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.year}</span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">, Kindly login to the system and confirm the payroll.</span></span></b></div>
        #     '''
        # body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
        #     body_html, 'hr.payslip.run', [res.id], )
        # body = body and body[res.id] or False
        #
        # res.message_post(
        #     subject='مراجعة مسير الرواتب العام Payroll review',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=res.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)
        # /////////////////////////////////////////////////////////////

        return res

    @api.multi
    def cancel_payslip_run(self):
        for rec in self:
            new_payslips = self.env['hr.payslip'].search([('payslip_run_id', '=', rec.id), ('state', '=', 'draft')])
            reviewed_payslips = self.env['hr.payslip'].search([('payslip_run_id', '=', rec.id), ('state', '=', 'Reviewed')])
            final_payslips = self.env['hr.payslip'].search([('payslip_run_id', '=', rec.id), ('state', '=', 'Final Reviewed')])
            done_payslips = self.env['hr.payslip'].search([('payslip_run_id', '=', rec.id), ('state', '=', 'done')])
            cancel_payslips = self.env['hr.payslip'].search([('payslip_run_id', '=', rec.id), ('state', '=', 'cancel')])
            msg = _("Attention !! \n"
                    "This payslip batch contains ( %s ) payslips.\n"
                    "( New Payslips ) is ( %s )\n"
                    "( Reviewed Payslips ) is ( %s )\n"
                    "( Final reviewed Payslips ) is ( %s )\n"
                    "( Confirmed Payslips ) is ( %s )\n"
                    "( Refused Payslips ) is ( %s )\n"
                    "You request from your system to cancel this payslip batch, your system will try to cancel all payslips except (Confirmed payslips) will not be cancelled."
                    ) % (len(rec.slip_ids), len(new_payslips), len(reviewed_payslips), len(final_payslips), len(done_payslips), len(cancel_payslips))
            return self.env.user.show_dialogue(msg, 'hr.payslip.run', 'cancel_payslip_run_action', rec.id)

    @api.one
    def cancel_payslip_run_action(self):
        if self.slip_ids:
            for slip in self.slip_ids:
                if slip.state not in ['cancel', 'done']:
                    slip.write({'state': 'cancel'})

        self.write({'state': 'cancel'})
        body = "Document Cancelled"
        self.message_post(body=body, message_type='email')
        return {}
        pass

    @api.one
    @api.depends('month')
    def _compute_is_live(self):
        payslip_done = self.env['hr.payslip'].search([('state', '=', 'done')])
        if payslip_done:
            self.is_live = True
        else:
            self.is_live = False

    @api.one
    @api.depends('slip_ids')
    def _compute_rules_fields(self):
        rule_basic = 0
        rule_house_allowance = 0
        rule_transportation_allowance = 0
        rule_phone_allowance = 0
        rule_other_llowance = 0
        rule_gross = 0
        rule_loan_deducted = 0
        rule_deductions_violations = 0
        rule_employee_rewards = 0
        rule_gosi_employee_share = 0
        rule_total_deductions = 0
        rule_net = 0
        rule_gosi_company_share = 0
        for line in self.slip_ids:
            rule_basic += line.rule_basic
            rule_house_allowance += line.rule_house_allowance
            rule_transportation_allowance += line.rule_transportation_allowance
            rule_phone_allowance += line.rule_phone_allowance
            rule_other_llowance += line.rule_other_llowance
            rule_gross += line.rule_gross
            rule_loan_deducted += line.rule_loan_deducted
            rule_deductions_violations += line.rule_deductions_violations
            rule_employee_rewards += line.rule_employee_rewards
            rule_gosi_employee_share += line.rule_gosi_employee_share
            rule_total_deductions += line.rule_total_deductions
            rule_net += line.rule_net
            rule_gosi_company_share += line.rule_gosi_company_share

        self.rule_basic = rule_basic
        self.rule_house_allowance = rule_house_allowance
        self.rule_transportation_allowance = rule_transportation_allowance
        self.rule_phone_allowance = rule_phone_allowance
        self.rule_other_llowance = rule_other_llowance
        self.rule_gross = rule_gross
        self.rule_loan_deducted = rule_loan_deducted
        self.rule_deductions_violations = rule_deductions_violations
        self.rule_employee_rewards = rule_employee_rewards
        self.rule_gosi_employee_share = rule_gosi_employee_share
        self.rule_total_deductions = rule_total_deductions
        self.rule_net = rule_net
        self.rule_gosi_company_share = rule_gosi_company_share

    @api.one
    def _compute_count_payslips(self):
        self.count_payslips = len(self.slip_ids)

    @api.one
    def compute_batch_payslips(self):
        if self.slip_ids:
            for slip in self.slip_ids:
                if slip.state not in ['done']:
                    slip.compute_sheet()

    @api.multi
    def review_payslip_run(self):
        for rec in self:
            if not self.is_live:
                msg = _(
                    "Dear HR team, \n Congratulation, you are about to generate your first Payslip Batch, your must be sure that all employees received their salaries for all previous months, specially all employees hired on the previous month. in some cases some employees may be hired at 25 from the previous month and you agreed with the employee to include this period in next month salary ... \n Don’t worry, your system will handle these cases on all future payslip batches, but in your first payslip batch and after generating employees payslips, you must review the employees hired on the previous month and change payslip period to be started from the first hiring date and ends at the end of current month")
                return self.env.user.show_dialogue(msg, 'hr.payslip.run', 'review_payslip_run_action', rec.id)
            else:
                rec.review_payslip_run_action()

    @api.one
    def review_payslip_run_action(self):
        if self.slip_ids:
            for slip in self.slip_ids:
                if slip.state == 'draft':
                    slip.review_payslip()
        else:
            raise UserError(_(
                "Not allowed !! \n There is no payslips found! What is the data which you reviewed? kindly go to Payslip tab and click on Generate payslips, then select all employees which you want to create Payslip for them. "))
        self.write({'state': 'Reviewed', 'reviewed_by': self.env.uid, 'reviewed_date': datetime.now().strftime('%Y-%m-%d')})
        # /////////////  send mail custom notification  /////////////////////////////////////////////
        # partners_ids = [9]
        #
        # body_html = '''
        #     <p style="margin-block-start:0px;direction: rtl;"><b><font style="font-size: 18px;">تم اصدار الرواتب عن&nbsp;شهر</font><font style="color: rgb(0, 0, 255); font-size: 18px;">&nbsp;</font><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.month}</span><span style="font-family: Arial; font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;"></span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;لسنة</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.year}</span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;"> .. نأمل منكم الدخول على النظام ومراجعة وإعتماد مسير الرواتب.</span></b></p><p style="margin-block-start:0px;"></p><p style="margin-block-start:0px;"></p><p></p><div style="direction: ltr;"><b><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;Payroll has been created for month =</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;</span><span style="color: initial; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;"><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.month}</span><span style="color: rgb(0, 0, 255); font-family: Arial; font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;"></span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;</span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">Year =&nbsp;</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.year}</span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">, Kindly login to the system and confirm the payroll.</span></span></b></div>
        #     '''
        # body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
        #     body_html, 'hr.payslip.run', [self.id], )
        # body = body and body[self.id] or False
        #
        # self.message_post(
        #     subject='مراجعة مسير الرواتب العام Payroll review',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=self.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)
        # /////////////////////////////////////////////////////////////
        body = "Document Reviewed"
        self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def final_review_payslip_run(self):
        for rec in self:
            if not self.is_live:
                msg = _(
                    "Dear HR team, \n Congratulation, you are about to generate your first Payslip Batch, your must be sure that all employees received their salaries for all previous months, specially all employees hired on the previous month. in some cases some employees may be hired at 25 from the previous month and you agreed with the employee to include this period in next month salary ... \n Don’t worry, your system will handle these cases on all future payslip batches, but in your first payslip batch and after generating employees payslips, you must review the employees hired on the previous month and change payslip period to be started from the first hiring date and ends at the end of current month")
                return self.env.user.show_dialogue(msg, 'hr.payslip.run', 'final_review_payslip_run_action', rec.id)
            else:
                rec.final_review_payslip_run_action()

    @api.one
    def final_review_payslip_run_action(self):
        if self.slip_ids:
            for slip in self.slip_ids:
                if slip.state == 'draft':
                    slip.review_payslip()
                    slip.final_review_payslip()
                if slip.state == 'Reviewed':
                    slip.final_review_payslip()
        else:
            raise UserError(_(
                "Not allowed !! \n There is no payslips found! What is the data which you reviewed? kindly go to Payslip tab and click on Generate payslips, then select all employees which you want to create Payslip for them. "))

        self.write({'state': 'Final Reviewed', 'final_reviewed_by': self.env.uid, 'final_reviewed_date': datetime.now().strftime('%Y-%m-%d')})
        # /////////////  send mail custom notification  /////////////////////////////////////////////
        # partners_ids = [8]
        #
        # body_html = '''
        #     <p style="margin-block-start:0px;direction: rtl;"><b><font style="font-size: 18px;">تم اصدار الرواتب عن&nbsp;شهر</font><font style="color: rgb(0, 0, 255); font-size: 18px;">&nbsp;</font><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.month}</span><span style="font-family: Arial; font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;"></span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;لسنة</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.year}</span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;"> .. نأمل منكم الدخول على النظام ومراجعة وإعتماد مسير الرواتب.</span></b></p><p style="margin-block-start:0px;"></p><p style="margin-block-start:0px;"></p><p></p><div style="direction: ltr;"><b><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;Payroll has been created for month =</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;</span><span style="color: initial; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;"><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.month}</span><span style="color: rgb(0, 0, 255); font-family: Arial; font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;"></span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">&nbsp;</span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial;">Year =&nbsp;</span><span style="color: rgb(0, 0, 255); font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">${object.year}</span><span style="font-size: 18px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: center; white-space: pre-wrap;">, Kindly login to the system and confirm the payroll.</span></span></b></div>
        #     '''
        # body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
        #     body_html, 'hr.payslip.run', [self.id], )
        # body = body and body[self.id] or False
        #
        # self.message_post(
        #     subject='مراجعة مسير الرواتب العام Payroll review',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=self.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)
        # /////////////////////////////////////////////////////////////
        body = "Document Final Reviewed"
        self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def confirm_payslip_run(self):
        for rec in self:
            if not self.is_live:
                msg = _(
                    "Dear HR team, \n Congratulation, you are about to generate your first Payslip Batch, your must be sure that all employees received their salaries for all previous months, specially all employees hired on the previous month. in some cases some employees may be hired at 25 from the previous month and you agreed with the employee to include this period in next month salary ... \n Don’t worry, your system will handle these cases on all future payslip batches, but in your first payslip batch and after generating employees payslips, you must review the employees hired on the previous month and change payslip period to be started from the first hiring date and ends at the end of current month")
                return self.env.user.show_dialogue(msg, 'hr.payslip.run', 'confirm_payslip_run_action', rec.id)
            else:
                rec.confirm_payslip_run_action()

    @api.one
    def confirm_payslip_run_action(self):
        if self.slip_ids:
            for slip in self.slip_ids:
                slip = slip.with_context(dict(self._context, without_compute_sheet=True))
                if slip.state == 'draft':
                    slip.review_payslip()
                    slip.final_review_payslip()
                    slip.action_payslip_done()
                if slip.state == 'Reviewed':
                    slip.final_review_payslip()
                    slip.action_payslip_done()
                if slip.state == 'Final Reviewed':
                    slip.action_payslip_done()
        else:
            raise UserError(_(
                "Not allowed !! \n There is no payslips found! What is the data which you confirmed? kindly go to Payslip tab and click on Generate payslips, then select all employees which you want to create Payslip for them. "))

        self.write({'state': 'done', 'confirmed_by': self.env.uid, 'confirmation_date': datetime.now().strftime('%Y-%m-%d')})
        body = "Document Confirmed"
        self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def set_draft_payslip_run(self):
        if self.slip_ids:
            for slip in self.slip_ids:
                if slip.state in ['Reviewed', 'Final Reviewed', 'cancel']:
                    slip.action_payslip_draft()
        else:
            raise UserError(_("Not allowed !! \n There is no payslips in order to set it to Draft. "))

        self.write({'state': 'draft'})
        body = "Document Set To Draft"
        self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def open_payslips(self):
        return {
            'domain': [('id', 'in', self.slip_ids.ids)],
            'name': _('Employee payslip'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.onchange('month', 'year')
    def onchange_period(self):
        if self.month and self.year:
            start_end = calendar.monthrange(self.year, int(self.month))
            self.date_start = str(self.year) + '-' + self.month + '-01'
            self.date_end = str(self.year) + '-' + self.month + '-' + str(start_end[1])


class BatchAttaches(models.Model):
    _name = "hr.payslip.run.attaches"
    _description = "Payslip Batch Attaches"

    batch_id = fields.Many2one('hr.payslip.run', 'Batch')
    file = fields.Binary('File', attachment=True, )
    file_name = fields.Char('File name')
    name = fields.Char('Description')
    note = fields.Char('Notes')


class hr_payslip_employees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def compute_sheet(self):
        res = super(hr_payslip_employees, self).compute_sheet()
        run_pool = self.env['hr.payslip.run']
        context = self.env.context
        batch = self.env.context and self.env.context.get('active_id', False) and run_pool.browse(self.env.context.get('active_id', False)) or None
        if batch:
            for slip in batch.slip_ids:
                # run_data = {}
                if context and context.get('active_id', False):
                    active_batch = self.env['hr.payslip.run'].browse(context['active_id'])
                    # run_data = run_pool.read([context['active_id']], ['date_start', 'date_end', 'credit_note', 'month', 'year'])[0]
                from_date = __(active_batch.date_start)
                emp_start_date = from_date
                old_payslips_ids = self.env['hr.payslip'].search([('state', '=', 'done')])
                emoployee_old_payslips_ids = self.env['hr.payslip'].search([('employee_id', '=', slip.employee_id.id), ('state', '=', 'done')])
                if old_payslips_ids and not emoployee_old_payslips_ids and slip.employee_id.contract_id and __(slip.employee_id.contract_id.start_work):
                    start_work = datetime.strptime(__(slip.employee_id.contract_id.start_work), "%Y-%m-%d")
                    patch_start = datetime.strptime(from_date, "%Y-%m-%d")
                    delta = start_work - patch_start
                    if abs(delta.days) <= 60:
                        emp_start_date = start_work.strftime("%Y-%m-%d")
                slip.date_from = emp_start_date
                slip.month = batch.month
                slip.year = batch.year
        return res


class Contract(models.Model):
    _inherit = "hr.contract"

    struct_id = fields.Many2one(default=lambda s: s.env.ref('saudi_hr_payroll.rz_salary_structure'))
