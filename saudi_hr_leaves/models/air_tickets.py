# -*- coding: utf-8 -*-


from odoo import models, fields, api, exceptions, _, SUPERUSER_ID
import datetime
# from odoo.addons.base_import.test_models import o2m
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from dateutil.relativedelta import relativedelta
from odoo.tools import __
# import openerp.addons.decimal_precision as dp
from odoo.tools import __

selection_field = fields.Selection
char_field = fields.Char
m2o_field = fields.Many2one
o2m_field = fields.One2many
m2m_field = fields.Many2many
bool_field = fields.Boolean
html_field = fields.Html
text_field = fields.Text
integer_field = fields.Integer
float_field = fields.Float
date_field = fields.Date
datetime_field = fields.Datetime


class air_ticket_type(models.Model):
    _name = 'air.ticket.type'
    _description = "Air ticket type"
    _inherit = ['mail.thread']
    _order = "id desc"
    _rec_name = "policy_name"

    name = fields.Char(_('Code'), readonly=True)
    policy_name = fields.Char(_('Air Ticket Policy Name'), required=True)
    nationality = fields.Selection([('Native', 'Native'),
                                    ('Non-native', 'Non-native'),
                                    ('All Nationalities', '‫All Nationalities‬‬'), ], _('Nationality'), required=True)
    frequency_air_ticket = fields.Selection([('Not allowed', 'Not allowed'),
                                             ('one time each', 'one time each'),
                                             ('One time per contract', 'One time per contract'),
                                             ('Unlimited air tickets based on request condition', 'Unlimited air tickets based on request condition')],
                                            _('Frequency Air Ticket'), required=True)
    number_of_months = fields.Float(_('Each'))
    months_to_request_air_ticket = fields.Integer('The employee is allowed to request air ticket if his balance is greater than')
    maximum_accumulated_balance = fields.Integer('Maximum accumulated balance', default=24)
    air_ticket_class = fields.Selection([('First Class', 'First Class'),
                                         ('Business Class', 'Business Class'),
                                         ('Economic Class', 'Economic Class')], _('Air ticket class'))
    give_cash_instead_tickets = fields.Selection([('Yes', 'Yes'),
                                                  ('No', 'No')], _('allow to give cash to employees instead of tickets'))
    relatives_tickets = fields.Selection([('Allow tickets for relatives', 'Allow tickets for relatives'),
                                          ('Never allow tickets for relatives', 'Never allow tickets for relatives')], _('Relatives Tickets'))
    number_of_wives = fields.Integer('Number Of Wives')
    children = fields.Integer('Number Of Children')
    max_child_age = fields.Integer('Max Age For Children')

    number_of_relatives = fields.Float(_('Number of relatives'), compute='_compute_number_of_relatives')
    notes = fields.Text(_('Notes'))
    state = fields.Selection([('New', 'New'),
                              ('Approved', 'Approved')], string='Status', readonly=True, index=True, copy=False, default='New')
    type = fields.Selection([('annual', 'Annual'), ('non-annual', 'Non-annual')], string='Air ticket Type')
    air_ticket_request_ids = fields.One2many('air.ticket.request', 'air_ticket_type', 'Air ticket requests')
    loan_type_id = fields.Many2one('hr_loans.loan_advance', 'Loan type', help="when an employee request for air ticket, if the company will pay instead of\
    employee, your system will automatically create a loan request using this loan type. ")

    @api.one
    @api.depends('number_of_wives', 'children')
    def _compute_number_of_relatives(self):
        self.number_of_relatives = self.number_of_wives + self.children

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('mits_a_t.air_ticket_type')
        res = super(air_ticket_type, self).create(vals)
        return res

    @api.multi
    def ticket_approve(self):
        for rec in self:
            rec.do_ticket_approve()

    @api.multi
    def do_ticket_approve(self):
        self.write({'state': 'Approved'})
        body = "Ticket Approved"
        self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def ticket_set_new(self):
        self.write({'state': 'New'})
        body = "Ticket Returned to New Status"
        self.message_post(body=body, message_type='email')
        return {}


class air_ticket_request(models.Model):
    _name = 'air.ticket.request'
    _order = "id desc"
    _inherit = ['mail.thread']
    _description = "Air Ticket Request"

    READONLY_STATE = {'approved': [('readonly', True)]}

    name = fields.Char(_('Code'), readonly=True)
    description = fields.Char(_('Description'), required=True, states=READONLY_STATE)
    employee_id = fields.Many2one('hr.employee', _('Employee'), required=True, states=READONLY_STATE,
                                  default=lambda self: self.env.user.employee_ids and self.env.user.employee_ids[0].id)
    branch_id = fields.Many2one('hr.branch', string='Branch', related="employee_id.branch_id", readonly=True, store=True)
    department_id = fields.Many2one('hr.department', string=_('Department'), related="employee_id.department_id", readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string=_('Job Title'), related="employee_id.job_id", readonly=True, store=True)
    country_id = fields.Many2one('res.country', '‫‪Nationality‬‬', related="employee_id.country_id", readonly=True, store=True)
    employee_nationality = fields.Selection(string='Nationality Type', related='employee_id.nationality_type', readonly=True, store=True)
    request_type = fields.Selection([('Annual air ticket', 'Annual air ticket'),
                                     ('Other', 'Other')], _('Request Type'), states=READONLY_STATE)
    contract_id = fields.Many2one('hr.contract', string='Contract', compute="_compute_contract", readonly=True, store=True)
    contract_leave_policy = fields.Many2one('hr.leave.type', _('Contract leave policy'), related="contract_id.annual_leave_policy", readonly=True)
    air_ticket_policy = fields.Many2one('air.ticket.type', string='Annual Air Ticket Policy', related="contract_id.air_ticket_policy", readonly=True)
    # working_months = fields.Char(_('Working months'), related="contract.total_contract_duration")
    cash_allowed = fields.Selection([('Yes', 'Yes'),
                                     ('No', 'No')], _('Cash allowed'), readonly=True, compute="_compute_cash_allowed")
    relatives_tickets = fields.Selection([('Allow tickets for relatives', 'Allow tickets for relatives'),
                                          ('Never allow tickets for relatives', 'Never allow tickets for relatives')], _('Relatives Tickets'), readonly=True,
                                         compute="_compute_relatives_tickets")
    number_of_relatives = fields.Float(_('Number of relatives'), related="contract_id.total_relatives", readonly=True)
    request_reason = fields.Selection([('leave', 'leave'),
                                       ('Air Ticket Cash Allowance', 'Air Ticket Cash Allowance'),
                                       ('Deputation / business trip', 'Business mission'),
                                       ('Final exit', 'Final exit'),
                                       ('Other', 'Other')], _('Air Ticket request reason'), required=True, states=READONLY_STATE)
    reason_detail = fields.Char('air ticket request reason', states=READONLY_STATE)
    leave_request = fields.Many2one('hr.leave', _('Leave Request'), states=READONLY_STATE)
    leave_from = fields.Datetime('Leave start', related='leave_request.date_from', readonly=True)
    leave_to = fields.Datetime('Leave start', related='leave_request.date_to', readonly=True)
    travel_date = fields.Date('Travel date', states=READONLY_STATE)
    leave_request_type_id = fields.Many2one('hr.leave.type', 'Leave request type', related='leave_request.holiday_status_id', readonly=True)
    contract_type_equal_leave_type = fields.Boolean('Contract leave policy equal leave type', compute='get_contract_type_equal_leave_type', store=True)
    air_ticket_type = fields.Many2one('air.ticket.type', 'Air ticket type', states=READONLY_STATE)
    i_want_to = fields.Selection([('Reserve a ticket through company', 'Reserve a ticket through company'),
                                  ('Cash', 'Cash')], _('I want to'), default='Reserve a ticket through company', states=READONLY_STATE)
    reserve_ticket_for = fields.Selection([('Employee only', 'Employee only'),
                                           ('Employee and his relatives', 'Employee and his relatives'),
                                           ('Relatives only', 'Relatives only')], _('Reserve ticket for'), required=True, states=READONLY_STATE)
    ticket_allowance_per_contract = fields.Float('Air ticket allowance as per contract')
    ticket_total_price = fields.Float('Air ticket total price', states=READONLY_STATE)
    company_share = fields.Float('Company share', states=READONLY_STATE)
    employee_share = fields.Float('Employee share', compute="get_employee_share")
    employee_share_method = selection_field([
        ('debit', 'The company will pay instead of employee + Create a Loan'),
        ('cash', 'Cash & bank transfer'),
    ], string="Employee share payment method", states=READONLY_STATE)
    request_date = fields.Date(_('Request date'), required=True, default=lambda s: time.strftime("%Y-%m-%d"), states=READONLY_STATE)
    skip_valid_approve_req = fields.Boolean(_('Skip system Validation And approve this request'), states=READONLY_STATE)
    reviewed_by = fields.Many2one('res.users', _('Reviewed by'), readonly=True)
    reviewed_on = fields.Date('Reviewed On', readonly=True)
    confirmed_by = fields.Many2one('res.users', _('Confirmed by'), readonly=True)
    confirmed_on = fields.Date('Confirmed On', readonly=True)
    air_ticket_details = fields.One2many('air.ticket.details', 'request_id', _('Air Ticket Details'), states=READONLY_STATE)
    state = fields.Selection([
        ('new', 'New request'),
        ('reviewed', 'Data reviewed'),
        ('approved', 'final Approved'),
        ('refused', 'Refused'),
    ], string='Status', default='new', track_visibility='onchange')
    old_tickets_request_ids = m2m_field('air.ticket.request', 'rel_old_air_ticket_request', 'air_ticket_request1', 'air_ticket_requets2', 'Old air tickets')
    note = fields.Html('Notes')
    attachment_ids = fields.One2many('air.ticket.request.attachment', 'source_id', 'Attachments', states=READONLY_STATE)
    id_ = integer_field('id', compute='save_id', store=True)
    wait = bool_field('wait', states=READONLY_STATE)
    expected_return_date = date_field('Expected Return date', compute='get_expected_return_date')
    # developer mode fields (Employee INfo)
    iqama_id = fields.Char('Iqama number', compute='get_employee_info', multi=True)
    iqama_id_ = fields.Char('Iqama number')
    iqama_expiry_date = fields.Date('Iqama Expiry date', compute='get_employee_info', multi=True)
    iqama_expiry_date_ = fields.Date('Iqama Expiry date', states=READONLY_STATE)
    passport_no = fields.Char('Passport Number', compute='get_employee_info', multi=True)
    passport_no_ = fields.Char('Passport Number', states=READONLY_STATE)
    passport_expiry_date = fields.Date('Passport expiry date', compute='get_employee_info', multi=True)
    passport_expiry_date_ = fields.Date('Passport expiry date', states=READONLY_STATE)
    # Smart buttons
    leave_request_ids = o2m_field('hr.leave', 'air_ticket_id', 'Leave requests', states=READONLY_STATE)
    loan_type_id = m2o_field('hr_loans.loan_advance', 'Loan type', related='air_ticket_type.loan_type_id', readonly=True)
    loan_request_id = m2o_field('loan.advance.request', 'Linked Loan request', states=READONLY_STATE)

    current_air_ticket_balance = integer_field('Current air Ticket balance', states=READONLY_STATE)
    deduct = float_field('If this Air Ticket approved, system will deduct', states=READONLY_STATE)
    remaining_balance = float_field('Remaining Balance', states=READONLY_STATE)
    show_remaining = bool_field('Show remaining', states=READONLY_STATE)
    payment_time = selection_field([
        ('now', 'Pay Now'),
        ('with_reconciliation', 'Pay with Leave reconciliation'),
    ], string='Payment time', states=READONLY_STATE)
    paid_through_reconciliation = bool_field('Paid through leave reconciliation', states=READONLY_STATE)

    @api.onchange('request_reason', 'contract_id')
    def leave_set_type(self):
        if self.request_reason in ['leave', 'Air Ticket Cash Allowance']:
            self.air_ticket_type = self.contract_id.air_ticket_policy.id
        else:
            self.air_ticket_type = False

    @api.onchange('i_want_to', 'request_reason')
    def onchange_i_want_to(self):
        payment_time = False
        if self.i_want_to == 'Cash' and self.request_reason != 'leave':
            payment_time = 'now'
        self.payment_time = payment_time

    @api.onchange('employee_id', 'air_ticket_type')
    def get_current_air_ticket_balance(self):
        one_time = self.show_remaining = self.air_ticket_type.frequency_air_ticket == 'one time each' and self.air_ticket_type.type == 'annual'
        self.current_air_ticket_balance = self.employee_id.air_ticket_balance if one_time else 0
        # self.deduct = self.air_ticket_type.number_of_months if one_time else 0
        self.deduct = self.employee_id.air_ticket_balance if one_time else 0
        self.remaining_balance = self.current_air_ticket_balance - self.deduct

    @api.one
    def get_remaining(self):
        self.get_current_air_ticket_balance()
        self._compute_ticket_total_price()

    @api.one
    @api.depends('employee_id')
    def get_employee_info(self):
        self.iqama_id = self.iqama_id_ or self.employee_id.identification_id
        self.iqama_expiry_date = __(self.iqama_expiry_date_) or __(self.employee_id.iqama_expiry_date)
        self.passport_no = self.passport_no_ or self.employee_id.passport_id
        self.passport_expiry_date = __(self.passport_expiry_date_) or __(self.employee_id.passport_expiry_date)

    @api.one
    @api.depends('air_ticket_details')
    def get_expected_return_date(self):
        expected_return_date = False
        for line in self.air_ticket_details:
            if line.check_box and line.relation == 'Employee':
                expected_return_date = (__(line.return_date))
        self.expected_return_date = expected_return_date

    @api.onchange('employee_id')
    def get_old_tickets_request(self):
        old_tickets_request_ids = [(5,)]
        if self.employee_id:
            domain = [['employee_id', '=', self.employee_id.id], ['id_', '!=', self.id_]]
            old_requests = self.search(domain)
            old_tickets_request_ids += [(4, r.id) for r in old_requests]
        self.old_tickets_request_ids = old_tickets_request_ids

    @api.one
    @api.depends('ticket_total_price', 'company_share')
    def get_employee_share(self):
        self.employee_share = self.ticket_total_price - self.company_share
        if self.employee_share <= 0:
            self.employee_share_method = False

    @api.onchange('ticket_total_price')
    def onchange_ticket_total_price(self):
        self.company_share = self.ticket_total_price

    @api.one
    def reset(self):
        self.state = 'new'
        body = "Document reset to new"
        self.message_post(body=body, message_type='email')

    @api.one
    def refuse(self):
        self.state = 'refused'
        body = "Document refused"
        self.message_post(body=body, message_type='email')

    @api.one
    def review(self):
        self.get_remaining()
        self.reviewed_by = self.env.user.id
        self.reviewed_on = datetime.datetime.today().strftime('%Y-%m-%d')
        self.state = 'reviewed'
        body = "Document Reviewed"
        self.message_post(body=body, message_type='email')

    @api.multi
    def approve(self, skip=False, confirm_no_company_share=False):
        # if self.state == 'approved' or self.wait:
        #     raise ValidationError(_("Please wait ..."))
        self.wait = True
        if self.request_reason in ['leave', 'Air Ticket Cash Allowance']:
            holiday_status_id = self.leave_request.holiday_status_id
            air_ticket_frequency = holiday_status_id.allowed_air_ticket_id.frequency_air_ticket
            if air_ticket_frequency == 'Not allowed':
                raise ValidationError(_("Not allowed !!\n\
                    Based on the leave policy, this employee cannot request air ticket for this leave type"))
            if air_ticket_frequency == 'one time each':
                A = self.employee_id.air_ticket_balance
                B = self.air_ticket_type.months_to_request_air_ticket
                D = self.company_share
                self.create_air_ticket_allocation()
            self.skip_validation_and_approve()
        # if self.reserve_ticket_for != 'Relatives only' and not self.expected_return_date:
        #     raise ValidationError(_("Data Error !! \n\
        #         Please select expected return date for ( %s )" % (self.employee_id.name)))
        self.get_remaining()
        self.confirmed_by = self.env.user.id
        self.confirmed_on = datetime.datetime.today().strftime('%Y-%m-%d')

        self.wait = False
        # Employee info
        self.iqama_id_ = self.employee_id.identification_id
        self.iqama_expiry_date_ = __(self.employee_id.iqama_expiry_date)
        self.passport_no_ = self.employee_id.passport_id
        self.passport_expiry_date_ = __(self.employee_id.passport_expiry_date)
        self.state = 'approved'
        body = "Document Approved"
        self.message_post(body=body, message_type='email')

    @api.one
    def create_air_ticket_allocation(self):
        exit_rentry = self.env['air.ticket.balance.allocation'].create({
            'employee_id': self.employee_id.id,
            'allocated_balance': self.air_ticket_type.number_of_months * -1,
            'allocated_date': __(self.travel_date),
            'reason': 'خصم رصيد تذاكر طيران من النظام',
            'auto_create': True,
            'air_ticket_request_id': self.id,
            'confirmed_uid': self.env.user.id,
            'state': 'confirmed',
        })

    @api.multi
    def open_company_share_validate_wizard(self, view_xml_id, A):
        ctx = {'default_air_ticket_request_id': self.id, 'default_a': str(A)}
        return {
            'domain': "[]",
            'name': _('Company share Validate'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'validate.wizard',
            'view_id': self.env.ref(view_xml_id).id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def open_skip_validate_wizard(self, view_xml_id):
        ctx = {'default_air_ticket_request_id': self.id}
        return {
            'domain': "[]",
            'name': _('Skip validate ?'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'validate.wizard',
            'view_id': self.env.ref(view_xml_id).id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def skip_validation_and_approve(self):
        self.leave_request.air_ticket_id = self.id

    @api.onchange('leave_from')
    def onchange_travel_date(self):
        self.travel_date = __(self.leave_from) and __(self.leave_from).split(' ')[0]

    @api.one
    @api.depends('leave_request_type_id', 'contract_leave_policy', 'leave_request')
    def get_contract_type_equal_leave_type(self):
        self.contract_type_equal_leave_type = (
                                                      self.leave_request and self.leave_request_type_id == self.contract_leave_policy) or self.request_reason == 'Air Ticket Cash Allowance'

    @api.onchange('leave_request', 'employee_id', 'request_reason')
    def get_air_ticket_type(self):
        if self.contract_type_equal_leave_type:
            self.air_ticket_type = self.air_ticket_policy.id

    @api.onchange('request_reason', 'employee_id')
    def clear_leave_request(self):
        self.leave_request = False

    # TODO: remove following function
    @api.model_cr
    def init(self):
        self.env.cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, 'request_type'))
        ids = self.search([])
        for rec in self.with_context(dict(self._context, allow_edit=True)).browse(ids):
            rec.save_id()

    @api.model
    def create(self, vals):
        res = super(air_ticket_request, self).create(vals)
        res.name = self.env['ir.sequence'].next_by_code('mits_a_t.air_ticket_request')
        res.save_id()
        return res

    @api.one
    @api.depends()
    def save_id(self):
        if not self.id_:
            self.id_ = self.id

    @api.one
    @api.depends('employee_id')
    def _compute_contract(self):
        for rec in self:
            contracts = self.env['hr.contract'].search([('employee_id', '=', rec.employee_id.id), ('active', '=', True)])
            if len(contracts):
                self.contract_id = contracts[0].id

    @api.onchange('air_ticket_details', 'employee_id', 'request_reason', 'deduct')
    def _compute_ticket_total_price(self):
        total = 0
        if self.request_reason == 'Air Ticket Cash Allowance':
            total = (self.ticket_allowance_per_contract / self.air_ticket_policy.number_of_months) * self.deduct
        else:
            for line in self.air_ticket_details:
                total += line.ticket_price
                if line.check_box and self.request_reason == 'leave' and line.relation == 'Employee' and __(line.departure_date):
                    self.travel_date = __(line.departure_date)
        self.ticket_total_price = total

    @api.one
    @api.depends('air_ticket_policy', 'request_reason')
    def _compute_cash_allowed(self):
        for rec in self:
            if rec.request_reason == 'Air Ticket Cash Allowance':
                rec.cash_allowed = 'Yes'
                rec.i_want_to = 'Cash'
            else:
                if rec.air_ticket_policy and rec.air_ticket_policy.frequency_air_ticket != 'Not allowed':
                    rec.cash_allowed = rec.contract_id.give_cash_instead_tickets
                else:
                    rec.cash_allowed = 'No'

    @api.one
    @api.depends('air_ticket_policy')
    def _compute_relatives_tickets(self):
        for rec in self:
            if rec.air_ticket_policy and rec.air_ticket_policy.frequency_air_ticket != 'Not allowed':
                rec.relatives_tickets = rec.air_ticket_policy.relatives_tickets
            else:
                rec.relatives_tickets = 'Never allow tickets for relatives'

    @api.onchange('cash_allowed')
    def onchange_cash_allowed(self):
        for rec in self:
            if rec.request_reason == 'Air Ticket Cash Allowance':
                rec.i_want_to = 'Cash'
            else:
                if rec.cash_allowed == 'No':
                    rec.i_want_to = 'Reserve a ticket through company'

    @api.onchange('relatives_tickets')
    def onchange_relatives_tickets(self):
        for rec in self:
            if rec.relatives_tickets == 'Never allow tickets for relatives':
                rec.reserve_ticket_for = 'Employee only'
            else:
                rec.reserve_ticket_for = ''

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            # Get details
            vals = []
            for detail in self.air_ticket_details:
                rec = (2, detail.id, False)
                vals.append(rec)
            emp = (0, False, {
                'name': self.employee_id.name,
                'name_in_passport': self.employee_id.name_in_passport,
                'relation': 'Employee',
            })
            vals.append(emp)
            for relative in self.employee_id.relatives:
                relative_vals = (0, False, {
                    'name': relative.name,
                    'name_in_passport': relative.name_in_passport,
                    'date_of_birth': __(relative.date_of_birth),
                    'relation': relative.type,
                })
                vals.append(relative_vals)
            self.air_ticket_details = vals

            # emp = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
            # employee = emp and emp[0] or self.env['hr.employee']
            # employees = self.env['hr.employee'].search([])
            # if not self.employee_id:
            #     self.employee_id = employee.id
            #
            # if self.env.user.has_group('hr.group_hr_user'):
            #     return {'domain': {'employee_id': [('id', 'in', employees.ids)], 'leave_request': [('employee_id', '=', employee.id), ('state', '=', 'validate')]}}
            # elif self.env.user.has_group('saudi_hr_employee.group_hr_department_manager'):
            #     return {'domain': {'employee_id': [('department_id', 'child_of', self.env.user.employee_ids[0].department_id.id)], 'leave_request': [('employee_id', '=', employee.id), ('state', '=', 'validate')]}}
            # elif self.env.user.has_group('saudi_hr_employee.group_hr_direct_manager'):
            #     return {'domain': {'employee_id': [('id', '=', 6)]}}
            # else:
            #     return {'domain': {'employee_id': [('user_id', '=', self.env.user.id)], 'leave_request': [('employee_id', '=', employee.id), ('state', '=', 'validate')]}}

            #
            # if employee and employee.manager:
            #     return {'domain': {'employee_id': [('id', 'in', employees.ids)]}}
            # if not employee:
            #     return {'domain': {'employee_id': [('id', 'in', [])]}}
            # if employee and not employee.manager:
            #     self.employee_id = employee.id
            #     # Get details
            #     vals = []
            #     emp = {
            #         'name': self.employee_id.name,
            #         'relation': 'Employee',
            #     }
            #     vals.append(emp)
            #     for relative in self.employee_id.relatives:
            #         relative_vals = {
            #             'name': relative.name,
            #             'relation': relative.type,
            #         }
            #         vals.append(relative_vals)
            #     self.air_ticket_details = vals
            #     return {'domain': {'employee_id': [('id', '=', employee.id)], 'leave_request': [('employee_id', '=', employee.id), ('state', '=', 'validate')]}}

            # @api.multi
            # def write(self, vals):
            #     if self.state == 'approved' and not self._context.get('allow_edit', False):
            #         raise ValidationError(_("You can not edit while approved"))
            #     return super(air_ticket_request, self).write(vals)

    @api.onchange('employee_id')
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


class air_ticket_details(models.Model):
    _name = 'air.ticket.details'

    request_id = fields.Many2one('air.ticket.request', _('Air Ticket Details'))
    check_box = fields.Boolean(_('Select'))
    name = fields.Char(_('Name'), readonly=True)
    name_in_passport = fields.Char('Name In Passport')
    relation = fields.Char(_('Relation'), readonly=True)
    ticket_type = fields.Selection([('One way', 'One way'),
                                    ('Return', 'Return')], _('Ticket type'))
    departure_date = fields.Date(_('Departure date'))
    departure_airport = fields.Char(_('Departure airport'))
    flight_number = fields.Char(_('Flight number'))
    airlines = fields.Char(_('Airlines'))
    return_date = fields.Date(_('Return date'))
    return_airport = fields.Char(_('Return airport'))
    return_flight_number = fields.Char(_('Return Flight number'))
    return_airlines = fields.Char(_('Airlines'))
    ticket_price = fields.Float(_('Air Ticket Price'))
    notes = fields.Text(_('Notes'))
    date_of_birth = fields.Date('Date Of Birth')
    current_age = fields.Char(string="Current Age", compute="_compute_current_age")

    @api.depends('date_of_birth')
    def _compute_current_age(self):
        for rec in self:
            if rec.date_of_birth:
                fmt = '%Y-%m-%d'
                date_of_birth = datetime.datetime.strptime(__(rec.date_of_birth), fmt)  # start date
                today = datetime.datetime.now()  # end date

                duration = relativedelta(today, date_of_birth)
                current_age = "%s years ,%s months" % (duration.years, duration.months)
                rec.current_age = current_age
            else:
                rec.current_age = 0

    # Clear data from ticket type field if check box = false
    @api.onchange('check_box')
    def _onchange_check_box(self):
        for rec in self:
            if not rec.check_box:
                rec.ticket_type = False
                rec.ticket_price = False
                rec.departure_date = False
                rec.return_date = False

    @api.onchange('check_box', 'ticket_type')
    def get_ticket_price(self):
        if self.check_box and self.ticket_type and not self.ticket_price:
            if self.request_id.employee_id.city_id or self.request_id.employee_id.country_id:
                source = self.request_id.employee_id.city_id or self.request_id.employee_id.country_id
                price = self.ticket_type == 'One way' and source.one_way_price or source.return_price
                price = (
                        self.ticket_type == 'One way' and self.request_id.employee_id.country_id.one_way_price or self.request_id.employee_id.country_id.return_price) if not price else price
            self.ticket_price = price


class Contract(models.Model):
    _inherit = 'hr.contract'

    air_ticket_policy = fields.Many2one('air.ticket.type', string='Annual Air Ticket Policy')
    number_of_wives = fields.Integer('Number Of Wives')
    children = fields.Integer('Number Of Children')
    max_child_age = fields.Integer('Max Age For Children')
    total_relatives = fields.Float('Total relatives included in air tickets', compute='_compute_total')
    give_cash_instead_tickets = fields.Selection([('Yes', 'Yes'),
                                                  ('No', 'No')], _('Allow cash instead of tickets'))
    air_ticket_cash_balance = fields.Float('Air ticket Cash balance', compute='get_air_ticket_cash_balance', store=True)

    @api.one
    @api.depends('employee_id')
    def get_air_ticket_cash_balance(self):
        if self.give_cash_instead_tickets == 'Yes':
            self.air_ticket_cash_balance = self.employee_id.air_ticket_balance_button
        else:
            self.air_ticket_cash_balance = 0

    @api.onchange('air_ticket_policy')
    def change_give_cash_instead_tickets(self):
        self.give_cash_instead_tickets = self.air_ticket_policy.give_cash_instead_tickets

    @api.one
    @api.depends('number_of_wives', 'children')
    def _compute_total(self):
        self.total_relatives = self.number_of_wives + self.children

    @api.onchange('air_ticket_policy')
    def onchange_air_ticket_policy(self):
        if self.air_ticket_policy.relatives_tickets == 'Allow tickets for relatives' and self.marital == 'married':
            self.number_of_wives = self.air_ticket_policy.number_of_wives
            self.children = self.air_ticket_policy.children
            self.max_child_age = self.air_ticket_policy.max_child_age

    @api.onchange('marital')
    def onchange_marital(self):
        if self.marital != 'married':
            self.number_of_wives = 0
            self.children = 0
            self.max_child_age = 0

    @api.onchange('nationality')
    def onchange_nationality(self):
        self.annual_leave_policy = False

    @api.onchange('employee_id')
    def onchange_air_ticket_policy_employee(self):
        self.air_ticket_policy = False

    @api.onchange('nationality_type')
    def onchange_employee_id(self):
        for rec in self:
            if rec.nationality_type == "Non-native":
                return {'domain': {'nationality_type': [('nationality', '=', 'Non-native'), ('state', '=', 'Approved')]}}
            if rec.nationality_type == "Native":
                return {'domain': {'nationality_type': [('nationality', '=', 'Native'), ('state', '=', 'Approved')]}}


class air_ticket_for_leave_type(models.Model):
    _inherit = 'hr.leave.type'

    allowed_air_ticket_id = fields.Many2one('air.ticket.type', 'Allowed air ticket')

    @api.onchange('nationality', 'can_request_air_ticket')
    def clear_allowed_air_ticket_id(self):
        self.allowed_air_ticket_id = False


class hr_holiday(models.Model):
    _inherit = "hr.leave"

    annual_air_ticket_policy_id = fields.Many2one('air.ticket.type', 'Annual air ticket policy', compute='get_annual_air_ticket_policy')
    allow_to_request_air_ticket = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Allow to request air ticket',
                                                   compute='get_allow_to_request_air_ticket')
    create_air_ticket_request = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Create air ticket request for this leave")
    air_ticket_id = fields.Many2one('air.ticket.request', string="Linked Air-Ticket")

    @api.one
    @api.depends('contract_id')
    def get_annual_air_ticket_policy(self):
        self.annual_air_ticket_policy_id = self.contract_id.air_ticket_policy

    @api.one
    @api.depends('holiday_status_id')
    def get_allow_to_request_air_ticket(self):
        self.allow_to_request_air_ticket = self.holiday_status_id.can_request_air_ticket

    @api.onchange('allow_to_request_air_ticket')
    def onchange_allow_to_request_air_ticket(self):
        if not self._context.get('default_create_air_ticket_request', False):
            if self.allow_to_request_air_ticket == 'no':
                self.create_air_ticket_request = 'no'
            else:
                self.create_air_ticket_request = False


class SkipValidate(models.TransientModel):
    _name = 'validate.wizard'
    air_ticket_request_id = fields.Many2one('air.ticket.request', 'Air ticket request')
    total_price = float_field('Total air ticket price', related='air_ticket_request_id.ticket_total_price', readonly=True)
    company_share = float_field('Company share', related='air_ticket_request_id.company_share', readonly=True)
    a = integer_field('A', related='air_ticket_request_id.employee_id.air_ticket_balance', readonly=True)
    aa = integer_field('A', related='a', readonly=True)

    @api.multi
    def approve_air_ticket(self):
        air_ticket_request = self.env['air.ticket.request'].browse(self._context.get('default_air_ticket_request_id', False))
        air_ticket_request.approve(skip=True)

    @api.multi
    def confirm_company_share(self):
        ctx = dict(self._context, default_air_ticket_request_id=self._context.get('default_air_ticket_request_id', False))
        self.with_context(ctx).air_ticket_request_id.approve(confirm_no_company_share=True)


class AirTicketBalanceAllocation(models.Model):
    _name = "air.ticket.balance.allocation"
    _inherit = ['mail.thread']
    _description = "Air ticket balance allocation"
    _rec_name = "employee_id"
    _order = "id desc"

    employee_id = m2o_field('hr.employee', 'Employee')
    allocated_balance = integer_field('Allocated balance')
    allocated_date = date_field('Allocated date')
    adjusted_date = date_field('Adjusted date', related='employee_id.contract_id.adjusted_date', readonly=True)
    last_allocation_date = date_field('Last allocation date', compute='get_last_allocation_date')
    last_allocation_date_ = date_field('Last allocation date', )
    reason = char_field('Reason')
    auto_create = bool_field('Created automatically')
    air_ticket_auto_allocation_id = m2o_field('air.ticket.automatic.allocation', 'Air ticket automatic allocation')
    air_ticket_request_id = m2o_field('air.ticket.request', 'Air ticket request')
    confirmed_uid = m2o_field('res.users', 'Confirmed by')
    note = html_field('Notes')
    attachment_ids = o2m_field('air.ticket.balance.attachment', 'air_ticket_balance_id', 'Attachments')
    state = selection_field([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
    ], 'Status', default='new', track_visibility='always')
    by_eos = fields.Boolean('Through EOS')

    @api.one
    @api.depends()
    def get_last_allocation_date(self):
        self.last_allocation_date = __(self.last_allocation_date_) or __(self.employee_id.last_reconciliation_date)

    @api.one
    def reverse_allocation(self):
        raise ValidationError(_("If you want to reverse the effect for this air ticket allocation, you have to manually create a new air ticket allocation with\
         a minus or positive value ( based on the condition)\nUse minus to reduce air ticket balance, use positive values to increase air ticket balance."))

    @api.one
    def confirm(self):
        self.last_allocation_date_ = __(self.employee_id.last_reconciliation_date)
        self.state = 'confirmed'
        self.confirmed_uid = self.env.user.id
        self.employee_id.contract_id.get_air_ticket_cash_balance()

    @api.onchange('employee_id')
    def clear_balance(self):
        self.allocated_balance = False


class AirTicketBalanceAttachment(models.Model):
    _name = "air.ticket.balance.attachment"
    _description = "Air ticket balance allocation Attachment"

    air_ticket_balance_id = fields.Many2one('air.ticket.balance.allocation', 'Job')
    name = fields.Char('Name')
    file = fields.Binary('File', attachment=True, )
    file_name = fields.Char('File name')
    note = fields.Char('Notes')


class AirTicketRequestAttachment(models.Model):
    _name = "air.ticket.request.attachment"

    air_ticket_request_id = fields.Many2one('air.ticket.request', 'Air ticket request')
    source_id = fields.Many2one('air.ticket.request', 'Air ticket request')

    file = fields.Binary('File', attachment=True, )
    file_name = fields.Char('File name')
    name = fields.Char('Description')
    note = fields.Char('Notes')


class AirTicketAutomaticAllocation(models.Model):
    _name = "air.ticket.automatic.allocation"
    _description = "Air Ticket Automatic Allocation"
    _inherit = ['mail.thread']
    _rec_name = "allocate_till_date"
    _order = "id desc"

    code = char_field('code')
    allocate_till_date = date_field('Allocate till this date')
    confirmed_uid = m2o_field('res.users', 'Confirmed by')
    note = html_field('Notes')
    state = selection_field([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='new', track_visibility='onchange')
    allocation_ids = o2m_field('air.ticket.balance.allocation', 'air_ticket_auto_allocation_id', 'Balance allocations')

    @api.model
    def action_create_allocation(self):
        allocation = self.create({
            'name': 'leave automatic allocation / All leaves',
            'allocate_till_date': datetime.datetime.today().strftime('%Y-%m-%d'),
        })
        allocation.confirm()

    @api.one
    def confirm(self):
        for employee in self.env['hr.employee'].search([]):
            a_date = max([__(employee.last_reconciliation_date), __(employee.contract_id.adjusted_date)])
            b_date = __(self.allocate_till_date)
            if not employee.contract_id.id or not a_date or a_date >= b_date: continue
            if employee.contract_id.air_ticket_policy.frequency_air_ticket == 'Not allowed':
                continue
            a_datetime = datetime.datetime.strptime(a_date, "%Y-%m-%d")
            b_datetime = datetime.datetime.strptime(b_date, "%Y-%m-%d")
            a_day = a_datetime.day
            b_day = b_datetime.day
            if a_day == b_day:
                z_months = abs(b_datetime.month - a_datetime.month)
                if z_months == 0: continue
                self.create_new_allocation(z_months, b_date, employee)
            if a_day != b_day:
                diff_day = a_day - b_day
                diff_month = 0 if b_day >= a_day else -1
                b_datetime += relativedelta(months=diff_month, days=diff_day)
                duration = relativedelta(b_datetime, a_datetime)
                z_months = duration.months + (duration.years * 12)
                if b_datetime > a_datetime:
                    self.create_new_allocation(z_months, b_datetime.strftime("%Y-%m-%d"), employee)
        self.state = 'confirmed'

    @api.one
    def create_new_allocation(self, months, date, employee):
        maximum_accumulated_balance = employee.contract_id.air_ticket_policy.maximum_accumulated_balance
        air_ticket_balance_remaining = maximum_accumulated_balance - employee.air_ticket_balance
        balance = min([months, air_ticket_balance_remaining])

        self.env['air.ticket.balance.allocation'].create({
            'employee_id': employee.id,
            'allocated_balance': balance,
            'allocated_date': date,
            'reason': 'توزيع رصيد تذاكر طيران تلقائى من النظام',
            'auto_create': True,
            'air_ticket_auto_allocation_id': self.id,
            'confirmed_uid': self.env.user.id,
            'state': 'confirmed',
            'last_allocation_date_': __(employee.last_reconciliation_date)
        })

    @api.model
    def create(self, vals):
        res = super(AirTicketAutomaticAllocation, self).create(vals)
        res.code = self.env['ir.sequence'].next_by_code(self._name)
        return res

    @api.one
    def unlink(self):
        if self.state == 'confirmed':
            raise ValidationError(_("Can not delete a confirmed Air ticket allocation."))
        return super(AirTicketAutomaticAllocation, self).unlink()


class Employee(models.Model):
    _inherit = "hr.employee"
    air_ticket_balance = integer_field('Air ticket allocation balance', compute='get_air_ticket_balance')
    air_ticket_balance_button = fields.Float('Air ticket allocation balance', compute='get_air_ticket_balance')
    last_reconciliation_date = fields.Date('Last  Air Ticket Reconciliation Date', compute='get_last_ait_ticket_allocation_date')
    air_ticket_cash_allowance = fields.Char('Air ticket cash allowance', compute='get_last_ait_ticket_allocation_date',
                                            search='_search_air_ticket_cash_allowance')

    def _search_air_ticket_cash_allowance(self, operator, value):
        id_list = []
        employees = self.env['hr.employee'].search([])
        for employee in employees:
            if employee.contract_id and employee.contract_id.give_cash_instead_tickets == 'Yes':
                id_list.append(employee.id)
        return [('id', 'in', id_list)]

    @api.one
    @api.depends('contract_id.air_ticket_policy.frequency_air_ticket', 'contract_id.air_ticket_policy.number_of_months')
    def get_air_ticket_balance(self):
        if not self.contract_id or not self.contract_id.air_ticket_policy:
            self.air_ticket_balance = 0
            self.air_ticket_balance_button = 0
        else:
            frequency_air_ticket = self.contract_id.air_ticket_policy.frequency_air_ticket
            if frequency_air_ticket in ['Not allowed', 'One time per contract']:
                self.air_ticket_balance = 0
                self.air_ticket_balance_button = 0
            if frequency_air_ticket == 'one time each':
                allocations = self.env['air.ticket.balance.allocation'].search([
                    ['employee_id', '=', self.id],
                    ['state', '=', 'confirmed'],
                ], order='allocated_date desc')
                total_allocation = sum([a.allocated_balance for a in allocations])
                maximum_accumulated_balance = self.contract_id.air_ticket_policy.maximum_accumulated_balance
                self.air_ticket_balance = min([total_allocation, maximum_accumulated_balance])
                if self.contract_id.air_ticket_policy.number_of_months:
                    self.air_ticket_balance_button = round(
                        min([total_allocation, maximum_accumulated_balance]) / self.contract_id.air_ticket_policy.number_of_months, 2)
                else:
                    self.air_ticket_balance_button = 0
            if frequency_air_ticket == 'Unlimited air tickets based on request condition':
                self.air_ticket_balance = 1000
                self.air_ticket_balance_button = 1000

    @api.one
    @api.depends()
    def get_last_ait_ticket_allocation_date(self):
        allocations = self.env['air.ticket.balance.allocation'].search([
            ['employee_id', '=', self.id],
            ['state', '=', 'confirmed'],
        ], order='allocated_date desc')
        # ['allocated_balance', '>', 0]
        if allocations:
            self.last_reconciliation_date = __(allocations[0].allocated_date)

    @api.multi
    def open_air_ticket_allocations(self):
        return {
            'domain': [['employee_id', '=', self.id]],
            'name': _('Air ticket balance allocation'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'air.ticket.balance.allocation',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'default_employee_id': self.id}
        }


class Countries(models.Model):
    _inherit = "res.country"

    one_way_price = fields.Float('One way price')
    return_price = fields.Float('Return price')


class res_country_state(models.Model):
    _inherit = "res.country.state"

    one_way_price = fields.Float('One way price')
    return_price = fields.Float('Return price')
