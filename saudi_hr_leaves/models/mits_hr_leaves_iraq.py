# -*- coding: utf-8 -*-

from openerp import models, fields, api, exceptions, _, SUPERUSER_ID
from openerp.exceptions import UserError, ValidationError, QWebException
from datetime import datetime, date
from datetime import timedelta
import calendar
from dateutil.relativedelta import relativedelta
from openerp import tools
import math
import pytz
from dateutil import tz
import os
from openerp.tools import float_compare

from openerp.addons.hr_holidays.hr_holidays import hr_holidays as hr_holidays_original


class effective_notice(models.Model):
    _name = 'effective.notice'
    _inherit = ['mail.thread']
    _order = "id desc"
    _rec_name = 'desc'

    name = fields.Char(_('Code'), readonly=True)
    desc = fields.Char('Description', required=True)
    employee_id = fields.Many2one('hr.employee', string=_('Employee'), required=True,
                                  default=lambda self: self.env.context.get('active_id', False) or self.env.user.employee_ids and
                                                       self.env.user.employee_ids[0].id)
    employee_number = fields.Char(_('Employee Number'))
    department_id = fields.Many2one('hr.department', string=_('Department'))
    job_id = fields.Many2one('hr.job', string=_('Job Title'))
    country_id = fields.Many2one('res.country', _('‫‪Nationality‬‬'))
    start_work = fields.Date(string="Starting Work at", required=True)
    start_work_day = fields.Char('Starting Work at Day', compute='get_date_day')
    payslip_date = fields.Date(string="Payslip Date")
    type = fields.Selection([('New Employee', 'New Employee'),
                             ('Return From Leave', 'Return From Leave')], _('Effective Notice Type'), required=True)
    created_by = fields.Many2one('res.users', default=lambda self: self.env.uid, readonly=True, string="Created By")
    notes = fields.Text(string="Notes")

    effective_ids = fields.Many2many('effective.notice', 'effective.notice_rel', 'eff_1', 'eff_2', _('Previous Effective Notices'), readonly=True,
                                     compute='_compute_previous')
    state = fields.Selection([
        ('New', 'New'),
        ('Department manager approval', 'Department manager approval'),
        ('HR department approval', 'HR department approval'),
        ('Refused', 'Refused'),
    ], string='Status', select=True, default='New', )

    leave_request_id = fields.Many2one('hr.holidays', string='Leave Request')
    leave_start_date = fields.Datetime('Leave Start Date', related="leave_request_id.date_from", readonly=True)
    leave_start_date_day = fields.Char('Leave Start Date Day', related="leave_request_id.date_from_day", readonly=True)
    leave_end_date = fields.Datetime('Leave End Date', related="leave_request_id.date_to", readonly=True)
    leave_end_date_day = fields.Char('Leave End Date Day', related="leave_request_id.date_to_day", readonly=True)
    expected_working_day = fields.Date('Expected working day', related="leave_request_id.expected_working_day", readonly=True)
    expected_working_week_day = fields.Char('Leave End Date Day', related="leave_request_id.expected_working_week_day", readonly=True)
    count_leave_allocations = fields.Integer('Number of Leave Allocations', compute='get_count_smart_buttons')
    count_deductions = fields.Integer('Number of Deductions', compute='get_count_smart_buttons')
    return_justification = fields.Text('Delay / Early Return Justification')
    hide_return_justification = fields.Boolean(compute='_compute_hide_return_justification')
    department_approved_by = fields.Many2one('res.users', string="Department Approved By")
    department_approved_date = fields.Date('Department Approved Date')
    hr_approved_by = fields.Many2one('res.users', string="HR Approved By")
    hr_approved_date = fields.Date('HR Approved Date')
    refused_by = fields.Many2one('res.users', string="Refused By")
    refused_date = fields.Date('Refused Date')
    report_employee_is_manager = fields.Boolean(compute='_compute_employee_is_manager')
    branch_id = fields.Many2one('hr.branch', string='Branch')

    @api.one
    @api.onchange('employee_id')
    def get_related_fields(self):
        self.branch_id = self.employee_id.branch_id
        self.department_id = self.employee_id.department_id
        self.job_id = self.employee_id.job_id
        self.country_id = self.employee_id.country_id
        self.employee_number = self.employee_id.employee_number

    @api.multi
    @api.onchange('employee_id')
    def get_employee_domain(self):
        employees = self.env['hr.employee'].search([])

        if self.env.user.has_group('base.group_hr_user'):
            return {'domain': {'employee_id': [('id', 'in', employees.ids)]}}
        elif self.env.user.has_group('saudi_hr_employee.group_hr_department_manager'):
            return {'domain': {'employee_id': [('department_id', 'child_of', self.env.user.employee_ids[0].department_id.id)]}}
        elif self.env.user.has_group('saudi_hr_employee.group_hr_direct_manager'):
            return {'domain': {'employee_id': [('id', 'child_of', self.env.user.employee_ids.ids)]}}
        else:
            return {'domain': {'employee_id': [('user_id', '=', self.env.user.id)]}}

    @api.multi
    def copy(self):
        for rec in self:
            raise ValidationError(_('Forbidden to duplicate'))

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
    @api.depends('start_work', 'expected_working_day')
    def _compute_hide_return_justification(self):
        if self.start_work and self.expected_working_day and self.start_work != self.expected_working_day:
            self.hide_return_justification = False
            self.return_justification
        else:
            self.hide_return_justification = True

    @api.one
    @api.depends('start_work')
    def get_date_day(self):
        if self.start_work:
            self.start_work_day = self.get_week_day(self.start_work, 'date')

    def get_week_day(self, some_date, type):
        week_day = {'Monday': 'Monday / الإثنين', 'Tuesday': 'Tuesday / الثلاثاء', 'Wednesday': 'Wednesday / الأربعاء',
                    'Thursday': 'Thursday / الخميس', 'Friday': 'Friday / الجمعة', 'Saturday': 'Saturday / السبت', 'Sunday': 'Sunday / الأحَد'}
        if type == 'datetime':
            some_date_datetime = datetime.strptime(some_date, "%Y-%m-%d %H:%M:%S")
        elif type == 'date':
            some_date_datetime = datetime.strptime(some_date, "%Y-%m-%d")
        else:
            return ''
        some_date_day = calendar.day_name[some_date_datetime.weekday()]
        return week_day[some_date_day]

    @api.multi
    def open_leave_allocations(self):
        return {
            'domain': ['|', ('early_return_from_leave', '=', self.id), ('late_return_from_leave', '=', self.id)],
            'name': _('Leave Allocations'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.holidays',
            'views': [([self.env.ref('hr_holidays.view_holiday_allocation_tree').id], 'tree'),
                      ([self.env.ref('hr_holidays.edit_holiday_new').id], 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    @api.multi
    def open_deductions(self):
        return {
            'domain': ['|', ('early_return_from_leave', '=', self.id), ('late_return_from_leave', '=', self.id)],
            'name': _('Deductions'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'employee.deductions.violations',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    @api.one
    @api.depends('employee_id', 'leave_request_id')
    def get_count_smart_buttons(self):
        leave_allocations = self.env['hr.holidays'].search(['|', ('early_return_from_leave', '=', self.id), ('late_return_from_leave', '=', self.id)])
        self.count_leave_allocations = len(leave_allocations)
        deductions = self.env['employee.deductions.violations'].search(
            ['|', ('early_return_from_leave', '=', self.id), ('late_return_from_leave', '=', self.id)])
        self.count_deductions = len(deductions)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'New':
                raise exceptions.ValidationError(_("Not allowed to delete a confirmed"))
        return super(effective_notice, self).unlink()

    @api.multi
    def action_department_manager_approval(self):
        for record in self:
            if record.employee_id.department_manager.user_id.id != self.env.uid and record.employee_id.parent_id.user_id.id != self.env.uid and not self.env.user.has_group(
                    'saudi_hr_employee.group_effective_bypass_department_approvals'):
                raise ValidationError(
                    'Not Allowed !! \n You did not have the permission to click on ( Department manager approval ) for this employee ( %s ), only His / Her Department manager  ( %s ) can click on this button, (or) you must have access to (Bypass Department manager approval)' % (
                    record.employee_id.name, record.employee_id.department_manager.name))
            record.sudo().write({'state': 'Department manager approval', 'department_approved_by': self.env.uid,
                                 'department_approved_date': datetime.now().strftime('%Y-%m-%d')})
            body = "This Record Approved By Department Manager"
            self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def action_hr_department_approval(self):
        for record in self:

            # //////////////  Check For Old Leave Request /////////////////////////////////////////////
            old_leave_requests = self.env['hr.holidays'].search(
                [('state', '!=', 'refuse'), ('employee_id', '=', record.employee_id.id), ('date_from', '<=', record.start_work),
                 ('date_to', '>=', record.start_work), ('id', '!=', record.leave_request_id.id)])
            if old_leave_requests:
                for old_leave_request in old_leave_requests:
                    error_msg = "Not allowed !! \n Based on the old leave Requests, there is a leave request start between ( %s ) the employee Returned back to work on ( %s ) which located in a leave ( %s ) Kindly review your data." % (
                    old_leave_request.date_from, old_leave_request.expected_working_day, old_leave_request.name)
                    raise ValidationError(_(error_msg))

            # //////////////  Check For Old National Holidays /////////////////////////////////////////////
            old_national_holidays = self.env['hr.national.holiday'].search(
                [('start_date', '<=', record.start_work), ('end_date', '>=', record.start_work)])
            if old_national_holidays:
                for old_national_holiday in old_national_holidays:
                    if not old_national_holiday.branches or record.employee_id.branch_id.id in old_national_holiday.branches.ids:
                        holiday_error_msg = "Not allowed !! \n We found that there is a Holiday ( %s ) which conflict with Return from leave Date." % old_national_holiday.name
                        raise ValidationError(_(holiday_error_msg))

            # //////////////  Check For Old Working schedule Days /////////////////////////////////////////////
            checked_date = datetime.strptime(record.start_work, "%Y-%m-%d")
            week_day = checked_date.weekday()
            contracts = self.env['hr.contract'].search([('employee_id', '=', record.employee_id.id), ('active', '=', True)])
            if len(contracts):
                contract = contracts[0]
            else:
                contract = False
            day_on_working_days = 0
            if contract and contract.attendance_ids:
                for attendance_id in contract.attendance_ids:
                    if week_day == int(attendance_id.dayofweek):
                        day_on_working_days = 1
                if not day_on_working_days:
                    weekday_error_msg = "Not allowed !! \n It is not logic that the employee will start working on ( %s ), because we found that this day is a weakly rest for this employee. " % record.start_work
                    raise ValidationError(_(weekday_error_msg))

            if record.type == 'New Employee':
                record.employee_id.start_working_date = record.start_work

            # /////////////////////////////////////////////////////////////////////////////////////
            if record.type == 'New Employee':
                old_effective_notices = self.env['effective.notice'].search(
                    [('state', '=', 'HR department approval'), ('employee_id', '=', record.employee_id.id), ('type', '=', 'New Employee'),
                     ('id', '!=', record.id)])
                if old_effective_notices:
                    raise exceptions.ValidationError(
                        "Dear Hr Manager. \n You cannot approve this effective notice, we found that this employee has old effective notices with type = New employee. Each employee can create effective notices as a new employee one time only. if this employee resigned and back to work, you must create a new employee with a different employee number.")
            if record.type == 'Return From Leave':
                old_return_from_leaves = self.env['effective.notice'].search(
                    [('state', 'not in', ['HR department approval', 'Refused']), ('employee_id', '=', record.employee_id.id),
                     ('type', '=', 'Return From Leave'), ('id', '!=', record.id)])
                if old_return_from_leaves:
                    raise exceptions.ValidationError(
                        "Not allowed !! \n Dear Hr Manager, we found that this employee have old Effective notice as a return from a leave which still under processing. Kindly complete the process for old return from leaves for this employee or delete it, then your system will allow you to approve this one.")

                if record.start_work <= record.leave_start_date:
                    error_msg_1 = "Data Error!! \n Not allowed to approve this return from leave, it is not logic that return from leave date ( %s ) is equal to or less than leave start date ( %s  ). kindly Review your data." % (
                    record.start_work, record.leave_start_date)
                    raise ValidationError(error_msg_1)
                if record.start_work < record.leave_end_date:
                    error_msg_2 = _(
                        "Attention !! \n It seems that the employee was planning for a leave between ( %s To %s ) based on your system calculations, it is expected that the employee will back to work on ( %s  ) Now you are trying to create a return from leave on ( %s  )  which mean that the employee return from a leave before the planned date ( %s  ) However, in some cases, payslip and deductions may affected by early return from a leave. \n Are you sure that you want to continue ? ") % (
                                  record.leave_start_date, record.leave_end_date, record.expected_working_day, record.start_work,
                                  record.expected_working_day)
                    return self.env.user.show_dialogue(error_msg_2, 'effective.notice', 'early_back_from_leave', record.id)
                if record.start_work > record.expected_working_day:
                    return self.late_back_from_leave_wizard()
            # ////////////////////////////////////////////////////////////////////////////////////

            return self.hr_department_approval()

    @api.multi
    def early_back_from_leave(self):
        for record in self:
            if record.leave_request_id.leave_request_extend_id:
                error_msg = "Attention !! \n We found that this leave request is already extended with another leave request ( %s ).So it is not logic to create a return from a leave for an extended leave. you are allowed to create a Return from leave for the new extended leave." % record.leave_request_id.leave_request_extend_id.name
                raise ValidationError(_(error_msg))
            if record.leave_request_id.holiday_status_id.type == 'Non Annual Leave':
                return self.hr_department_approval()
            if record.leave_request_id.holiday_status_id.type == 'Annual Leave':
                if record.leave_request_id.reconciliation_method == 'Stop payslip during leave and use leave reconciliation':
                    return self.early_leave_reconciliation_wizard()
                else:
                    record.early_leave_reconciliation('reallocate')

    @api.multi
    def early_leave_reconciliation_wizard(self):
        for record in self:
            ctx = {'record_id': record.id, }
            return {
                'domain': "[]",
                'name': _('Reconciliation Confirmation'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'early.leave.reconciliation.wizard',
                'view_id': self.env.ref('saudi_hr_leaves.early_leave_reconciliation_wizard').id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': ctx,
            }

    @api.multi
    def early_leave_reconciliation(self, choice):
        for record in self:
            if choice == 'reallocate':
                if record.leave_request_id.leave_reconciliation_amount > 0:
                    from_dt = datetime.strptime(record.leave_start_date, "%Y-%m-%d %H:%M:%S")
                    to_dt = datetime.strptime(record.start_work, "%Y-%m-%d")
                    timedelta_custom = to_dt - from_dt
                    new_leave_duration = timedelta_custom.days
                    # //////////////////////////// Compute recon Amount
                    based_on_value = 0
                    if record.leave_request_id.reconciliation_method == 'Stop payslip during leave and use leave reconciliation':
                        if record.leave_request_id.request_reason == 'annual' and record.leave_request_id.contract_id and record.leave_request_id.holiday_status_type == 'Annual Leave':
                            if record.leave_request_id.reconciliation_based_on == 'basic':
                                based_on_value = record.leave_request_id.basic_salary
                            if record.leave_request_id.reconciliation_based_on == 'basic_house':
                                based_on_value = record.leave_request_id.basic_salary + record.leave_request_id.house_allowance_amount
                            if record.leave_request_id.reconciliation_based_on == 'basic_house_transportation':
                                based_on_value = record.leave_request_id.basic_salary + record.leave_request_id.house_allowance_amount + record.leave_request_id.transportation_allowance_amount
                            if record.leave_request_id.reconciliation_based_on == 'basic_house_transportation_phone':
                                based_on_value = record.leave_request_id.basic_salary + record.leave_request_id.house_allowance_amount + record.leave_request_id.transportation_allowance_amount + record.leave_request_id.phone_allowance_amount
                            if record.leave_request_id.reconciliation_based_on == 'total':
                                based_on_value = record.leave_request_id.total_salary
                        new_leave_reconciliation_amount = (based_on_value / 30) * (new_leave_duration)
                    else:
                        new_leave_reconciliation_amount = 0
                    # /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
                    if new_leave_reconciliation_amount > record.leave_request_id.leave_reconciliation_amount:
                        raise exceptions.ValidationError("Data Error! \n Unhandled case !")
                    if new_leave_reconciliation_amount < record.leave_request_id.leave_reconciliation_amount:
                        if new_leave_reconciliation_amount >= record.leave_request_id.paid_amount:
                            record.leave_request_id.leave_reconciliation_amount = new_leave_reconciliation_amount
                        else:
                            deduction_vals = {
                                'desc': 'auto deduction due to early return from leave',
                                'employee_id': record.employee_id.id,
                                'deduction_date': datetime.today().strftime('%Y-%m-%d'),
                                'deduction_reason': 'other',
                                'decision': 'deduction',
                                'deduction_type': 'fixed',
                                'deduction_value': record.leave_request_id.paid_amount - new_leave_reconciliation_amount,
                                'auto_deduction': True,
                                'early_return_from_leave': record.id,
                            }
                            leave_deduction_id = self.env['employee.deductions.violations'].create(deduction_vals)
                            leave_deduction_id.confirm()
                            leave_deduction_id.get_emloyee_related()

                # //////////////////////////// Make Reallocation ///////////////////////////////////
                old_end_date = record.leave_request_id.date_to
                last_allocation = self.env['hr.holidays'].search(
                    [('type', '=', 'add'), ('employee_id', '=', record.employee_id.id), ('state', '=', 'validate')], limit=1,
                    order="allocation_date desc")
                if last_allocation:
                    allocation_date = last_allocation.allocation_date
                else:
                    contracts = self.env['hr.contract'].search([('employee_id', '=', record.employee_id.id), ('active', '=', True)])
                    if len(contracts):
                        contract = contracts[0]
                    if contract:
                        allocation_date = contract.adjusted_date
                date_1 = datetime.strptime(record.start_work, "%Y-%m-%d")
                date_2 = datetime.strptime(old_end_date, "%Y-%m-%d %H:%M:%S")
                # //////////////////////////////////////////////////////////////////
                if record.leave_request_id.holiday_status_id == record.leave_request_id.annual_leave_policy:
                    if not record.leave_request_id.contract_id.working_calendar:
                        raise exceptions.ValidationError(
                            "Dear HR manager, Employee ( %s ) returned early from a leave, you requested from your system to re-allocate leave balance due to early return from leave, in order to automatically calculate number of days, your system must know if you calculate this leave in ( calendar or working days ), kindly review employee contract and make sure that employee contract have a valid data in ( working / calendar ) field." % record.employee_id.name)
                    working_calendar = record.leave_request_id.contract_id.working_calendar

                    if working_calendar == 'Working Days':
                        if not record.leave_request_id.contract_id.attendance_ids:
                            raise exceptions.ValidationError(
                                "Data Error !! Dear HR manager, your system is trying to calculate number of leave days, it seems that you configured your system to deduct working days, when your system reviewed employee contract ( %s ) we found that you forget to select the working schedule for this employee, kindly review working days ( Contracts >> Other >> working schedule)." % record.employee_id.name)
                        working_days = 0
                        for leave_date in record.leave_request_id.daterange(date_1, date_2):
                            if record.leave_request_id.check_day_on_working_days(leave_date):
                                if record.leave_request_id.check_day_not_on_holiday(leave_date):
                                    working_days += 1
                        early_returned_days = working_days

                    if working_calendar == 'Calendar days':
                        working_days = 0
                        for leave_date in record.leave_request_id.daterange(date_1, date_2):
                            if record.leave_request_id.check_day_not_on_holiday(leave_date):
                                working_days += 1
                        early_returned_days = working_days
                # /////////////////////////////////////////////////////////////////////////////////////////////////
                # diff = date_2 - date_1
                # early_returned_days = diff.days + 1
                vals = {
                    'name': 'Re-allocate annual leave balance due to early return from leave',
                    'employee_id': record.employee_id.id,
                    'allocation_date': allocation_date,
                    'number_of_days_temp': early_returned_days,
                    'type': 'add',
                    'system_created': True,
                    'approved_by': self.env.uid,
                    'holiday_status_id': record.leave_request_id.holiday_status_id.id,
                    'early_return_from_leave': record.id,
                }
                leave_allocation_id = self.env['hr.holidays'].create(vals)
                leave_allocation_id.signal_workflow('validate')
                if leave_allocation_id.double_validation:
                    leave_allocation_id.signal_workflow('second_validate')

                # ///////////////////////////////////////////////////////////////////////////////////

            # ///////// Add Report As Attachment

            # //////////////////////////// Make end date = startwork - 1 day ///////////////////////////////////
            body = "This leave Request had been modified due to early return from leave"
            self.message_post(body=body, message_type='email')
            new_leave_end_date = datetime.strptime(record.start_work, '%Y-%m-%d') - timedelta(days=1)
            record.leave_request_id.date_to = new_leave_end_date.strftime('%Y-%m-%d %H:%M:%S')
            record.leave_request_id._compute_leave_days_ids()
            record.leave_request_id.expected_working_day = record.start_work

            return self.hr_department_approval()

    @api.multi
    def late_back_from_leave_wizard(self):
        for record in self:
            absence_days = record.leave_request_id.get_duration_number_of_days(record.expected_working_day, record.start_work) - 1
            leave_balance = str(record.employee_id.leaves_count)
            message = "Attention !! \n Dear Hr manager, \n There is ( %s ) days absence. Employee annual leave balance is ( %s ) " % (
            absence_days, leave_balance)
            ctx = {'record_id': record.id, 'default_message': message}
            return {
                'domain': "[]",
                'name': _('Late Back From Leave'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'late.back.from.leave.wizard',
                'view_id': self.env.ref('saudi_hr_leaves.late_back_from_leave_wizard').id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': ctx,
            }

    @api.multi
    def late_back_from_leave(self, choice):
        for record in self:
            if choice == 'deduct':
                # //////////////////////////// Make Reallocation ///////////////////////////////////
                contracts = self.env['hr.contract'].search([('employee_id', '=', record.employee_id.id), ('active', '=', True)])
                if len(contracts):
                    contract = contracts[0]

                last_allocation = self.env['hr.holidays'].search(
                    [('type', '=', 'add'), ('employee_id', '=', record.employee_id.id), ('state', '=', 'validate')], limit=1,
                    order="allocation_date desc")
                if last_allocation:
                    allocation_date = last_allocation.allocation_date
                else:

                    if contract:
                        allocation_date = contract.adjusted_date
                date_2 = datetime.strptime(record.start_work, "%Y-%m-%d")
                date_1 = datetime.strptime(record.leave_request_id.date_to, "%Y-%m-%d %H:%M:%S")
                # ////////////////////////////////////////////////////////////////////////
                if record.leave_request_id.holiday_status_id == record.leave_request_id.annual_leave_policy:
                    if not self.leave_request_id.contract_id.working_calendar:
                        raise exceptions.ValidationError(
                            "Dear HR manager, Employee ( %s ) returned late from a leave, you requested from your system to re-allocate leave balance due to late return from leave, in order to automatically calculate number of days, your system must know if you calculate this leave in ( calendar or working days ), kindly review employee contract and make sure that employee contract have a valid data in ( working / calendar ) field." % self.employee_id.name)
                    working_calendar = self.leave_request_id.contract_id.working_calendar

                    if working_calendar == 'Working Days':
                        if not self.leave_request_id.contract_id.attendance_ids:
                            raise exceptions.ValidationError(
                                "Data Error !! Dear HR manager, your system is trying to calculate number of leave days, it seems that you configured your system to deduct working days, when your system reviewed employee contract ( %s ) we found that you forget to select the working schedule for this employee, kindly review working days ( Contracts >> Other >> working schedule)." % self.employee_id.name)
                        working_days = 0
                        for leave_date in self.leave_request_id.daterange(date_1, date_2):
                            if self.leave_request_id.check_day_on_working_days(leave_date):
                                if self.check_day_not_on_holiday(leave_date):
                                    working_days += 1
                        late_returned_days = working_days

                    if working_calendar == 'Calendar days':
                        working_days = 0
                        for leave_date in self.leave_request_id.daterange(date_1, date_2):
                            if self.leave_request_id.check_day_not_on_holiday(leave_date):
                                working_days += 1
                        late_returned_days = working_days
                # ////////////////////////////////////////////////////////////////////////
                # diff = date_2 - date_1
                # late_returned_days = diff.days - 1
                minus_late_returned_days = late_returned_days * -1
                vals = {
                    'name': 'Deduct annual leave balance due to late return from leave',
                    'employee_id': record.employee_id.id,
                    'allocation_date': allocation_date,
                    'number_of_days_temp': minus_late_returned_days,
                    'type': 'add',
                    'system_created': True,
                    'approved_by': self.env.uid,
                    'holiday_status_id': contract.annual_leave_policy.id,
                    'allow_minus_value': True,
                    'late_return_from_leave': record.id,
                }
                leave_allocation_id = self.env['hr.holidays'].create(vals)
                leave_allocation_id.signal_workflow('validate')
                if leave_allocation_id.double_validation:
                    leave_allocation_id.signal_workflow('second_validate')

                # ///////////////////////////////////////////////////////////////////////////////////
            if choice == 'extend':
                leave_request = record.leave_request_id
                extend_start = datetime.strptime(leave_request.date_to, '%Y-%m-%d %H:%M:%S') + timedelta(1)
                extend_end = datetime.strptime(record.start_work, '%Y-%m-%d') - timedelta(1)
                ctx = self.env.context.copy()
                custom_context = {
                    "default_employee_id": leave_request.employee_id.id,
                    "default_date_from": extend_start.strftime('%Y-%m-%d %H:%M:%S'),
                    "default_date_to": extend_end.strftime('%Y-%m-%d %H:%M:%S'),
                    "default_original_leave_request_id": leave_request.id,
                    "default_create_air_ticket_request": 'no',
                    'popup': True,
                    'return_from_leave': record.id,
                    'readonly_by_pass': True
                }
                ctx.update(custom_context)
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'hr.holidays',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': self.env.ref('saudi_hr_leaves.leave_request_form').id,
                    'context': ctx,
                    'target': 'current',
                }
            if choice == 'absent':
                leave_request = record.leave_request_id
                ctx = self.env.context.copy()
                custom_context = {
                    "default_employee_id": leave_request.employee_id.id,
                    "default_desc": 'Deduction due to late return from leave',
                    "default_deduction_date": record.start_work,
                    'popup': True,
                    'return_from_leave': record.id,
                    'readonly_by_pass': True,
                    'default_auto_deduction': True,
                    'default_late_return_from_leave': record.id,
                }
                ctx.update(custom_context)
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'employee.deductions.violations',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': self.env.ref('hr_loans.employee_deductions_violations_form').id,
                    'context': ctx,
                    'target': 'current',
                }

            # ///////////////////////////////////////////////////////////////////////////////////
            return self.hr_department_approval()

    @api.multi
    def hr_department_approval(self):
        for record in self:
            if record.type == 'Return From Leave':
                if record.leave_request_id.return_from_leave:
                    raise exceptions.ValidationError(
                        "Not Allowed !! \n We found that the leave which you selected is already linked with another Return from leave, it is not logic to create 2 return from leave for the same leave request,  kindly review old return from leave  for the same employee.")
                else:
                    record.leave_request_id.return_from_leave = record.id
                    record.leave_request_id.return_from_leave_counter = 0

            record.write({'state': 'HR department approval'})
            record.hr_approved_by = self.env.uid
            record.hr_approved_date = datetime.now().strftime('%Y-%m-%d')
            body = "This Record approved by hr department "
            self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def action_Refuse(self):
        for record in self:
            record.write({'state': 'Refused'})
            self.refused_by = self.env.uid
            self.refused_date = datetime.now().strftime('%Y-%m-%d')
            body = "This Record Refused"
            self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def action_set_to_new(self):
        for record in self:
            record.write({'state': 'New'})
            body = "This Record Set To New"
            self.message_post(body=body, message_type='email')
        return {}

    @api.depends('employee_id')
    def _compute_previous(self):
        for rec in self:
            # Get Old Effective notices
            if not rec.id:
                old_notices = self.env['effective.notice'].search([('employee_id', '=', rec.employee_id.id)])
            else:
                old_notices = self.env['effective.notice'].search([('employee_id', '=', rec.employee_id.id), ('id', '!=', rec.id)])
            rec.effective_ids = old_notices.ids

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].sudo().next_by_code('effective.notice')
        res = super(effective_notice, self).create(vals)
        return res

    @api.one
    @api.onchange('type')
    def onchange_type(self):
        self.leave_request_id = ''
        self.start_work = False
        self.payslip_date = False


class dynamic_leave_line(models.Model):
    _name = 'dynamic.leave.line'

    leave_type_id = fields.Many2one('hr.holidays.status', string='Leave Type')
    days_from = fields.Integer(string="From / Days")
    days_to = fields.Integer(string="To / Days")
    deduction_rate = fields.Integer(string="Deduction Rate %")

    @api.one
    @api.constrains('days_from', 'days_to')
    def check_leave_days_ids(self):
        if self.days_from >= self.days_to:
            raise ValidationError('(To / Days) must be greater than (From / Days)')
        domain = [
            ('days_from', '<=', self.days_from),
            ('days_to', '>=', self.days_to),
            ('leave_type_id', '=', self.leave_type_id.id),
            ('id', '!=', self.id),
        ]
        conflicts = self.search_count(domain)
        if conflicts:
            raise ValidationError('Configuration Error! \n For Dynamic leave calculations, Not allowed to have Overlap between periods.')


class hr_holidays_status(models.Model):
    _name = 'hr.holidays.status'
    _inherit = ['mail.thread', 'hr.holidays.status']

    name = fields.Char('Leave Description‬‬', size=64, required=True, translate=True)
    double_validation = fields.Boolean('Apply Double Validation', default=True,
                                       help="When selected, the Allocation/Leave Requests for this type require a second validation to be approved.")
    type = fields.Selection([('Annual Leave', 'Annual Leave'),
                             ('Non Annual Leave', '‫‪Non Annual Leave‬‬')], _('Leave Type'), required=True)
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
    ], _('Nationality'), required=True)
    reconciliation_based_on = fields.Selection([
        ('basic', 'Basic Salary'),
        ('basic_house', 'Basic Salary + House allowance'),
        ('basic_house_transportation', 'Basic Salary + House allowance + transportation'),
        ('basic_house_transportation_phone', 'Basic salary + House + transportation + phone'),
        ('total', 'Total salary'),
    ], string='Leave Reconciliation based on')

    start_calc_from = fields.Selection([('First Effective Notice', 'First Effective Notice'),
                                        ('Contract Start Date', 'Contract Start Date'),
                                        ('Trial Period Start Date', '‫Trial Period Start Date‬‬')], _('Start Calculation From'),
                                       default="First Effective Notice")
    start_allocation_after = fields.Integer(string="Start Automatic Allocation After (months)",
                                            help='If = 3 months, employee hiring date = 15-01-2020, annual leave balance = 30 days, monthly balance = 2.5 days your system will allocate leave balance for this employee as following \n - 15-01-2020, balance = 0 days \n- 15-02-2020, balance = 0 days \n- 15-03-2020, balance = 7.5 days \n- 15-04-2020, balance = 10 days \n- 15-05-2020, balance = 12.5 days \n  …… \n- 15-12-2020, balance = 27.5 days \n- 15-01-2021, balance = 30 days')
    max_balance = fields.Integer(string="Max Accumulated Balance", default=180)
    notes = fields.Html(string="Notes")
    lines = fields.One2many('leaves.calc.method.line', 'leave_type_id', string="Calculation Method")
    max_line_less = fields.Integer()
    can_request_air_ticket = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='can request air ticket')
    can_request_exit_rentry = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Can request For Exit and R-entry')
    linked_exit_renry_id = fields.Many2one('hr.exit.entry.request', 'Linked exit and Re-entry')

    state = fields.Selection([('New', 'New'), ('Approved', 'Approved')], string='Status', readonly=True, select=True, default='New', )
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
    non_annual_frequency = fields.Selection([
        ('contract', 'Per contract'),
        ('financial_year', 'Per financial year ( 1Jan : 31 Dec)'),
        ('contractual_year', 'Each contractual year ( hiring dat to next year)'),
        ('one_time', 'one time per live.'),
        ('per_request', 'based on request (no limitation)'),
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
        ('Working Days', 'Working Days'),
        ('Calendar days', 'Calendar days'),
    ], string='Working / Calendar')
    # /////////////////// Smart Buttons /////////////////////////////////////////////////////////////
    count_leave_requests = fields.Float('Number of leave requests', compute='get_count_smart_buttons')
    count_contracts = fields.Float('Number of contracts', compute='get_count_smart_buttons')
    count_leave_allocations = fields.Float('Number of leave allocations', compute='get_count_smart_buttons')
    leave_conditions = fields.Text('Leave Conditions')

    check_iqama_expiry = fields.Boolean('Check for IQAMA / National ID expiry',
                                        help='In order to force your system to Check for IQAMA / National ID expiry date, this field must be flagged in Leave type and employee nationality.')
    check_passport_expiry = fields.Boolean('Check for Passport expiry date',
                                           help='In order to force your system to Check for Passport expiry date, this field must be flagged in Leave type and employee nationality.')
    max_per_month = fields.Integer('Maximum per month', help='Zero for no limits')
    is_alternative_employee = fields.Selection([
        ('yes', 'yes'),
        ('No', 'No'),
    ], string='Must have alternative employee',
        help='If = Yes, and job position requires alternative employee, leave request will not be approved until provide an alternative employee.')
    alternative_approval = fields.Selection([
        ('Yes', 'Yes'),
        ('No', 'No'),
    ], 'Alternative Employee Approval is required in leave request process ?',
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
    leave_address_required = fields.Boolean('Leave Address and leave phone number is required',
                                            help='If = yes, employee will not be allowed to request for this leave type until (s)he fill the leve address and phone number during leave.')
    mandatory_return_from_leave = fields.Selection([
        ('Yes', 'Yes'),
        ('No', 'No'),
    ], string='Mandatory to create Return from leave', default='Yes',
        help='If = yes, employee will not allowed to request for new leave until he create a return from leave for all old leaves …. If = No, your system will not consider return from leave into account, so any employee can request for a new leave without create a return from leave for old leaves.')
    leave_extend_timeout = fields.Integer('Allow to extend leave request within', default=30,
                                          help='If = 10 days, you will be allowed to extend leave requests related to this leave types after 10 days from leave end date. e.g, if leave end date = 20 January and  Allow to extend leave request within 5 Days … leave extend button will appear till 25 January. ')
    dynamic_leaves = fields.Boolean('Dynamic leave deduction', )
    dynamic_leave_ids = fields.One2many('dynamic.leave.line', 'leave_type_id', string="Dynamic leave Calculation")
    print_conditions_arabic = fields.Html('Arabic')
    print_conditions_english = fields.Html('English')
    allocation_technique = fields.Selection([
        ('Each Contractual Month', 'Each Contractual Month'),
        ('Each Financial Month', 'Each Financial Month'),
    ], string='Allocation Technique',
        help='If = Contractual Month. employee hiring date = 16 march, your system will allocate leave balance on day 16 from each month e.g, ( 16 April , 16 May … etc) If = Financial march, your system will allocate leave balance on last day from each month e.g, ( first month form 16 March to 31 March, second month = 30 April , third month = 31 May … etc)')
    allocation_period = fields.Selection([
        ('Monthly', 'Monthly'),
        ('Yearly', 'Yearly'),
    ], string='Allocation Period',
        help='If = monthly ,when you run Automatic leave allocation your system will allocate leave based on the date which you selected on ( allocate till this date ) field, If = yearly,  when you run Automatic leave allocation your system will allocate leave till 31 December or end of contractual year instead of the date which you selected on ( allocate till this date ) field.')

    @api.one
    @api.constrains('dynamic_leaves', 'dynamic_leave_ids')
    def check_dynamic_leaves(self):
        if self.dynamic_leaves and not self.dynamic_leave_ids:
            raise ValidationError('Please add at least one line in Dynamic leave Calculation tab')

    @api.one
    @api.onchange('allow_leave_advance', 'max_advance_type')
    def empty_advance_days(self):
        self.advance_days = 0

    @api.one
    @api.constrains('advance_days')
    def check_advance_days(self):
        if self.advance_days < 0:
            raise exceptions.ValidationError("Number of advanced days field can not be minus")

    @api.one
    @api.onchange('allow_leave_advance')
    def empty_max_advance_type(self):
        self.max_advance_type = False

    @api.one
    @api.onchange('allocate_after_trial')
    def empty_start_allocation_after(self):
        self.start_allocation_after = 0

    @api.one
    @api.onchange('reconciliation_method', 'type')
    def empty_leave_reconciliation_minimum(self):
        self.leave_reconciliation_minimum = 0

    @api.one
    @api.constrains('leave_reconciliation_minimum')
    def check_leave_reconciliation_minimum(self):
        if self.leave_reconciliation_minimum < 0:
            raise exceptions.ValidationError("Attention!! \n Minimum days to use leave reconciliation can not be minus.")

    @api.one
    @api.onchange('is_alternative_employee')
    def onchange_is_alternative_employee(self):
        self.alternative_employee_days = 0
        self.alternative_approval = False

    @api.one
    @api.constrains('alternative_employee_days')
    def check_alternative_employee_days(self):
        if self.alternative_employee_days <= 0 and self.is_alternative_employee == 'yes':
            raise exceptions.ValidationError("Attention!! \n Number of leave days requires alternative employee can not be zero or minus.")

    @api.one
    @api.constrains('max_per_month')
    def check_max_per_month(self):
        if self.max_per_month < 0:
            raise exceptions.ValidationError("Attention!! \n Maximum per Month can not be zero or minus.")

    @api.one
    def get_count_smart_buttons(self):
        self.count_leave_requests = self.env['hr.holidays'].search_count([('holiday_status_id', '=', self.id), ('type', '=', 'remove')])
        self.count_contracts = self.env['hr.contract'].search_count([('annual_leave_policy', '=', self.id)])
        self.count_leave_allocations = self.env['hr.holidays'].search_count([('holiday_status_id', '=', self.id), ('type', '=', 'add')])

    @api.multi
    def open_leave_requests(self):
        return {
            'domain': [('holiday_status_id', '=', self.id), ('type', '=', 'remove')],
            'name': _('Leave requests'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.holidays',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    @api.multi
    def open_contracts(self):
        return {
            'domain': [('annual_leave_policy', '=', self.id)],
            'name': _('Contracts'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.contract',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    @api.multi
    def open_allocations(self):
        return {
            'domain': [('holiday_status_id', '=', self.id), ('type', '=', 'add')],
            'name': _('Leave Allocations'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.holidays',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    # ///////////////////////////////////////////////////////////////////////////////////////////////////

    @api.one
    @api.onchange('nationality')
    def onchange_nationality(self):
        self.can_request_exit_rentry = False

    @api.one
    @api.onchange('limit')
    def onchange_limit(self):
        self.number_of_days = 0
        if self.limit:
            self.allocate_after_trial = False
        else:
            self.allocate_after_trial = True

    @api.one
    @api.onchange('non_annual_frequency')
    def onchange_non_annual_frequency(self):
        if self.non_annual_frequency == 'per_request':
            self.limit = True

    @api.constrains('limit', 'days_per_leave')
    def _check_days_per_leave(self):
        if self.limit and self.days_per_leave <= 0:
            raise exceptions.ValidationError("Attention!! \n Maximum days per each leave can not be zero or minus.")

    @api.constrains('allow_past')
    def _check_allow_past(self):
        if self.allow_past < 0:
            raise exceptions.ValidationError("Attention!! \n Allow to request leave for past can not be minus.")
        if self.allow_future < 0:
            raise exceptions.ValidationError("Attention!! \n Allow to request leave for future can not be minus.")

    @api.constrains('number_of_days')
    def _check_number_of_days(self):
        if self.number_of_days < 0:
            raise exceptions.ValidationError("Number Of Days cannot be negative")

    @api.constrains('type')
    def _check_type(self):
        if self.type == 'Non Annual Leave' and not self.limit:
            if self.number_of_days <= 0:
                error_msg = "Data Error !! \n You are trying to add a new Non annual leave ( %s ) It is not logic that Number of days assigned to this leave is zero or minus or contain days Fractions." % (
                    self.name)
                raise ValidationError(_(error_msg))

    @api.constrains('non_annual_type')
    def _check_non_annual_type(self):
        if self.id:
            old_same_leave_types = self.env['hr.holidays.status'].search(
                [('non_annual_type', '=', self.non_annual_type), ('nationality', '=', self.nationality), ('who_request', '=', self.who_request),
                 ('religion', '=', self.religion), ('non_annual_type', 'not in', ['Other', 'Sick Leave']), ('id', '!=', self.id)])
        else:
            old_same_leave_types = self.env['hr.holidays.status'].search(
                [('non_annual_type', '=', self.non_annual_type), ('nationality', '=', self.nationality), ('who_request', '=', self.who_request),
                 ('religion', '=', self.religion), ('non_annual_type', 'not in', ['Other', 'Sick Leave'])])

        if len(old_same_leave_types) and self.type == 'Non Annual Leave':
            error_msg = "Dear Hr manager, \n It is not allowed to define same Non-annual leave type ( %s ) for same Nationality ( %s ) and same gender ( %s ) and same religion ( %s )" % (
            self.non_annual_type, self.nationality, self.who_request, self.religion)
            raise ValidationError(_(error_msg))

    @api.one
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

    @api.constrains('days_in_month', 'months_in_year')
    def _check_values(self):
        if self.days_in_month <= 0 or self.months_in_year <= 0:
            raise exceptions.ValidationError(
                _("Configuration error!! ‫‪The‬‬ ‫‪calculations‬‬ ‫‪mustn’t‬‬ ‫‪contains‬‬ ‫‪a‬‬ ‫‪value‬‬ ‫‪equal‬‬ ‫‪to‬‬ ‫‪zero‬‬"))

    @api.constrains('start_allocation_after')
    def _check_start_allocation_after(self):
        if self.start_allocation_after < 0:
            raise exceptions.ValidationError("Start Automatic Allocation After (months) cannot be negative")

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
            rec.allocation_technique = False
            rec.allocation_period = False

    @api.onchange('non_annual_type')
    def onchange_non_annual_type(self):
        for rec in self:
            rec.number_of_days = 0
            rec.non_annual_frequency = ''
            rec.divide_leave_balance = ''
            rec.who_request = ''
            rec.marital_status = ''
            rec.religion = ''
            if rec.non_annual_type in ['Unpaid Leave']:
                rec.reconciliation_method = 'Stop payslip during leave and use leave reconciliation'
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

    @api.constrains('max_balance')
    def _check_max_balance(self):
        if self.max_balance <= 0:
            raise exceptions.ValidationError("Configuration error!! Max accumulated balance cannot be equal to zero Or Negative !!")

    @api.multi
    def action_hr_approve(self):
        for record in self:
            if record.type == 'Annual Leave':
                if record.max_advance_type == 'fixed' and not record.advance_days:
                    raise exceptions.ValidationError("Number of advanced days   cannot be zero or negative value.")
                if len(record.lines) == 0:
                    raise exceptions.ValidationError("Data error!! You must insert at least one line in the calculation method table")
            if record.limit:
                msg = _(
                    "Dear HR manager, \n Attention , you selected ( Unlimited leave balance ) for this leave, which mean that your system will not check employee leave balance when requesting for this leave. \n Are you sure that you want to continue ? ")
                return self.env.user.show_dialogue(msg, 'hr.holidays.status', 'hr_approve', record.id)

            return record.hr_approve()

    @api.multi
    def hr_approve(self):
        for record in self:
            if record.type == 'Non Annual Leave' and record.non_annual_type == 'Sick Leave':
                old_same_leave_types = self.env['hr.holidays.status'].search(
                    [('non_annual_type', '=', record.non_annual_type), ('nationality', '=', record.nationality),
                     ('who_request', '=', record.who_request), ('religion', '=', record.religion), ('non_annual_type', '=', 'Sick Leave'),
                     ('id', '!=', record.id)])

                if len(old_same_leave_types):
                    msg = "Dear Hr manager, \n Attention,there is another  Non-annual leave type ( %s ) for same Nationality ( %s ) and same gender ( %s ) and same religion ( %s ) Are you sure that you want to continue ? " % (
                    record.non_annual_type, record.nationality, record.who_request, record.religion)
                    return self.env.user.show_dialogue(msg, 'hr.holidays.status', 'hr_approve_confirm', record.id)
            return record.hr_approve_confirm()

    @api.multi
    def hr_approve_confirm(self):
        for record in self:
            record.write({'state': 'Approved'})
            body = "Document Approved By Hr Department"
            self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def action_set_to_new(self):
        for record in self:
            record.write({'state': 'New'})
            body = "Document changed to ->  New Status"
            self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def unlink(self):
        if self.state != 'New':
            raise exceptions.ValidationError("Not allowed to delete approved document, you can set it to new and delete it")
        contracts = self.env['hr.contract'].search([['annual_leave_policy', '=', self.id]])
        if contracts:
            raise ValidationError(
                _("You can not delete Leave type while it linked with Contract%s\n" % (str('\n'.join([str(c.name) for c in contracts])))))
        return super(hr_holidays_status, self).unlink()


class calc_method_line(models.Model):
    _name = 'leaves.calc.method.line'

    leave_type_id = fields.Many2one('hr.holidays.status', string='Leave Type')
    greater_than = fields.Integer(string="Greater Than", default=lambda self: self._default_greater_than(), readonly=True)
    less_than = fields.Integer(string="Less Than")
    number_of_months = fields.Integer(string="Number Of Months", compute="_compute_number_of_months", store=True)
    calc_method = fields.Selection([('None', 'None'),
                                    ('Fixed Number', 'Fixed Number')], _('Calculation Method'), required=True, default="None")
    balance = fields.Float(string="Balance")
    monthly_balance = fields.Float(string="Monthly Balance", compute="_compute_monthly_balance", store=True)
    notes = fields.Text(string="Notes")
    max_line_less = fields.Integer(related="leave_type_id.max_line_less", readonly=True)

    def _default_greater_than(self):
        leave_type = self.env['hr.holidays.status'].search([('id', '=', self.env.context.get('leave_type_id', False))])
        return leave_type.max_line_less

    @api.onchange('less_than')
    def onchange_less_than(self):
        for rec in self:
            leave_type = self.env['hr.holidays.status'].search([('id', '=', self.env.context.get('leave_type_id', False))])
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
                [('greater_than', '=', rec.less_than), ('leave_type_id', '=', rec.leave_type_id.id)])
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
            [('leave_type_id', '=', vals['leave_type_id']), ('greater_than', '=', vals['greater_than'])])
        if same_record:
            same_record.with_context({'on_create': True}).unlink()
        res = super(calc_method_line, self).create(vals)
        last_line = self.env['leaves.calc.method.line'].search([('leave_type_id', '=', vals['leave_type_id'])], order="less_than desc", limit=1)
        if last_line:
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

    @api.constrains('balance')
    def _check_balance(self):
        if self.balance <= 0 and self.calc_method == "Fixed Number":
            raise exceptions.ValidationError("Balance Must be Positive number")

    @api.depends('balance')
    def _compute_monthly_balance(self):
        for rec in self:
            if rec.number_of_months == 0 or not rec.leave_type_id.months_in_year:
                rec.monthly_balance = 0
            else:
                mb = rec.balance / rec.leave_type_id.months_in_year
                rec.monthly_balance = round(mb, 2)

    @api.constrains('greater_than', 'less_than')
    def _check_greater_than(self):
        if self.greater_than >= self.less_than:
            raise exceptions.ValidationError("Configuration error!! The value in (less than) should be greater than the value in (greater than)")


class contract_work_permit_line(models.Model):
    _name = "contract.work.permit.line"

    name = fields.Char("Name")
    dayofweek = fields.Selection(
        [('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday')],
        'Day of Week', required=True, select=True)
    date_from = fields.Date('Starting Date')
    date_to = fields.Date('End Date')
    hour_from = fields.Float('Work from', required=True, help="Start and End time of working.", select=True)
    hour_to = fields.Float("Work to", required=True)
    contract_id = fields.Many2one("hr.contract", "Contract", required=True)


class hr_contract(models.Model):
    _inherit = "hr.contract"

    annual_leave_policy = fields.Many2one('hr.holidays.status', string='Annual Leave Policy', required=True)
    first_effective_notice = fields.Many2one('effective.notice', string='First Effective Notice')
    start_work = fields.Date(string="Starting Work at")
    leaves_calc_on = fields.Date('Leaves Will Be Calculated On')
    adjusted_date = fields.Date('Adjusted Date')
    attendance_ids = fields.One2many('contract.work.permit.line', 'contract_id', string='Working Time')
    working_calendar = fields.Selection([
        ('Working Days', 'Working Days'),
        ('Calendar days', 'Calendar days'),
    ], string='Working / Calendar')

    @api.multi
    @api.onchange('start_work', 'adjusted_date', 'leaves_calc_on')
    def check_dates(self):
        for rec in self:
            res = {}
            if rec.start_work and rec.adjusted_date and rec.leaves_calc_on:
                if rec.start_work != rec.adjusted_date or rec.start_work != rec.leaves_calc_on:
                    message = _(
                        'Attention !! Be careful, Employee Start working on ( %s ) adjusted date is ( %s ) leaves will be calculated on ( %s ) this may affect annual leave and air ticket automatic allocation. we highly recommend not to change the dates on these fields.') % (
                              rec.start_work, rec.adjusted_date, rec.leaves_calc_on)
                    res = {'warning': {
                        'title': _('Warning'),
                        'message': message}
                    }
            return res

    @api.one
    @api.onchange('annual_leave_policy')
    def change_working_calendar(self):
        self.working_calendar = self.annual_leave_policy.working_calendar

    @api.one
    @api.onchange('first_effective_notice')
    def onchange_first_effective_notice(self):
        self.start_work = self.first_effective_notice.start_work

    @api.onchange('employee_id')
    def onchange_employee(self):
        if not self.employee_id:
            self.job_id = False
            self.department_id = False
        if self.employee_id.job_id:
            self.job_id = self.employee_id.job_id.id
        if self.employee_id.department_id:
            self.department_id = self.employee_id.department_id.id

        self.first_effective_notice = 'null'
        self.working_hours = 'null'
        return {'domain': {
            'first_effective_notice': [('employee_id', '=', self.employee_id.id), ('state', '!=', 'Refused'), ('type', '=', 'New Employee')]}}

    @api.onchange('annual_leave_policy', 'start_work', 'trial_date_start', 'date_start')
    def _compute_leaves_calc_on(self):
        for rec in self:
            if rec.annual_leave_policy.start_calc_from == "First Effective Notice":
                rec.leaves_calc_on = rec.start_work
            if rec.annual_leave_policy.start_calc_from == "Contract Start Date":
                rec.leaves_calc_on = rec.date_start
            if rec.annual_leave_policy.start_calc_from == "Trial Period Start Date":
                rec.leaves_calc_on = rec.trial_date_start

    @api.multi
    @api.onchange('working_hours')
    def get_attendance_ids(self):
        for rec in self:
            if rec.working_hours:
                attendance_ids = self.env['resource.calendar.attendance'].search([['calendar_id', '=', rec.working_hours.id]])
                line_vals = []
                for attendance_id in attendance_ids:
                    vals = {
                        'name': attendance_id.name,
                        'dayofweek': attendance_id.dayofweek,
                        'date_from': attendance_id.date_from,
                        'date_to': attendance_id.date_to,
                        'hour_from': attendance_id.hour_from,
                        'hour_to': attendance_id.hour_to,
                        'contract_id': rec.id,
                    }
                    line_vals.append(vals)
                rec.attendance_ids = line_vals
            else:
                rec.attendance_ids = False

    @api.onchange('leaves_calc_on')
    def _compute_adjusted_date(self):
        for rec in self:
            if rec.leaves_calc_on:
                date = datetime.strptime(rec.leaves_calc_on, "%Y-%m-%d")
                day = date.day
                if day in [29, 30, 31]:
                    date = date.replace(day=28)
                rec.adjusted_date = date


class ContractHistory(models.Model):
    _inherit = ['hr.contract', 'hr.contract.history']
    _name = "hr.contract.history"


class ContractRenewal(models.Model):
    _inherit = 'contract.renewal'

    adjusted_date = fields.Date('Adjusted Date')

    @api.one
    @api.onchange('employee_id')
    def onchange_employee_id_leaves(self):
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('active', '=', True)])
        if len(contracts):
            self.adjusted_date = self.contract_id.adjusted_date


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

    leave_id = fields.Many2one('hr.holidays', string='leave request')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    holidays_status_id = fields.Many2one('hr.holidays.status', 'Leave type')
    month = fields.Selection(_PERIOD, 'Month')
    year = fields.Integer('Year')
    days = fields.Float('Number of days per month')
    complete_month = fields.Boolean('Complete Month')
    deduction_date = fields.Date()
    state = fields.Selection(string='Leave request status', related='leave_id.state', readonly=True, store=True)


class hr_holidays(models.Model):
    _name = "hr.holidays"
    _inherit = ["hr.holidays", "salary.details"]
    _order = "id desc"

    MONTHS_SELECTION = {'01': 'January', '02': 'February', '03': 'March', '04': 'April', '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                        '09': 'September', '10': 'October', '11': 'November', '12': 'December'}

    employee_id = fields.Many2one('hr.employee', "Employee", default=lambda self: self.env.user.employee_ids and self.env.user.employee_ids[0].id)

    holiday_status_id = fields.Many2one("hr.holidays.status", "Leave Type", required=True, readonly=True,
                                        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                        domain=[('state', 'in', ['Approved'])])
    reconciliation_method = fields.Selection([('Stop payslip during leave and use leave reconciliation', 'Yes'),
                                              ('Continue payslip during leave ( no need for leave reconciliation)', 'No')],
                                             string='Request Salary In Advance')
    reconciliation_method_readonly = fields.Boolean(compute='get_reconciliation_method_readonly')
    holiday_status_type = fields.Selection([('Annual Leave', 'Annual Leave'),
                                            ('Non Annual Leave', '‫‪Non Annual Leave‬‬')], related='holiday_status_id.type', readonly=True)
    allow_minus_value = fields.Boolean('Allow Minus Value')
    contract_id = fields.Many2one('hr.contract', string=_('Contract'), compute="_compute_contract", readonly=True, store=True)
    annual_leave_policy = fields.Many2one('hr.holidays.status', string='Annual Leave Policy', related="contract_id.annual_leave_policy",
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
    nationality_type = fields.Selection([('Native', 'Native'),
                                         ('Non-native', 'Non-native')], )
    branch_id = fields.Many2one('hr.branch', string='Branch')
    department_id = fields.Many2one('hr.department', string=_('Department'))
    job_id = fields.Many2one('hr.job', string=_('Job Title'))
    country_id = fields.Many2one('res.country', '‫‪Nationality‬‬')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender')
    last_working_day = fields.Date('last working day', compute='compute_last_working_day')
    last_working_week_day = fields.Char('Last Working week day', compute='get_date_day')
    expected_working_day = fields.Date('Expected working day', compute='compute_expected_working_day')
    expected_working_week_day = fields.Char('Expected working week day', compute='get_date_day')
    reconciliation_based_on = fields.Selection([
        ('basic', 'Basic Salary'),
        ('basic_house', 'Basic Salary + House allowance'),
        ('basic_house_transportation', 'Basic Salary + House allowance + transportation'),
        ('basic_house_transportation_phone', 'Basic salary + House + transportation + phone'),
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
    holiday_history_ids = fields.Many2many('hr.holidays', 'rel_leave_history', 'leave_id', 'history_id', string='Leave history')
    linked_exit_renry_id = fields.Many2one('hr.exit.entry.request', 'Linked exit and Re-entry')
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
    count_exit_rentry_requests = fields.Float('Number of Exit and Re-entry', compute='get_count_smart_buttons', multi=True)
    exit_rentry_request_ids = fields.One2many('hr.exit.entry.request', 'leave_request_id', 'Exit and Re-entry requests')
    leave_requests_id = fields.Many2one('hr.holidays')
    old_leave_requests_ids = fields.One2many('hr.holidays', 'leave_requests_id', 'Old leave requests', compute='get_old_leave_requests')
    count_old_leave_requests = fields.Integer('Number of old leave requests', compute='get_count_smart_buttons', multi=True)
    old_similar_leave_requests_ids = fields.One2many('hr.holidays', 'leave_requests_id', 'Similar leave requests',
                                                     compute='get_similar_leave_requests')
    count_similar_leave_requests = fields.Integer('Number of old leave requests', compute='get_count_smart_buttons', multi=True)
    linked_leave_reconciliation_id = fields.Many2one('hr.leave.reconciliation', 'Linked Leave reconciliation')
    date_from_day = fields.Char('Date From Day', compute='get_date_day')
    date_to_day = fields.Char('Date To Day', compute='get_date_day')
    leave_extended = fields.Boolean('Leave Extended')
    leave_request_extend_id = fields.Many2one('hr.holidays', 'leave request to extend this leave')
    original_leave_request_id = fields.Many2one('hr.holidays', 'Original Leave request')
    return_from_leave = fields.Many2one('effective.notice', 'Return from leave')
    return_from_leave_date = fields.Date('Return from leave date', related="return_from_leave.start_work", readonly=True)
    button_extend_invisible = fields.Boolean('button extend invisible', compute='get_button_extend_invisible')
    early_return_from_leave = fields.Many2one('effective.notice', 'Early Return from leave')
    late_return_from_leave = fields.Many2one('effective.notice', 'Late Return from leave')
    count_reconciliations = fields.Integer('Number of old leave requests', compute='get_count_smart_buttons', multi=True)
    count_return_from_leave = fields.Integer('Number of return from leaves', compute='get_count_smart_buttons')
    adjusted_date = fields.Date('Adjusted Date', related='contract_id.adjusted_date', readonly=True)
    reconciliation_paid_line_ids = fields.One2many('leave.reconciliation.paid.line', 'request_id', 'Paid Amounts')
    by_eos = fields.Boolean('Through EOS')
    state = fields.Selection(
        [('draft', 'Draft'), ('cancel', 'Cancelled'), ('confirm', 'Direct Manager Approval'), ('validate1', 'Dep Manager Approval'),
         ('validate', 'HR Approval'), ('refuse', 'Refused')],
        'Status', readonly=False, copy=False, default='draft', )
    show_recompute_balance = fields.Boolean('Show', compute='_compute_show_recompute_balance')
    expected_addition_days = fields.Float('Expected Addition Days', compute='_compute_expected_addition_days', store=1)
    expected_balance_leave_start = fields.Float('Expected balance At Leave Start Date', compute='_compute_expected_addition_days', store=1,
                                                help='If employee deserves 3 days annual leave per month, at leave request date ( for example 01/01/2018), employee’s balance was 10 days, if he request for a leave at 01/3/2018, your system expect that his balance should be ( 10 current balance + 3 days for Jan + 3 days for Feb = 16 days. this is what is meant by (Expected balance at leave start date).')
    expected_balance_year_end = fields.Float('Expected balance At year end date', compute='_compute_expected_balance_year_end', store=1, )
    show_expected_balance_year_end = fields.Boolean(compute='_compute_show_expected_balance_year_end')
    show_expected_balance_leave_start = fields.Boolean(compute='_compute_show_expected_balance_leave_start')
    expected_remaining_balance = fields.Float('Expected Remaining balance', compute='_compute_expected_remaining_balance', store=True)
    request_leave_in_advance = fields.Boolean('Request leave in advance')
    show_request_leave_in_advance = fields.Boolean(compute='_compute_show_request_leave_in_advance')
    days_label = fields.Char(compute='_compute_days_label')
    can_reset = fields.Boolean('Can Reset', compute='_get_can_reset')
    leave_days_ids = fields.One2many('leave.month.days', 'leave_id', 'Number of days per each month')
    days_per_months = fields.Float('Number of days per month', compute='_compute_days_per_months', store=True)
    alternative_employee = fields.Many2one('hr.employee', 'Alternative Employee')
    show_alternative_employee = fields.Boolean('Show Alternative Employee', compute='_compute_show_alternative_employee')
    accept_without_alternative = fields.Boolean('accept leave request without employee alternative')
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
    report_holiday_na_balance = fields.Float('Non annual balance')
    alternative_approval = fields.Boolean('Alternative employee Approval')
    leave_address_required = fields.Boolean(related='holiday_status_id.leave_address_required', readonly=1)
    mandatory_return_from_leave = fields.Selection([
        ('Yes', 'Yes'),
        ('No', 'No'),
    ], string='Mandatory to create Return from leave', )
    return_from_leave_counter = fields.Integer('Return from leave counter')
    bypass_past_days = fields.Boolean('Bypass validation for past days')
    bypass_future_days = fields.Boolean('Bypass validation for future days')

    @api.one
    @api.onchange('contract_id')
    def get_related_fields(self):
        self.nationality_type = self.employee_id.nationality_type
        self.branch_id = self.employee_id.branch_id
        self.department_id = self.employee_id.department_id
        self.job_id = self.employee_id.job_id
        self.country_id = self.employee_id.country_id
        self.gender = self.employee_id.gender

    @api.one
    def check_past_future(self):
        if self.type == 'remove':
            if not self.bypass_past_days:
                allowed_past = datetime.now() - timedelta(days=self.holiday_status_id.allow_past + 1)
                if self.date_from < allowed_past.strftime("%Y-%m-%d"):
                    raise ValidationError(
                        'Not allowed !! \n Employee ( %s ) is not allowed to request for this leave, start date must be greater than ( %s ). Based on system configuration for leave type ( %s )  it is allowed to request leave for past ( %s ) days'
                        % (self.employee_id.name, allowed_past.strftime("%Y-%m-%d"), self.holiday_status_id.name, self.holiday_status_id.allow_past))
            if not self.bypass_future_days:
                allowed_future = datetime.now() + timedelta(days=self.holiday_status_id.allow_future + 1)
                if self.date_from > allowed_future.strftime("%Y-%m-%d"):
                    raise ValidationError(
                        'Not allowed !! \n Employee ( %s ) is not allowed to request for this leave, start date must be less than ( %s ). Based on system configuration for leave type ( %s )  it is allowed to request leave for future ( %s ) days'
                        % (
                        self.employee_id.name, allowed_future.strftime("%Y-%m-%d"), self.holiday_status_id.name, self.holiday_status_id.allow_future))

    @api.one
    @api.constrains('date_from', 'employee_id')
    def check_leave_after_contract_start(self):
        if self.type == 'remove' and self.date_from < self.contract_id.start_work:
            raise ValidationError(
                'Not allowed !! \n Employee ( %s ) joining date is ( %s ) it is not logic to start the leave on ( %s ) which is less than joining date.' % (
                self.employee_id.name, self.contract_id.start_work, self.date_from))

    @api.one
    def compute_return_from_leave_counter(self):
        has_return_from_leave = self.env['effective.notice'].search([('leave_request_id', '=', self.id), ('state', '!=', 'Refused'), ])
        if has_return_from_leave:
            self.return_from_leave_counter = 0
        else:
            self.return_from_leave_counter = (datetime.strptime(self.expected_working_day, "%Y-%m-%d") - datetime.today()).days

    @api.model
    def update_numerical_fields(self):
        for leave in self.search([('type', '=', 'remove'), ('mandatory_return_from_leave', '=', 'Yes'), ('state', '=', 'validate'),
                                  ('leave_request_extend_id', '=', False), ('return_from_leave', '=', False)]):
            leave.compute_return_from_leave_counter()

    @api.multi
    @api.onchange('contract_id')
    def get_employee_domain(self):
        employees = self.env['hr.employee'].search([])

        if self.env.user.has_group('base.group_hr_user'):
            return {'domain': {'employee_id': [('id', 'in', employees.ids)]}}
        elif self.env.user.has_group('saudi_hr_employee.group_hr_department_manager'):
            return {'domain': {'employee_id': [('department_id', 'child_of', self.env.user.employee_ids[0].department_id.id)]}}
        elif self.env.user.has_group('saudi_hr_employee.group_hr_direct_manager'):
            return {'domain': {'employee_id': [('id', 'child_of', self.env.user.employee_ids.ids)]}}
        else:
            return {'domain': {'employee_id': [('user_id', '=', self.env.user.id)]}}

    @api.one
    def _compute_report_holiday_na_balance(self):
        report_holiday_na_balance = 0
        for line in self.employee_id.non_annual_leave_balance:
            if line.holidays_status_id.id == self.holiday_status_id.id:
                report_holiday_na_balance = line.net_balance + self.number_of_days_temp
        self.report_holiday_na_balance = report_holiday_na_balance

    @api.one
    def _compute_report_holiday_till_date(self):
        if self.remaining_balance or self.remaining_balance == 0 or not self.holiday_status_id.max_advance_type or self.holiday_status_id.max_advance_type == 'fixed':
            self.report_holiday_till_balance = self.current_balance
            allocations = self.env['hr.holidays'].search([
                ('type', '=', 'add'),
                ('state', '=', 'validate'),
                ('employee_id', '=', self.employee_id.id),
                ('contract_id', '=', self.contract_id.id),
                ('holiday_status_id', '=', self.holiday_status_id.id),
            ], order='allocation_date desc')
            if allocations and allocations[0].allocation_date:
                self.report_holiday_till_date = allocations[0].allocation_date
            else:
                self.report_holiday_till_date = self.adjusted_date
        else:
            date_from = datetime.strptime(self.date_from, "%Y-%m-%d")
            year_end_date = date(date_from.year, 12, 31)
            self.report_holiday_till_date = year_end_date.strftime("%Y-%m-%d")
            self.report_holiday_till_balance = self.expected_balance_year_end

    @api.one
    def alternative_approve(self):
        if self.alternative_employee.user_id.id != self.env.uid and not self.env.user.has_group(
                'saudi_hr_employee.group_leave_Bypass_alternative_approval'):
            raise ValidationError(
                'Not Allowed !! \n You did not have the permission to click on ( Alternative employee approval ) for this employee ( %s ), '
                'only ( %s ) is allowed to click on this button, (or) you must have access to (Leave request Bypass Alternative employee approval)' % (
                self.employee_id.name, self.alternative_employee.name))
        self.sudo().alternative_approval = True
        body = "Alternative employee approval by %s" % self.env.user.name
        self.sudo().message_post(body=body, message_type='email')

    @api.one
    @api.constrains('expected_remaining_balance')
    def check_expected_remaining_balance(self):
        if self.type == 'remove' and self.holiday_status_id.type == 'Annual Leave‬‬' and self.expected_remaining_balance < 0:
            if not self.holiday_status_id.allow_leave_advance:
                raise ValidationError('Not Allowed! \n For Employee ( %s ) and based on your company policy for leave ( %s ) '
                                      'it is not allowed to request for a leaves in advance. Current balance is ( %s )  days, '
                                      'expected balance at leave start date is ( %s ) , so the expected remaining balance is ( %s ) days'
                                      % (self.employee_id.name, self.holiday_status_id.name, self.current_balance, self.expected_balance_leave_start,
                                         self.expected_remaining_balance))
            else:
                if self.holiday_status_id.max_advance_type == 'fixed':
                    if self.holiday_status_id.advance_days < abs(self.expected_remaining_balance):
                        raise ValidationError('Not Allowed! \n Employee ( %s ) is requesting for ( %s ) , current balance is ( %s ) '
                                              ', expected balance at leave start date is  ( %s ) ,  based on leave policy, maximum days in advance is '
                                              '( %s ) , based on your system calculation, you are requesting for ( %s ) days in advance which exceeds company policy.'
                                              % (self.employee_id.name, self.holiday_status_id.name, self.current_balance,
                                                 self.expected_balance_leave_start, self.holiday_status_id.advance_days,
                                                 self.expected_remaining_balance))
                if self.holiday_status_id.max_advance_type == 'year_end':
                    if self.expected_remaining_balance < 0:
                        raise ValidationError('Not Allowed! \n Employee ( %s ) is requesting for ( %s ) , current balance is ( %s ) '
                                              ', expected leave balance at year end date is   ( %s ) ,  number of days requested is '
                                              '( %s ) , so the expected remaining balance is ( %s ) \n'
                                              'Based on your company policy, it is not allowed to request for leave in advance which exceeds employee balance at financial year end date ( 31-12 )'
                                              % (self.employee_id.name, self.holiday_status_id.name, self.current_balance,
                                                 self.expected_balance_year_end, self.number_of_days_temp, self.expected_remaining_balance))

    @api.one
    @api.depends('employee_id', 'holiday_status_id', 'request_reason')
    def _compute_show_expected_balance_year_end(self):
        if self.request_reason == 'annual' and self.holiday_status_id.allow_leave_advance and self.holiday_status_id.max_advance_type == 'year_end':
            self.show_expected_balance_year_end = True
        else:
            self.show_expected_balance_year_end = False

    @api.one
    @api.depends('employee_id', 'holiday_status_id', 'annual_leave_policy', )
    def _compute_expected_balance_year_end(self):
        year_end_addition_days = 0
        if self.show_expected_balance_year_end and self.contract_id:
            # ////////////////////////////////////////////////////////////////////
            contract = self.contract_id
            allocate_till_year_end = date(date.today().year, 12, 31)
            if contract.adjusted_date >= allocate_till_year_end.strftime("%Y-%m-%d"):
                year_end_addition_days = 0
                self.expected_balance_year_end = year_end_addition_days + self.current_balance
                return
            start_after_months = contract.annual_leave_policy.start_allocation_after
            adjusted_date = datetime.strptime(contract.adjusted_date, "%Y-%m-%d")
            start_after_date = adjusted_date + relativedelta(months=start_after_months)
            if allocate_till_year_end.strftime("%Y-%m-%d") < start_after_date.strftime("%Y-%m-%d"):
                year_end_addition_days = 0
                self.expected_balance_year_end = year_end_addition_days + self.current_balance
                return
            adjusted_date_day = adjusted_date.day
            allocate_till_year_end_day = allocate_till_year_end.day
            effictive_allocate_date = allocate_till_year_end
            if adjusted_date_day > allocate_till_year_end_day:
                effictive_allocate_date = allocate_till_year_end.replace(day=adjusted_date_day)
                effictive_allocate_date = effictive_allocate_date - relativedelta(months=1)
            elif adjusted_date_day < allocate_till_year_end_day:
                effictive_allocate_date = allocate_till_year_end.replace(day=adjusted_date_day)
            duration = relativedelta(effictive_allocate_date, adjusted_date)
            duration_months = duration.months + duration.years * 12
            if duration_months == 0 or duration_months < start_after_months:
                year_end_addition_days = 0
                self.expected_balance_year_end = year_end_addition_days + self.current_balance
                return
            alloctions = self.env['hr.holidays'].search(
                [('employee_id', '=', contract.employee_id.id), ('holiday_status_id', '=', contract.annual_leave_policy.id), ('type', '=', 'add')])
            first_calc_line = self.env['leaves.calc.method.line'].search(
                [('greater_than', '=', 0), ('leave_type_id', '=', contract.annual_leave_policy.id)])
            if not first_calc_line:
                raise exceptions.ValidationError(
                    "Out of range!! Cannot calculate automatic leave Please review your leave type’s configuration. for contract (%s)" % contract.name)
            if not len(alloctions):
                leaves = self.env['leave.automatic.allocation'].calc_leaves(first_calc_line, duration_months)
                number_dec = str(leaves - int(leaves))[1:]
                if number_dec >= 0.9:
                    leaves = round(leaves, 0)
                year_end_addition_days = leaves
            if len(alloctions):
                last_allocation = self.env['hr.holidays'].search(
                    [('employee_id', '=', contract.employee_id.id), ('holiday_status_id', '=', contract.annual_leave_policy.id),
                     ('type', '=', 'add')],
                    order="allocation_date desc", limit=1)
                if last_allocation and last_allocation.allocation_date:
                    last_allocation_date = datetime.strptime(last_allocation.allocation_date, "%Y-%m-%d")
                    if allocate_till_year_end.strftime("%Y-%m-%d") <= last_allocation_date.strftime("%Y-%m-%d"):
                        year_end_addition_days = 0
                        self.expected_balance_year_end = year_end_addition_days + self.current_balance
                        return
                else:
                    year_end_addition_days = 0
                    self.expected_balance_year_end = year_end_addition_days + self.current_balance
                    return
                non_computed_duration = relativedelta(effictive_allocate_date, last_allocation_date)
                non_computed_duration_months = non_computed_duration.months + non_computed_duration.years * 12
                if non_computed_duration_months <= 0:
                    year_end_addition_days = 0
                    self.expected_balance_year_end = year_end_addition_days + self.current_balance
                    return
                computed_duration = relativedelta(last_allocation_date, adjusted_date)
                computed_duration_months = computed_duration.months + computed_duration.years * 12 + computed_duration.days / contract.annual_leave_policy.days_in_month

                computed_leaves = self.env['leave.automatic.allocation'].calc_leaves(first_calc_line, computed_duration_months)
                leaves = self.env['leave.automatic.allocation'].calc_leaves(first_calc_line, duration_months)
                non_computed_leaves = leaves - computed_leaves
                number_dec = str(non_computed_leaves - int(non_computed_leaves))[1:]
                if number_dec >= 0.9:
                    non_computed_leaves = non_computed_leaves  # round(non_computed_leaves, 0)

                year_end_addition_days = non_computed_leaves

            # ////////////////////////////////////////////////////////////////////
        self.expected_balance_year_end = year_end_addition_days + self.current_balance

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
    @api.onchange('department_id')
    def get_leave_address(self):
        self.leave_address = self.employee_id.leave_address
        self.leave_phone = self.employee_id.leave_phone

    @api.one
    def set_refused_by(self):
        self.refused_by = self.env.uid
        self.refused_date = datetime.now().strftime('%Y-%m-%d')
        body = "Document Refused"
        self.message_post(body=body, message_type='email')

    @api.one
    def holidays_reset_message(self):
        if self.create_date != self.write_date:
            body = "Document Reset to draft"
            self.message_post(body=body, message_type='email')

    @api.one
    def set_confirmed_by(self):
        self.direct_approved_by = self.env.uid
        self.direct_approved_date = datetime.now().strftime('%Y-%m-%d')
        body = "Document Approved By Direct Manager"
        self.message_post(body=body, message_type='email')
        if not self.employee_id.department_manager or not self.employee_id.department_manager.active or self.employee_id.department_manager == self.employee_id.parent_id or self.employee_id == self.employee_id.department_manager:
            self.sudo().signal_workflow('validate')

    @api.one
    def check_confirm_authorized(self):
        if self.type == 'remove' and self.employee_id.department_manager.user_id.id != self.env.uid and self.employee_id.parent_id.user_id.id != self.env.uid and not self.env.user.has_group(
                'saudi_hr_employee.group_leave_bypass_direct_manager'):
            raise ValidationError(
                'Not Allowed !! \n You did not have the permission to click on ( Direct manager approval ) for this employee ( %s ), only His / Her Department manager  ( %s ) can click on this button, (or) you must have access to (Leave request Bypass Department manager approval)' % (
                self.employee_id.name, self.employee_id.department_manager.name))

    @api.one
    @api.onchange('request_reason', 'holiday_status_id', 'number_of_days_temp')
    def get_reconciliation_method(self):
        if self.request_reason == 'annual':
            if self.holiday_status_id.reconciliation_method == 'Continue payslip during leave ( no need for leave reconciliation)' or (
                    self.holiday_status_id.reconciliation_method == 'Stop payslip during leave and use leave reconciliation' and self.holiday_status_id.leave_reconciliation_minimum > self.number_of_days_temp):
                self.reconciliation_method = 'Continue payslip during leave ( no need for leave reconciliation)'
            else:
                self.reconciliation_method = False
        else:
            self.reconciliation_method = self.holiday_status_id.reconciliation_method

    @api.one
    @api.depends('request_reason', 'holiday_status_id', 'number_of_days_temp')
    def get_reconciliation_method_readonly(self):
        if self.request_reason == 'annual' and self.holiday_status_id.reconciliation_method == 'Stop payslip during leave and use leave reconciliation' and self.holiday_status_id.leave_reconciliation_minimum <= self.number_of_days_temp:
            self.reconciliation_method_readonly = False
        else:
            self.reconciliation_method_readonly = True

    @api.one
    @api.constrains('employee_id', 'alternative_employee')
    def check_employee_equal_alternative(self):
        if self.employee_id == self.alternative_employee:
            raise ValidationError('Employee %s can not be alternative for himself' % self.employee_id.name)

    @api.one
    def check_alternative(self):
        if self.employee_id == self.alternative_employee:
            raise ValidationError('Employee %s can not be alternative for himself' % self.employee_id.name)
        if not self.skip_basic_return:
            domain = [
                ('date_from', '<=', self.date_to),
                ('date_to', '>=', self.date_from),
                ('alternative_employee', '=', self.employee_id.id),
                ('type', '=', 'remove'),
                ('state', '=', 'validate'),
            ]
            me_alternative_leaves_conflicts = self.env['hr.holidays'].search(domain)
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
                                          % (self.employee_id.name, self.date_from.split(' ')[0], self.date_to.split(' ')[0],
                                             self.employee_id.name, conflict.employee_id.name,
                                             conflict.date_from.split(' ')[0], conflict.date_to.split(' ')[0],
                                             self.employee_id.name, conflict.employee_id.name,
                                             conflict.employee_id.name,))

        if self.show_alternative_employee and not self.accept_without_alternative:
            if not self.alternative_employee:
                raise ValidationError('Data Error !! \n Not allowed to approve this leave request ( %s ) '
                                      'Based on your company policy, leave type ( %s ) and job position  ( %s ) '
                                      'requires to have alternative employee, if number if leave days is equal to or greater than ( %s ) '
                                      'kindly select the alternative employee.'
                                      % (self.name, self.holiday_status_id.name, self.job_id.name, self.holiday_status_id.alternative_employee_days))

            domain = [
                ('date_from', '<=', self.date_to),
                ('date_to', '>=', self.date_from),
                ('employee_id', '=', self.alternative_employee.id),
                ('type', '=', 'remove'),
                ('state', '=', 'validate'),
            ]
            alternative_leaves_conflicts = self.env['hr.holidays'].search(domain)
            if alternative_leaves_conflicts:
                for conflict in alternative_leaves_conflicts:
                    raise ValidationError('Not allowed !! \n Employee ( %s ) requests for a leave between ( %s ) and  ( %s ) '
                                          'Alternative employee for ( %s ) is ( %s ) your system found that ( %s ) have approved leave '
                                          'request between ( %s ) and ( %s ) which conflict with ( %s ) leave request.\n'
                                          'You have 3 options.\n'
                                          '1 - Change the start and end date for ( %s ) to avoid any conflict with  ( %s ) leave\n'
                                          '2 - Select another alternative employee for ( %s )\n'
                                          '3 - Employee ( %s ) Cancel his leave or return early from leave.\n'
                                          % (self.employee_id.name, self.date_from.split(' ')[0], self.date_to.split(' ')[0],
                                             self.employee_id.name, self.alternative_employee.name, self.alternative_employee.name,
                                             conflict.date_from.split(' ')[0], conflict.date_to.split(' ')[0], self.employee_id.name,
                                             self.employee_id.name, self.alternative_employee.name,
                                             self.employee_id.name, self.alternative_employee.name,))

            if not self.alternative_approval and self.state == 'confirm':
                raise ValidationError('Not Allowed !! \n Employee ( %s  ) Leave request requires alternative '
                                      'employee approval before HR department approval.' % self.employee_id.name)

    @api.one
    @api.onchange('holiday_status_id', 'employee_id', 'date_from', 'date_to', 'request_reason')
    def empty_alternative_employee(self):
        self.alternative_employee = False
        self.accept_without_alternative = False

    @api.one
    @api.onchange('accept_without_alternative')
    def onchange_accept_without_alternative(self):
        self.alternative_employee = False

    @api.one
    @api.depends('holiday_status_id', 'job_id', 'date_from', 'date_to')
    def _compute_show_alternative_employee(self):
        if self.holiday_status_id.is_alternative_employee == 'yes' and self.job_id.is_alternative_employee == 'yes' and self.number_of_days_temp >= self.holiday_status_id.alternative_employee_days:
            self.show_alternative_employee = True
        else:
            self.show_alternative_employee = False

    @api.one
    @api.depends('leave_days_ids')
    def _compute_days_per_months(self):
        self.days_per_months = sum(line.days for line in self.leave_days_ids)

    @api.one
    @api.constrains('leave_days_ids')
    def check_leave_days_ids(self):
        if self.holiday_status_id.max_per_month:
            for line in self.leave_days_ids:
                month_same_leaves = self.env['leave.month.days'].search(
                    [('employee_id', '=', line.employee_id.id), ('holidays_status_id', '=', line.holidays_status_id.id), ('month', '=', line.month),
                     ('year', '=', line.year), ('state', '=', 'validate'), ('id', '!=', line.id)])
                month_same_leaves_days = sum(l.days for l in month_same_leaves)
                total_month_days = month_same_leaves_days + line.days
                if total_month_days > self.holiday_status_id.max_per_month:
                    raise ValidationError(
                        "Not allowed !! \n Maximum days per month allowed for ( %s ) is ( %s ) days, you system found that employee ( %s ) exceeds this limit for ( %s ) , year = ( %s )" % (
                        self.holiday_status_id.name, self.holiday_status_id.max_per_month, self.employee_id.name, self.MONTHS_SELECTION[line.month],
                        line.year))

    @api.onchange('date_from', 'date_to', 'request_reason', 'holiday_status_id')
    def _compute_leave_days_ids(self):
        if self.date_to and self.date_from:
            periods_by_month = self.devide_period_by_month(self.date_from, self.date_to)
            for period in periods_by_month:
                number_of_days = self.get_duration_number_of_days(period['from'], period['to'])
                period['number_of_days'] = number_of_days

            self.leave_days_ids = [(5,)]
            vals = []
            for period in periods_by_month:
                DATE_FORMAT = "%Y-%m-%d"
                period_date = datetime.strptime(period['from'].split(' ')[0], DATE_FORMAT)
                # //////// check period is complete month ////////////////////////////////
                start_end = calendar.monthrange(int(period_date.strftime('%Y')), int(period_date.strftime("%m")))
                month_last_day = str(period_date.strftime('%Y')) + '-' + str(period_date.strftime("%m")) + '-' + str(start_end[1])
                month_start = str(period_date.strftime('%Y')) + '-' + str(period_date.strftime("%m")) + '-01'
                complete_month = False
                if period['from'] == month_start and period['to'] == month_last_day:
                    month_days = (datetime.strptime(period['to'], DATE_FORMAT) - datetime.strptime(period['from'], DATE_FORMAT)).days + 1
                    if month_days == period['number_of_days']:
                        complete_month = True
                vals.append({
                    'employee_id': self.employee_id.id,
                    'holidays_status_id': self.holiday_status_id.id,
                    'month': period_date.strftime("%m"),
                    'year': period_date.strftime('%Y'),
                    'days': period['number_of_days'],
                    'complete_month': complete_month,
                    'deduction_date': period['to'],
                })
            self.leave_days_ids = vals

    def get_duration_number_of_days(self, date_from, date_to):
        # Compute and update the number of days
        if date_to and date_from:
            # ///////// Check if working days or calendar days
            if self.holiday_status_id == self.annual_leave_policy:
                working_calendar = self.contract_id.working_calendar
            else:
                working_calendar = self.holiday_status_id.working_calendar
            if working_calendar == 'Working Days':
                if self.contract_id.attendance_ids:
                    date_from_date = datetime.strptime(date_from, "%Y-%m-%d")
                    date_to_date = datetime.strptime(date_to, "%Y-%m-%d")
                    working_days = 0
                    for leave_date in self.daterange(date_from_date, date_to_date):
                        if self.check_day_on_working_days(leave_date):
                            if self.check_day_not_on_holiday(leave_date):
                                working_days += 1
                    number_of_days = working_days
                    return number_of_days

            if working_calendar == 'Calendar days':
                national_holidays = self.env['hr.national.holiday'].search([('duration_in_leave_request', '=', 'No'), ('state', '=', 'Confirmed')])
                total_conflict_days = 0
                for holiday in national_holidays:
                    if holiday.end_date < date_from or holiday.start_date > date_to:
                        continue
                    else:
                        if holiday.start_date > date_from:
                            conflict_start = holiday.start_date
                        else:
                            conflict_start = date_from

                        if holiday.end_date < date_to:
                            conflict_end = holiday.end_date
                        else:
                            conflict_end = date_to
                        if not holiday.branches or self.employee_id.branch_id.id in holiday.branches.ids:
                            conflict_days = self._get_number_of_days(conflict_start, conflict_end) + 1
                            total_conflict_days += conflict_days
                diff_day = self._get_number_of_days(date_from, date_to)
                number_of_days = round(math.floor(diff_day)) + 1 - total_conflict_days
                return number_of_days
        else:
            number_of_days = 0
            return number_of_days

    def get_month_days(self, date_from, date_to):

        start_date = datetime.strptime(date_from, "%Y-%m-%d")
        end_date = datetime.strptime(date_to, "%Y-%m-%d")
        duration = relativedelta(end_date, start_date)

        month_start = date(start_date.year, start_date.month, 1)
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        month_end = date(start_date.year, start_date.month, last_day)
        if duration.days in [27, 28, 30] and (
                start_date.month == end_date.month and start_date.day == month_start.day and end_date.day == month_end.day):
            duration_days = 29
        else:
            duration_days = duration.days
        number_of_days = (duration.years * 12 + duration.months) * 30 + duration_days + 1
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
            month_last_day = datetime.strptime(month_last_day, DATE_FORMAT).strftime(DATE_FORMAT)

            next_month = date_from_date + relativedelta(months=1)
            next_month_start = str(next_month.year) + '-' + str(next_month.month) + '-01'
            period['to'] = month_last_day
            periods.append(period)
            return periods + self.devide_period_by_month(next_month_start, date_to)

    # @api.v7
    @api.one
    def _get_can_reset(self):
        """User can reset a leave request if it is its own leave request or if
        he is an Hr Manager. """
        user = self.env.user
        group_hr_user_id = self.env['ir.model.data'].get_object_reference('base', 'group_hr_user')[1]
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
    def check_all_constrains(self):
        self.check_paid_amount()
        self.check_contract_and_annual_leave_policy()
        # self._check_employee_id()
        self._check_holiday_type()
        self._check_number_of_days_temp()
        self._check_contract_id()
        self._check_holiday_status_id()
        self.check_leave_days_ids()

    @api.multi
    def write(self, vals):
        self.check_past_future()
        self.check_all_constrains()
        res = super(hr_holidays, self).write(vals)
        for rec in self:
            rec.sudo().employee_id.refresh_non_annual()
        return res

    @api.one
    @api.depends('holiday_status_id', 'annual_leave_policy')
    def _compute_days_label(self):
        if self.holiday_status_id == self.annual_leave_policy:
            working_calendar = self.contract_id.working_calendar
        else:
            working_calendar = self.holiday_status_id.working_calendar

        self.days_label = working_calendar

    def check_holidays(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.holiday_type != 'employee' or record.type != 'remove' or not record.employee_id or record.holiday_status_id.limit or record.holiday_status_id == record.annual_leave_policy:
                continue
            # leave_days = self.pool.get('hr.holidays.status').get_days(cr, uid, [record.holiday_status_id.id], record.employee_id.id, context=context)[record.holiday_status_id.id]
            # if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or \
            #   float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
            #     return False
        return True

    @api.one
    @api.constrains('state', 'number_of_days_temp')
    def check_old_balance(self):
        if self.holiday_type == 'employee' and self.type == 'remove' and self.employee_id and not self.holiday_status_id.limit and self.holiday_status_id != self.annual_leave_policy and self.state != 'validate':
            leave_days = self.holiday_status_id.get_days(self.employee_id.id)[self.holiday_status_id.id]
            if leave_days['remaining_leaves'] < self.number_of_days_temp:
                raise ValidationError(
                    'Not allowed !! \n Employee (%s) Request for ( %s ) days, employee balance is ( %s ). you are not allowed to request number of days more than the remaining balance.' % (
                    self.employee_id.name, self.number_of_days_temp, leave_days['remaining_leaves']))

    @api.one
    @api.onchange('show_request_leave_in_advance')
    def onchange_show_request_leave_in_advance(self):
        if not self.show_request_leave_in_advance:
            self.request_leave_in_advance = False

    @api.one
    @api.depends('show_expected_balance_leave_start', 'number_of_days_temp', 'expected_balance_leave_start')
    def _compute_show_request_leave_in_advance(self):
        if self.show_expected_balance_leave_start and self.expected_balance_leave_start < self.number_of_days_temp:
            self.show_request_leave_in_advance = True
        else:
            self.show_request_leave_in_advance = False

    @api.one
    @api.depends('employee_id', 'holiday_status_id', 'date_from', 'date_to')
    def _compute_expected_remaining_balance(self):
        if self.holiday_status_id.limit:
            self.expected_remaining_balance = 0
        else:
            if self.current_balance > self.expected_balance_leave_start:
                self.expected_remaining_balance = self.current_balance - self.number_of_days_temp
            else:
                if self.show_expected_balance_year_end:
                    self.expected_remaining_balance = self.expected_balance_year_end - self.number_of_days_temp
                else:
                    self.expected_remaining_balance = self.expected_balance_leave_start - self.number_of_days_temp

    @api.one
    @api.depends('employee_id', 'holiday_status_id', 'annual_leave_policy', 'date_from')
    def _compute_expected_addition_days(self):
        self.expected_addition_days = 0
        if self.show_expected_balance_leave_start:
            # ////////////////////////////////////////////////////////////////////
            contract = self.contract_id
            allocate_till_date = self.date_from
            if contract.adjusted_date >= allocate_till_date:
                self.expected_addition_days = 0
                self.expected_balance_leave_start = self.expected_addition_days + self.current_balance
                return
            start_after_months = contract.annual_leave_policy.start_allocation_after
            adjusted_date = datetime.strptime(contract.adjusted_date, "%Y-%m-%d")
            allocate_till_date = datetime.strptime(allocate_till_date, "%Y-%m-%d %H:%M:%S")
            start_after_date = adjusted_date + relativedelta(months=start_after_months)
            if allocate_till_date < start_after_date:
                self.expected_addition_days = 0
                self.expected_balance_leave_start = self.expected_addition_days + self.current_balance
                return
            adjusted_date_day = adjusted_date.day
            allocate_till_date_day = allocate_till_date.day
            effictive_allocate_date = allocate_till_date
            if adjusted_date_day > allocate_till_date_day:
                effictive_allocate_date = allocate_till_date.replace(day=adjusted_date_day)
                effictive_allocate_date = effictive_allocate_date - relativedelta(months=1)
            elif adjusted_date_day < allocate_till_date_day:
                effictive_allocate_date = allocate_till_date.replace(day=adjusted_date_day)
            duration = relativedelta(effictive_allocate_date, adjusted_date)
            duration_months = duration.months + duration.years * 12
            if duration_months == 0 or duration_months < start_after_months:
                self.expected_addition_days = 0
                self.expected_balance_leave_start = self.expected_addition_days + self.current_balance
                return
            alloctions = self.env['hr.holidays'].search(
                [('employee_id', '=', contract.employee_id.id), ('holiday_status_id', '=', contract.annual_leave_policy.id), ('type', '=', 'add')])
            first_calc_line = self.env['leaves.calc.method.line'].search(
                [('greater_than', '=', 0), ('leave_type_id', '=', contract.annual_leave_policy.id)])
            if not first_calc_line:
                raise exceptions.ValidationError(
                    "Out of range!! Cannot calculate automatic leave Please review your leave type’s configuration. for contract (%s)" % contract.name)
            if not len(alloctions):
                leaves = self.env['leave.automatic.allocation'].calc_leaves(first_calc_line, duration_months)
                number_dec = str(leaves - int(leaves))[1:]
                if number_dec >= 0.9:
                    leaves = round(leaves, 0)
                self.expected_addition_days = leaves
            if len(alloctions):
                last_allocation = self.env['hr.holidays'].search(
                    [('employee_id', '=', contract.employee_id.id), ('holiday_status_id', '=', contract.annual_leave_policy.id),
                     ('type', '=', 'add')],
                    order="allocation_date desc", limit=1)
                if last_allocation and last_allocation.allocation_date:
                    last_allocation_date = datetime.strptime(last_allocation.allocation_date, "%Y-%m-%d")
                    if allocate_till_date <= last_allocation_date:
                        self.expected_addition_days = 0
                        self.expected_balance_leave_start = self.expected_addition_days + self.current_balance
                        return
                else:
                    self.expected_addition_days = 0
                    self.expected_balance_leave_start = self.expected_addition_days + self.current_balance
                    return
                non_computed_duration = relativedelta(effictive_allocate_date, last_allocation_date)
                non_computed_duration_months = non_computed_duration.months + non_computed_duration.years * 12
                if non_computed_duration_months <= 0:
                    self.expected_addition_days = 0
                    self.expected_balance_leave_start = self.expected_addition_days + self.current_balance
                    return
                computed_duration = relativedelta(last_allocation_date, adjusted_date)
                computed_duration_months = computed_duration.months + computed_duration.years * 12 + computed_duration.days / contract.annual_leave_policy.days_in_month

                computed_leaves = self.env['leave.automatic.allocation'].calc_leaves(first_calc_line, computed_duration_months)
                leaves = self.env['leave.automatic.allocation'].calc_leaves(first_calc_line, duration_months)
                non_computed_leaves = leaves - computed_leaves
                number_dec = str(non_computed_leaves - int(non_computed_leaves))[1:]
                if number_dec >= 0.9:
                    non_computed_leaves = non_computed_leaves  # round(non_computed_leaves, 0)

                self.expected_addition_days = non_computed_leaves

            # ////////////////////////////////////////////////////////////////////
        self.expected_balance_leave_start = self.expected_addition_days + self.current_balance

    @api.one
    @api.depends('employee_id', 'holiday_status_id', 'annual_leave_policy', 'date_from')
    def _compute_show_expected_balance_leave_start(self):
        allocation_show = False
        allocations = self.env['hr.holidays'].search([
            ('type', '=', 'add'),
            ('state', '=', 'validate'),
            ('employee_id', '=', self.employee_id.id),
            ('contract_id', '=', self.contract_id.id),
            ('holiday_status_id', '=', self.holiday_status_id.id),
        ], order='allocation_date desc')
        if allocations:
            last_allocations_date = allocations[0].allocation_date
            if not last_allocations_date or last_allocations_date <= self.date_from:
                allocation_show = True
        else:
            allocation_show = True

        if self.show_recompute_balance and self.remaining_balance < 0 and allocation_show:
            self.show_expected_balance_leave_start = True
        else:
            self.show_expected_balance_leave_start = False

    @api.one
    @api.depends('holiday_status_id', 'annual_leave_policy')
    def _compute_show_recompute_balance(self):
        if not self.holiday_status_id.limit and self.state not in ['refuse', 'validate'] and self.holiday_status_id == self.annual_leave_policy:
            self.show_recompute_balance = True
        else:
            self.show_recompute_balance = False

    @api.one
    def recompute_balance(self):
        pass

    @api.one
    @api.depends()
    def get_similar_leave_requests(self):
        domain = [['employee_id', '=', self.employee_id.id], ['holiday_status_id', '=', self.holiday_status_id.id]]
        if not isinstance(self.id, models.NewId):
            domain.append(['id', '!=', self.id])
        self.old_similar_leave_requests_ids = [l.id for l in self.search(domain)]

    @api.one
    @api.depends()
    def get_old_leave_requests(self):
        domain = [['employee_id', '=', self.employee_id.id], ['create_date', '<=', self.create_date]]
        if not isinstance(self.id, models.NewId):
            domain.append(['id', '!=', self.id])
        self.old_leave_requests_ids = [l.id for l in self.search(domain)]

    @api.multi
    def open_similar_leave_requests(self):
        return {
            'domain': [['id', '=', [l.id for l in self.old_similar_leave_requests_ids]]],
            'name': _('Similar leave requests'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.holidays',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    @api.multi
    def open_old_leave_requests(self):
        return {
            'domain': [['id', '=', [l.id for l in self.old_leave_requests_ids]]],
            'name': _('Old leave requests'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.holidays',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    @api.multi
    def open_exit_rentry_requests(self):
        return {
            'domain': [['leave_request_id', '=', self.id]],
            'name': _('Exit and Re-entry'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.exit.entry.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    @api.multi
    def open_air_ticket_requests(self):
        return {
            'domain': [['leave_request', '=', self.id]],
            'name': _('Air tickets'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'air.ticket.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    @api.multi
    def open_return_from_leave(self):
        return {
            'domain': [['leave_request_id', '=', self.id], ('type', '=', 'Return From Leave')],
            'name': _('Return From Leave'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'effective.notice',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'search_default_return_from_leave': 1, 'default_type': 'Return From Leave', }
        }

    @api.one
    @api.depends('air_ticket_request_ids', 'exit_rentry_request_ids')
    def get_count_smart_buttons(self):
        self.count_air_ticket_requests = len(self.air_ticket_request_ids)
        self.count_exit_rentry_requests = len(self.exit_rentry_request_ids)
        self.count_old_leave_requests = len(self.old_leave_requests_ids)
        self.count_similar_leave_requests = len(self.old_similar_leave_requests_ids)
        self.count_reconciliations = self.env['hr.leave.reconciliation'].search_count([('linked_leave_request_id', '=', self.id)])
        self.count_return_from_leave = self.env['effective.notice'].search_count([('leave_request_id', '=', self.id)])

    @api.one
    @api.depends('date_from', 'date_to')
    def get_date_day(self):
        if self.date_from:
            self.date_from_day = self.get_week_day(self.date_from, 'datetime')
        if self.date_to:
            self.date_to_day = self.get_week_day(self.date_to, 'datetime')
        if self.last_working_day:
            self.last_working_week_day = self.get_week_day(self.last_working_day, 'date')
        if self.expected_working_day:
            self.expected_working_week_day = self.get_week_day(self.expected_working_day, 'date')

    def get_week_day(self, some_date, type):
        week_day = {'Monday': 'Monday / الإثنين', 'Tuesday': 'Tuesday / الثلاثاء', 'Wednesday': 'Wednesday / الأربعاء',
                    'Thursday': 'Thursday / الخميس', 'Friday': 'Friday / الجمعة', 'Saturday': 'Saturday / السبت', 'Sunday': 'Sunday / الأحَد'}
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
        self.iqama_expiry_date = self.iqama_expiry_date_ or self.employee_id.iqama_expiry_date
        self.passport_no = self.passport_no_ or self.employee_id.passport_id
        self.passport_expiry_date = self.passport_expiry_date_ or self.employee_id.passport_expiry_date

    @api.one
    @api.depends('leave_reconciliation_amount', 'paid_amount')
    def get_remaining_amount(self):
        remaining_amount = self.leave_reconciliation_amount - self.paid_amount
        leave_fully_reconciled = False
        if remaining_amount <= 0:
            leave_fully_reconciled = True
        self.remaining_amount = remaining_amount
        self.leave_fully_reconciled = leave_fully_reconciled

    @api.constrains('paid_amount')
    def check_paid_amount(self):
        if self.paid_amount < 0:
            raise ValidationError(_("Paid amount can not be less that zero"))

    @api.one
    def _compute_paid_amount(self):
        self.paid_amount = round(sum(l.amount for l in self.reconciliation_paid_line_ids), 2)

    @api.one
    @api.depends('contract_id', 'number_of_days_temp', 'request_reason', 'reconciliation_based_on', 'holiday_status_id', 'reconciliation_method')
    def get_leave_reconciliation_amount(self):
        based_on_value = 0
        if self.reconciliation_method == 'Stop payslip during leave and use leave reconciliation':
            if self.request_reason == 'annual' and self.contract_id and self.holiday_status_type == 'Annual Leave':
                if self.reconciliation_based_on == 'basic':
                    based_on_value = self.basic_salary
                if self.reconciliation_based_on == 'basic_house':
                    based_on_value = self.basic_salary + self.house_allowance_amount
                if self.reconciliation_based_on == 'basic_house_transportation':
                    based_on_value = self.basic_salary + self.house_allowance_amount + self.transportation_allowance_amount
                if self.reconciliation_based_on == 'basic_house_transportation_phone':
                    based_on_value = self.basic_salary + self.house_allowance_amount + self.transportation_allowance_amount + self.phone_allowance_amount
                if self.reconciliation_based_on == 'total':
                    based_on_value = self.total_salary
            self.leave_reconciliation_amount = round((based_on_value / 30) * (self.number_of_days_temp), 2)
        else:
            self.leave_reconciliation_amount = 0

    @api.one
    @api.constrains('contract_id', 'annual_leave_policy')
    def check_contract_and_annual_leave_policy(self):
        if self.type == 'remove' and (not self.contract_id or not self.annual_leave_policy):
            raise ValidationError(_("Configuration error!\n\
                Your system couldn’t find an active contract or the annual leave policy for the employee which you selected."))

    @api.onchange('holiday_status_id')
    def onchange_leave_type(self):
        reconciliation_based_on = False
        self.mandatory_return_from_leave = self.holiday_status_id.mandatory_return_from_leave
        if self.holiday_status_id and self.holiday_status_id.reconciliation_based_on:
            reconciliation_based_on = self.holiday_status_id.reconciliation_based_on
        self.reconciliation_based_on = reconciliation_based_on
        if self.holiday_status_id.leave_conditions:
            res = {'warning': {
                'title': _('Leave Conditions'),
                'message': self.holiday_status_id.leave_conditions
            }}
            return res

    @api.multi
    def show_leave_conditions(self):
        if self.holiday_status_id.leave_conditions:
            return self.env.user.show_dialogue(self.holiday_status_id.leave_conditions, 'hr.holidays', 'do_nothing', self.id)

    def do_nothing(self):
        pass

    @api.onchange('employee_id', 'holiday_status_id')
    def get_leave_history(self):
        if self.employee_id and self.holiday_status_id and self.type == 'remove':
            history = self.search(
                [['employee_id', '=', self.employee_id.id], ['holiday_status_id', '=', self.holiday_status_id.id], ['type', '=', 'remove']])
            self.holiday_history_ids = [(6, False, [h.id for h in history])]
        else:
            self.holiday_history_ids = [(5,)]

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
        if self.type == 'remove' and self.request_reason == 'non-annual':
            domain += [['type', '=', 'Non Annual Leave'], ['nationality', 'in', ['All Nationalities', self.nationality_type]]]
        return {'domain': {'holiday_status_id': domain}}

    @api.one
    @api.depends('current_balance', 'number_of_days_temp')
    def get_remaining_balance(self):
        self.remaining_balance = self.current_balance - self.number_of_days_temp

    @api.one
    def create_exit_rentry(self):
        vals = {
            'name': 'Exit Entry For %s' % (self.employee_id.name),
            'employee_id': self.employee_id.id,
            'reason': 'leave',
            'leave_request_id': self.id,
            'one_mutli': 'one',
            'state': 'new'
        }
        exit_rentry = self.env['hr.exit.entry.request'].create(vals)
        exit_rentry.onchange_leave_request_id()

    @api.one
    def exit_and_rentry_validation(self):
        exit_rentry = self.env['hr.exit.entry.request'].search([['employee_id', '=', self.employee_id.id], ['state', '=', 'confirmed']],
                                                               order='expected_return_date desc')
        if not exit_rentry:
            self.create_exit_rentry()
        if exit_rentry:
            X = self.date_to
            Y = exit_rentry[0].expected_return_date
            if X > Y:
                self.create_exit_rentry()
            else:
                Z = self.date_from
                M = self.linked_exit_renry_id.expected_return_date
                if Z < M:
                    self.create_exit_rentry()
                else:
                    if exit_rentry[-1].one_mutli == 'one':
                        self.create_exit_rentry()
                    elif exit_rentry[-1].one_mutli == 'multi':
                        return {
                            'domain': "[]",
                            'name': _('Not Allowed'),
                            'view_type': 'form',
                            'view_mode': 'form',
                            'res_model': 'exit.rentry.validation',
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            'context': {
                                'default_leave_request_id': self.id,
                                'default_employee_id': self.employee_id.id,
                                'default_exit_rentry_id': exit_rentry[-1].id,
                                'default_validation_from': 'leave',
                            },
                        }

    def _check_state_access_right(self, cr, uid, vals, context=None):
        return True

    @api.one
    def holidays_first_validate(self):
        if self.type == 'remove':
            self.check_alternative()

        if self.type == 'remove' and self.employee_id.department_manager.user_id.id != self.env.uid and not self.env.user.has_group(
                'saudi_hr_employee.group_leave_bypass_department_manager'):
            raise ValidationError(
                'Not Allowed !! \n You did not have the permission to click on ( Department manager approval  ) for this employee ( %s ), only His / Her Department manager  ( %s ) can click on this button, (or) you must have access to (Leave request Bypass Department manager approval)' % (
                self.employee_id.name, self.employee_id.department_manager.name))

        res = super(hr_holidays, self).holidays_first_validate()
        self.department_approved_by = self.env.uid
        self.department_approved_date = datetime.now().strftime('%Y-%m-%d')
        body = "Document Department Approved"
        self.message_post(body=body, message_type='email')
        return res

    @api.one
    def holidays_validate(self):
        if self.type == 'remove':
            self.check_alternative()
            self.check_leave_days_ids()
            if not self.holiday_status_id.limit and self.expected_remaining_balance < 0 and self.holiday_status_id.type == "Annual Leave":
                if not self.request_leave_in_advance:
                    message = _(
                        "Not allowed, \n Dear HR team, employee ( %s ) Requested for ( %s ) number of requested days is ( %s ) , at leave start date  ( %s ) employee’s balance expected to be ( %s )  his balance is not sufficient to approve this request. In order to accept this leave request, you must select ( Request leave in advance ). Note: if you request for a leave in advance, employee balance will be negative. each month employee balance will be increased automatically.") % (
                              self.employee_id.name, self.holiday_status_id.name, self.number_of_days_temp, self.date_from,
                              self.expected_balance_leave_start)
                    raise ValidationError(message)

            if self.reconciliation_method == 'Stop payslip during leave and use leave reconciliation' and self.holiday_status_id.type == "Annual Leave":
                domain = [
                    ('date_from', '<=', self.date_to),
                    ('date_to', '>=', self.date_from),
                    ('employee_id', '=', self.employee_id.id),
                    ('state', '!=', 'cancel'),
                ]
                conflict_payslips = self.env['hr.payslip'].search(domain)
                if conflict_payslips:
                    message = _(
                        "Data Error !! \n Based on your configuration, the leave reconciliation method for ( %s ) is to Stop payslip during this leave and create leave reconciliation, when we reviewed old payslip for this employee, we found that there is old payslip for the same employee which conflict with this leave request !!! Kindly review your old payslip data. ") % self.holiday_status_id.name
                    raise ValidationError(message)
            if self.holiday_status_id.check_iqama_expiry and self.employee_id.country_id.check_iqama_expiry:
                if not self.iqama_expiry_date:
                    raise ValidationError(_("Data Error!\n\
                        Not allowed to approve this leave request, there is no Iqama / National ID expiry date for the selected employee."))
                elif self.date_to and not self.iqama_expiry_date > self.date_to.split(' ')[0]:
                    raise ValidationError(_("Data Error !!\n\
                        Not allowed to approve this leave request, Employee Iqama / National ID will expire before return from leave, kindly renew employee Iqama\
                        before approving this leave request."))
            if self.holiday_status_id.check_passport_expiry and self.employee_id.country_id.check_passport_expiry:
                if not self.passport_expiry_date:
                    raise ValidationError(_("Data Error!\n\
                        Not allowed to approve this leave request, there is no  passport expiry date for the selected employee."))
                elif not self.passport_expiry_date > self.date_to.split(' ')[0]:
                    raise ValidationError(_("Data Error !!\n\
                        Not allowed to approve this leave request, Employee passport will expire before return from leave, kindly renew employee Iqama before approving\
                    this leave request."))
            if self.last_working_day > self.date_from.split(' ')[0]:
                raise ValidationError(_("Date Error!\n\
                    Last working date must be equal to or less than leave start date!."))
            if self.can_request_exit_rentry == 'yes' or self.nationality_type != 'Native':
                if not self.linked_exit_renry_id:
                    if not self.air_ticket_id:
                        self.exit_and_rentry_validation()
                    else:
                        if self.air_ticket_id.linked_exit_rentry_id:
                            self.linked_exit_renry_id = self.air_ticket_id.linked_exit_rentry_id.id
                        else:
                            self.exit_and_rentry_validation()
            if not self.last_working_day:
                raise ValidationError(_("Please select last working day."))
            if self.original_leave_request_id:
                self.original_leave_request_id.leave_extended = True
                body = "Leave Extended"
                self.original_leave_request_id.message_post(body=body, message_type='email')

            self.current_balance_ = self.employee_id.leaves_count
            # Employee info
            self.iqama_id_ = self.employee_id.identification_id
            self.iqama_expiry_date_ = self.employee_id.iqama_expiry_date
            self.passport_no_ = self.employee_id.passport_id
            self.passport_expiry_date_ = self.employee_id.passport_expiry_date

            old_leave_requests = self.env['hr.holidays'].search(
                [('mandatory_return_from_leave', '=', 'Yes'), ('type', '=', 'remove'), ('state', '=', 'validate'),
                 ('employee_id', '=', self.employee_id.id), ('leave_request_extend_id', '=', False), ('return_from_leave', '=', False),
                 ('date_from', '<', self.date_from)])
            if old_leave_requests and self.mandatory_return_from_leave == 'Yes':
                raise ValidationError(_("Not allowed !!\n\
                    Not allowed to approve this leave for this employee, our records indicated that this employee has old leave request, till now this employee didn’t return from this leave.\n To solve this issue, kindly create a return from a leave for this employee, then you can request for another leave."))

        res = super(hr_holidays, self).holidays_validate()
        self.hr_approved_by = self.env.uid
        self.hr_approved_date = datetime.now().strftime('%Y-%m-%d')
        body = "Document Approved By HR Department"
        self.message_post(body=body, message_type='email')
        return res

    @api.one
    @api.depends('employee_id', 'request_reason', 'contract_id')
    def get_current_balance(self):
        self.current_balance = self.current_balance_ or self.employee_id.leaves_count

    @api.one
    @api.depends('employee_id', 'request_reason', 'contract_id')
    def get_button_extend_invisible(self):
        button_timeout = False
        if self.date_to:
            button_end_date = datetime.strptime(self.date_to, '%Y-%m-%d %H:%M:%S') + timedelta(self.holiday_status_id.leave_extend_timeout)
            button_timeout = datetime.now() > button_end_date

        # self.state != "validate" or
        if button_timeout or self.leave_request_extend_id or self.return_from_leave or self.env.context.get(
                'popup') == True or self.state != 'validate':
            self.button_extend_invisible = True
        else:
            self.button_extend_invisible = False

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
            'res_model': 'hr.holidays',
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

    @api.multi
    def open_reconciles(self):
        return {
            'domain': [('linked_leave_request_id', '=', self.id)],
            'name': _('Leave reconciliations'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.leave.reconciliation',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.v7
    def init(self, cr):
        cr.execute('ALTER TABLE hr_holidays ALTER COLUMN allocation_date DROP NOT NULL')

    _sql_constraints = [
        ('date_check', "CHECK ( 1 == 1 )", "The number of days must be greater than 0."),
    ]

    @api.one
    @api.constrains('employee_id')
    def _check_employee_id(self):
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('active', '=', True)])
        if not len(contracts):
            raise exceptions.ValidationError("This employee has no active contract ,Please create a contract to the selecte d employee")
        if self.type == 'remove':
            old_leaves = self.env['hr.holidays'].search(
                [('type', '=', 'remove'), ('state', 'not in', ['validate', 'refuse']), ('employee_id', '=', self.employee_id.id),
                 ('holiday_status_id', '=', self.holiday_status_id.id), ('id', '!=', self.id)])
            if old_leaves:
                for old_leave in old_leaves:
                    raise ValidationError(_("Not allowed !!\n\
                        Employee ( %s ) is not allowed to request for a leave ( %s ) because he already have another leave request for the same leave type, Old leave request start from ( %s ) and end at ( %s ) leave type is ( %s ) Kindly approve or refuse the old leave requests before requesting for a new one") % (
                    self.employee_id.name, self.holiday_status_id.name, old_leave.date_from, old_leave.date_to, self.holiday_status_id.name))
            # old_leave_requests = self.env['hr.holidays'].search([('type','=','remove'),('state', '=', 'validate'),('employee_id', '=', self.employee_id.id),('leave_extended', '=', False),('return_from_leave', '=', False),('id', '!=', self.id)])
            # if old_leave_requests:
            #     for old_leave_request in old_leave_requests:
            #         raise ValidationError(_("Not allowed !!\n Employee ( %s ) is not allowed to request for a new leave, because he did not create a return from a leave for the old leave ( %s ) this leave starts from ( %s ) and ends on ( %s ) ") %(self.employee_id.name,old_leave_request.name,old_leave_request.date_from,old_leave_request.date_to))

    @api.one
    @api.depends('employee_id')
    def _compute_contract(self):
        for rec in self:
            contracts = self.env['hr.contract'].search([('employee_id', '=', rec.employee_id.id), ('active', '=', True)])
            if len(contracts):
                rec.contract_id = contracts[0].id

    @api.one
    @api.constrains('holiday_type')
    def _check_holiday_type(self):
        if self.holiday_type == 'category':
            raise exceptions.ValidationError("Couldn’t save, allocation based on employee tag still under development")

    @api.one
    @api.constrains('number_of_days_temp')
    def _check_number_of_days_temp(self):
        if self.number_of_days_temp <= 0 and self.type == 'remove':
            raise ValidationError(_("Not allowed \n Number of days requested can not be Zero or negative value."))
        if self.number_of_days_temp < 0 and not self.allow_minus_value:
            raise exceptions.ValidationError(
                "The number of days must be greater than 0. To allow minus values, you must click on allow minus quantities field.")
        if self.number_of_days_temp > self.holiday_status_id.days_per_leave and self.type == 'remove':
            raise exceptions.ValidationError(
                _("Not Allowed. Number of days requested ( %s ) is greater than the Maximum days per each leave request  (%s)") % (
                self.number_of_days_temp, self.holiday_status_id.days_per_leave))
        if self.type == 'remove':
            if self.holiday_status_id == self.annual_leave_policy:
                if not self.contract_id.working_calendar:
                    raise exceptions.ValidationError(
                        "Data Error In order to calculate Number Of Days Requested, you have to select leave calculation method ( working / Calendar ) in employee contract.")
                if self.contract_id.working_calendar == 'Working Days':
                    if not self.contract_id.attendance_ids:
                        raise exceptions.ValidationError(
                            "Data Error !! Dear HR manager, your system is trying to calculate number of leave days, it seems that you configured your system to deduct working days, when your system reviewed employee contract ( %s ) we found that you forget to select the working schedule for this employee, kindly review working days ( Contracts >> Other >> working schedule)." % self.employee_id.name)
            else:
                if not self.holiday_status_id.working_calendar:
                    raise exceptions.ValidationError(
                        "Data Error In order to calculate Number Of Days Requested, you have to select leave calculation method ( working / Calendar ) in Leave Types window.")

    @api.one
    @api.constrains('contract_id')
    def _check_contract_id(self):
        if self.type == 'remove' and not self.contract_id.adjusted_date:
            raise exceptions.ValidationError("Can’t save this allocation request because we couldn’t calculate adjusted date for employee contract.")

    @api.one
    @api.constrains('holiday_status_id')
    def _check_holiday_status_id(self):
        if self.type == 'remove':
            if not self.contract_id.end_trial_period_approved and not self.holiday_status_id.request_during_trial:
                raise exceptions.ValidationError(
                    "Not allowed \n Employee ( %s ) is not allowed to request for ( %s ) Based on your company policy, employees are not allowed to request for this kind of leave until (End of trial period process), If you sure that this employee already passed Trial period duration,  kindly request from HR department to ( Approve End of trial period process) for your contract. you still have the option to select another leave type." % (
                    self.employee_id.name, self.holiday_status_id.name))
        if self.holiday_status_id.type == "Annual Leave" and self.holiday_status_id != self.annual_leave_policy:
            raise exceptions.ValidationError(
                "Not allowed to assign this annual leave to this employee. Please review the annual leave policy at employee contract.")
        if self.number_of_days_temp > self.holiday_status_id.days_per_leave and self.type == 'remove':
            raise exceptions.ValidationError(
                _("Not Allowed. Number of days requested ( %s ) is greater than the Maximum days per each leave request  (%s)") % (
                self.number_of_days_temp, self.holiday_status_id.days_per_leave))
        if self.holiday_status_id.type == 'Non Annual Leave' and self.type == 'remove':
            if self.holiday_status_id.limit:
                if self.holiday_status_id.days_per_leave <= 0:
                    raise exceptions.ValidationError(
                        "Configuration Error! \n For Employee ( %s ) Based on system configuration … Maximum days allowed for ( %s ) is ( %s ) , Kindly Review configuration for this Leave type." % (
                        self.employee_id.name, self.holiday_status_id.name, self.holiday_status_id.days_per_leave))
                else:
                    if self.number_of_days_temp > self.holiday_status_id.days_per_leave:
                        raise exceptions.ValidationError(
                            "Not Allowed !! \n Maximum days allowed for ( %s ) is ( %s ) , so you are not allowed to request for ( %s )" % (
                            self.holiday_status_id.name, self.holiday_status_id.days_per_leave, self.number_of_days_temp))
            if not self.employee_id.gender:
                raise exceptions.ValidationError("Data Error !! Kindly select employee gender in employee file.")
            else:
                if self.employee_id.gender == 'female' and self.holiday_status_id.who_request == 'Male only':
                    raise exceptions.ValidationError(
                        "Not Allowed !! This Leave is allowed for males only. based on data found in employee file, this employee is a female.")
                if self.employee_id.gender == 'male' and self.holiday_status_id.who_request == 'Females only':
                    raise exceptions.ValidationError(
                        "Not Allowed !! This Leave is allowed for Females only. based on data found in employee file, this employee is a male.")

            if not self.contract_id.marital:
                raise exceptions.ValidationError(
                    "Data Error !! Kindly review last active contract for this employee, you have to select data in ( Single / Married ) field in employee contract.")
            else:
                if self.contract_id.marital == 'married' and self.holiday_status_id.marital_status == 'Single':
                    raise exceptions.ValidationError(
                        "Not Allowed !! \n For employee ( %s ) This Leave is allowed for singles only. based on data found in employee file, this employee is married." % self.employee_id.name)
                if self.contract_id.marital == 'single' and self.holiday_status_id.marital_status == 'Married':
                    raise exceptions.ValidationError(
                        "Not Allowed !! This Leave is allowed for married only. based on data found in employee file, this employee is a single.")

            if not self.employee_id.religion:
                raise exceptions.ValidationError("Data Error !! Kindly select employee religion in employee file.")
            else:
                if self.employee_id.religion == 'Non-Muslim' and self.holiday_status_id.religion == 'Muslim':
                    raise exceptions.ValidationError(
                        "Not Allowed !! This Leave is allowed for Muslims only. based on data found in employee file, this employee is not a Muslim")
                if self.employee_id.religion == 'Muslim' and self.holiday_status_id.religion == 'Non-Muslim':
                    raise exceptions.ValidationError(
                        "Not Allowed !! This Leave is allowed for Non-Muslims only. based on data found in employee file, this employee is a Muslim.")

            if not self.employee_id.nationality_type:
                raise exceptions.ValidationError("Data Error !! Kindly select employee Nationality in employee file.")
            else:
                if self.employee_id.nationality_type == 'Non-native' and self.holiday_status_id.nationality == 'Native':
                    raise exceptions.ValidationError(
                        "This Leave is allowed for Natives only. based on data found in employee file, this employee is not a Native.")
                if self.employee_id.nationality_type == 'Native' and self.holiday_status_id.nationality == 'Non-native':
                    raise exceptions.ValidationError(
                        "Not Allowed !! This Leave is allowed for Non-Natives only. based on data found in employee file, this employee is a Native.")

    @api.multi
    def check_adjust_day(self):
        for record in self:
            if record.type == 'remove' and record.report_employee_is_manager and not self.env.user.has_group(
                    'saudi_hr_employee.group_leave_hr_approval_for_managers'):
                raise ValidationError(
                    'Not Allowed !! \n You did not have the permission to approve leave request for Department managers or branch managers, only HR manager or users who have access rights = (Leave request HR approval for managers) are allowed to click on this button.')

            if record.type == 'add' and record.holiday_status_id.type == "Annual Leave" and record.holiday_status_id.allocation_technique != 'Each Financial Month':
                adjusted_date = datetime.strptime(record.contract_id.adjusted_date, "%Y-%m-%d")
                allocation_date = datetime.strptime(record.allocation_date, "%Y-%m-%d")

                if adjusted_date.day >= 28 and allocation_date.day >= 28:
                    pass
                elif adjusted_date.day != allocation_date.day and not self.by_eos:
                    raise exceptions.ValidationError(
                        "Attention!! \n For employee ( %s )We found that you configured your system give the employee a monthly annual leave balance at a certain day from each month\
                        , now you are trying to allocate leaves on a different day. We highly recommend to use a monthly base (except the termination cases or \
                        EOC cases)" % record.employee_id.name)

    @api.multi
    def set_approved_by(self):
        for record in self:
            record.approved_by = self.env.uid

    # @api.v7
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

    # @api.v7
    def _get_number_of_days(self, date_from, date_to):
        DATE_FORMAT = "%Y-%m-%d"
        from_dt = datetime.strptime(date_from.split(' ')[0], DATE_FORMAT)
        to_dt = datetime.strptime(date_to.split(' ')[0], DATE_FORMAT)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days  # + float(timedelta.seconds) / 86400
        return diff_day

    def daterange(self, start_date, end_date):
        for n in range(int((end_date - start_date).days + 1)):
            yield start_date + timedelta(n)

    def check_day_not_on_holiday(self, leave_date):
        day_not_on_holiday = 1
        national_holidays = self.env['hr.national.holiday'].search([('duration_in_leave_request', '=', 'No'), ('state', '=', 'Confirmed')])
        for holiday in national_holidays:
            if leave_date.strftime("%Y-%m-%d") >= holiday.start_date and leave_date.strftime("%Y-%m-%d") <= holiday.end_date:
                if not holiday.branches or self.employee_id.branch_id.id in holiday.branches.ids:
                    day_not_on_holiday = 0
        return day_not_on_holiday

    def check_day_on_working_days(self, leave_date):
        week_day = leave_date.weekday()
        day_on_working_days = 0
        if self.contract_id and self.contract_id.attendance_ids:
            for attendance_id in self.contract_id.attendance_ids:
                if week_day == int(attendance_id.dayofweek):
                    day_on_working_days = 1
        return day_on_working_days

    @api.one
    @api.onchange('date_to', 'date_from', 'request_reason', 'holiday_status_id')
    def onchange_period_custom(self):
        date_from = self.date_from
        date_to = self.date_to

        # Compute and update the number of days
        if date_to and date_from:
            # ///////// Check if working days or calendar days
            if self.holiday_status_id == self.annual_leave_policy:
                working_calendar = self.contract_id.working_calendar
            else:
                working_calendar = self.holiday_status_id.working_calendar
            if working_calendar == 'Working Days':
                if self.contract_id.attendance_ids:
                    date_from_date = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S")
                    date_to_date = datetime.strptime(date_to, "%Y-%m-%d %H:%M:%S")
                    working_days = 0
                    for leave_date in self.daterange(date_from_date, date_to_date):
                        if self.check_day_on_working_days(leave_date):
                            if self.check_day_not_on_holiday(leave_date):
                                working_days += 1
                    self.number_of_days_temp = working_days

            if working_calendar == 'Calendar days':
                national_holidays = self.env['hr.national.holiday'].search([('duration_in_leave_request', '=', 'No'), ('state', '=', 'Confirmed')])
                total_conflict_days = 0
                for holiday in national_holidays:
                    if holiday.end_date < date_from.split(' ')[0] or holiday.start_date > date_to.split(' ')[0]:
                        continue
                    else:
                        if holiday.start_date > date_from:
                            conflict_start = holiday.start_date
                        else:
                            conflict_start = date_from

                        if holiday.end_date < date_to:
                            conflict_end = holiday.end_date
                        else:
                            conflict_end = date_to
                        if not holiday.branches or self.employee_id.branch_id.id in holiday.branches.ids:
                            conflict_days = self._get_number_of_days(conflict_start, conflict_end) + 1
                            total_conflict_days += conflict_days
                diff_day = self._get_number_of_days(date_from, date_to)
                self.number_of_days_temp = round(math.floor(diff_day)) + 1 - total_conflict_days
        else:
            self.number_of_days_temp = 0

    @api.model
    def get_user_tz(self):
        tz = self.env.user.tz
        return

    def holidays_refuse(self, cr, uid, ids, context=None):
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        for holiday in self.browse(cr, uid, ids, context=context):
            if holiday.return_from_leave:
                raise exceptions.ValidationError(
                    "Not Allowed !! Not allowed to refuse / cancel this leave Request because there is a return from leave already linked with this leave request. If you have any special cases which requires to cancel this approved leave request, you can create a new leave allocation to increase employee balance.")
            if holiday.state == 'validate1':
                self.write(cr, uid, [holiday.id], {'state': 'refuse', 'manager_id': manager})
            else:
                self.write(cr, uid, [holiday.id], {'state': 'refuse', 'manager_id2': manager})
            if holiday.original_leave_request_id:
                holiday.original_leave_request_id.leave_extended = False
                holiday.original_leave_request_id.leave_request_extend_id = ''
            if holiday.leave_request_extend_id:
                raise exceptions.ValidationError(
                    "Not Allowed, There is a leave request to extend this leave, you must refuse or delete the leave request extension before refusing this leave.")
        self.holidays_cancel(cr, uid, ids, context=context)
        return True

    @api.model
    def create(self, vals):
        self.check_past_future()
        res = super(hr_holidays, self).create(vals)
        if res.original_leave_request_id:
            res.original_leave_request_id.leave_request_extend_id = res
        if self.env.context.get('return_from_leave', False):
            return_from_leave_id = self.env.context.get('return_from_leave', False)
            return_from_leave = self.env['effective.notice'].search([('id', '=', return_from_leave_id)])
            return_from_leave.hr_department_approval()
        if res.type == 'remove' and not res.employee_id.parent_id and not res.employee_id.department_manager:
            res.signal_workflow('confirm')
        self.sudo().employee_id.refresh_non_annual()
        res._compute_report_holiday_na_balance()
        return res

    @api.one
    def unlink(self):
        if not self._context.get('force_delete', False):
            if self.original_leave_request_id or self.leave_request_extend_id or self.leave_extended:
                raise ValidationError(_("Not allowed to delete this leave request because there is leave extension already linked with this leave."))
            if self.type == 'remove' and self.system_created:
                raise ValidationError(_(
                    "Not allowed!! \n Not allowed to delete a record which is automatically created by the system, try to refuse or set to new.  Or create another leave allocation with a negative / Positive sign to reverse this allocation."))
            if self.state not in ['draft', 'cancel', 'confirm']:
                raise UserError(_('You cannot delete a leave which is in %s state.') % (self.state,))
        employee = self.employee_id
        res = super(hr_holidays_original, self).unlink()
        employee.sudo().refresh_non_annual()
        return res

    @api.one
    @api.depends('employee_id', 'date_from')
    def compute_last_working_day(self):
        if self.date_from and self.employee_id:
            start_date = datetime.strptime(self.date_from, "%Y-%m-%d %H:%M:%S")
            start_date_yesterday = start_date - timedelta(days=1)
            self.last_working_day = self.get_last_working_date(start_date_yesterday, self.employee_id)

    def get_last_working_date(self, checked_date, employee_id):
        # //////////////  Check For Old Leave Request /////////////////////////////////////////////
        old_leave_requests = self.env['hr.holidays'].search(
            [('state', '!=', 'refuse'), ('employee_id', '=', employee_id.id), ('date_from', '<=', checked_date.strftime('%Y-%m-%d %H:%M:%S')),
             ('date_to', '>=', checked_date.strftime('%Y-%m-%d %H:%M:%S'))])
        if old_leave_requests:
            for old_leave_request in old_leave_requests:
                leave_start_date = datetime.strptime(old_leave_request.date_from, "%Y-%m-%d %H:%M:%S")
                leave_start_date_yesterday = leave_start_date - timedelta(days=1)
                return self.get_last_working_date(leave_start_date_yesterday, employee_id)

        # //////////////  Check For Old National Holidays /////////////////////////////////////////////
        old_national_holidays = self.env['hr.national.holiday'].search(
            [('start_date', '<=', checked_date.strftime('%Y-%m-%d')), ('end_date', '>=', checked_date.strftime('%Y-%m-%d'))])
        employee_old_national_holidays = []
        for old_national_holiday in old_national_holidays:
            if not old_national_holiday.branches or self.employee_id.branch_id.id in old_national_holiday.branches.ids:
                employee_old_national_holidays.append(old_national_holiday)

        if employee_old_national_holidays:
            for employee_old_national_holiday in employee_old_national_holidays:
                n_holiday_start_date = datetime.strptime(employee_old_national_holiday.start_date, "%Y-%m-%d")
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
        if self.date_to and self.employee_id:
            end_date = datetime.strptime(self.date_to, "%Y-%m-%d %H:%M:%S")
            end_date_tomorrow = end_date + timedelta(days=1)
            self.expected_working_day = self.get_expected_working_day(end_date_tomorrow, self.employee_id)

    def get_expected_working_day(self, checked_date, employee_id):
        # //////////////  Check For Old Leave Request /////////////////////////////////////////////
        old_leave_requests = self.env['hr.holidays'].search(
            [('state', '!=', 'refuse'), ('employee_id', '=', employee_id.id), ('date_from', '<=', checked_date.strftime('%Y-%m-%d %H:%M:%S')),
             ('date_to', '>=', checked_date.strftime('%Y-%m-%d %H:%M:%S'))])
        if old_leave_requests:
            for old_leave_request in old_leave_requests:
                leave_end_date = datetime.strptime(old_leave_request.date_to, "%Y-%m-%d %H:%M:%S")
                leave_end_date_tomorrow = leave_end_date + timedelta(days=1)
                return self.get_expected_working_day(leave_end_date_tomorrow, employee_id)

        # //////////////  Check For Old National Holidays /////////////////////////////////////////////
        old_national_holidays = self.env['hr.national.holiday'].search(
            [('start_date', '<=', checked_date.strftime('%Y-%m-%d')), ('end_date', '>=', checked_date.strftime('%Y-%m-%d'))])
        employee_old_national_holidays = []
        for old_national_holiday in old_national_holidays:
            if not old_national_holiday.branches or self.employee_id.branch_id.id in old_national_holiday.branches.ids:
                employee_old_national_holidays.append(old_national_holiday)

        if employee_old_national_holidays:
            for employee_old_national_holiday in employee_old_national_holidays:
                n_holiday_end_date = datetime.strptime(employee_old_national_holiday.end_date, "%Y-%m-%d")
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

    def onchange_type(self, cr, uid, ids, holiday_type, employee_id=False, context=None):
        return


class LeaveReconciliationPaidLine(models.Model):
    _name = "leave.reconciliation.paid.line"

    request_id = fields.Many2one('hr.holidays', 'Leave Request')
    date = fields.Date('Date')
    amount = fields.Float('Amount')
    reconciliation_id = fields.Many2one('hr.leave.reconciliation', 'Leave Reconciliation')
    eos = fields.Many2one('employee_eos', 'EOS')
    note = fields.Char('Notes')


class ExitRentryValidateion(models.TransientModel):
    _name = "exit.rentry.validation"

    validation_from = fields.Selection([
        ('leave', 'Leave'),
        ('air_ticket', 'Air ticket'),
        ('exit_rentry', 'Exit Re-entry'),
    ])
    leave_request_id = fields.Many2one('hr.holidays', 'Leave request')
    exit_rentry_id = fields.Many2one('hr.exit.entry.request', 'Exit Re-entry')
    employee_id = fields.Many2one('hr.employee', 'Employee')

    air_ticket_id = fields.Many2one('air.ticket.request', 'Air ticket request')

    @api.one
    def create_exit_rentry(self):
        if self.validation_from == 'leave':
            self.leave_request_id.create_exit_rentry()
        if self.validation_from == 'air_ticket':
            self.air_ticket_id.create_exit_rentry()
        if self.validation_from == 'exit_rentry':
            ctx = dict(self._context.copy(), exit_rentry_validation=True)
            self.with_context(ctx).exit_rentry_id.confirm()


class leave_automatic_allocation(models.Model):
    _name = "leave.automatic.allocation"
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(_('Code'), readonly=True)
    allocate_till_date = fields.Date(string="Allocate Till This Date", required=True)
    confirm_uid = fields.Many2one('res.users', string="Confirmed By", readonly=True)
    notes = fields.Text(string="Notes")
    allocation_number = fields.Integer(string="Number Of Leaves Allocation")
    allocation_ids = fields.One2many('hr.holidays', 'leave_automatic_allocation', 'Leave Allocations')
    count_allocations = fields.Integer('Number of allocations', compute='get_count_allocations')
    state = fields.Selection([
        ('New', 'New'),
        ('Confirmed', 'Confirmed'),
    ], string='Status', readonly=True, select=True, default='New', )
    leave_type = fields.Selection([
        ('Annual Leaves Only', 'Annual Leaves Only'),
        ('Non-annual Leaves Only', 'Non-annual Leaves Only'),
        ('All Leaves', 'All Leaves'),
    ], string='Annual / Non-annual')
    by_branch = fields.Boolean('Leave allocation by branch')
    branch_ids = fields.Many2many('hr.branch', 'automatic_branch_rel', 'auto', 'bran', 'Branches')
    by_employee = fields.Boolean('Leave allocation by employees')
    employee_ids = fields.Many2many('hr.employee', 'automatic_employee_rel', 'auto', 'emp', 'Employees')

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
            'res_model': 'hr.holidays',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'tree_view_ref': 'hr_holidays.view_holiday_allocation_tree', 'form_view_ref': 'hr_holidays.edit_holiday_new'},
        }

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].sudo().next_by_code('Leave.automatic.allocation')
        res = super(leave_automatic_allocation, self).create(vals)
        return res

    def get_duration_months(self, start_date, end_date, days_in_month=30):
        periods_by_month = self.env['hr.holidays'].devide_period_by_month(start_date, end_date)
        if len(periods_by_month) == 1:
            number_of_days = self.env['hr.holidays'].get_month_days(periods_by_month[0]['from'], periods_by_month[0]['to'])
            return number_of_days / float(days_in_month)
        elif len(periods_by_month) > 1:
            return self.env['hr.holidays'].get_month_days(periods_by_month[0]['from'], periods_by_month[0]['to']) / float(days_in_month) + self.env[
                'hr.holidays'].get_month_days(periods_by_month[-1]['from'], periods_by_month[-1]['to']) / float(days_in_month) + (
                               len(periods_by_month) - 2)
        else:
            return 0

    @api.multi
    def action_confirm(self):
        for record in self:
            if record.leave_type in ['Annual Leaves Only', 'All Leaves']:
                if record.by_branch and not record.branch_ids:
                    raise ValidationError('Data error !!  \n Kindly select branches')
                if record.by_employee and not record.employee_ids:
                    raise ValidationError('Data error !!  \n Kindly select Employees')
                domain = []
                if record.by_branch and not record.by_employee:
                    domain = [('branch_id', 'in', record.branch_ids.ids)]
                if record.by_employee and not record.by_branch:
                    domain = [('id', 'in', record.employee_ids.ids)]
                if record.by_branch and record.by_employee:
                    domain = ['|', ('branch_id', 'in', record.branch_ids.ids), ('id', 'in', record.employee_ids.ids)]
                employees = self.env['hr.employee'].search(domain)
                for employee in employees:
                    contracts = self.env['hr.contract'].search([('employee_id', '=', employee.id), ('active', '=', True)])
                    if len(contracts):
                        contract = contracts[0]
                    else:
                        continue
                    if contract.annual_leave_policy.allocate_after_trial and not contract.end_trial_period_approved:
                        continue

                    allocate_till_date = datetime.strptime(record.allocate_till_date, "%Y-%m-%d")
                    start_after_months = contract.annual_leave_policy.start_allocation_after
                    adjusted_date = datetime.strptime(contract.adjusted_date, "%Y-%m-%d")
                    start_after_date = adjusted_date + relativedelta(months=start_after_months)
                    # compute allocation Monthly
                    if contract.annual_leave_policy.allocation_period == 'Monthly':
                        # compute allocation Each Contractual Month
                        if contract.annual_leave_policy.allocation_technique == 'Each Contractual Month':
                            if contract.adjusted_date >= record.allocate_till_date:
                                continue
                            if allocate_till_date < start_after_date:
                                continue
                            adjusted_date_day = adjusted_date.day
                            allocate_till_date_day = allocate_till_date.day
                            effictive_allocate_date = allocate_till_date
                            if adjusted_date_day > 28:
                                adjusted_date_day = 28
                                new_adjusted_date = adjusted_date.replace(day=28)
                                body = "adjusted date changed by automatic leave allocation from ( %s ) to ( %s )" % (
                                adjusted_date, new_adjusted_date)
                                contract.adjusted_date = adjusted_date.replace(day=28)
                                contract.message_post(body=body, message_type='email')
                            if adjusted_date_day > allocate_till_date_day:
                                effictive_allocate_date = allocate_till_date.replace(day=adjusted_date_day)
                                effictive_allocate_date = effictive_allocate_date - relativedelta(months=1)
                            elif adjusted_date_day < allocate_till_date_day:
                                effictive_allocate_date = allocate_till_date.replace(day=adjusted_date_day)
                            duration_months = self.get_duration_months(adjusted_date.strftime("%Y-%m-%d %H:%M:%S"),
                                                                       effictive_allocate_date.strftime("%Y-%m-%d %H:%M:%S"),
                                                                       contract.annual_leave_policy.days_in_month)
                            if duration_months == 0 or duration_months < start_after_months:
                                continue

                        # compute allocation Each Financial Month
                        if contract.annual_leave_policy.allocation_technique == 'Each Financial Month':
                            # get the last day in month
                            start_end = calendar.monthrange(int(allocate_till_date.strftime('%Y')), int(allocate_till_date.strftime("%m")))  # New
                            actual_allocate_till_date = str(allocate_till_date.strftime('%Y')) + '-' + str(
                                allocate_till_date.strftime("%m")) + '-' + str(start_end[1])  # New

                            if contract.adjusted_date >= actual_allocate_till_date:
                                continue
                            if actual_allocate_till_date < start_after_date.strftime('%Y-%m-%d'):
                                continue
                            effictive_allocate_date = datetime.strptime(actual_allocate_till_date, "%Y-%m-%d")
                            duration_months = self.get_duration_months(adjusted_date.strftime("%Y-%m-%d %H:%M:%S"),
                                                                       effictive_allocate_date.strftime("%Y-%m-%d %H:%M:%S"),
                                                                       contract.annual_leave_policy.days_in_month)

                    # compute allocation yearly
                    if contract.annual_leave_policy.allocation_period == 'Yearly':
                        # compute allocation Each Financial Month
                        if contract.annual_leave_policy.allocation_technique == 'Each Contractual Month':
                            if contract.adjusted_date >= record.allocate_till_date:
                                continue
                            if allocate_till_date < start_after_date:
                                continue
                            adjusted_date_day = adjusted_date.day
                            allocate_till_date_day = allocate_till_date.day
                            if adjusted_date_day > 28:
                                adjusted_date_day = 28
                                new_adjusted_date = adjusted_date.replace(day=28)
                                body = "adjusted date changed by automatic leave allocation from ( %s ) to ( %s )" % (
                                adjusted_date, new_adjusted_date)
                                contract.adjusted_date = adjusted_date.replace(day=28)
                                contract.message_post(body=body, message_type='email')

                            effictive_allocate_date = allocate_till_date.replace(day=adjusted_date.day, month=adjusted_date.month)
                            if effictive_allocate_date <= allocate_till_date:
                                effictive_allocate_date = effictive_allocate_date + relativedelta(years=1)

                            duration_months = self.get_duration_months(adjusted_date.strftime("%Y-%m-%d %H:%M:%S"),
                                                                       effictive_allocate_date.strftime("%Y-%m-%d %H:%M:%S"),
                                                                       contract.annual_leave_policy.days_in_month)
                            if duration_months == 0 or duration_months < start_after_months:
                                continue

                        # compute allocation Each Financial Month
                        if contract.annual_leave_policy.allocation_technique == 'Each Financial Month':
                            # get the last day in year
                            actual_allocate_till_date = str(allocate_till_date.strftime('%Y')) + '-12-31'

                            if contract.adjusted_date >= actual_allocate_till_date:
                                continue
                            if actual_allocate_till_date < start_after_date.strftime('%Y-%m-%d'):
                                continue
                            effictive_allocate_date = datetime.strptime(actual_allocate_till_date, "%Y-%m-%d")
                            duration_months = self.get_duration_months(adjusted_date.strftime("%Y-%m-%d %H:%M:%S"),
                                                                       effictive_allocate_date.strftime("%Y-%m-%d %H:%M:%S"),
                                                                       contract.annual_leave_policy.days_in_month)

                    alloctions = self.env['hr.holidays'].search(
                        [('employee_id', '=', contract.employee_id.id), ('holiday_status_id', '=', contract.annual_leave_policy.id),
                         ('state', '!=', 'refuse'), ('type', '=', 'add')])
                    first_calc_line = self.env['leaves.calc.method.line'].search(
                        [('greater_than', '=', 0), ('leave_type_id', '=', contract.annual_leave_policy.id)])
                    if not first_calc_line:
                        raise exceptions.ValidationError(
                            "Out of range!! Cannot calculate automatic leave Please review your leave type’s configuration. for contract (%s)" % contract.name)
                    if not len(alloctions):
                        leaves = self.calc_leaves(first_calc_line, duration_months)
                        number_dec = str(leaves - int(leaves))[1:]
                        if float(number_dec) >= 0.9:
                            leaves = round(leaves, 0)

                        leave_allocation_data = {
                            'name': 'Automatic Leave Allocation',
                            'type': 'add',
                            'holiday_status_id': contract.annual_leave_policy.id,
                            'number_of_days_temp': leaves,
                            'holiday_type': 'employee',
                            'employee_id': contract.employee_id.id,
                            'department_id': contract.employee_id.job_id.department_id.id,
                            'allocation_date': effictive_allocate_date,
                            'system_created': True,
                            'leave_automatic_allocation': record.id
                        }
                        leave_allocation = self.env['hr.holidays'].create(leave_allocation_data)
                        leave_allocation.signal_workflow('validate')
                        if leave_allocation.double_validation:
                            leave_allocation.signal_workflow('second_validate')
                    if len(alloctions):
                        last_allocation = self.env['hr.holidays'].search(
                            [('employee_id', '=', contract.employee_id.id), ('holiday_status_id', '=', contract.annual_leave_policy.id),
                             ('state', '!=', 'refuse'), ('type', '=', 'add')],
                            order="allocation_date desc", limit=1)
                        if last_allocation and last_allocation.allocation_date:
                            last_allocation_date = datetime.strptime(last_allocation.allocation_date, "%Y-%m-%d")
                            if effictive_allocate_date <= last_allocation_date:
                                continue
                        else:
                            continue
                        non_computed_duration = relativedelta(effictive_allocate_date, last_allocation_date)
                        non_computed_duration_months = non_computed_duration.months + non_computed_duration.years * 12
                        if contract.annual_leave_policy.allocation_technique == 'Each Financial Month':
                            non_computed_duration_months += non_computed_duration.days / float(contract.annual_leave_policy.days_in_month)
                        if non_computed_duration_months <= 0:
                            continue
                        computed_duration_months = self.get_duration_months(adjusted_date.strftime("%Y-%m-%d %H:%M:%S"),
                                                                            last_allocation_date.strftime("%Y-%m-%d %H:%M:%S"),
                                                                            contract.annual_leave_policy.days_in_month)

                        computed_leaves = self.calc_leaves(first_calc_line, computed_duration_months)
                        leaves = self.calc_leaves(first_calc_line, duration_months)
                        non_computed_leaves = leaves - computed_leaves
                        number_dec = str(non_computed_leaves - int(non_computed_leaves))[1:]
                        if number_dec >= 0.9:
                            non_computed_leaves = non_computed_leaves  # round(non_computed_leaves, 0)

                        leave_allocation_data = {
                            'name': 'Automatic Leave Allocation',
                            'type': 'add',
                            'holiday_status_id': contract.annual_leave_policy.id,
                            'number_of_days_temp': non_computed_leaves,
                            'holiday_type': 'employee',
                            'employee_id': contract.employee_id.id,
                            'department_id': contract.employee_id.job_id.department_id.id,
                            'allocation_date': effictive_allocate_date,
                            'system_created': True,
                            'leave_automatic_allocation': record.id
                        }
                        leave_allocation = self.env['hr.holidays'].create(leave_allocation_data)
                        leave_allocation.signal_workflow('validate')
                        if leave_allocation.double_validation:
                            leave_allocation.signal_workflow('second_validate')
                        leave_allocation.check_adjust_day()
                        leave_allocation.holidays_validate()
                        leave_allocation.set_approved_by()

            if record.leave_type in ['Non-annual Leaves Only', 'All Leaves']:
                refresh_employee_ids = []
                if record.by_branch and not record.branch_ids:
                    raise ValidationError('Data error !!  \n Kindly select branches')
                if record.by_employee and not record.employee_ids:
                    raise ValidationError('Data error !!  \n Kindly select Employees')
                domain = []
                if record.by_branch and not record.by_employee:
                    domain = [('branch_id', 'in', record.branch_ids.ids)]
                if record.by_employee and not record.by_branch:
                    domain = [('id', 'in', record.employee_ids.ids)]
                if record.by_branch and record.by_employee:
                    domain = ['|', ('branch_id', 'in', record.branch_ids.ids), ('id', 'in', record.employee_ids.ids)]
                employees = self.env['hr.employee'].search(domain)
                for employee in employees:
                    contracts = self.env['hr.contract'].search([('employee_id', '=', employee.id), ('active', '=', True)])
                    if len(contracts):
                        contract = contracts[0]
                    else:
                        continue
                    if not contract.adjusted_date:
                        raise ValidationError(
                            _("Can not find adjusted date for contract (%s) for employee (%s)" % (contract.name, contract.employee_id.name)))
                    if contract.adjusted_date > record.allocate_till_date:
                        continue
                    employee.refresh_non_annual()
                    for leave_balance in employee.non_annual_leave_balance:
                        if leave_balance.holidays_status_id.allocate_after_trial and not contract.end_trial_period_approved:
                            continue
                        create_allocation = 0
                        number_of_days = 0
                        allow_minus_value = 0

                        if leave_balance.non_annual_frequency == 'contract':
                            allocations = self.env['hr.holidays'].search([
                                ('type', '=', 'add'),
                                ('state', '!=', 'refuse'),
                                ('employee_id', '=', employee.id),
                                ('contract_id', '=', contract.id),
                                ('holiday_status_id', '=', leave_balance.holidays_status_id.id),
                            ])
                            if not len(allocations):
                                create_allocation = 1
                                number_of_days = leave_balance.holidays_status_id.number_of_days
                        if leave_balance.non_annual_frequency == 'financial_year':
                            allocate_till_date = datetime.strptime(record.allocate_till_date, "%Y-%m-%d")
                            year_start = date(allocate_till_date.year, 1, 1)
                            year_end = date(allocate_till_date.year, 12, 31)
                            allocations = self.env['hr.holidays'].search([
                                ('type', '=', 'add'),
                                ('state', '!=', 'refuse'),
                                ('employee_id', '=', employee.id),
                                ('holiday_status_id', '=', leave_balance.holidays_status_id.id),
                                ('allocation_date', '>=', year_start.strftime('%Y-%m-%d')),
                                ('allocation_date', '<=', year_end.strftime('%Y-%m-%d'))
                            ])
                            if not len(allocations) and leave_balance.holidays_status_id.number_of_days > leave_balance.net_balance:
                                create_allocation = 1
                                number_of_days = leave_balance.holidays_status_id.number_of_days - leave_balance.net_balance
                                if number_of_days < 0:
                                    allow_minus_value = 1

                        if leave_balance.non_annual_frequency == 'contractual_year':
                            adjusted_date = datetime.strptime(contract.adjusted_date, "%Y-%m-%d")
                            allocate_till_date = datetime.strptime(record.allocate_till_date, "%Y-%m-%d")
                            check_date = date(allocate_till_date.year, adjusted_date.month, adjusted_date.day)
                            if allocate_till_date.strftime('%Y-%m-%d') < check_date.strftime('%Y-%m-%d'):
                                year_start = date(allocate_till_date.year - 1, adjusted_date.month, adjusted_date.day)
                            else:
                                year_start = date(allocate_till_date.year, adjusted_date.month, adjusted_date.day)
                            year_end = year_start + relativedelta(years=1) - relativedelta(days=1)
                            allocations = self.env['hr.holidays'].search([
                                ('type', '=', 'add'),
                                ('state', '!=', 'refuse'),
                                ('employee_id', '=', employee.id),
                                ('holiday_status_id', '=', leave_balance.holidays_status_id.id),
                                ('allocation_date', '>=', year_start.strftime('%Y-%m-%d')),
                                ('allocation_date', '<=', year_end.strftime('%Y-%m-%d'))
                            ])

                            if not len(allocations) and leave_balance.holidays_status_id.number_of_days > leave_balance.net_balance:
                                create_allocation = 1
                                number_of_days = leave_balance.holidays_status_id.number_of_days - leave_balance.net_balance
                                if number_of_days < 0:
                                    allow_minus_value = 1

                        if leave_balance.non_annual_frequency == 'one_time':
                            allocations = self.env['hr.holidays'].search([
                                ('type', '=', 'add'),
                                ('state', '!=', 'refuse'),
                                ('employee_id', '=', employee.id),
                                ('holiday_status_id', '=', leave_balance.holidays_status_id.id),
                            ])
                            if not len(allocations):
                                create_allocation = 1
                                number_of_days = leave_balance.holidays_status_id.number_of_days

                        if create_allocation:
                            leave_allocation_data = {
                                'name': 'Non Annual leave automatic allocation',
                                'type': 'add',
                                'holiday_status_id': leave_balance.holidays_status_id.id,
                                'number_of_days_temp': number_of_days,
                                'allow_minus_value': allow_minus_value,
                                'employee_id': employee.id,
                                'allocation_date': record.allocate_till_date,
                                'system_created': True,
                                'leave_automatic_allocation': record.id
                            }
                            print(leave_allocation_data)
                            leave_allocation = self.env['hr.holidays'].create(leave_allocation_data)
                            print(leave_allocation)

                            leave_allocation.signal_workflow('validate')
                            if leave_allocation.double_validation:
                                leave_allocation.signal_workflow('second_validate')
                            refresh_employee_ids.append(employee)

                print(refresh_employee_ids)
                for e in refresh_employee_ids:
                    e.refresh_non_annual()

            record.write({'state': 'Confirmed'})
            body = "Document Confirmed"
            self.message_post(body=body, message_type='email')
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

    leave_request_id = fields.Many2one('hr.holidays', 'Leave request')
    name = fields.Char('Description')
    file = fields.Binary('Attachments')
    file_name = fields.Char('File name')
    note = fields.Char('Notes')


class Employee(models.Model):
    _inherit = "hr.employee"

    leaves_count = fields.Float('Number of Leaves', compute='_get_leaves_count')
    leaves_count_float = fields.Float('Number of Leaves', compute='_get_leaves_count')
    non_annual_leave_balance = fields.One2many('non.annual.leave.balance', 'employee_id', string="Non Annual leave Balance")
    start_working_date = fields.Datetime(string="Start Working Date", readonly=True)
    effective_count = fields.Float('Effective Notices count', compute='get_effective_count')
    annual_leave_rate = fields.Float('Annual leave Rate', compute='_compute_annual_leave_rate', store=True)

    @api.one
    @api.depends('leaves_count')
    def _compute_annual_leave_rate(self):
        if self.contract_id and self.contract_id.annual_leave_policy and self.contract_id.annual_leave_policy.days_per_leave:
            self.annual_leave_rate = (self.leaves_count / self.contract_id.annual_leave_policy.days_per_leave) * 100
        else:
            self.annual_leave_rate = 0

    @api.model
    def employee_update_fields(self):
        res = super(Employee, self).employee_update_fields()
        for e in self.search([]):
            e._compute_annual_leave_rate()
        return res

    @api.one
    def get_effective_count(self):
        self.effective_count = len(self.env['effective.notice'].search([['employee_id', '=', self.id]]))

    def action_effective_notices(self, cr, uid, ids, context=None):
        return {
            'domain': "[('employee_id','in',[" + ','.join(map(str, ids)) + "])]",
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
            'res_model': 'hr.holidays',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'default_employee_id': self.id, 'readonly_by_pass': True}
        }

    @api.multi
    def open_other_leaves(self):
        domain = [('id', 'in', self.non_annual_leave_balance.ids)]
        return {
            'domain': domain,
            'name': _('Non Annual leave Balance'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'non.annual.leave.balance',
            'type': 'ir.actions.act_window',
            'target': 'current',
            # 'context': {'default_employee_id': self.id,'readonly_by_pass': True}
        }

    @api.one
    @api.depends()
    def _get_leaves_count(self):
        contracts = self.env['hr.contract'].sudo().search([('employee_id', '=', self.id), ('active', '=', True)])
        if len(contracts):
            contract = contracts[0]
        else:
            contract = False
        if contract and contract.annual_leave_policy:
            leaves = self.env['hr.holidays'].sudo().search(
                [['employee_id', '=', self.id], ['holiday_status_id.limit', '=', False], ['state', '=', 'validate'],
                 ['holiday_status_id', '=', contract.annual_leave_policy.id]])
            self.leaves_count = self.leaves_count_float = round(sum([l.number_of_days for l in leaves]), 2)
        else:
            self.leaves_count = 0

    @api.model
    def create(self, vals):
        res = super(Employee, self).create(vals)
        self.sudo().refresh_non_annual()
        return res

    @api.multi
    def write(self, vals):
        res = super(Employee, self).write(vals)
        self.sudo().refresh_non_annual()
        return res

    @api.multi
    def refresh_non_annual(self):
        for record in self:
            contracts = self.env['hr.contract'].search([('employee_id', '=', record.id), ('active', '=', True)])
            if len(contracts):
                contract = contracts[0]
            else:
                return

            if not record.nationality_type or not record.marital or not record.gender or not record.religion:
                return

            nationality_filter = ['All Nationalities']
            if record.nationality_type == 'Native':
                nationality_filter.append('Native')
            else:
                nationality_filter.append('Non-native')

            marital_filter = ['Both']
            if record.marital == 'single':
                marital_filter.append('Single')
            else:
                marital_filter.append('Married')

            who_request_filter = ['Both']
            if record.gender == 'male':
                who_request_filter.append('Male only')
            else:
                who_request_filter.append('Females only')

            religion_filter = ['All Religions']
            if record.religion == 'single':
                religion_filter.append('Muslim')
            else:
                religion_filter.append('Non-Muslim')

            domain = [
                ('type', '=', 'Non Annual Leave'),
                ('state', '=', 'Approved'),
                ('nationality', 'in', nationality_filter),
                ('marital_status', 'in', marital_filter),
                ('who_request', 'in', who_request_filter),
                ('religion', 'in', religion_filter),
            ]
            non_annual_leaves = self.env['hr.holidays.status'].search(domain)
            # delete lines that not belongs to employee non annual leaves
            for balance in record.non_annual_leave_balance:
                if balance.holidays_status_id.id not in non_annual_leaves.ids:
                    balance.unlink()
            for non_annual_leave in non_annual_leaves:
                allocations = self.env['hr.holidays'].search([
                    ('type', '=', 'add'),
                    ('state', '!=', 'refuse'),
                    ('employee_id', '=', record.id),
                    ('contract_id', '=', contract.id),
                    ('holiday_status_id', '=', non_annual_leave.id),
                    ('allocation_date', '>=', contract.date_start),
                ])
                total_allocation_days = 0
                for allocation in allocations:
                    total_allocation_days += allocation.number_of_days_temp

                requests = self.env['hr.holidays'].search([
                    ('type', '=', 'remove'),
                    ('state', '!=', 'refuse'),
                    ('employee_id', '=', record.id),
                    ('contract_id', '=', contract.id),
                    ('holiday_status_id', '=', non_annual_leave.id),
                    ('date_from', '>=', contract.date_start),
                ], order="date_from desc")
                total_request_days = 0
                for request in requests:
                    total_request_days += request.number_of_days_temp
                total_request_days *= -1

                if len(requests):
                    last_leave_request = requests[0]
                else:
                    last_leave_request = False

                line_to_update = self.env['non.annual.leave.balance'].search([
                    ('holidays_status_id', '=', non_annual_leave.id),
                    ('employee_id', '=', record.id),
                ])

                if line_to_update:
                    line_to_update.non_annual_frequency = non_annual_leave.non_annual_frequency
                    line_to_update.total_allocated_days = total_allocation_days
                    line_to_update.total_requested_days = total_request_days
                    line_to_update.last_leave_request = last_leave_request and last_leave_request.id
                else:
                    line_data = {
                        'holidays_status_id': non_annual_leave.id,
                        'non_annual_frequency': non_annual_leave.non_annual_frequency,
                        'total_allocated_days': total_allocation_days,
                        'total_requested_days': total_request_days,
                        'last_leave_request': last_leave_request and last_leave_request.id,
                        'employee_id': record.id
                    }
                    self.env['non.annual.leave.balance'].create(line_data)


class non_annual_leave_balance(models.Model):
    _name = "non.annual.leave.balance"

    holidays_status_id = fields.Many2one('hr.holidays.status', string=_('Description'))
    non_annual_frequency = fields.Selection([
        ('contract', 'Per contract'),
        ('financial_year', 'Per financial year ( 1Jan : 31 Dec)'),
        ('contractual_year', 'Each contractual year ( hiring dat to next year)'),
        ('one_time', 'one time per live.'),
        ('per_request', 'based on request (no limitation)'),
    ], string='Non annual leave Frequency')
    total_allocated_days = fields.Integer('Total Days Allocated')
    total_requested_days = fields.Integer('Total Days Requested')
    net_balance = fields.Integer('Net Balance', compute='_compute_net_balance')
    last_leave_request = fields.Many2one('hr.holidays', string="Last Leave Request")
    leave_request_date = fields.Datetime('Leave Request Date', related="last_leave_request.date_from", readonly=True)
    employee_id = fields.Many2one('hr.employee', string=_('Employee'), )

    @api.depends('total_allocated_days', 'total_requested_days')
    def _compute_net_balance(self):
        for rec in self:
            rec.net_balance = rec.total_allocated_days + rec.total_requested_days


class res_country(models.Model):
    _inherit = "res.country"

    check_iqama_expiry = fields.Boolean('Check for IQAMA / National ID expiry',
                                        help='In order to force your system to Check for IQAMA / National ID expiry date, this field must be flagged in Leave type and employee nationality.')
    check_passport_expiry = fields.Boolean('Check for Passport expiry date',
                                           help='In order to force your system to Check for Passport expiry date, this field must be flagged in Leave type and employee nationality.')
