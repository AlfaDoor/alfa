# -*- coding: utf-8 -*-
from .base_tech import *

from odoo import models, fields, api, exceptions, _, SUPERUSER_ID
import datetime
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from dateutil.relativedelta import relativedelta

# _logger = logging.getLogger(__name__)
# _logger.info(error_msg)
from odoo.tools.float_utils import float_compare
from odoo.tools import __


class RewardsType(models.Model):
    _name = "hr.reward.type"
    _description = "Reward type"
    _inherit = "mail.thread"
    _order = "id desc"

    state = selection_field([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
    ], string="Status", default='new', track_visibility='onchange')
    code = char_field('Code')
    name = char_field('Arabic Description')
    en_name = char_field('English Description')
    calc_method = selection_field([
        ('basic', 'Basic Salary'),
        ('basic_house', 'Basic Salary + House allowance'),
        ('basic_house_transportation', 'Basic Salary + House allowance + transportation'),
        ('basic_house_transportation_phone', 'Basic salary + House + transportation + phone'),
        ('total', 'Total salary'),
        ('fixed', 'fixed amount'),
        ('annual', 'Free annual leave balance'),
    ], string='Rewards calculation method')
    amount = float_field('Amount')
    maximum_numbers = float_field('maximum amount')
    confirm_uid = m2o_field('res.users', 'Confirmed by')
    employee_reward_ids = o2m_field('hr.employee.rewards', 'reward_type_id', 'Employee old Rewards')
    attachment_ids = o2m_field('rewards.type.attaches', 'source_id', 'Attachments')
    note = html_field('Notes')

    @api.one
    def reset(self):
        self.state = 'new'

    @api.one
    def confirm(self):
        self.confirm_uid = self.env.user.id
        self.state = 'confirmed'

    @api.model
    def create(self, vals):
        res = super(RewardsType, self).create(vals)
        res.code = self.env['ir.sequence'].sudo().next_by_code(self._name)
        return res


class EmployeeRewards(models.Model):
    _name = "hr.employee.rewards"
    _inherit = "mail.thread"
    _description = "Employee Rewards"
    _order = "id desc"
    _rec_name = "employee_id"

    state = selection_field([
        ('new', 'New'),
        ('reviewed', 'reviewed'),
        ('confirmed', 'Confirmed'),
    ], string="Status", default='new', track_visibility='onchange')
    employee_id = m2o_field('hr.employee', 'Employee')
    contract_id = m2o_field('hr.contract', 'Contract', related='employee_id.contract_id', store=True, readonly=True)
    adjusted_date = date_field('Join date', related='contract_id.start_work', readonly=True)
    reward_type_id = m2o_field('hr.reward.type', 'Reward type')
    desc = char_field('Description')
    reward_date = date_field('Reward date')
    calc_method = selection_field([
        ('basic', 'Basic Salary'),
        ('basic_house', 'Basic Salary + House allowance'),
        ('basic_house_transportation', 'Basic Salary + House allowance + transportation'),
        ('basic_house_transportation_phone', 'Basic salary + House + transportation + phone'),
        ('total', 'Total salary'),
        ('fixed', 'fixed amount'),
        ('annual', 'Free annual leave balance'),
    ], string='Rewards calculation method')
    amount = float_field('Amount')
    maximum_numbers = float_field('maximum amount')
    reversed_reward_id = m2o_field('hr.employee.rewards', 'Reversed Reward')
    source_reward_id = m2o_field('hr.employee.rewards', 'Reversed Reward')
    reward_reverse_reason = char_field('Reward Reverse Reason')
    minus_value = bool_field('Accept minus value', default=False)
    reward_amount = float_field('Rewarded amount')
    old_reward_id = m2o_field('hr.employee.rewards')
    attachment_ids = o2m_field('employee.reward.attaches', 'source_id', 'Attachments')
    note = html_field('Notes')
    auto_created = fields.Boolean('Auto created')
    reversed_deduction = fields.Many2one('employee.deductions.violations', 'Reversed  Deduction - violation')
    deduction = fields.Many2one('employee.deductions.violations', 'Deduction')
    branch_id = fields.Many2one('hr.branch', string='Branch', related="employee_id.branch_id", readonly=True, store=True)
    loan_id = fields.Many2one('loan.advance.request', 'Loan Request')
    absence_report_id = fields.Many2one('employee.absence.line', 'Employee Absence Report')

    @api.onchange('calc_method', 'amount', 'contract_id')
    def get_reward_amount(self):
        reward_amount = 0
        if self.calc_method in ['fixed', 'annual']:
            reward_amount = self.amount
        else:
            if self.contract_id.id:
                based_on_value = self.contract_id.total
                reward_amount = (based_on_value / 30) * (self.amount / 100)
        self.reward_amount = reward_amount

    @api.onchange('reward_type_id')
    def onchange_reward_type_id(self):
        self.amount = self.reward_type_id.amount
        self.calc_method = self.reward_type_id.calc_method
        self.maximum_numbers = self.reward_type_id.maximum_numbers

    @api.model
    def create(self, vals):
        res = super(EmployeeRewards, self).create(vals)
        res.code = self.env['ir.sequence'].sudo().next_by_code(self._name)
        return res

    @api.one
    def review(self):
        self.state = 'reviewed'
        body = "Document Reviewed"
        self.message_post(body=body, message_type='email')

    @api.multi
    def confirm(self):
        for rec in self:
            rec.state = 'confirmed'
            body = "Document Confirmed"
            self.message_post(body=body, message_type='email')

    @api.one
    def reset(self):
        self.state = 'new'
        body = "Document reset to new"
        self.message_post(body=body, message_type='email')

    @api.one
    def reverse(self):
        raise ValidationError(_("Reversing Rewards Still under development\n\
            If you want to do it manually, go to deduction window, and create a deduction with the same amount."))


class RewardsTypeAttaches(models.Model):
    _name = "rewards.type.attaches"
    _description = "Reward type Attaches"

    source_id = m2o_field('hr.reward.type', 'hr.reward.type')
    file = binary('File', required=True)
    name = char_field('Description', required=True)
    note = char_field('Notes')


class EmployeeRwardAttaches(models.Model):
    _name = "employee.reward.attaches"
    _description = "employee Reward Attaches"

    source_id = m2o_field('hr.employee.rewards', 'hr.reward.type')
    file = binary('File', required=True)
    name = char_field('Description', required=True)
    note = char_field('Notes')


class Contract(models.Model):
    _inherit = "hr.contract"
    employee_reward_ids = o2m_field('hr.employee.rewards', 'contract_id', 'Employee Rewards',
                                    domain=[['state', '=', 'confirmed'], ['calc_method', '!=', 'annual']])
    total_rewards = float_field('Total rewards', compute='get_count_rewards')
    reward_paid_amount_ids = o2m_field('contract.paid.rewards', 'contract_id', 'Reward paid amount')
    reward_total_paid_amount = float_field('Total paid amount', compute='get_reward_total_paid_amount')
    total_rewards_copy = float_field('Total rewards', related='total_rewards', readonly=True)
    reward_total_paid_amount_copy = float_field('Total paid amount', compute='get_reward_total_paid_amount', related='reward_total_paid_amount', readonly=True)
    remaining_rewards = float_field('Remaining', compute='get_remaining_rewards')

    @api.one
    @api.depends('total_rewards', 'reward_total_paid_amount')
    def get_remaining_rewards(self):
        self.remaining_rewards = round(self.total_rewards, 2) - round(self.reward_total_paid_amount, 2)

    @api.one
    @api.depends('reward_paid_amount_ids')
    def get_reward_total_paid_amount(self):
        self.reward_total_paid_amount = sum([p.amount for p in self.reward_paid_amount_ids])

    @api.one
    @api.depends('employee_reward_ids')
    def get_count_rewards(self):
        self.total_rewards = sum([r.reward_amount for r in self.employee_reward_ids])


class ContractPaidRewards(models.Model):
    _name = "contract.paid.rewards"

    contract_id = m2o_field('hr.contract', 'Contract')
    reference_id = m2o_field('hr.payslip', 'Payment reference')
    date = char_field('Payment date')
    amount = float_field('Payment amount')
    note = char_field('Notes')


class Payroll(models.Model):
    _inherit = "hr.payslip"

    total_rewards = float_field('Total Rewards', compute='get_total_rewards')
    total_rewards_ = float_field('Total Rewards')
    total_reward_paid = float_field('Total paid', compute='get_total_reward_paid')
    total_reward_paid_ = float_field('Total paid')
    remaining_rewards = float_field('Remaining', compute='get_remaining_rewards')
    remaining_rewards_ = float_field('Remaining')
    rewards_remaining = fields.Float('Remaining Rewards', compute="_compute_rewards_remaining")
    reward_pay_this_month = float_field('Pay this month')
    reward_remove_amount = float_field('Remove this amount from employee')
    reward_next_balance = float_field('Next Month balance', compute='get_reward_next_balance')
    reward_next_balance_history = float_field('Next Month balance')
    reward_fixed_amount = fields.Boolean('Reward Fixed Amount')

    @api.one
    def _compute_rewards_remaining(self):
        if self.state == 'done':
            self.rewards_remaining = self.remaining_rewards_
        else:
            self.rewards_remaining = self.remaining_rewards

    @api.one
    @api.depends('remaining_rewards', 'reward_pay_this_month', 'reward_remove_amount')
    def get_reward_next_balance(self):
        self.reward_next_balance = round(self.remaining_rewards, 2) - round(self.reward_pay_this_month , 2) - round(self.reward_remove_amount, 2)

    @api.one
    @api.depends('total_rewards', 'total_reward_paid')
    def get_remaining_rewards(self):
        self.remaining_rewards = round(self.total_rewards - self.total_reward_paid, 2)

    @api.one
    @api.depends('contract_id')
    def get_total_reward_paid(self):
        self.total_reward_paid = self.total_rewards_ or self.contract_id.reward_total_paid_amount

    @api.one
    @api.depends('contract_id')
    def get_total_rewards(self):
        self.total_rewards = self.total_rewards_ or self.contract_id.total_rewards

    @api.one
    def action_payslip_done(self):
        if self.remaining_rewards and not self.loans_data_reviewed:
            mess_1 = _(
                "Attention!! \n This employee  ( %s  ) had old loans or deductions or rewards which is not fully paid ….before confirm this payslip. kindly go to ( other payment / deduction) tab,  and make sure that you checked (other payments / deduction reviewed).") % (
                         self.employee_id.name)
            raise ValidationError(mess_1)
        if self.reward_next_balance <= -.01:
            raise ValidationError(_("Validation Error! \n\
                It seems that you Paid an amount bigger than the employee rewards balance. kindly review your data.\n- Employee: %s\nSlip: %s" % (self.employee_id.display_name,self.name)))
        self.total_rewards_ = self.total_rewards
        self.total_reward_paid_ = self.total_reward_paid
        self.remaining_rewards_ = self.remaining_rewards
        self.reward_next_balance_history = self.reward_next_balance
        if self.reward_pay_this_month:
            self.env['contract.paid.rewards'].create({
                'contract_id': self.contract_id.id,
                'reference_id': self.id,
                'date': __(self.date_to),
                'amount': self.reward_pay_this_month,
            })
        if self.reward_remove_amount:
            self.env['contract.paid.rewards'].create({
                'contract_id': self.contract_id.id,
                'reference_id': self.id,
                'date': __(self.date_to),
                'amount': self.reward_remove_amount,
            })
        return super(Payroll, self).action_payslip_done()


class Employee(models.Model):
    _inherit = "hr.employee"

    rewards_count = integer_field('Employee rewards', compute='get_rewards_count')

    @api.one
    @api.depends()
    def get_rewards_count(self):
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.id), ('active', '=', True)])
        if len(contracts):
            contract = contracts[0]
            self.rewards_count = contract.remaining_rewards
        else:
            self.rewards_count = 0

    @api.multi
    def open_rewards(self):
        return {
            'domain': [['employee_id', '=', self.id]],
            'name': _('Employee Rewards'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.employee.rewards',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'default_employee_id': self.id, 'readonly_by_pass': True},
        }
