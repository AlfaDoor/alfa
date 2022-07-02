# -*- coding: utf-8 -*-
from .base_tech import *

from odoo import models, fields, api, _
import datetime
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools import __

class ContractPaidViolation(models.Model):
    _name = "contract.paid.violation"

    contract_id = m2o_field('hr.contract', 'Contract')
    reference_id = m2o_field('hr.payslip', 'Payment reference')
    date = char_field('Payment date')
    amount = float_field('Payment amount')
    note = char_field('Notes')


class DeductionViolationCategory(models.Model):
    _name = "deduction.violation.category"
    _inherit = "mail.thread"
    _description = "Deduction / Violation category"
    _order = "id desc"

    READONLY_STATES = {'confirmed': [('readonly', True)]}
    code = char_field('code')
    name = char_field('Arabic name', states=READONLY_STATES)
    english_name = char_field('English name', states=READONLY_STATES)
    sub_type_ids = o2m_field('deduction.violation.type', 'deduction_categ_id', 'Sub types')
    note = html_field('Notes', states=READONLY_STATES)
    state = selection_field([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
    ], string='Status', track_visibility='onchange', default='new')

    used_for_absence = fields.Boolean('This violation category can be used for absence')
    reset_each = fields.Integer('Reset Violation Counter each', default=6)

    @api.one
    def confirm(self):
        self.state = 'confirmed'
        body = "Document Confirmed"
        self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def set_new(self):
        self.state = 'new'
        body = "Document Set To New"
        self.message_post(body=body, message_type='email')
        return {}

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].sudo().next_by_code(self._name)
        res = super(DeductionViolationCategory, self).create(vals)
        return res


class DeductionViolationType(models.Model):
    _name = "deduction.violation.type"
    _inherit = "mail.thread"
    _description = "Deduction / Violation Types"
    _order = "id desc"

    state = selection_field([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
    ], string='Status', track_visibility='onchange', default='new')
    code = char_field('code')
    name = char_field('Violation / deduction Arabic Description')
    english_name = char_field('Violation / deduction English Description')
    deduction_categ_id = m2o_field('deduction.violation.category', 'Deduction / Violation category')
    deduction_based_on = selection_field([
        ('basic', 'Basic Salary'),
        ('basic_house', 'Basic Salary + House allowance'),
        ('basic_house_transportation', 'Basic Salary + House allowance + transportation'),
        ('basic_house_transportation_phone', 'Basic salary + House + transportation + phone'),
        ('total', 'Total salary'),
    ], string='Deduction based on')
    # First time
    deduction_type1 = selection_field([
        ('verbal', 'Verbal warning'),
        ('letter', 'Send notification letter'),
        ('deduction', 'Deduct from employee salary'),
        ('deduction_action', 'Deduct from employee salary + other action'),
    ], string="Deduction type")
    template1_id = m2o_field('mail.template', 'Notification letter', domain=lambda self: [['model', '=', self._name]])
    deduction_percentage1 = float_field('Deduction percentage')
    other_action1 = selection_field([
        ('terminate', 'Termination without rewards'),
        ('terminate_rewards', 'Termination with rewards'),
        ('other', 'Other action'),
    ], string='Other action')
    other_action_desc1 = char_field('Other action description')
    # second time
    deduction_type2 = selection_field([
        ('verbal', 'Verbal warning'),
        ('letter', 'Send notification letter'),
        ('deduction', 'Deduct from employee salary'),
        ('deduction_action', 'Deduct from employee salary + other action'),
    ], string="Deduction type")
    template2_id = m2o_field('mail.template', 'Notification letter', domain=lambda self: [['model', '=', self._name]])
    deduction_percentage2 = float_field('Deduction percentage')
    other_action2 = selection_field([
        ('terminate', 'Termination without rewards'),
        ('terminate_rewards', 'Termination with rewards'),
        ('other', 'Other action'),
    ], string='Other action')
    other_action_desc2 = char_field('Other action description')
    # Third time
    deduction_type3 = selection_field([
        ('verbal', 'Verbal warning'),
        ('letter', 'Send notification letter'),
        ('deduction', 'Deduct from employee salary'),
        ('deduction_action', 'Deduct from employee salary + other action'),
    ], string="Deduction type")
    template3_id = m2o_field('mail.template', 'Notification letter', domain=lambda self: [['model', '=', self._name]])
    deduction_percentage3 = float_field('Deduction percentage')
    other_action3 = selection_field([
        ('terminate', 'Termination without rewards'),
        ('terminate_rewards', 'Termination with rewards'),
        ('other', 'Other action'),
    ], string='Other action')
    other_action_desc3 = char_field('Other action description')
    # Forth time
    deduction_type4 = selection_field([
        ('verbal', 'Verbal warning'),
        ('letter', 'Send notification letter'),
        ('deduction', 'Deduct from employee salary'),
        ('deduction_action', 'Deduct from employee salary + other action'),
    ], string="Deduction type")
    template4_id = m2o_field('mail.template', 'Notification letter', domain=lambda self: [['model', '=', self._name]])
    deduction_percentage4 = float_field('Deduction percentage')
    other_action4 = selection_field([
        ('terminate', 'Termination without rewards'),
        ('terminate_rewards', 'Termination with rewards'),
        ('other', 'Other action'),
    ], string='Other action')
    other_action_desc4 = char_field('Other action description')

    confirm_uid = m2o_field('res.users', 'Confirmed by')
    attachment_ids = o2m_field('deduction.type.attaches', 'type_id', 'Attachments')
    note = html_field('Notes')
    model_name = char_field('Model name', default=lambda self: self._name)
    used_for_absence = fields.Boolean('This violation can be used for absence')
    reset_each = fields.Integer('Reset Violation Counter each', default=6)

    @api.one
    def confirm(self):
        self.state = 'confirmed'
        self.confirm_uid = self.env.user.id
        body = "Document Confirmed"
        self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def reset(self):
        self.state = 'new'

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].sudo().next_by_code(self._name)
        res = super(DeductionViolationType, self).create(vals)
        return res


class EmployeeDeductionsPayment(models.Model):
    _name = "employee.deductions.payment"
    _description = "Employee Deductions Payment"

    deduction_id = fields.Many2one('employee.deductions.violations', "Deduction")
    payslip_id = fields.Many2one('hr.payslip', 'Payslip')
    leave_reconciliation_id = fields.Many2one('hr.leave.reconciliation', 'Leave Reconciliation')
    paid = fields.Float('Paid Amount')
    note = fields.Char('Notes')


class EmployeeDeductionsViolations(models.Model):
    _name = "employee.deductions.violations"
    _inherit = "mail.thread"
    _description = "Employee deductions - violations"
    _order = "id desc"
    _rec_name = "employee_id"

    MONTHS_SELECTION = {'01': 'January', '02': 'February', '03': 'March', '04': 'April', '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                        '09': 'September', '10': 'October', '11': 'November', '12': 'December'}
    state = selection_field([
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('confirmed', 'Confirmed'),
        ('refused', 'Refused'),
    ], string='Status', default='new', track_visibility='onchange')
    code = char_field('Code')
    deduction_violation_category_id = m2o_field('deduction.violation.category', 'Violation - deduction category',
                                                related='violation_type_id.deduction_categ_id', store=True, readonly=True)
    violation_type_id = m2o_field('deduction.violation.type', 'Violation Type')
    desc = char_field('Description')
    employee_id = m2o_field('hr.employee', 'Employee')
    sponsor = char_field(related='employee_id.sponsor_id', store=True)
    supervisor = m2o_field(related='employee_id.coach_id', store=True)
    emp_status = m2o_field(related='employee_id.employee_status', store=True)
    contract_id = m2o_field('hr.contract', 'Contract', related='employee_id.contract_id', store=True, readonly=True)
    department_id = m2o_field('hr.department', 'Department', related='employee_id.department_id', store=True, readonly=True)
    adjusted_date = date_field('Join date', related='contract_id.start_work', readonly=True)
    deduction_date = date_field('Deduction date')
    issue_date = date_field('Issue date')
    month = char_field('Month', compute='get_month', store=True)
    deduction_reason = selection_field([
        ('manual', 'Manual deduction'),
        ('violation', 'Violation'),
        ('other', 'Other'),
    ], string='Deduction Reason')
    previous_violations = integer_field('Previous violations', compute='get_previous_violations', store=True)
    decision = selection_field([
        ('verbal', 'Verbal warning'),
        ('letter', 'Send notification letter'),
        ('deduction', 'Deduct from employee salary'),
        ('deduction_action', 'Deduct from employee salary + other action'),
    ], string='Decision')
    template_id = m2o_field('mail.template', 'Notification letter', domain=lambda self: [['model', '=', self._name]])
    deduction_percentage = float_field('Deduction percentage')
    other_action = selection_field([
        ('terminate', 'Termination without rewards'),
        ('terminate_rewards', 'Termination with rewards'),
        ('other', 'Other action'),
    ], string='Other action')
    action_desc = char_field('Other action description')
    deduction_based_on = selection_field([
        ('basic', 'Basic Salary'),
        ('basic_house', 'Basic Salary + House allowance'),
        ('basic_house_transportation', 'Basic Salary + House allowance + transportation'),
        ('basic_house_transportation_phone', 'Basic salary + House + transportation + phone'),
        ('total', 'Total salary'),
    ], string='Deduction based on')
    deduction_type = selection_field([
        ('fixed', 'Fixed amount'),
        ('percentage', 'percentage'),
    ], string='Deduction type')
    percentage_type = fields.Selection([('monthly', 'Monthly'), ('daily', 'Daily'), ], string='Percentage type', default='monthly')
    deduction_value = float_field('Deduction value')
    minus_deduction = bool_field('Accept minus deduction value', default=False)
    amount = float_field('Amount', compute='get_amount', store=True)
    note = html_field('Note')
    attachment_ids = o2m_field('deductions.violations.attaches', 'source_id', 'Attachments')
    reverse_deduction_id = m2o_field('employee.deductions.violations', 'Reversed Deduction')
    source_deduction_id = m2o_field('employee.deductions.violations', 'Source deduction')
    deduction_reverse_reason = char_field('Deduction reverse reason')
    old_deduction_id = m2o_field('employee.deductions.violations')
    early_return_from_leave = fields.Many2one('effective.notice', 'Early Return from leave')
    late_return_from_leave = fields.Many2one('effective.notice', 'Late Return from leave')
    auto_deduction = bool_field('Automatic deduction')
    absence_record = fields.Many2one('employee.absence.line', 'Absence Record')
    absence_deduction_amount = fields.Float('Employee Absence Amount', related='absence_record.deduction_amount', readonly=True)
    total = fields.Float('Total Absence + Violation', compute='_compute_total', store=True)
    reversed_reward = fields.Many2one('hr.employee.rewards', 'Reversed Employee Reward')
    employee_reward = fields.Many2one('hr.employee.rewards', 'Employee-rewards')
    payment_ids = fields.One2many('employee.deductions.payment', 'deduction_id', 'Payment details')
    paid_amount = fields.Float('Paid Amount', compute='_compute_paid_amount', store=True)
    remaining_amount = fields.Float('Remaining Amount', compute='_compute_remaining_amount', store=True)
    branch_id = fields.Many2one('hr.branch', string='Branch', related="employee_id.branch_id", readonly=True, store=True)

    @api.model_cr
    def init(self):
        for deduction in self.search([('deduction_date', '<', '2020-12-01')]):
            if deduction.remaining_amount > 0:
                print(
                    "Deduction,Code:%s Employee:%s, Amount:%s, Remain:%s, date:%s" % (
                        deduction.code, deduction.employee_id.name, deduction.amount, deduction.remaining_amount, deduction.deduction_date))
                self.env['employee.deductions.payment'].create({
                    'deduction_id': deduction.id,
                    'paid': deduction.remaining_amount,
                })
        self.env['contract.paid.violation'].search([]).unlink()
        for contract in self.env['hr.contract'].search([]):
            dec_deductions = self.env['employee.deductions.violations'].search([('employee_id', '=', contract.employee_id.id),
                                                                                ('deduction_date', '>=', '2020-12-01')])
            amount = contract.remaining
            if dec_deductions:
                dec_deductions_amount = sum([d.amount for d in dec_deductions])
                amount -= dec_deductions_amount
            if amount:
                self.env['contract.paid.violation'].create({
                    'contract_id': contract.id,
                    'amount': amount,
                })
                print("Contract: %s, Amount: %s" % (contract.employee_id.name, amount))
            # if remain < 0:
            #     print("Contract, Employee: %s, Amount:%s" % (contract.employee_id.name, remain))
            #     for paid in contract.paid_amount_ids:
            #         if remain >= paid.amount > 0:
            #             print("Contract removing 1:%s" % paid.amount)
            #             remain -= paid.amount
            #             paid.unlink()
            #             if remain <= 0: break
            #             continue
            #         elif remain < paid.amount:
            #             paid.amount -= remain
            #             print("Contract removing 2:%s" % remain)
            #             break
            #         if remain < 1: break

    @api.onchange('employee_id', 'deduction_based_on', 'deduction_type', 'deduction_value', 'percentage_type')
    def onchange_deduction_pecentage(self):
        balance = 0
        if self.employee_id.contract_id and self.deduction_based_on and self.deduction_type in ['percentage']:
            contract = self.contract_id
            based_on_value = 0
            if self.deduction_based_on == 'basic':
                based_on_value = contract.basic_salary
            if self.deduction_based_on == 'basic_house':
                based_on_value = contract.basic_salary + contract.house_allowance_amount
            if self.deduction_based_on == 'basic_house_transportation':
                based_on_value = contract.basic_salary + contract.house_allowance_amount + contract.transportation_allowance_amount
            if self.deduction_based_on == 'basic_house_transportation_phone':
                based_on_value = contract.basic_salary + contract.house_allowance_amount + contract.transportation_allowance_amount + contract.phone_allowance_amount
            if self.deduction_based_on == 'total':
                based_on_value = contract.total
            balance = based_on_value * self.deduction_value / 100
            if self.percentage_type == 'daily':
                balance = balance / 30
        self.amount = balance

    @api.one
    @api.depends('payment_ids')
    def _compute_paid_amount(self):
        self.paid_amount = sum([p.paid for p in self.payment_ids])

    @api.one
    @api.depends('paid_amount', 'amount')
    def _compute_remaining_amount(self):
        self.remaining_amount = self.amount - self.paid_amount

    @api.one
    @api.depends('amount', 'absence_deduction_amount')
    def _compute_total(self):
        self.total = self.amount + self.absence_deduction_amount

    @api.onchange('deduction_percentage')
    def onchange_deduction_percentage(self):
        self.deduction_value = self.deduction_percentage

    @api.one
    @api.depends('deduction_date')
    def get_month(self):
        month = __(self.deduction_date).split('-')[1]
        year = __(self.deduction_date).split('-')[0]
        self.month = '%s - %s' % (self.MONTHS_SELECTION[month], str(year))

    @api.one
    @api.depends('deduction_type', 'contract_id', 'deduction_value', 'deduction_based_on')
    def get_amount(self):
        self.amount = 0
        if self.deduction_type == 'fixed':
            self.amount = self.deduction_value
        if self.deduction_type == 'percentage':
            based_on_value = self.contract_id.basic_salary + self.contract_id.house_allowance_amount + self.contract_id.transportation_allowance_amount
            self.amount = (based_on_value / 30) * (self.deduction_value / 100)

    @api.onchange('deduction_reason', 'violation_type_id')
    def onchange_deduction_reason(self):
        if self.deduction_reason == 'violation':
            self.deduction_type = 'percentage'
            if self.violation_type_id:
                self.deduction_based_on = self.violation_type_id.deduction_based_on or False

    @api.onchange('decision', 'deduction_percentage', 'violation_type_id')
    def get_deduction_type(self):
        if self.decision == 'violation':
            self.deduction_type = self.deduction_percentage

    @api.onchange('previous_violations', 'violation_type_id')
    def get_decision(self):
        self.get_previous_violations()
        if self.violation_type_id:
            times = self.previous_violations + 1
            times = times <= 4 and str(times) or '4'
            self.decision = getattr(self.violation_type_id, 'deduction_type%s' % times)
            self.template_id = getattr(self.violation_type_id, 'template%s_id' % times)
            self.deduction_percentage = getattr(self.violation_type_id, 'deduction_percentage%s' % times)
            self.other_action = getattr(self.violation_type_id, 'other_action%s' % times)
            self.action_desc = getattr(self.violation_type_id, 'other_action_desc%s' % times)

    @api.one
    @api.depends('violation_type_id', 'employee_id', 'deduction_date')
    def get_previous_violations(self):
        if self.violation_type_id and __(self.deduction_date) and self.employee_id:
            d2 = datetime.datetime.strptime(__(self.deduction_date), "%Y-%m-%d") - relativedelta(months=self.violation_type_id.reset_each)
            self.previous_violations = len(self.search([
                ['state', '=', 'confirmed'],
                ['employee_id', '=', self.employee_id.id],
                ['violation_type_id', '=', self.violation_type_id.id],
                ['reverse_deduction_id', '=', False],
                ['source_deduction_id', '=', False],
                ['deduction_reverse_reason', '=', False],
                ['deduction_date', '>=', d2],
            ])) or 0.00

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].sudo().next_by_code(self._name)
        res = super(EmployeeDeductionsViolations, self).create(vals)
        return res

    @api.multi
    def open_confirm_other_action(self):
        ctx = {'deduction_violation_id': self.id, 'default_action': self.action_desc}
        return {
            'domain': [],
            'name': _('Attention'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'confirm.other.action',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def confirm(self, confirm_other_action=False):
        if self.decision == 'deduction_action' and self.other_action == 'other':
            if not (isinstance(confirm_other_action, bool) and confirm_other_action):
                return self.open_confirm_other_action()
        self.state = 'confirmed'
        body = "Document Confirmed"
        self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def review(self):
        self.state = 'reviewed'
        body = "Document Reviewed"
        self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def refuse(self):

        self.state = 'refused'
        body = "Document Refused"
        self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def set_draft(self):
        self.state = 'new'
        body = "Document Set To New"
        self.message_post(body=body, message_type='email')
        return {}


class DeductionTypeAttaches(models.Model):
    _name = "deduction.type.attaches"
    _description = "DeductionType Attaches"

    type_id = m2o_field('deduction.violation.type', 'deduction violation type')
    file = binary('File')
    name = char_field('Description')
    note = char_field('Notes')


class DeductionViolationAttaches(models.Model):
    _name = "deductions.violations.attaches"
    _description = "deductions violations Attaches"

    source_id = m2o_field('employee.deductions.violations', 'Employee deductions - violations')
    file = binary('File')
    name = char_field('Description')
    note = char_field('Notes')


class ConfirmOtherAction(models.TransientModel):
    _name = "confirm.other.action"

    action = char_field(string='Other action')

    @api.multi
    def confirm(self):
        deduction_violation_id = self._context.get('deduction_violation_id', False)
        self.env['employee.deductions.violations'].browse(deduction_violation_id).confirm(confirm_other_action=True)


class Contract(models.Model):
    _inherit = "hr.contract"

    deduction_violation_ids = o2m_field('employee.deductions.violations', 'contract_id', 'Old deductions - Violations', domain=[['state', '=', 'confirmed']])
    total_deduction_amount = float_field('Total deduction amount', compute='get_total_deduction_amount')
    total_deduction_amount_ = float_field('Total deduction amount', related='total_deduction_amount', readonly=True)
    paid_amount_ids = o2m_field('contract.paid.violation', 'contract_id', 'Paid amounts')
    total_paid_amount = float_field('Total paid amount', compute='get_total_paid_amount')
    total_paid_amount_ = float_field('Total paid amount', related='total_paid_amount', readonly=True)
    remaining = float_field('Remaining', compute='get_remaining')

    @api.one
    @api.depends('total_deduction_amount', 'total_paid_amount')
    def get_remaining(self):
        self.remaining = round(self.total_deduction_amount, 2) - round(self.total_paid_amount, 2)

    @api.one
    @api.depends('deduction_violation_ids')
    def get_total_deduction_amount(self):
        self.total_deduction_amount = round(sum([l.amount for l in self.deduction_violation_ids]), 2)

    @api.one
    @api.depends('paid_amount_ids')
    def get_total_paid_amount(self):
        self.total_paid_amount = round(sum([float(l.amount) for l in self.paid_amount_ids]), 2)


class Payroll(models.Model):
    _inherit = "hr.payslip"

    total_deduction = float_field('Total deductions', compute='get_total_deduction')
    total_deduction_ = float_field('Total deductions')
    total_paid = float_field('Total paid', compute='get_total_paid')
    total_paid_ = float_field('Total paid')
    remaining = float_field('Remaining', compute='get_remaining')
    remaining_ = float_field('Remaining')
    remaining_deduction = fields.Float('Remaining Violations', compute="_compute_remaining_deduction")
    deduct_this_month_ = float_field('Deduct this month')
    remove_from_employee = float_field('Remove this amount from employee')
    next_month_balance = float_field('Next Month balance', compute='get_next_month_balance')
    next_month_balance_history = float_field('Next Month balance')
    deduction_fixed_amount = fields.Boolean('Deduction Fixed Amount')

    @api.one
    def _compute_remaining_deduction(self):
        if self.state == 'done':
            self.remaining_deduction = self.remaining_
        else:
            self.remaining_deduction = self.remaining

    @api.one
    @api.depends('remaining', 'remove_from_employee', 'deduct_this_month_')
    def get_next_month_balance(self):
        self.next_month_balance = round(self.remaining - self.remove_from_employee - self.deduct_this_month_, 2)

    @api.one
    @api.depends('total_deduction', 'total_paid')
    def get_remaining(self):
        self.remaining = self.total_deduction - self.total_paid
        if self.remaining == 0:
            self.remove_from_employee = 0

    @api.one
    @api.depends('contract_id')
    def get_total_deduction(self):
        self.total_deduction = self.total_deduction_ or self.contract_id.total_deduction_amount

    @api.one
    @api.depends('contract_id')
    def get_total_paid(self):
        self.total_paid = self.total_paid_ or self.contract_id.total_paid_amount

    @api.one
    def action_payslip_done(self):
        if self.remaining and not self.loans_data_reviewed:
            raise ValidationError(_("Attention!! \n\
            This employee  ( %s  ) had old loans or deductions or rewards which is not fully paid before confirm this payslip. kindly go to ( other payment /\
             deduction) tab,  and make sure that you checked (other payments / deduction reviewed).") % (self.employee_id.name))
        self.total_deduction_ = self.total_deduction
        self.total_paid_ = self.total_paid
        self.remaining_ = self.remaining
        self.next_month_balance_history = self.next_month_balance
        if self.deduct_this_month_:
            self.env['contract.paid.violation'].create({
                'contract_id': self.contract_id.id,
                'reference_id': self.id,
                'date': __(self.date_to),
                'amount': self.deduct_this_month_,
            })
            # /////////// Register payments to deductions records ////////////////////
            deductions = self.env["employee.deductions.violations"].search([
                ('state', '=', 'confirmed'),
                ('employee_id', '=', self.employee_id.id),
                ('deduction_date', '<=', __(self.date_to)),
                ('remaining_amount', '>', 0),
            ])
            if deductions:
                remaining_deduction = self.deduct_this_month_
                for deduction in deductions:
                    deducted = 0
                    if remaining_deduction <= 0:
                        break
                    if deduction.remaining_amount > 0:
                        if remaining_deduction < deduction.remaining_amount:
                            deducted = remaining_deduction
                        else:
                            deducted = deduction.remaining_amount
                        # Create payment to deduction
                        payment_vals = {
                            'deduction_id': deduction.id,
                            'payslip_id': self.id,
                            'paid': deducted,
                        }
                        payment_id = self.env['employee.deductions.payment'].create(payment_vals)
                        remaining_deduction -= deducted
        if self.remove_from_employee:
            self.env['contract.paid.violation'].create({
                'contract_id': self.contract_id.id,
                'reference_id': self.id,
                'date': __(self.date_to),
                'amount': self.remove_from_employee,
            })
        return super(Payroll, self).action_payslip_done()

    @api.model
    def loan_deduction_rule(self):
        return self.deduct_this_month * -1

    @api.model
    def violation_deduction_rule(self):
        return self.deduct_this_month_ * -1

    @api.model
    def rewards_rule(self):
        return self.reward_pay_this_month

    @api.model
    def total_deductions(self):
        res = super(Payroll, self).total_deductions()
        return res + self.loan_deduction_rule() + self.violation_deduction_rule() + self.rewards_rule() + self.RULE_overtime()


class Employee(models.Model):
    _inherit = "hr.employee"

    deductions_count = float_field('Deduction count', compute='get_deductions_count')

    @api.one
    def get_deductions_count(self):
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.id), ('active', '=', True)])
        if len(contracts):
            contract = contracts[0]
            self.deductions_count = round(contract.remaining, 2)
        else:
            self.deductions_count = 0

    @api.multi
    def open_deductions(self):
        return {
            'domain': [['employee_id', '=', self.id]],
            'name': _('Employee deductions - violations'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'employee.deductions.violations',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'default_employee_id': self.id},
        }
