# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
from datetime import timedelta
import calendar
from dateutil.relativedelta import relativedelta
import math
from dateutil import tz
from odoo.tools import float_compare
from odoo.addons.hr_holidays.models.hr_leave import HolidaysRequest as hr_holidays_original
from odoo.tools import __
from odoo.tools import __


class hr_leave_type(models.Model):
    _name = 'hr.leave.type'
    _inherit = ['mail.thread', 'hr.leave.type']

    name = fields.Char('Leave Description‬‬', size=64, required=True, translate=True)
    double_validation = fields.Boolean('Apply Double Validation', default=True,
                                       help="When selected, the Allocation/Leave Requests for this type require a second validation to be approved.")
    type = fields.Selection([('Annual Leave', 'Annual Leave'),
                             ('Non Annual Leave', '‫‪Non Annual Leave‬‬')], 'Leave Type', required=True)
    limit = fields.Boolean('Unlimited leave balance',
                           help='If you select this check box, the system allows the employees to take more leaves than the available ones for this type and \
                           will not take them into account for the "Remaining Legal Leaves" defined on the employee form.')
    days_per_leave = fields.Integer(string="Maximum Days Per Each Leave")
    allow_past = fields.Integer(string="Allow to request leave for past", default=10,
                                help='if = zero, not allowed to request for any leave for past days, if = 5 employee will be allowed to request for this leave type for past 5 days.')
    allow_future = fields.Integer(string="Allow to request leave for future",
                                  help='if = zero, not allowed to request for any leave for future days, if = 5 employee will be allowed to request for this leave type for future 5 days.')
    days_in_month = fields.Integer(string="Days In Month", default=30)
    months_in_year = fields.Integer(string="Months In Year", default=12)
    days_in_year = fields.Integer(string="Days In Year", compute="_compute_days_in_year", store=True, readonly=True)
    nationality = fields.Selection([
        ('Native', 'Native Only'),
        ('Non-native', 'Non-native only'),
        ('All Nationalities', '‫All Nationalities‬‬'),
    ], 'Nationality', required=True)
    reconciliation_based_on = fields.Selection([
        ('total', 'Total salary'),
    ], string='Leave Reconciliation based on')

    start_calc_from = fields.Selection([('First Effective Notice', 'First Effective Notice'),
                                        ('Contract Start Date', 'Contract Start Date'),
                                        ('Trial Period Start Date', '‫Trial Period Start Date‬‬')],
                                       'Start Calculation From',
                                       default="First Effective Notice")
    max_balance = fields.Integer(string="Max Accumulated Balance", default=180)
    notes = fields.Html(string="Notes")
    lines = fields.One2many('leaves.calc.method.line', 'leave_type_id', string="Calculation Method")
    max_line_less = fields.Integer()
    can_request_air_ticket = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='can request air ticket')

    state = fields.Selection([('New', 'New'), ('Approved', 'Approved')], string='Status', readonly=True, index=True, default='New', )
    reconciliation_method = fields.Selection(
        [('Stop payslip during leave and use leave reconciliation', 'Stop payslip during leave and use leave reconciliation'),
         ('Continue payslip during leave ( no need for leave reconciliation)', 'Continue payslip during leave ( no need for leave reconciliation)')],
        string='Leave Reconciliation method')

    non_annual_type = fields.Selection([
        ('Unpaid Leave', 'Unpaid Leave'),
        ('Hajj Leave', 'Hajj Leave'),
        ('Omra Leave', 'Omra Leave'),
        ('New Baby For Men', 'New Baby For Men'),
        ('Marriage Leave', 'Marriage Leave'),
        ('New Baby For Women', 'New Baby For Women'),
        ('Husband Death', 'Husband Death'),
        ('Death Of A Relative', 'Death Of A Relative'),
        ('Exams Vacation', 'Exams Vacation'),
        ('Sick Leave', 'Sick Leave'),
        ('Other', 'Other'),
    ], string='Non Annual Leave Type')
    sick_message = fields.Char('=>', compute="_compute_sick_message")
    number_of_days = fields.Integer(string="Number Of Days")
    # """
    # كل سنة تعاقدية .
    # مرة واحدة .
    # حسب الطلب .
    # كل سنه هجرية .
    # كل سنة ميلادية .
    # كل سنة ابتدأ من اول طلب .
    # كل عقد .
    # """
    non_annual_frequency = fields.Selection([
        ('contractual_year', 'Each contractual year ( hiring dat to next year)'),
        ('one_time', 'one time per live.'),
        ('per_request', 'based on request (no limitation)'),
        ('hijri_year', 'Per hijri year'),
        ('year', 'Per Year'),
        ('year_request', 'Per year based on first request'),
        ('contract', 'Per contract'),
    ], string='Non annual leave Frequency')
    divide_leave_balance = fields.Selection([
        ('allow_to_divide', 'Allow to divide leave balance ( more than leave request)'),
        ('one_time', 'One time, if employee request this leave, deduct all balance.'),
    ], string='Divide Leave Balance')
    who_request = fields.Selection([
        ('Male only', 'Male only'),
        ('Females only', 'Females only'),
        ('Both', 'Both'),
    ], string='Who can request this leave')

    marital_status = fields.Selection([
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Both', 'Both'),
    ], string='Marital Status')

    religion = fields.Selection([
        ('Muslim', 'Muslim'),
        ('Non-Muslim', 'Non-Muslim'),
        ('All Religions', 'All Religions'),
    ], string='Religion')
    working_calendar = fields.Selection([
        ('Calendar days', 'Calendar days'),
    ], string='Working / Calendar', default='Calendar days')
    # /////////////////// Smart Buttons /////////////////////////////////////////////////////////////

    check_iqama_expiry = fields.Boolean('Check for IQAMA / National ID expiry',
                                        help='In order to force your system to Check for IQAMA / National ID expiry date, this field must be flagged in Leave type and employee nationality.')
    check_passport_expiry = fields.Boolean('Check for Passport expiry date',
                                           help='In order to force your system to Check for Passport expiry date, this field must be flagged in Leave type and employee nationality.')
    max_per_month = fields.Integer('Maximum per month', help='Zero for no limits')
    # ===== Alternative Employee ======
    alternative_employee = fields.Boolean('Alternative Employee')
    is_alternative_employee = fields.Boolean(string='Must have alternative employee',
                                             help='If = Yes, and job position requires alternative employee, '
                                                  'leave request will not be approved until provide an alternative employee.')
    alternative_approval = fields.Boolean('Alternative Employee Approval is mandatory ',
                                          help='If = Yes, you will not be able to continue leave request workflow process unless the alternative employee login to the system and approve the leave request. HR assistant and Hr manager have the option to bypass alternative employee approval.')
    alternative_employee_days = fields.Integer('Number of leave days requires alternative employee',
                                               help='If employee request for leave 3 days and Number of leave days requires alternative employee = 5. Your system will not request for alternative employee. If employee request for leave 5 days and Number of leave days requires alternative employee = 1. Your system will refuse to approve leave request until providing an alternative employee.')

    leave_reconciliation_minimum = fields.Integer('Minimum days to use leave reconciliation',
                                                  help="If = 20 and employee request for a leave for 15 days, your system will not create a leave reconciliation for this leave request.")
    allocate_after_trial = fields.Boolean('Allocate leave after End of trial period process', default=True,
                                          help='If you select this option, your system will not allocate this leave until HR manager approves (End of trial period process).')
    request_during_trial = fields.Boolean('Can Request this leave during trial period',
                                          help='If you select this option, Employees will be allowed to request for this leave type before end of trial period process.')
    allow_leave_advance = fields.Boolean('Allow to request leave in advance')
    max_advance_type = fields.Selection([
        ('fixed', 'Fixed days'),
        ('year_end', 'Employee Balance at End of financial year 31-12'),
    ], string='Maximum advance days type')
    advance_days = fields.Integer('Number of advanced days')
    leave_address_required = fields.Boolean('Leave Address and leave phone number is required', default='Yes',
                                            help='If = yes, employee will not be allowed to request for this leave type until (s)he fill the leve address and phone number during leave.')
    mandatory_return_from_leave = fields.Selection([
        ('Yes', 'Yes'),
        ('No', 'No'),
    ], string='Mandatory to create Return from leave', default='Yes',
        help='If = yes, employee will not allowed to request for new leave until he create a return from leave for all old leaves …. If = No, your system will not consider return from leave into account, so any employee can request for a new leave without create a return from leave for old leaves.')
    leave_extend_timeout = fields.Integer('Allow to extend leave request within', default=30,
                                          help='If = 10 days, you will be allowed to extend leave requests related to this leave types after 10 days from leave end date. e.g, if leave end date = 20 January and  Allow to extend leave request within 5 Days … leave extend button will appear till 25 January. ')

    @api.onchange('allow_leave_advance', 'max_advance_type')
    def empty_advance_days(self):
        self.advance_days = 0

    @api.onchange('allow_leave_advance')
    def empty_max_advance_type(self):
        self.max_advance_type = False

    # @api.onchange('allocate_after_trial')
    # def empty_start_allocation_after(self):
    #     self.start_allocation_after = 0

    @api.onchange('reconciliation_method', 'type')
    def empty_leave_reconciliation_minimum(self):
        self.leave_reconciliation_minimum = 0

    @api.onchange('alternative_employee')
    def onchange_alternative_employee(self):
        self.is_alternative_employee = False
        self.onchange_is_alternative_employee()

    @api.onchange('is_alternative_employee')
    def onchange_is_alternative_employee(self):
        self.alternative_approval = False
        self.alternative_employee_days = 0

    @api.onchange('limit')
    def onchange_limit(self):
        self.number_of_days = 0
        if self.limit:
            self.allocate_after_trial = False
        else:
            self.allocate_after_trial = True

    @api.onchange('non_annual_frequency')
    def onchange_non_annual_frequency(self):
        if self.non_annual_frequency == 'per_request':
            self.limit = True

    @api.onchange('type', 'nationality')
    def clear_can_request(self):
        self.can_request_air_ticket = False
        if self.type != 'Annual Leave':
            self.reconciliation_based_on = False

    @api.one
    @api.depends('days_in_month', 'months_in_year')
    def _compute_days_in_year(self):
        self.days_in_year = self.days_in_month * self.months_in_year

    @api.one
    @api.depends('non_annual_type')
    def _compute_sick_message(self):
        self.sick_message = 'Full Salary for first 30 days , 75 % from total salary for next 60 days and no salary for last 30 days.'

    @api.onchange('type')
    def onchange_type(self):
        for rec in self:
            rec.reconciliation_method = ''
            rec.non_annual_type = ''
            rec.number_of_days = 0
            rec.non_annual_frequency = ''
            rec.divide_leave_balance = ''
            rec.who_request = ''
            rec.marital_status = ''
            rec.religion = ''
            if rec.type == 'Annual Leave':
                rec.limit = False
            if rec.type == "Non Annual Leave":
                rec.lines = []
                rec.allow_leave_advance = False
            rec.is_alternative_employee = False

    @api.onchange('non_annual_type')
    def onchange_non_annual_type(self):
        for rec in self:
            rec.number_of_days = 0
            rec.non_annual_frequency = ''
            rec.divide_leave_balance = ''
            rec.who_request = ''
            rec.marital_status = ''
            rec.religion = ''
            if rec.non_annual_type == 'Unpaid Leave':
                rec.reconciliation_method = 'Stop payslip during leave and use leave reconciliation'
            elif rec.non_annual_type == 'Sick Leave':
                rec.reconciliation_method = 'Continue payslip during leave ( no need for leave reconciliation)'
                # rec.number_of_days = 120
            else:
                rec.reconciliation_method = ''

            if rec.non_annual_type == 'New Baby For Men':
                rec.who_request = 'Male only'
                rec.marital_status = 'Married'

            if rec.non_annual_type == 'Marriage Leave':
                rec.marital_status = 'Single'

            if rec.non_annual_type in ['New Baby For Women', 'Husband Death']:
                rec.who_request = 'Females only'
                rec.marital_status = 'Married'

    @api.multi
    def action_hr_approve(self):
        for record in self:
            if record.type == 'Annual Leave':
                # if record.max_advance_type == 'fixed' and not record.advance_days:
                #     raise exceptions.ValidationError("Number of advanced days   cannot be zero or negative value.")
                if len(record.lines) == 0:
                    raise exceptions.ValidationError("Data error!! You must insert at least one line in the calculation method table")
            if record.limit:
                msg = _(
                    "Dear HR manager, \n Attention , you selected ( Unlimited leave balance ) for this leave, which mean that your system will not check employee leave balance when requesting for this leave. \n Are you sure that you want to continue ? ")
                return self.env.user.show_dialogue(msg, 'hr.leave.type', 'hr_approve', record.id)

            return record.hr_approve()

    @api.multi
    def hr_approve(self):
        for record in self:
            if record.type == 'Non Annual Leave' and record.non_annual_type == 'Sick Leave':
                old_same_leave_types = self.env['hr.leave.type'].search(
                    [('non_annual_type', '=', record.non_annual_type), ('nationality', '=', record.nationality),
                     ('who_request', '=', record.who_request),
                     ('religion', '=', record.religion), ('non_annual_type', '=', 'Sick Leave'), ('id', '!=', record.id)])

                if len(old_same_leave_types):
                    msg = "Dear Hr manager, \n Attention,there is another  Non-annual leave type ( %s ) for same Nationality ( %s ) and same gender ( %s ) and same religion ( %s ) Are you sure that you want to continue ? " % (
                        record.non_annual_type, record.nationality, record.who_request, record.religion)
                    return self.env.user.show_dialogue(msg, 'hr.leave.type', 'hr_approve_confirm', record.id)
            return record.hr_approve_confirm()

    @api.multi
    def hr_approve_confirm(self):
        for record in self:
            record.write({'state': 'Approved'})
            # body = "Document Approved By Hr Department"
            # self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def action_set_to_new(self):
        for record in self:
            record.write({'state': 'New'})
            # body = "Document changed to ->  New Status"
            # self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def unlink(self):
        if self.state != 'New':
            raise exceptions.ValidationError("Not allowed to delete approved document, you can set it to new and delete it")
        contracts = self.env['hr.contract'].search([['annual_leave_policy', '=', self.id]])
        if contracts:
            raise ValidationError(
                _("You can not delete Leave type while it linked with Contract%s\n" % (str('\n'.join([str(c.name) for c in contracts])))))
        return super(hr_leave_type, self).unlink()


class calc_method_line(models.Model):
    _name = "leaves.calc.method.line"
    _order = "greater_than, id"

    leave_type_id = fields.Many2one('hr.leave.type', string='Leave Type')
    greater_than = fields.Integer(string="Greater Than", default=lambda self: self._default_greater_than(), readonly=True)
    less_than = fields.Integer(string="Less Than")
    number_of_months = fields.Integer(string="Number Of Months", compute="_compute_number_of_months", store=True)
    calc_method = fields.Selection([('None', 'None'),
                                    ('Fixed Number', 'Fixed Number')], 'Calculation Method', required=True, default="None")
    balance = fields.Float(string="Balance")
    monthly_balance = fields.Float(string="Monthly Balance", compute="_compute_monthly_balance", store=True)
    notes = fields.Text(string="Notes")
    max_line_less = fields.Integer(related="leave_type_id.max_line_less", readonly=True)

    def _default_greater_than(self):
        leave_type = self.env['hr.leave.type'].search([('id', '=', self.env.context.get('leave_type_id', False))])
        return leave_type.max_line_less

    @api.onchange('less_than')
    def onchange_less_than(self):
        for rec in self:
            leave_type = self.env['hr.leave.type'].search([('id', '=', self.env.context.get('leave_type_id', False))])
            current_rec = self.env['leaves.calc.method.line'].search([('leave_type_id', '=', leave_type.id), ('greater_than', '=', rec.greater_than)])
            if rec.less_than > 0:
                if current_rec:
                    current_rec.write({'less_than': rec.less_than})
                    leave_type.write({'max_line_less': rec.less_than})
                else:
                    rec = rec.create({'leave_type_id': leave_type.id, 'greater_than': rec.greater_than, 'less_than': rec.less_than})
                    leave_type.write({'max_line_less': rec.less_than})

    @api.multi
    def unlink(self):
        for rec in self:
            next_calc_line = self.env['leaves.calc.method.line'].search(
                [('greater_than', '=', rec.less_than), ('leave_type_id', '=', rec.leave_type_id.id), ('id', '!=', self.id)])
            if next_calc_line and not self.env.context.get('on_create', False):
                raise exceptions.ValidationError(_("Please Delete The Last Line First"))
            record_id = rec.leave_type_id.id
            leave_type = rec.leave_type_id
            res = super(calc_method_line, self).unlink()
            last_line = self.env['leaves.calc.method.line'].search([('leave_type_id', '=', record_id)], order="less_than desc", limit=1)
            if last_line:
                leave_type.max_line_less = last_line.less_than
            else:
                leave_type.max_line_less = 0
        return res

    @api.model
    def create(self, vals):
        same_record = self.env['leaves.calc.method.line'].search(
            [('leave_type_id', '=', vals.get('leave_type_id', 0)), ('greater_than', '=', vals.get('greater_than', 0))])
        if same_record:
            same_record.with_context({'on_create': True}).unlink()
        res = super(calc_method_line, self).create(vals)
        last_line = self.env['leaves.calc.method.line'].search([('leave_type_id', '=', vals['leave_type_id'])], order="less_than desc", limit=1)
        if vals.get('leave_type_id', False) and last_line:
            last_line.leave_type_id.max_line_less = last_line.less_than
        return res

    @api.depends('greater_than', 'less_than')
    def _compute_number_of_months(self):
        for rec in self:
            rec.number_of_months = rec.less_than - rec.greater_than

    @api.onchange('calc_method')
    def onchange_balance(self):
        for rec in self:
            if rec.calc_method == "None":
                rec.balance = 0

    @api.depends('balance')
    def _compute_monthly_balance(self):
        for rec in self:
            if rec.number_of_months == 0 or not rec.leave_type_id.months_in_year:
                rec.monthly_balance = 0
            else:
                mb = rec.balance / rec.leave_type_id.months_in_year
                rec.monthly_balance = round(mb, 2)

    @api.multi
    def write(self, vals):
        res = super(calc_method_line, self).write(vals)
        return res


class contract_work_permit_line(models.Model):
    _name = "contract.work.permit.line"

    name = fields.Char("Name")
    dayofweek = fields.Selection(
        [('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday')],
        'Day of Week',
        required=True, index=True)
    date_from = fields.Date('Starting Date')
    date_to = fields.Date('End Date')
    hour_from = fields.Float('Work from', required=True, help="Start and End time of working.", index=True)
    hour_to = fields.Float("Work to", required=True)
    contract_id = fields.Many2one("hr.contract", "Contract", required=True)


class hr_contract(models.Model):
    _inherit = "hr.contract"

    annual_leave_policy = fields.Many2one('hr.leave.type', string='Annual Leave Policy', required=True)
    adjusted_date = fields.Date('Adjusted Date', related='start_allocation_date')
    attendance_ids = fields.One2many('contract.work.permit.line', 'contract_id', string='Working Time')
    working_calendar = fields.Selection([
        ('Calendar days', 'Calendar days'),
    ], string='Working / Calendar', default='Calendar days')
    start_allocation_date = fields.Date('Start allocation date', related="employee_id.start_allocation_date", inverse='set_start_allocation_date',
                                        readonly=False)

    def set_start_allocation_date(self):
        self.employee_id.start_allocation_date = __(self.start_allocation_date)

    @api.onchange('annual_leave_policy')
    def change_working_calendar(self):
        self.working_calendar = self.annual_leave_policy.working_calendar

    @api.onchange('first_effective_notice')
    def onchange_first_effective_notice(self):
        self.start_work = self.first_effective_notice.start_work or False

    @api.onchange('employee_id')
    def onchange_employee(self):
        if not self.employee_id:
            self.job_id = False
            self.department_id = False
        if self.employee_id.job_id:
            self.job_id = self.employee_id.job_id.id
        if self.employee_id.department_id:
            self.department_id = self.employee_id.department_id.id
        self.first_effective_notice = False
        self.resource_calendar_id = False
        return {'domain': {
            'first_effective_notice': [('employee_id', '=', self.employee_id.id), ('state', '!=', 'Refused'), ('type', '=', 'New Employee')]}}


class leave_month_days(models.Model):
    _name = "leave.month.days"
    _description = 'leave month days'

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

    leave_id = fields.Many2one('hr.leave', string='leave request')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    holidays_status_id = fields.Many2one('hr.leave.type', 'Leave type')
    month = fields.Selection(_PERIOD, 'Month')
    year = fields.Integer('Year')
    days = fields.Float('Number of days per month')
    state = fields.Selection(string='Leave request status', related='leave_id.state', readonly=True, store=True)


class hr_leaves(models.Model):
    _name = "hr.leave"
    _inherit = ["hr.leave", "salary.details"]
    _order = "id desc"

    MONTHS_SELECTION = {'01': 'January', '02': 'February', '03': 'March', '04': 'April', '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                        '09': 'September', '10': 'October', '11': 'November', '12': 'December'}

    employee_id = fields.Many2one('hr.employee', "Employee", default=lambda self: self.env.user.employee_ids and self.env.user.employee_ids[0].id)

    holiday_status_id = fields.Many2one("hr.leave.type", "Leave Type", required=True, readonly=True,
                                        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                        domain=[('state', 'in', ['Approved'])])
    reconciliation_method = fields.Selection(
        [('Stop payslip during leave and use leave reconciliation', 'Yes'),
         ('Continue payslip during leave ( no need for leave reconciliation)', 'No')],
        string='Request Salary In Advance')
    reconciliation_method_readonly = fields.Boolean(compute='get_reconciliation_method_readonly')
    holiday_status_type = fields.Selection([('Annual Leave', 'Annual Leave'),
                                            ('Non Annual Leave', '‫‪Non Annual Leave‬‬')], related='holiday_status_id.type', readonly=True)
    allow_minus_value = fields.Boolean('Allow Minus Value')
    contract_id = fields.Many2one('hr.contract', string='Contract', compute="_compute_contract", readonly=True, store=True)
    annual_leave_policy = fields.Many2one('hr.leave.type', string='Annual Leave Policy', related="contract_id.annual_leave_policy",
                                          readonly=True)
    allocation_date = fields.Date('Allocation Date')
    system_created = fields.Boolean('Created By The System', readonly=True)
    approved_by = fields.Many2one('res.users', string="Approved By", readonly=True)
    leave_automatic_allocation = fields.Many2one('leave.automatic.allocation', string="Leave Automatic Allocation", readonly=True)
    request_reason = fields.Selection([
        ('annual', 'annual leave'),
        ('non-annual', 'Non-annual leave'),
    ], string='Leave request reason')
    current_balance = fields.Float('Current balance', compute='get_current_balance')
    current_balance_ = fields.Float('Current balance')
    remaining_balance = fields.Float('Remaining balance', compute='get_remaining_balance')
    nationality_type = fields.Selection(related='employee_id.nationality_type', store=True, readonly=True)
    branch_id = fields.Many2one('hr.branch', string='Branch', related="employee_id.branch_id", readonly=True, store=True)
    department_id = fields.Many2one('hr.department', string='Department', related="employee_id.department_id", readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string='Job Title', related="employee_id.job_id", readonly=True, store=True)
    country_id = fields.Many2one('res.country', '‫‪Nationality‬‬', related="employee_id.country_id", readonly=True, store=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender', related='employee_id.gender', store=True, readonly=True)
    last_working_day = fields.Date('last working day', compute='compute_last_working_day')
    last_working_week_day = fields.Char('Last Working week day', compute='get_date_day')
    expected_working_day = fields.Date('Expected working day', compute='compute_expected_working_day')
    expected_working_week_day = fields.Char('Expected working week day', compute='get_date_day')
    reconciliation_based_on = fields.Selection([
        ('total', 'Total salary'),
    ], string='Leave Reconciliation based on')
    basic_salary = fields.Float('Basic salary')
    trial_wage = fields.Float('Trial Basic salary')
    trial_total_salary = fields.Float('Total')
    total_salary = fields.Float('Total')
    leave_reconciliation_amount = fields.Float('Leave Reconciliation amount', compute='get_leave_reconciliation_amount', store=True)
    paid_amount = fields.Float('Paid amount', compute='_compute_paid_amount')
    remaining_amount = fields.Float('Remaining amount', compute='get_remaining_amount')
    leave_fully_reconciled = fields.Boolean('Leave Fully Reconciled', compute='get_remaining_amount', store=False)
    holiday_history_ids = fields.Many2many('hr.leave', 'rel_leave_history', 'leave_id', 'history_id', string='Leave history')
    attachment_ids = fields.One2many('leave.attachment', 'leave_request_id', 'Attachments')
    # developer mode fields (Employee INfo)
    iqama_id = fields.Char('Iqama number', compute='get_employee_info', multi=True)
    iqama_id_ = fields.Char('Iqama number')
    iqama_expiry_date = fields.Date('Iqama Expiry date', compute='get_employee_info', multi=True)
    iqama_expiry_date_ = fields.Date('Iqama Expiry date')
    passport_no = fields.Char('Passport Number', compute='get_employee_info', multi=True)
    passport_no_ = fields.Char('Passport Number')
    passport_expiry_date = fields.Date('Passport expiry date', compute='get_employee_info', multi=True)
    passport_expiry_date_ = fields.Date('Passport expiry date')
    note = fields.Html('Notes')
    # Smart buttons
    count_air_ticket_requests = fields.Float('Number of air tickets', compute='get_count_smart_buttons', multi=True)
    air_ticket_request_ids = fields.One2many('air.ticket.request', 'leave_request', 'air ticket requests')
    leave_requests_id = fields.Many2one('hr.leave')
    old_leave_requests_ids = fields.One2many('hr.leave', 'leave_requests_id', 'Old leave requests', compute='get_old_leave_requests')
    linked_leave_reconciliation_id = fields.Many2one('hr.leave.reconciliation', 'Linked Leave reconciliation')
    date_from_day = fields.Char('Date From Day', compute='get_date_day')
    date_to_day = fields.Char('Date To Day', compute='get_date_day')
    leave_extended = fields.Boolean('Leave Extended')
    leave_request_extend_id = fields.Many2one('hr.leave', 'leave request to extend this leave')
    original_leave_request_id = fields.Many2one('hr.leave', 'Original Leave request')
    return_from_leave = fields.Many2one('effective.notice', 'Return from leave')
    return_from_leave_date = fields.Date('Return from leave date', related="return_from_leave.start_work", readonly=True)
    button_extend_invisible = fields.Boolean('button extend invisible', compute='get_button_extend_invisible')
    early_return_from_leave = fields.Many2one('effective.notice', 'Early Return from leave')
    late_return_from_leave = fields.Many2one('effective.notice', 'Late Return from leave')
    adjusted_date = fields.Date('Adjusted Date', related='contract_id.start_allocation_date', readonly=True)
    reconciliation_paid_line_ids = fields.One2many('leave.reconciliation.paid.line', 'request_id', 'Paid Amounts')
    by_eos = fields.Boolean('Through EOS')
    state = fields.Selection(
        [('draft', 'Draft'), ('cancel', 'Cancelled'), ('confirm', 'Direct Manager Approval'), ('validate1', 'Dep Manager Approval'),
         ('validate', 'HR Approval'), ('refuse', 'Refused')], 'Status', readonly=False, copy=False, default='draft', )

    days_label = fields.Char(compute='_compute_days_label')
    can_reset = fields.Boolean('Can Reset', compute='_get_can_reset')
    leave_days_ids = fields.One2many('leave.month.days', 'leave_id', 'Number of days per each month')
    days_per_months = fields.Float('Number of days per month', compute='_compute_days_per_months', store=True)

    # ======= Alternative Employee ======
    alternative_employee_id = fields.Many2one('hr.employee', 'Alternative Employee')
    show_alternative_employee = fields.Boolean('Show Alternative Employee', compute='_compute_show_alternative_employee')
    accept_without_alternative = fields.Boolean('accept leave request without employee alternative')
    alternative_approval = fields.Boolean('Alternative employee Approval')
    alternative_employee = fields.Boolean(related='holiday_status_id.alternative_employee')
    is_alternative_employee = fields.Boolean(related='holiday_status_id.is_alternative_employee')
    alternative_approval_ = fields.Boolean(related='holiday_status_id.alternative_approval')
    alternative_employee_days = fields.Integer(related='holiday_status_id.alternative_employee_days')
    skip_basic_return = fields.Boolean('Skip waiting for the return of the basic employee from his leave')

    direct_approved_by = fields.Many2one('res.users', string="Direct Manager Approved By")
    direct_approved_date = fields.Date('Direct Manager Approved Date')
    department_approved_by = fields.Many2one('res.users', string="Department Approved By")
    department_approved_date = fields.Date('Department Approved Date')
    hr_approved_by = fields.Many2one('res.users', string="HR Approved By")
    hr_approved_date = fields.Date('HR Approved Date')
    refused_by = fields.Many2one('res.users', string="Refused By")
    refused_date = fields.Date('Refused Date')
    leave_address = fields.Char('Leave Address')
    leave_phone = fields.Char('Leave Phone No')
    report_employee_is_manager = fields.Boolean(compute='_compute_employee_is_manager')
    report_holiday_till_date = fields.Date(compute='_compute_report_holiday_till_date')
    report_holiday_till_balance = fields.Float(compute='_compute_report_holiday_till_date')
    leave_address_required = fields.Boolean(related='holiday_status_id.leave_address_required', readonly=1)
    mandatory_return_from_leave = fields.Selection([
        ('Yes', 'Yes'),
        ('No', 'No'),
    ], string='Mandatory to create Return from leave', default='Yes')
    bypass_past_days = fields.Boolean('Bypass validation for past days')
    bypass_future_days = fields.Boolean('Bypass validation for future days')
    is_init = fields.Boolean('This is begging allocation', default=False)

    visa_no = fields.Char('Exit Re-entry visa NO.')
    visa_issue_date = fields.Date('Visa Issue date')
    visa_expiry_date = fields.Date('Visa expiry date')

    @api.onchange('job_id')
    def get_employee_domain(self):
        employees = self.env['hr.employee'].search([])

        if self.env.user.has_group('hr.group_hr_user'):
            return {'domain': {'employee_id': [('id', 'in', employees.ids)]}}
        elif self.env.user.has_group('saudi_hr_employee.group_hr_department_manager'):
            return {'domain': {'employee_id': [('department_id', 'child_of', self.env.user.employee_ids[0].department_id.id)]}}
        elif self.env.user.has_group('saudi_hr_employee.group_hr_direct_manager'):
            return {'domain': {'employee_id': [('id', 'child_of', self.env.user.employee_ids.ids)]}}
        else:
            return {'domain': {'employee_id': [('user_id', '=', self.env.user.id)]}}

    @api.onchange('department_id')
    def get_leave_address(self):
        self.leave_address = self.employee_id.leave_address
        self.leave_phone = self.employee_id.leave_phone

    @api.onchange('request_reason', 'holiday_status_id', 'number_of_days')
    def get_reconciliation_method(self):
        if self.request_reason == 'annual':
            if self.holiday_status_id.reconciliation_method == 'Continue payslip during leave ( no need for leave reconciliation)' or (
                    self.holiday_status_id.reconciliation_method == 'Stop payslip during leave and use leave reconciliation' and self.holiday_status_id.leave_reconciliation_minimum > self.number_of_days):
                self.reconciliation_method = 'Continue payslip during leave ( no need for leave reconciliation)'
            else:
                self.reconciliation_method = False
        else:
            self.reconciliation_method = self.holiday_status_id.reconciliation_method

    @api.onchange('holiday_status_id', 'employee_id', 'date_from', 'date_to', 'request_reason')
    def empty_alternative_employee(self):
        self.alternative_employee_id = False
        self.accept_without_alternative = False

    @api.onchange('date_from', 'date_to', 'request_reason', 'holiday_status_id')
    def _compute_leave_days_ids(self):
        if __(self.date_to) and __(self.date_from):
            periods_by_month = self.devide_period_by_month(__(self.date_from), __(self.date_to))
            for period in periods_by_month:
                number_of_days = self.get_duration_number_of_days(period['from'], period['to'])
                period['number_of_days'] = number_of_days

            self.leave_days_ids = [(5,)]
            vals = []
            for period in periods_by_month:
                DATE_FORMAT = "%Y-%m-%d"
                period_date = datetime.strptime(period['from'].split(' ')[0], DATE_FORMAT)
                vals.append({
                    'employee_id': self.employee_id.id,
                    'holidays_status_id': self.holiday_status_id.id,
                    'month': period_date.strftime("%m"),
                    'year': period_date.strftime('%Y'),
                    'days': period['number_of_days'],
                })
            self.leave_days_ids = vals

    @api.onchange('accept_without_alternative')
    def onchange_accept_without_alternative(self):
        self.alternative_employee_id = False

    @api.onchange('holiday_status_id')
    def onchange_leave_type(self):
        reconciliation_based_on = False
        self.mandatory_return_from_leave = self.holiday_status_id.mandatory_return_from_leave
        if self.holiday_status_id and self.holiday_status_id.reconciliation_based_on:
            reconciliation_based_on = self.holiday_status_id.reconciliation_based_on
        self.reconciliation_based_on = reconciliation_based_on

    @api.onchange('employee_id', 'holiday_status_id')
    def get_leave_history(self):
        if self.employee_id and self.holiday_status_id:
            history = self.search(
                [['employee_id', '=', self.employee_id.id], ['holiday_status_id', '=', self.holiday_status_id.id]])
            self.holiday_history_ids = [(6, False, [h.id for h in history])]

    @api.onchange('employee_id', 'contract_id')
    def reset_leave_type(self):
        self.request_reason = False
        self.holiday_status_id = False

    @api.onchange('contract_id', 'request_reason', 'employee_id', 'holiday_status_id', 'holiday_status_type')
    def get_salary_allowances(self):
        self.trial_house_allowance_type = False
        self.trial_house_allowance = False
        self.trial_house_allowance_amount = False
        self.trial_transportation_allowance_type = False
        self.trial_transportation_allowance = False
        self.trial_transportation_allowance_amount = False
        self.trial_phone_allowance_type = False
        self.trial_phone_allowance = False
        self.trial_phone_allowance_amount = False
        self.trial_insurance = False
        self.trial_commission = False
        self.trial_other_allowance = False
        self.trial_other_allowance_name = False
        self.house_allowance_type = False
        self.house_allowance = False
        self.house_allowance_amount = False
        self.transportation_allowance_type = False
        self.transportation_allowance = False
        self.transportation_allowance_amount = False
        self.phone_allowance_type = False
        self.phone_allowance = False
        self.phone_allowance_amount = False
        self.insurance = False
        self.commission = False
        self.other_allowance = False
        self.other_allowance_name = False
        self.trial_wage = False
        self.basic_salary = False
        self.total_salary = False
        self.trial_total_salary = False
        if self.contract_id and self.request_reason == 'annual':
            self.basic_salary = self.contract_id.basic_salary
            self.trial_wage = self.contract_id.trial_wage
            self.update_allowances_from_(self.contract_id, self)
            self.total_salary = self.contract_id.total
            self.trial_total_salary = self.contract_id.trial_total

    @api.onchange('request_reason', 'employee_id')
    def get_leave_type(self):
        self.holiday_status_id = False
        if self.request_reason == 'annual':
            self.holiday_status_id = self.annual_leave_policy.id

    @api.onchange('request_reason')
    def onchange_request_reason(self):
        domain = [['state', 'in', ['Approved']]]
        if self.request_reason == 'non-annual':
            domain += [['type', '=', 'Non Annual Leave'],
                       ['nationality', 'in', ['All Nationalities', self.nationality_type]]]
        return {'domain': {'holiday_status_id': domain}}

    @api.onchange('date_to', 'date_from', 'request_reason', 'holiday_status_id')
    def onchange_period_custom(self):
        date_from = __(self.date_from)
        date_to = __(self.date_to)

        # Compute and update the number of days
        if date_to and date_from:
            diff_day = self._get_number_of_days(date_from, date_to, self.employee_id.id)
            self.number_of_days = round(math.floor(diff_day)) + 1
        else:
            self.number_of_days = 0

    @api.onchange('date_from', 'date_to', 'employee_id')
    def _onchange_leave_dates(self):
        if __(self.date_from) and __(self.date_to):
            self.number_of_days = self._get_number_of_days(__(self.date_from), __(self.date_to), self.employee_id.id)
        else:
            self.number_of_days = 0

    @api.constrains('state', 'number_of_days', 'holiday_status_id')
    def _check_holidays(self):
        for holiday in self:
            if holiday.holiday_type != 'employee' or False or not holiday.employee_id or holiday.holiday_status_id.limit:
                continue
            # leave_days = holiday.holiday_status_id.get_days(holiday.employee_id.id)[holiday.holiday_status_id.id]
            if self.employee_id.current_balance(self.holiday_status_id.id, __(self.date_from)) < self.number_of_days:
                raise ValidationError(_('The number of remaining leaves is not sufficient for this leave type.\n'
                                        'Please verify also the leaves waiting for validation.'))

    @api.constrains('number_of_days')
    def check_non_annual_leave(self):
        if self.request_reason != 'non-annual':
            return
        # Maximum number of days
        if self.number_of_days > self.holiday_status_id.days_per_leave:
            raise ValidationError(_("Sorry!! You can not request more %s day/s for %s" %
                                    (self.holiday_status_id.days_per_leave, self.holiday_status_id.name)))
        # Gender
        if self.holiday_status_id.who_request == 'male' and self.employee_id.gender != 'male':
            raise ValidationError(_("Sorry!! Only Male employees can request \"%s\" Leave" % (self.holiday_status_id.name)))
        if self.holiday_status_id.who_request == 'female' and self.employee_id.gender != 'female':
            raise ValidationError(_("Sorry!! Only Female employees can request \"%s\" Leave" % (self.holiday_status_id.name)))
        # Marital Status
        if self.holiday_status_id.marital_status == 'Single' and self.employee_id.marital != 'single':
            raise ValidationError(_("Sorry!! Only Single employees can request \"%s\" Leave" % (self.holiday_status_id.name)))
        if self.holiday_status_id.marital_status == 'Married' and self.employee_id.marital != 'married':
            raise ValidationError(_("Sorry!! Only Married employees can request \"%s\" Leave" % (self.holiday_status_id.name)))
        # Religion
        if self.holiday_status_id.marital_status == 'Muslim' and self.employee_id.marital != 'Muslim':
            raise ValidationError(_("Sorry!! Only Muslim employees can request \"%s\" Leave" % (self.holiday_status_id.name)))
        if self.holiday_status_id.marital_status == 'Non-Muslim' and self.employee_id.marital != 'Non-Muslim':
            raise ValidationError(_("Sorry!! Only Non-Muslim employees can request \"%s\" Leave" % (self.holiday_status_id.name)))

    @api.one
    def set_refused_by(self):
        self.refused_by = self.env.uid
        self.refused_date = datetime.now().strftime('%Y-%m-%d')
        # body = "Document Refused"
        # self.message_post(body=body, message_type='email')

    @api.multi
    def holidays_reset_message(self):
        body = "Document Reset to draft"
        # self.message_post(body=body, message_type='email')

    @api.one
    def set_confirmed_by(self):
        self.direct_approved_by = self.env.uid
        self.direct_approved_date = datetime.now().strftime('%Y-%m-%d')
        # /////////////  send mail custom notification  /////////////////////////////////////////////
        # partners_ids = [self.employee_id.department_manager.user_id.partner_id]
        # body_html = temp4
        # body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
        #     body_html, 'hr.leave', [self.id], )
        # body = body and body[self.id] or False
        #
        # self.message_post(
        #     subject='طلب موافقة مدير القسم لأجازة Department manager Approval is required for a leave request',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=self.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)
        # /////////////////////////////////////////////////////////////
        # body = "Document Approved By Direct Manager"
        # self.message_post(body=body, message_type='email')
        if not self.employee_id.department_manager or not self.employee_id.department_manager.active or self.employee_id.department_manager == self.employee_id.parent_id or self.employee_id == self.employee_id.department_manager:
            self.sudo().action_validate()

    @api.one
    def check_confirm_authorized(self):
        if self.employee_id.department_manager.user_id.id != self.env.uid and self.employee_id.parent_id.user_id.id != self.env.uid and not self.env.user.has_group(
                'saudi_hr_employee.group_leave_bypass_direct_manager'):
            raise ValidationError(
                'Not Allowed !! \n You did not have the permission to click on ( Direct manager approval ) for this employee ( %s ), only His / Her Department manager  ( %s ) can click on this button, (or) you must have access to (Leave request Bypass Department manager approval)' % (
                    self.employee_id.name, self.employee_id.department_manager.name))

    @api.one
    def _compute_report_holiday_till_date(self):
        self.report_holiday_till_date = self.date_from.strftime("%Y-%m-%d")
        self.report_holiday_till_balance = self.current_balance
        # if self.remaining_balance or self.remaining_balance == 0 or not self.holiday_status_id.max_advance_type or self.holiday_status_id.max_advance_type == 'fixed':
        #     self.report_holiday_till_balance = self.current_balance
        #     allocations = self.env['hr.leave'].search([
        #         ('type', '=', 'add'),
        #         ('state', '=', 'validate'),
        #         ('employee_id', '=', self.employee_id.id),
        #         ('contract_id', '=', self.contract_id.id),
        #         ('holiday_status_id', '=', self.holiday_status_id.id),
        #     ], order='allocation_date desc')
        #     if allocations and __(allocations[0].allocation_date):
        #         self.report_holiday_till_date = __(allocations[0].allocation_date)
        #     else:
        #         self.report_holiday_till_date = __(self.adjusted_date)
        # else:
        #     date_from = datetime.strptime(__(self.adjusted_date), "%Y-%m-%d")
        #     year_end_date = date(date_from.year, 12, 31)
        #     self.report_holiday_till_date = year_end_date.strftime("%Y-%m-%d")
        #     self.report_holiday_till_balance = self.current_balance

    @api.one
    def alternative_approve(self):
        if self.alternative_employee_id.user_id.id != self.env.uid and not self.env.user.has_group(
                'saudi_hr_employee.group_leave_Bypass_alternative_approval'):
            raise ValidationError(
                'Not Allowed !! \n You did not have the permission to click on ( Alternative employee approval ) for this employee ( %s ), '
                'only ( %s ) is allowed to click on this button, (or) you must have access to (Leave request Bypass Alternative employee approval)' % (
                    self.employee_id.name, self.alternative_employee_id.name))
        self.sudo().alternative_approval = True
        # body = "Alternative employee approval by %s" % self.env.user.name
        # self.sudo().message_post(body=body, message_type='email')

    @api.one
    def action_approve(self):
        self.check_alternative()

        if self.employee_id.department_manager.user_id.id != self.env.uid and not self.env.user.has_group(
                'saudi_hr_employee.group_leave_bypass_department_manager'):
            raise ValidationError(
                'Not Allowed !! \n You did not have the permission to click on ( Department manager approval  ) for this employee ( %s ), only His / Her Department manager  ( %s ) can click on this button, (or) you must have access to (Leave request Bypass Department manager approval)' % (
                    self.employee_id.name, self.employee_id.department_manager.name or _("Not set")))

        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        self.write({'state': 'validate1', 'first_approver_id': current_employee.id})
        self.department_approved_by = self.env.uid
        self.department_approved_date = datetime.now().strftime('%Y-%m-%d')

    @api.one
    def holiday_final_checks(self):
        # if not self.holiday_status_id.limit and self.expected_remaining_balance < 0 and self.holiday_status_id.type == "Annual Leave":
        #     if not self.request_leave_in_advance:
        #         message = _(
        #             "Not allowed, \n Dear HR team, employee ( %s ) Requested for ( %s ) number of requested days is ( %s ) , at leave start date  ( %s ) employee’s balance expected to be ( %s )  his balance is not sufficient to approve this request. In order to accept this leave request, you must select ( Request leave in advance ). Note: if you request for a leave in advance, employee balance will be negative. each month employee balance will be increased automatically.") % (
        #                       self.employee_id.name, self.holiday_status_id.name, self.number_of_days, self.date_from,
        #                       self.expected_balance_leave_start)
        #         raise ValidationError(message)

        if self.reconciliation_method == 'Stop payslip during leave and use leave reconciliation':
            domain = [
                ('date_from', '<=', __(self.date_to)),
                ('date_to', '>=', __(self.date_from)),
                ('employee_id', '=', self.employee_id.id),
                ('state', '!=', 'cancel'),
            ]
            conflict_payslips = self.env['hr.payslip'].search(domain)
            if conflict_payslips:
                message = _(
                    "Data Error !! \n Based on your configuration, the leave reconciliation method for ( %s ) is to Stop payslip during this leave and create leave reconciliation, when we reviewed old payslip for this employee, we found that there is old payslip for the same employee which conflict with this leave request !!! Kindly review your old payslip data. ") % self.holiday_status_id.name
                raise ValidationError(message)
        if self.holiday_status_id.check_iqama_expiry and self.employee_id.country_id.check_iqama_expiry:
            if not __(self.iqama_expiry_date):
                raise ValidationError(_("Data Error!\n\
                    Not allowed to approve this leave request, there is no Iqama / National ID expiry date for the selected employee."))
            elif __(self.date_to, True) and not __(self.iqama_expiry_date) > __(self.date_to, True).split(' ')[0]:
                raise ValidationError(_("Data Error !!\n\
                    Not allowed to approve this leave request, Employee Iqama / National ID will expire before return from leave, kindly renew employee Iqama\
                    before approving this leave request."))
        if self.holiday_status_id.check_passport_expiry and self.employee_id.country_id.check_passport_expiry:
            if not __(self.passport_expiry_date):
                raise ValidationError(_("Data Error!\n\
                    Not allowed to approve this leave request, there is no  passport expiry date for the selected employee."))
            elif not __(self.passport_expiry_date) > __(self.date_to, True).split(' ')[0]:
                raise ValidationError(_("Data Error !!\n\
                    Not allowed to approve this leave request, Employee passport will expire before return from leave, kindly renew employee Iqama before approving\
                this leave request."))
        if __(self.last_working_day) > __(self.date_from, True).split(' ')[0]:
            raise ValidationError(_("Date Error!\n\
                Last working date must be equal to or less than leave start date!."))
        if not __(self.last_working_day):
            raise ValidationError(_("Please select last working day."))

        old_leave_requests = self.env['hr.leave'].search(
            [('mandatory_return_from_leave', '=', 'Yes'), ('state', '=', 'validate'),
             ('employee_id', '=', self.employee_id.id),
             ('leave_request_extend_id', '=', False), ('return_from_leave', '=', False), ('date_from', '<', __(self.date_from))])
        if old_leave_requests and self.mandatory_return_from_leave == 'Yes':
            raise ValidationError(_("Not allowed !!\n\
                Not allowed to approve this leave for this employee, our records indicated that this employee has old leave request, till now this employee didn’t return from this leave.\n To solve this issue, kindly create a return from a leave for this employee, then you can request for another leave."))

    @api.one
    def action_validate(self):
        self.holiday_final_checks()
        self.check_alternative()
        if self.original_leave_request_id:
            self.original_leave_request_id.leave_extended = True
            body = "Leave Extended"
            self.original_leave_request_id.message_post(body=body, message_type='email')
        self.current_balance_ = self.employee_id.leaves_count
        # Employee info
        self.iqama_id_ = self.employee_id.identification_id
        self.iqama_expiry_date_ = __(self.employee_id.iqama_expiry_date)
        self.passport_no_ = self.employee_id.passport_id
        self.passport_expiry_date_ = __(self.employee_id.passport_expiry_date)
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        self.write({'state': 'validate', 'second_approver_id': current_employee.id})
        if self.holiday_type == 'employee':
            self._validate_leave_request()
        elif self.holiday_type == 'category':
            leaves = self.env['hr.leave']
            for employee in self.category_id.employee_ids:
                values = self._prepare_create_by_category(employee)
                leaves += self.with_context(mail_notify_force_send=False).create(values)
            # TODO is it necessary to interleave the calls?
            leaves.action_validate()
        # res = super(hr_leaves, self).action_validate()
        self.hr_approved_by = self.env.uid
        self.hr_approved_date = datetime.now().strftime('%Y-%m-%d')
        # /////////////  send mail custom notification  /////////////////////////////////////////////
        # partners_ids = [self.employee_id.user_id.partner_id]
        #
        # body_html = temp7
        # body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
        #     body_html, 'hr.leave', [self.id], )
        # body = body and body[self.id] or False
        #
        # self.message_post(
        #     subject='تمت الموافقه على طلب الأجازه Leave request approved',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=self.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)
        # /////////////////////////////////////////////////////////////
        body = "Document Approved By HR Department"
        # self.message_post(body=body, message_type='email')
        return True

    @api.one
    def recompute_balance(self):
        pass

    # @api.v7
    @api.one
    def _get_can_reset(self):
        """User can reset a leave request if it is its own leave request or if
        he is an Hr Manager. """
        user = self.env.user
        group_hr_user_id = self.env['ir.model.data'].get_object_reference('hr', 'group_hr_user')[1]
        group_hr_direct_manager_id = self.env['ir.model.data'].get_object_reference('saudi_hr_employee', 'group_hr_direct_manager')[1]
        if group_hr_user_id in [g.id for g in user.groups_id]:
            self.can_reset = True
        elif group_hr_direct_manager_id in [g.id for g in user.groups_id]:
            self.can_reset = True
        else:
            if self.employee_id and self.employee_id.user_id and self.employee_id.user_id.id == self.env.uid:
                self.can_reset = True
            else:
                self.can_reset = False

    @api.one
    @api.depends('employee_id')
    def _compute_employee_is_manager(self):
        branches = self.env['hr.branch'].search([('manager_id', '=', self.employee_id.id)])
        departments = self.env['hr.department'].search([('manager_id', '=', self.employee_id.id)])
        if departments or branches:
            self.report_employee_is_manager = True
        else:
            self.report_employee_is_manager = False

    @api.one
    @api.depends('request_reason', 'holiday_status_id', 'number_of_days')
    def get_reconciliation_method_readonly(self):
        if self.request_reason == 'annual' and self.holiday_status_id.reconciliation_method == 'Stop payslip during leave and use leave reconciliation' and self.holiday_status_id.leave_reconciliation_minimum <= self.number_of_days:
            self.reconciliation_method_readonly = False
        else:
            self.reconciliation_method_readonly = True

    @api.one
    def check_alternative(self):
        if self.employee_id.id == self.alternative_employee_id.id:
            raise ValidationError('Employee %s can not be alternative for himself' % self.employee_id.name)
        if not self.skip_basic_return:
            domain = [
                ('date_from', '<=', __(self.date_to)),
                ('date_to', '>=', __(self.date_from)),
                ('alternative_employee_id', '=', self.employee_id.id),
                ('state', '=', 'validate'),
            ]
            me_alternative_leaves_conflicts = self.env['hr.leave'].search(domain)
            if me_alternative_leaves_conflicts:
                for conflict in me_alternative_leaves_conflicts:
                    raise ValidationError('Not allowed !! \n Employee ( %s ) requests for a leave between ( %s ) and  ( %s ) '
                                          'your system found that ( %s ) is an alternative employee for ( %s ) '
                                          'on a leave request starts on ( %s ) and ends on ( %s )'
                                          'You have 2 options.\n'
                                          '1 - Change the start and end date for ( %s ) to avoid any conflict with  ( %s ) leave\n'
                                          '2 - Employee ( %s ) Cancel his leave or return early from leave.\n'
                                          'As HR manager, you still have the option to Skip waiting for the return of the basic employee '
                                          'from his leave by check ( Skip waiting for the return of the basic employee from his leave) field.'
                                          % (self.employee_id.name, __(self.date_from).split(' ')[0], __(self.date_to).split(' ')[0],
                                             self.employee_id.name, conflict.employee_id.name,
                                             __(conflict.date_from).split(' ')[0], __(conflict.date_to).split(' ')[0],
                                             self.employee_id.name, conflict.employee_id.name,
                                             conflict.employee_id.name,))

        if self.show_alternative_employee and not self.accept_without_alternative:
            if not self.alternative_employee_id:
                raise ValidationError('Data Error !! \n Not allowed to approve this leave request ( %s ) '
                                      'Based on your company policy, leave type ( %s ) and job position  ( %s ) '
                                      'requires to have alternative employee, if number if leave days is equal to or greater than ( %s ) '
                                      'kindly select the alternative employee.'
                                      % (self.name, self.holiday_status_id.name, self.job_id.name, self.holiday_status_id.alternative_employee_days))

            domain = [
                ('date_from', '<=', __(self.date_to)),
                ('date_to', '>=', __(self.date_from)),
                ('employee_id', '=', self.alternative_employee_id.id),
                ('state', '=', 'validate'),
            ]
            alternative_leaves_conflicts = self.env['hr.leave'].search(domain)
            if alternative_leaves_conflicts:
                for conflict in alternative_leaves_conflicts:
                    raise ValidationError('Not allowed !! \n Employee ( %s ) requests for a leave between ( %s ) and  ( %s ) '
                                          'Alternative employee for ( %s ) is ( %s ) your system found that ( %s ) have approved leave '
                                          'request between ( %s ) and ( %s ) which conflict with ( %s ) leave request.\n'
                                          'You have 3 options.\n'
                                          '1 - Change the start and end date for ( %s ) to avoid any conflict with  ( %s ) leave\n'
                                          '2 - Select another alternative employee for ( %s )\n'
                                          '3 - Employee ( %s ) Cancel his leave or return early from leave.\n'
                                          % (self.employee_id.name, __(self.date_from).split(' ')[0], __(self.date_to).split(' ')[0],
                                             self.employee_id.name, self.alternative_employee_id.name, self.alternative_employee_id.name,
                                             __(conflict.date_from).split(' ')[0], __(conflict.date_to).split(' ')[0], self.employee_id.name,
                                             self.employee_id.name, self.alternative_employee_id.name,
                                             self.employee_id.name, self.alternative_employee_id.name,))

            if not self.alternative_approval and self.state == 'confirm':
                raise ValidationError('Not Allowed !! \n Employee ( %s  ) Leave request requires alternative '
                                      'employee approval before HR department approval.' % self.employee_id.name)

    @api.one
    @api.depends('holiday_status_id', 'job_id', 'date_from', 'date_to')
    def _compute_show_alternative_employee(self):
        if self.holiday_status_id.is_alternative_employee and self.number_of_days >= self.holiday_status_id.alternative_employee_days:
            self.show_alternative_employee = True
        else:
            self.show_alternative_employee = False

    @api.one
    @api.depends('leave_days_ids')
    def _compute_days_per_months(self):
        self.days_per_months = sum(line.days for line in self.leave_days_ids)

    def get_duration_number_of_days(self, date_from, date_to):
        # Compute and update the number of days
        if date_to and date_from:
            # ///////// Check if working days or calendar days
            if self.holiday_status_id == self.annual_leave_policy:
                working_calendar = self.contract_id.working_calendar
            else:
                working_calendar = self.holiday_status_id.working_calendar

            if working_calendar == 'Calendar days':
                national_holidays = self.env['hr.national.holiday'].search([('duration_in_leave_request', '=', 'No'), ('state', '=', 'Confirmed')])
                total_conflict_days = 0
                for holiday in national_holidays:
                    if __(holiday.end_date) < date_from or __(holiday.start_date) > date_to:
                        continue
                    else:
                        conflict_start = __(holiday.start_date) > date_from and __(holiday.start_date) or date_from
                        conflict_end = __(holiday.end_date) < date_to and __(holiday.end_date) or date_to
                        conflict_days = self._get_number_of_days(conflict_start, conflict_end, self.employee_id.id) + 1
                        total_conflict_days += conflict_days
                diff_day = self._get_number_of_days(date_from, date_to, self.employee_id.id)
                number_of_days = round(math.floor(diff_day)) + 1 - total_conflict_days
                return number_of_days
        else:
            number_of_days = 0
            return number_of_days

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

    @api.one
    @api.depends('holiday_status_id', 'annual_leave_policy')
    def _compute_days_label(self):
        if self.holiday_status_id == self.annual_leave_policy:
            working_calendar = self.contract_id.working_calendar
        else:
            working_calendar = self.holiday_status_id.working_calendar

        self.days_label = working_calendar

    @api.one
    def check_holidays(self):
        if self.holiday_type != 'employee' or False or not self.employee_id or self.holiday_status_id.limit or self.holiday_status_id == self.annual_leave_policy:
            return True
        leave_days = self.env['hr.leave.type'].browse(self.holiday_status_id.id).get_days(self.employee_id.id)[self.holiday_status_id.id]
        if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or \
                float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
            return False
        return True

    @api.one
    @api.depends()
    def get_old_leave_requests(self):
        domain = [['employee_id', '=', self.employee_id.id], ['create_date', '<=', __(self.create_date, True)]]
        if not isinstance(self.id, models.NewId):
            domain.append(['id', '!=', self.id])
        self.old_leave_requests_ids = [l.id for l in self.search(domain)]

    @api.one
    @api.depends('date_from', 'date_to')
    def get_date_day(self):
        if self.date_from:
            self.date_from_day = self.get_week_day(__(self.date_from, True), 'datetime')
        if self.date_to:
            self.date_to_day = self.get_week_day(__(self.date_to, True), 'datetime')
        if self.last_working_day:
            self.last_working_week_day = self.get_week_day(__(self.last_working_day), 'date')
        if self.expected_working_day:
            self.expected_working_week_day = self.get_week_day(__(self.expected_working_day), 'date')

    def get_week_day(self, some_date, type):
        week_day = {'Monday': 'Monday / الإثنين', 'Tuesday': 'Tuesday / الثلاثاء', 'Wednesday': 'Wednesday / الأربعاء',
                    'Thursday': 'Thursday / الخميس',
                    'Friday': 'Friday / الجمعة', 'Saturday': 'Saturday / السبت', 'Sunday': 'Sunday / الأحَد'}
        if type == 'datetime':
            some_date_datetime = datetime.strptime(some_date, "%Y-%m-%d %H:%M:%S")
        elif type == 'date':
            some_date_datetime = datetime.strptime(some_date, "%Y-%m-%d")
        else:
            return ''
        some_date_day = calendar.day_name[some_date_datetime.weekday()]
        return week_day[some_date_day]

    @api.one
    @api.depends('employee_id')
    def get_employee_info(self):
        self.iqama_id = self.iqama_id_ or self.employee_id.identification_id
        self.iqama_expiry_date = __(self.iqama_expiry_date_) or __(self.employee_id.iqama_expiry_date)
        self.passport_no = self.passport_no_ or self.employee_id.passport_id
        self.passport_expiry_date = __(self.passport_expiry_date_) or __(self.employee_id.passport_expiry_date)

    @api.one
    @api.depends('leave_reconciliation_amount', 'paid_amount')
    def get_remaining_amount(self):
        remaining_amount = self.leave_reconciliation_amount - self.paid_amount
        leave_fully_reconciled = False
        if remaining_amount <= 0:
            leave_fully_reconciled = True
        self.remaining_amount = remaining_amount
        self.leave_fully_reconciled = leave_fully_reconciled

    @api.one
    def _compute_paid_amount(self):
        self.paid_amount = round(sum(l.amount for l in self.reconciliation_paid_line_ids), 2)

    @api.one
    @api.depends('contract_id', 'number_of_days', 'request_reason', 'reconciliation_based_on', 'holiday_status_id', 'reconciliation_method')
    def get_leave_reconciliation_amount(self):
        based_on_value = 0
        if self.reconciliation_method == 'Stop payslip during leave and use leave reconciliation':
            if self.request_reason == 'annual' and self.contract_id and self.holiday_status_type == 'Annual Leave':
                based_on_value = self.total_salary
            self.leave_reconciliation_amount = round((based_on_value / 30) * (self.number_of_days), 2)
        else:
            self.leave_reconciliation_amount = 0

    @api.one
    @api.depends('current_balance', 'number_of_days')
    def get_remaining_balance(self):
        self.remaining_balance = self.current_balance - self.number_of_days

    @api.one
    @api.depends('employee_id', 'request_reason', 'contract_id', 'date_from')
    def get_current_balance(self):
        if self.request_reason == 'annual':
            self.current_balance = self.current_balance_ or self.employee_id.current_balance(self.holiday_status_id.id, __(self.date_from))

    @api.one
    @api.depends('employee_id', 'request_reason', 'contract_id')
    def get_button_extend_invisible(self):
        button_timeout = False
        if not self.date_to:
            self.button_extend_invisible = False
            return
        if self.date_to:
            button_end_date = datetime.strptime(__(self.date_to, True), '%Y-%m-%d %H:%M:%S') + timedelta(self.holiday_status_id.leave_extend_timeout)
            button_timeout = datetime.now() > button_end_date

        # self.state != "validate" or
        if button_timeout or self.leave_request_extend_id or self.return_from_leave or self.env.context.get(
                'popup') == True or self.state != 'validate':
            self.button_extend_invisible = True
        else:
            self.button_extend_invisible = False

    @api.one
    @api.depends('employee_id')
    def _compute_contract(self):
        for rec in self:
            contracts = self.env['hr.contract'].search([('employee_id', '=', rec.employee_id.id), ('active', '=', True)])
            if len(contracts):
                rec.contract_id = contracts[0].id

    @api.one
    @api.depends('employee_id', 'date_from')
    def compute_last_working_day(self):
        if self.date_from and self.employee_id:
            start_date = datetime.strptime(__(self.date_from, True), "%Y-%m-%d %H:%M:%S")
            start_date_yesterday = start_date - timedelta(days=1)
            self.last_working_day = self.get_last_working_date(start_date_yesterday, self.employee_id).strftime("%Y-%m-%d")

    def get_last_working_date(self, checked_date, employee_id):
        # //////////////  Check For Old Leave Request /////////////////////////////////////////////
        old_leave_requests = self.env['hr.leave'].search(
            [('state', '!=', 'refuse'), ('employee_id', '=', employee_id.id), ('date_from', '<=', checked_date.strftime('%Y-%m-%d %H:%M:%S')),
             ('date_to', '>=', checked_date.strftime('%Y-%m-%d %H:%M:%S'))])
        if old_leave_requests:
            for old_leave_request in old_leave_requests:
                leave_start_date = datetime.strptime(__(old_leave_request.date_from, True), "%Y-%m-%d %H:%M:%S")
                leave_start_date_yesterday = leave_start_date - timedelta(days=1)
                return self.get_last_working_date(leave_start_date_yesterday, employee_id)

        # //////////////  Check For Old National Holidays /////////////////////////////////////////////
        old_national_holidays = self.env['hr.national.holiday'].search(
            [('start_date', '<=', checked_date.strftime('%Y-%m-%d')), ('end_date', '>=', checked_date.strftime('%Y-%m-%d'))])
        if old_national_holidays:
            for old_national_holiday in old_national_holidays:
                n_holiday_start_date = datetime.strptime(__(old_national_holiday.start_date, ), "%Y-%m-%d")
                n_holiday_start_date_yesterday = n_holiday_start_date - timedelta(days=1)
                return self.get_last_working_date(n_holiday_start_date_yesterday, employee_id)

        # //////////////  Check For Old Working schedule Days /////////////////////////////////////////////
        week_day = checked_date.weekday()
        contracts = self.env['hr.contract'].search([('employee_id', '=', employee_id.id), ('active', '=', True)])
        contract = contracts and contracts[0] or False
        day_on_working_days = 0
        if contract and contract.attendance_ids:
            for attendance_id in contract.attendance_ids:
                if week_day == int(attendance_id.dayofweek):
                    day_on_working_days = 1
            if not day_on_working_days:
                checked_date_yesterday = checked_date - timedelta(days=1)
                return self.get_last_working_date(checked_date_yesterday, employee_id)

        return checked_date

    @api.one
    @api.depends('employee_id', 'date_to')
    def compute_expected_working_day(self):
        if __(self.date_to) and self.employee_id:
            end_date = datetime.strptime(__(self.date_to, True), "%Y-%m-%d %H:%M:%S")
            end_date_tomorrow = end_date + timedelta(days=1)
            self.expected_working_day = self.get_expected_working_day(end_date_tomorrow, self.employee_id).strftime("%Y-%m-%d")

    @api.model
    def _check_state_access_right(self, vals):
        return True

    @api.multi
    def action_extend_request(self):
        if self.leave_request_extend_id:
            raise ValidationError(_(
                "There is an old request to extend this leave, kindly refuse or delete the old one, then you can request for a new extension.If you want to re-extend this leave, go to the extended leave which you previously created and request for a new extension."))
        leave_end = self.env.context.get("date_to", False)
        extend_start = datetime.strptime(leave_end, '%Y-%m-%d %H:%M:%S') + timedelta(1)
        custom_context = {"default_employee_id": self.env.context.get("employee_id", False),
                          "default_date_from": extend_start.strftime('%Y-%m-%d %H:%M:%S'),
                          "default_original_leave_request_id": self.env.context.get("active_id", False), }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('saudi_hr_leaves.leave_request_form').id,
            'context': custom_context,
            'target': 'current',
        }

    @api.multi
    def action_reconcile(self):
        custom_context = {
            "default_name": "Leave reconciliation",
            "default_employee_id": self.env.context.get("employee_id", False),
            "default_type": "reconciliation",
            "default_linked_leave_request_id": self.env.context.get("active_id", False),
        }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.reconciliation',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('saudi_hr_leaves.hr_leave_reconciliation_form').id,
            'context': custom_context,
            'target': 'current',
        }

    @api.model_cr
    def init(self):
        self.env.cr.execute('ALTER TABLE hr_leave ALTER COLUMN allocation_date DROP NOT NULL')

    _sql_constraints = [
        ('date_check', "CHECK ( 1 = 1 )", "The number of days must be greater than 0."),
    ]

    @api.multi
    def check_adjust_day(self):
        for record in self:
            if record.report_employee_is_manager and not self.env.user.has_group(
                    'saudi_hr_employee.group_leave_hr_approval_for_managers'):
                raise ValidationError(
                    'Not Allowed !! \n You did not have the permission to approve leave request for Department managers or branch managers, only HR manager or users who have access rights = (Leave request HR approval for managers) are allowed to click on this button.')

    @api.multi
    def set_approved_by(self):
        for record in self:
            record.approved_by = self.env.uid

    # @api.v7
    def localize_dt(self, date, to_tz):
        from_zone = tz.gettz('UTC')
        to_zone = tz.gettz(to_tz)
        utc = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        utc = utc.replace(tzinfo=from_zone)
        res = utc.astimezone(to_zone)
        return res.strftime('%Y-%m-%d %H:%M:%S')

    @api.model
    def _get_number_of_days(self, date_from, date_to, employee_id):
        DATE_FORMAT = "%Y-%m-%d"
        from_dt = datetime.strptime(date_from, DATE_FORMAT)
        to_dt = datetime.strptime(date_to, DATE_FORMAT)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days  # + float(timedelta.seconds) / 86400
        return diff_day

    @api.model
    def get_user_tz(self):
        tz = self.env.user.tz
        return

    @api.multi
    def holidays_refuse(self):
        obj_emp = self.env['hr.employee']
        ids2 = obj_emp.search([('user_id', '=', self.env.user.id)])
        manager = ids2 and ids2[0] or False
        for holiday in self:
            if holiday.return_from_leave:
                raise exceptions.ValidationError(
                    "Not Allowed !! Not allowed to refuse / cancel this leave Request because there is a return from "
                    "leave already linked with this leave request. If you have any special cases which requires to "
                    "cancel this approved leave request, you can create a new leave allocation "
                    "to increase employee balance.")
            if holiday.state == 'validate1':
                holiday.write({'state': 'refuse', 'manager_id': manager})
            else:
                holiday.write({'state': 'refuse', 'manager_id2': manager})
            if holiday.original_leave_request_id:
                holiday.original_leave_request_id.leave_extended = False
                holiday.original_leave_request_id.leave_request_extend_id = False
            if holiday.leave_request_extend_id:
                raise exceptions.ValidationError(
                    "Not Allowed, There is a leave request to extend this leave, you must refuse or delete the leave request extension before refusing this leave.")
            holiday.holidays_cancel()
        return True

    @api.model
    def create(self, vals):
        res = super(hr_holidays_original, self).create(vals)
        if res.original_leave_request_id:
            res.original_leave_request_id.leave_request_extend_id = res
        if self.env.context.get('return_from_leave', False):
            return_from_leave_id = self.env.context.get('return_from_leave', False)
            return_from_leave = self.env['effective.notice'].search([('id', '=', return_from_leave_id)])
            return_from_leave.hr_department_approval()
        if True and not res.employee_id.parent_id and not res.employee_id.department_manager:
            res.action_confirm()
        return res

    @api.one
    def unlink(self):
        if not self._context.get('force_delete', False):
            if self.original_leave_request_id or self.leave_request_extend_id or self.leave_extended:
                raise ValidationError(_("Not allowed to delete this leave request because there is leave extension already linked with this leave."))
            if self.system_created:
                raise ValidationError(_(
                    "Not allowed!! \n Not allowed to delete a record which is automatically created by the system, try to refuse or set to new.  Or create another leave allocation with a negative / Positive sign to reverse this allocation."))
            if self.state not in ['draft', 'cancel', 'confirm']:
                raise UserError(_('You cannot delete a leave which is in %s state.') % (self.state,))
        return super(hr_leaves, self).unlink()

    def get_expected_working_day(self, checked_date, employee_id):
        # //////////////  Check For Old Leave Request /////////////////////////////////////////////
        old_leave_requests = self.env['hr.leave'].search(
            [('state', '!=', 'refuse'), ('employee_id', '=', employee_id.id), ('date_from', '<=', checked_date.strftime('%Y-%m-%d %H:%M:%S')),
             ('date_to', '>=', checked_date.strftime('%Y-%m-%d %H:%M:%S'))])
        if old_leave_requests:
            for old_leave_request in old_leave_requests:
                leave_end_date = datetime.strptime(__(old_leave_request.date_to, True), "%Y-%m-%d %H:%M:%S")
                leave_end_date_tomorrow = leave_end_date + timedelta(days=1)
                return self.get_expected_working_day(leave_end_date_tomorrow, employee_id)

        # //////////////  Check For Old National Holidays /////////////////////////////////////////////
        old_national_holidays = self.env['hr.national.holiday'].search(
            [('start_date', '<=', checked_date.strftime('%Y-%m-%d')), ('end_date', '>=', checked_date.strftime('%Y-%m-%d'))])
        if old_national_holidays:
            for old_national_holiday in old_national_holidays:
                n_holiday_end_date = datetime.strptime(__(old_national_holiday.end_date), "%Y-%m-%d")
                n_holiday_end_date_tomorrow = n_holiday_end_date + timedelta(days=1)
                return self.get_expected_working_day(n_holiday_end_date_tomorrow, employee_id)

        # //////////////  Check For Old Working schedule Days /////////////////////////////////////////////
        week_day = checked_date.weekday()
        contracts = self.env['hr.contract'].search([('employee_id', '=', employee_id.id), ('active', '=', True)])
        contract = contracts and contracts[0] or False
        day_on_working_days = 0
        if contract and contract.attendance_ids:
            for attendance_id in contract.attendance_ids:
                if week_day == int(attendance_id.dayofweek):
                    day_on_working_days = 1
            if not day_on_working_days:
                checked_date_tomorrow = checked_date + timedelta(days=1)
                return self.get_expected_working_day(checked_date_tomorrow, employee_id)

        return checked_date


class LeaveReconciliationPaidLine(models.Model):
    _name = "leave.reconciliation.paid.line"

    request_id = fields.Many2one('hr.leave', 'Leave Request')
    date = fields.Date('Date')
    amount = fields.Float('Amount')
    reconciliation_id = fields.Many2one('hr.leave.reconciliation', 'Leave Reconciliation')
    eos = fields.Many2one('employee.eos', 'EOS')
    note = fields.Char('Notes')


class leave_automatic_allocation(models.Model):
    _name = "leave.automatic.allocation"
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char('Code', readonly=True)
    allocate_till_date = fields.Date(string="Allocate Till This Date", required=True)
    confirm_uid = fields.Many2one('res.users', string="Confirmed By", readonly=True)
    notes = fields.Text(string="Notes")
    allocation_number = fields.Integer(string="Number Of Leaves Allocation")
    allocation_ids = fields.One2many('hr.leave', 'leave_automatic_allocation', 'Leave Allocations')
    count_allocations = fields.Integer('Number of allocations', compute='get_count_allocations')
    state = fields.Selection([
        ('New', 'New'),
        ('Confirmed', 'Confirmed'),
    ], string='Status', readonly=True, index=True, default='New', )
    leave_type = fields.Selection([
        ('Annual Leaves Only', 'Annual Leaves Only'),
        ('Non-annual Leaves Only', 'Non-annual Leaves Only'),
        ('All Leaves', 'All Leaves'),
    ], string='Annual / Non-annual')

    @api.one
    def unlink(self):
        if self.state == 'Confirmed':
            raise exceptions.ValidationError("Not allowed to delete this record because it is confirmed !!")
        return super(leave_automatic_allocation, self).unlink()

    @api.model
    def action_create_allocation(self, leave_type):
        if leave_type == 'annual':
            l_type = 'Annual Leaves Only'
            name = 'leave automatic allocation / annual'
        if leave_type == 'non_annual':
            l_type = 'Non-annual Leaves Only'
            name = 'leave automatic allocation / non-annual leave'
        if leave_type == 'all':
            l_type = 'All Leaves'
            name = 'leave automatic allocation / All leaves'
        if leave_type:
            allocation = self.create({
                'name': name,
                'leave_type': l_type,
                'allocate_till_date': datetime.today().strftime('%Y-%m-%d'),
            })
            allocation.action_confirm()

    @api.one
    @api.depends('allocation_ids', )
    def get_count_allocations(self):
        self.count_allocations = len(self.allocation_ids)

    @api.multi
    def open_allocations(self):
        return {
            'domain': [['id', 'in', self.allocation_ids.ids]],
            'name': _('Leave allocations'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.leave',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'tree_view_ref': 'hr_holidays.view_holiday_allocation_tree', 'form_view_ref': 'hr_holidays.edit_holiday_new'},
        }

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].sudo().next_by_code('Leave.automatic.allocation')
        res = super(leave_automatic_allocation, self).create(vals)
        return res

    @api.multi
    def action_confirm(self):
        for record in self:
            if record.leave_type in ['Annual Leaves Only', 'All Leaves']:
                contracts = self.env['hr.contract'].search([('active', '=', True)])
                for contract in contracts:
                    if not __(contract.adjusted_date):
                        raise ValidationError(
                            _("Can not find adjusted date for contract (%s) for employee (%s)" % (contract.name, contract.employee_id.name)))
                for contract in contracts:
                    if contract.annual_leave_policy.allocate_after_trial and not contract.end_trial_period_approved:
                        continue
                    if contract.adjusted_date >= __(record.allocate_till_date):
                        continue
                    start_after_months = contract.annual_leave_policy.start_allocation_after
                    adjusted_date = datetime.strptime(__(contract.adjusted_date), "%Y-%m-%d")
                    allocate_till_date = datetime.strptime(__(record.allocate_till_date), "%Y-%m-%d")
                    start_after_date = adjusted_date + relativedelta(months=start_after_months)
                    if allocate_till_date < start_after_date:
                        continue
                    adjusted_date_day = adjusted_date.day
                    allocate_till_date_day = allocate_till_date.day
                    effictive_allocate_date = allocate_till_date
                    if adjusted_date_day > 28:
                        raise ValidationError(
                            'Can not create allocation for employee ( %s ) because adjusted date day is greater than 28' % contract.employee_id.name)
                    if adjusted_date_day > allocate_till_date_day:
                        effictive_allocate_date = allocate_till_date.replace(day=adjusted_date_day)
                        effictive_allocate_date = effictive_allocate_date - relativedelta(months=1)
                    elif adjusted_date_day < allocate_till_date_day:
                        effictive_allocate_date = allocate_till_date.replace(day=adjusted_date_day)

                    duration = relativedelta(effictive_allocate_date, adjusted_date)
                    duration_months = duration.months + duration.years * 12
                    if duration_months == 0 or duration_months < start_after_months:
                        continue
                    first_calc_line = self.env['leaves.calc.method.line'].search(
                        [('greater_than', '=', 0), ('leave_type_id', '=', contract.annual_leave_policy.id)])
                    if not first_calc_line:
                        raise exceptions.ValidationError(
                            "Out of range!! Cannot calculate automatic leave Please review your leave type’s configuration. for contract (%s)" % contract.name)

            if record.leave_type in ['Non-annual Leaves Only', 'All Leaves']:
                employees = self.env['hr.employee'].search([('active', '=', True)])
                for employee in employees:
                    contracts = self.env['hr.contract'].search([('employee_id', '=', employee.id), ('active', '=', True)])
                    if len(contracts):
                        contract = contracts[0]
                    else:
                        continue
                    if __(contract.adjusted_date) > __(record.allocate_till_date):
                        continue
                    for leave_balance in employee.non_annual_leave_balance:
                        if leave_balance.holidays_status_id.allocate_after_trial and not contract.end_trial_period_approved:
                            continue
                        create_allocation = 0
                        number_of_days = 0
                        allow_minus_value = 0

                        if leave_balance.non_annual_frequency == 'contractual_year':
                            adjusted_date = datetime.strptime(__(contract.adjusted_date), "%Y-%m-%d")
                            allocate_till_date = datetime.strptime(__(record.allocate_till_date), "%Y-%m-%d")
                            year_start = date(allocate_till_date.year, adjusted_date.month, adjusted_date.day)
                            year_end = date(allocate_till_date.year + 1, adjusted_date.month, adjusted_date.day)
                            allocations = self.env['hr.leave'].search([
                                ('type', '=', 'add'),
                                ('state', '!=', 'refuse'),
                                ('employee_id', '=', employee.id),
                                ('holiday_status_id', '=', leave_balance.holidays_status_id.id),
                                ('allocation_date', '>=', year_start.strftime('%Y-%m-%d')),
                                ('allocation_date', '<', year_end.strftime('%Y-%m-%d'))
                            ])
                            if not len(allocations) or not leave_balance.net_balance == leave_balance.holidays_status_id.number_of_days:
                                create_allocation = 1
                                number_of_days = leave_balance.holidays_status_id.number_of_days - leave_balance.net_balance
                                if number_of_days < 0:
                                    allow_minus_value = 1

                        if create_allocation:
                            leave_allocation_data = {
                                'name': 'Non Annual leave automatic allocation',
                                'holiday_status_id': leave_balance.holidays_status_id.id,
                                'number_of_days': number_of_days,
                                'allow_minus_value': allow_minus_value,
                                'employee_id': employee.id,
                                'allocation_date': __(record.allocate_till_date),
                                'system_created': True,
                                'leave_automatic_allocation': record.id
                            }
                            leave_allocation = self.env['hr.leave.allocation'].create(leave_allocation_data)
                            leave_allocation.action_validate()

            record.write({'state': 'Confirmed'})
            # body = "Document Confirmed"
            # self.message_post(body=body, message_type='email')
        return {}

    def calc_leaves(self, start_line, months):
        if months >= start_line.number_of_months:
            current_leaves = start_line.number_of_months * start_line.monthly_balance
            remaining_months = months - start_line.number_of_months
        else:
            current_leaves = months * start_line.monthly_balance
            remaining_months = 0

        if remaining_months == 0:
            return current_leaves
        else:
            next_calc_line = self.env['leaves.calc.method.line'].search(
                [('greater_than', '=', start_line.less_than), ('leave_type_id', '=', start_line.leave_type_id.id)])
            if not next_calc_line:
                raise exceptions.ValidationError(
                    "Out of range!! Cannot calculate automatic leave Please review your leave type’s configuration.for leave type(%s)" % start_line.leave_type_id.name)
            return current_leaves + self.calc_leaves(next_calc_line, remaining_months)


class LeaveAttachments(models.Model):
    _name = "leave.attachment"

    leave_request_id = fields.Many2one('hr.leave', 'Leave request')
    name = fields.Char('Description')
    file = fields.Binary('Attachments')
    file_name = fields.Char('File name')
    note = fields.Char('Notes')


class Employee(models.Model):
    _inherit = "hr.employee"

    leaves_count = fields.Float('Number of Leaves', compute='_get_leaves_info')
    leaves_count_float = fields.Float('Number of Leaves', compute='_get_leaves_info')
    automatic_allocation_amount = fields.Float('Automatic Leave allocation', compute='_get_leaves_info')
    non_annual_leave_balance = fields.One2many('non.annual.leave.balance', 'employee_id', string="Non Annual leave Balance")
    start_working_date = fields.Date(string="Start Working Date", related="contract_id.start_work", readonly=True)
    effective_count = fields.Float('Effective Notices count', compute='get_effective_count')
    start_allocation_date = fields.Date('Start allocation date')

    @api.one
    def get_effective_count(self):
        self.effective_count = len(self.env['effective.notice'].search([['employee_id', '=', self.id]]))

    @api.multi
    def action_effective_notices(self):
        return {
            'domain': "[('employee_id','in',[" + ','.join(map(str, self.ids)) + "])]",
            'name': _('Effective Notices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'effective.notice',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.multi
    def open_employee_leaves(self):
        domain = [('employee_id', '=', self.id), ('holiday_status_id.limit', '=', False), ('state', '=', 'validate')]
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.id), ('active', '=', True)])
        if len(contracts):
            contract = contracts[0]
        else:
            contract = False
        if contract and contract.annual_leave_policy:
            domain.append(('holiday_status_id', '=', contract.annual_leave_policy.id))
        return {
            'domain': domain,
            'name': _('Leaves'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.leave',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'default_employee_id': self.id, 'readonly_by_pass': True}
        }

    @api.one
    @api.depends()
    def _get_leaves_info(self):
        self.leaves_count = self.current_balance(self.contract_id.annual_leave_policy.id)

    @api.model
    def to_dt(self, date, is_datetime=False):
        return datetime.strptime(date, "%Y-%m-%d" if not is_datetime else "%Y-%m-%d %H:%M:%S")

    @api.one
    def _compute_leaves_count(self):
        self.leaves_count = self.leaves_count_float = self.current_balance(self.contract_id.annual_leave_policy.id)

    @api.model
    def current_balance(self, leave_type_id, to_date=False):
        if not leave_type_id or not self.contract_id:
            return 0
        dt_fmt = "%Y-%m-%d"
        to_date = to_date and to_date or self._context.get('to_date', False) or datetime.today().strftime(dt_fmt)
        to_date = to_date.split(' ')[0]
        domain = [('employee_id', '=', self.id), ('is_init', '=', True), ('allocation_date', '<=', to_date),
                  ('holiday_status_id', '=', leave_type_id)]
        init_allocations = self.env['hr.leave.allocation'].search(domain, order="allocation_date desc")
        init_allocation_date = init_allocations and __(init_allocations[0].allocation_date) or False
        join_date = __(self.contract_id.start_work)
        start_allocate_date = init_allocation_date or __(self.start_allocation_date) or join_date
        leave_type = self.env['hr.leave.type'].browse(leave_type_id)
        total_allocation = 0
        # ====== Automatic Allocations =======
        for line in self.env['leaves.calc.method.line'].search([('id', 'in', leave_type.lines.ids)], order='greater_than'):
            line_start_date = (self.to_dt(join_date) + relativedelta(months=line.greater_than)).strftime(dt_fmt)
            line_end_date = (self.to_dt(join_date) + relativedelta(months=line.less_than < 12000 and line.less_than or 12000)).strftime(dt_fmt)
            d1 = line_start_date >= start_allocate_date and line_start_date or start_allocate_date
            d2 = line_end_date <= to_date and line_end_date or to_date
            if d2 <= d1:
                break
            diff = relativedelta(self.to_dt(d2), self.to_dt(d1))
            month_balance = line.balance / 12.0
            daily_balance = month_balance / 30.0
            total_allocation += (diff.years * line.balance) + (diff.months * month_balance) + ((diff.days + 1) * daily_balance)
        self.automatic_allocation_amount = total_allocation
        # ==== Other allocations After init allocation ====
        additional_allocation = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.id), ('allocation_date', '>=', start_allocate_date), ('holiday_status_id', '=', leave_type_id)])
        total_allocation += sum([a.number_of_days for a in additional_allocation])
        # ========= Leaves ======
        holidays = self.env['hr.leave'].search([
            ('allocation_date', '>', start_allocate_date),
            ('employee_id', '=', self.id), ('state', '=', 'validate')
        ])
        total_holidays = sum([h.number_of_days for h in holidays])
        balance = total_allocation - total_holidays
        return balance

    non_annual_frequency = fields.Selection([
        ('contractual_year', 'Each contractual year ( hiring dat to next year)'),
        ('one_time', 'one time per live.'),
        ('per_request', 'based on request (no limitation)'),
        ('hijri_year', 'Per hijri year'),
        ('year', 'Per Year'),
        ('year_request', 'Per year based on first request'),
        ('contract', 'Per contract'),
    ], string='Non annual leave Frequency')

    def get_non_annual_leave_balance(self, leave_type_id, date_from):
        leave_type = self.env['hr.leave.type'].browse(leave_type_id)


class non_annual_leave_balance(models.Model):
    _name = "non.annual.leave.balance"

    holidays_status_id = fields.Many2one('hr.leave.type', string='Description')
    non_annual_frequency = fields.Selection([
        ('contractual_year', 'Each contractual year ( hiring dat to next year)'),
        ('per_request', 'based on request (no limitation)'),
    ], string='Non annual leave Frequency')
    total_allocated_days = fields.Integer('Total Days Allocated')
    total_requested_days = fields.Integer('Total Days Requested')
    net_balance = fields.Integer('Net Balance', compute='_compute_net_balance')
    last_leave_request = fields.Many2one('hr.leave', string="Last Leave Request")
    leave_request_date = fields.Datetime('Leave Request Date', related="last_leave_request.date_from", readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')

    @api.depends('total_allocated_days', 'total_requested_days')
    def _compute_net_balance(self):
        for rec in self:
            rec.net_balance = rec.total_allocated_days + rec.total_requested_days

