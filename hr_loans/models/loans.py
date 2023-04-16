# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError, QWebException
from dateutil.relativedelta import relativedelta
import calendar
import time
from odoo.tools import __


# import openerp.addons.decimal_precision as dp

class loan_advance(models.Model):
    _name = 'hr_loans.loan_advance'
    _inherit = ['mail.thread', 'hr_loans.loan_advance']
    _description = "Loan Type"

    name = fields.Char(_('Loan / advance description'), required=True)
    type = fields.Selection([('Loan', 'Loan'),
                             ('Salary In Advance', 'Salary In Advance')], _('Loan / Advance Type'), required=True, default='Loan')
    maximum_amount = fields.Selection([('Unlimited', 'Unlimited'),
                                       ('Fixed Amount', 'Fixed Amount'),
                                       ('Based On Basic Salary', 'Based On Basic Salary'),
                                       ('Based On Total Salary', 'Based On Total Salary'), ], _('Maximum Amount'), required=True,
                                      help="Determine maximum amount which is allowed for this loan / advance")
    amount = fields.Float(_('Amount'))
    number_of_months = fields.Float(_('Number of Months'))
    gm_exceeds = fields.Float(_('GM Must approve if the amount exceeds'))
    notes = fields.Text(_('Notes'))

    state = fields.Selection([
        ('New', 'New'),
        ('Confirmed', 'Confirmed'),
    ], string='Status', readonly=True, index=True, copy=False, default='New', )
    is_installment = fields.Boolean('Installments For Each Loan', compute='_compute_is_installment')
    default_installment_number = fields.Integer('Default Number Of Installment')
    for_air_ticket = fields.Boolean('Used for Air tickets')

    # /////////////////// Smart Buttons /////////////////////////////////////////////////////////////
    count_loan_requests = fields.Float('Number of loan/advance requests', compute='get_count_smart_buttons')


    @api.one
    def get_count_smart_buttons(self):
        self.count_loan_requests = self.env['loan.advance.request'].search_count([('loan_type', '=', self.id)])

    @api.multi
    def open_loan_requests(self):
        return {
            'domain': [('loan_type', '=', self.id)],
            'name': _('Loan / Advance Requests'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'loan.advance.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }
    # ///////////////////////////////////////////////////////////////////////////////////////////////////

    @api.one
    @api.depends('type')
    def _compute_is_installment(self):
        self.is_installment = True

    @api.constrains('amount', 'number_of_months')
    def _check_maximum_amount(self):
        if self.maximum_amount == 'Fixed Amount' and self.amount == 0:
            raise exceptions.ValidationError("Configuration error!! Fixed amount cannot be equal to zero")
        if self.maximum_amount in ['Based On Basic Salary', 'Based On Total Salary'] and self.number_of_months == 0:
            raise exceptions.ValidationError("Configuration error!! Number of months cannot be equal to zero")

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state == 'Confirmed':
                raise exceptions.ValidationError(_("Not allowed to delete a confirmed loan type !!"))
        return super(loan_advance, self).unlink()

    @api.multi
    def action_confirm(self):
        for record in self:
            # Fixme: uncomment 
            # if record.is_installment and record.type == 'Loan' and record.default_installment_number <= 0:
            #     raise exceptions.ValidationError(_("Data error !! Invalid default number of installments.!"))
            if record.is_installment and record.type == 'Loan' and record.default_installment_number > 60:
                raise exceptions.ValidationError(_("Default number of installments can not be greater than 60"))
            record.write({'state': 'Confirmed'})
            body = "Document Confirmed"
            self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def action_set_new(self):
        for record in self:
            record.write({'state': 'New'})
            body = "Document Set To New"
            self.message_post(body=body, message_type='email')
        return {}

    @api.onchange('maximum_amount')
    def onchange_maximum_amount(self):
        for rec in self:
            if rec.type != "Salary In Advance":
                rec.number_of_months = 0

    @api.onchange('type')
    def onchange_type(self):
        for rec in self:
            if rec.type == "Salary In Advance":
                rec.maximum_amount = 'Based On Total Salary'
                rec.number_of_months = 1
                rec.for_air_ticket = False
            else:
                rec.maximum_amount = False
                rec.number_of_months = 0


class loan_advance_tag(models.Model):
    _name = 'hr_loans.loan_advance_tag'
    _description = "Loan Type Tag"

    name = fields.Char(_('Tag Name'), required=True)


class loan_advance_request(models.Model):
    _name = 'loan.advance.request'
    _inherit = ['mail.thread', 'loan.advance.request']
    _description = "Loan Request"
    _order = "id desc"

    name = fields.Char(_('Code'), readonly=True)
    reason = fields.Char(_('loan / advance reason'), required=True)
    loan_type = fields.Many2one('hr_loans.loan_advance', string=_('loan / advance type'), required=True, domain=[('state', '=', 'Confirmed')])
    type = fields.Selection([('Loan', 'Loan'),
                             ('Salary In Advance', 'Salary In Advance')], _('Type'), default="Loan")
    loan_date_from = fields.Date()
    loan_date_to = fields.Date()
    tag_ids = fields.Many2many('hr_loans.loan_advance_tag', 'loan_tag_rel', 'loan_id', 'tag_id', _('Tags'))
    date = fields.Date(_('loan / advance date'), default=lambda s: datetime.now().strftime("%Y-%m-%d"), required=True)
    employee_id = fields.Many2one('hr.employee', string=_('Employee'), default=lambda self: self.env.user.employee_ids and self.env.user.employee_ids[0].id)
    department_id = fields.Many2one('hr.department', string=_('Department'), related="employee_id.department_id", readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string=_('Job Title'), related="employee_id.job_id", readonly=True, store=True)
    contract_id = fields.Many2one('hr.contract', string=_('Contract'), compute="_compute_contract", readonly=True, store=True)
    contract_start = fields.Date(string=_('Contract Duration'), related="contract_id.date_start", readonly=True)
    contract_end = fields.Date(string=_('Contract End'), related="contract_id.date_end", readonly=True)
    loan_amount = fields.Float(string=_('Requested Loan Amount'))
    hr_manager_approval = fields.Float(string=_('HR Manager Approval'))
    financial_manager_approval = fields.Float(string=_('Financial Manager Approval'))
    general_manager_approval = fields.Float(string='CEO / GM approval')
    paid_amount = fields.Float(string=_('Loan paid amount'))
    remaining_amount = fields.Float(string=_('remaining amount'), compute="_compute_remaining_amount")
    requested_by = fields.Many2one('res.users', default=lambda self: self.env.uid, readonly=True)
    notes = fields.Text(string=_('Notes'))
    state = fields.Selection([
        ('New', 'New'),
        ('Payroll Officer Approval', 'Payroll Officer Approval'),
        ('HR Manager Approve', 'HR Manager Approve'),
        ('Financial Manager Approve', 'Financial Manager Approve'),
        ('GM Approve', 'CEO / GM approval'),
        ('Loan Fully Paid', 'Loan Fully Paid'),
        ('Refused', 'Refused'),
    ], string='Status', readonly=True, index=True, default='New', )
    linked_air_ticket_id = fields.Many2one('air.ticket.request', 'Linked air ticket')
    loan_remaining = fields.Float(string=_('Loan Remaining'), related="contract_id.remaining_amount", readonly=True)
    another_loan_before_pay = fields.Boolean('The employee can request another loan before fully pay the old one',
                                             default=lambda self: self._default_another_loan_before_pay())
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

    month = fields.Selection(_PERIOD, _('Month'), compute="_compute_month_year")
    year = fields.Integer(_('Year'), compute="_compute_month_year")
    payslip_id = fields.Many2one('hr.payslip', 'Payslip')
    attachment_ids = fields.One2many('loan.advance.request.attaches', 'request_id', 'Attachments')
    expected_payment = fields.Date('Expected Payment To Employee')
    country_id = fields.Many2one('res.country', 'Nationality', related='employee_id.country_id', readonly=True, store=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender', related='employee_id.gender', readonly=True, store=True)
    is_installment = fields.Boolean('Installments For Each Loan', compute='_compute_is_installment')
    installment_number = fields.Integer('Number Of Installment')
    installment_start_month = fields.Selection(_PERIOD, _('Start Deduction From - Month'))
    installment_start_year = fields.Integer(_('Start Deduction From - Year'))
    installment_ids = fields.One2many('loan.installment', 'loan_request_id', 'Installments Details')
    hr_reason = fields.Char('HR Reason To reduce Loan request')
    show_hr_reason = fields.Boolean('Show Hr Reason' , compute='_compute_reason')
    financial_reason = fields.Char('Financial Reason To reduce Loan request', compute='_compute_reason')
    show_financial_reason = fields.Boolean('Show Hr Reason' , compute='_compute_reason')
    branch_id = fields.Many2one('hr.branch', string='Branch', related="employee_id.branch_id", readonly=True, store=True)
    reversed_reward = fields.Many2one('hr.employee.rewards', 'Reward')
    reversed = fields.Boolean('Reversed')


    @api.onchange('expected_payment')
    def onchange_expected_payment(self):
        if self.expected_payment and not (self.installment_start_month and self.installment_start_year):
            expected_payment = datetime.strptime(__(self.expected_payment), "%Y-%m-%d")
            self.installment_start_month = expected_payment.strftime("%m")
            self.installment_start_year = expected_payment.strftime('%Y')

    @api.onchange('type')
    def onchange_type(self):
        for rec in self:
            rec.loan_type = False

    @api.onchange('type','employee_id')
    def onchange_type_employee_id(self):
        for rec in self:
            if rec.type == 'Salary In Advance':
                if rec.contract_id:
                    rec.loan_amount = rec.contract_id.total
                    rec.hr_manager_approval = rec.contract_id.total
                    rec.financial_manager_approval = rec.contract_id.total
                    rec.general_manager_approval = rec.contract_id.total
            else:
                rec.loan_amount = 0
                rec.hr_manager_approval = 0
                rec.financial_manager_approval = 0
                rec.general_manager_approval = 0

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

    @api.onchange('loan_type', 'employee_id')
    def get_installment_number(self):
        self.installment_number = 1

    @api.onchange('loan_type', 'employee_id', 'expected_payment')
    def get_month_year(self):
        if self.loan_type.type == "Loan" and self.is_installment:
            if self.expected_payment:
                fmt = '%Y-%m-%d'
                expected_payment = datetime.strptime(__(self.expected_payment), fmt)
                self.installment_start_month = expected_payment.strftime('%m')
                self.installment_start_year = expected_payment.strftime('%Y')

    @api.one
    @api.constrains('installment_number')
    def _check_installment_number(self):
        if self.installment_number < 0 :
            raise exceptions.ValidationError(_("Number Of Installment cannot be Minus"))

    @api.one
    @api.constrains('year','installment_start_year')
    def _check_years(self):
        if self.installment_start_year < 0 :
            raise exceptions.ValidationError(_("Start Deduction From - Year cannot be Minus"))
        if self.year < 0 :
            raise exceptions.ValidationError(_("Year cannot be Minus"))

    @api.constrains('type', 'loan_amount')
    def _check_type(self):
        if self.type == 'Loan':
            if self.loan_amount == 0:
                raise exceptions.ValidationError(_("Loan Amount cannot be equal to zero"))

    @api.constrains('employee_id','loan_amount','another_loan_before_pay','loan_type')
    def _check_employee(self):
        # Check for Employee
        employee = self.employee_id
        if not employee:
            raise exceptions.ValidationError(
                " Not allowed!! This user is not linked with any employee. To continue this request, you must go to employee window, and link between the employee and this user. Don’t forget to flag (is a manager) field if you want this employee to request loans for other staff.")
        if not self.employee_id:
            raise exceptions.ValidationError(_("Please Select Employee"))
        # Check for Employee Contract
        if not self.contract_id:
            raise exceptions.ValidationError(_("Configuration error!! This employee didn’t have an active contract"))
        # Check for Employee Can request loan
        if not employee.request_loan:
            raise exceptions.ValidationError(_("Not allowed!! This employee is not allowed to request for any loans / salary in advance"))
        # Check for Requested amount
        if self.type == 'Loan':
            if self.loan_amount <= 0:
                raise exceptions.ValidationError(_("Configuration error!! Requested loan amount cannot be zero or negative amount."))
            if self.contract_id.remaining_amount > 0 and not self.another_loan_before_pay:
                    error_msg = "Dear \n You are not allowed to request / approve this loan request because this employee have old loans which not paid ( %s ) .For more details, go to employee contract then Loans Based on your company policy, you are not allowed to request any new loans before fully pay the old ones. " % (self.contract_id.remaining_amount)
                    raise ValidationError(_(error_msg))
            # Check Max Amount
            maximum_amount = self.loan_type.maximum_amount
            if maximum_amount == 'Fixed Amount':
                fixed_amount = self.loan_type.amount
                if self.loan_amount > fixed_amount:
                    raise exceptions.ValidationError(_("Amount error!! You requested an amount greater than the amount allowed based on your company policy"))
            if maximum_amount == 'Based On Basic Salary':
                number_of_months = self.loan_type.number_of_months
                basic_salary = self.contract_id.basic_salary
                based_basic_amount = number_of_months * basic_salary
                if self.loan_amount > based_basic_amount:
                    raise exceptions.ValidationError(_("Amount error!! You requested an amount greater than the amount allowed based on your company policy"))
            if maximum_amount == 'Based On Total Salary':
                number_of_months = self.loan_type.number_of_months
                total_salary = self.contract_id.total
                based_total_amount = number_of_months * total_salary
                if self.loan_amount > based_total_amount:
                    raise exceptions.ValidationError(_("Amount error!! You requested an amount greater than the amount allowed based on your company policy"))


    @api.one
    @api.depends('hr_manager_approval','financial_manager_approval')
    def _compute_reason(self):
        if self.hr_manager_approval > 0 and self.hr_manager_approval < self.loan_amount:
            self.show_hr_reason = True
        if self.financial_manager_approval > 0 and self.financial_manager_approval < self.loan_amount:
            self.show_financial_reason = True


    @api.one
    @api.depends('employee_id')
    def _compute_is_installment(self):
        self.is_installment = True


    @api.depends('date')
    def _compute_month_year(self):
        for rec in self:
            loan_date = datetime.strptime(__(rec.date), "%Y-%m-%d")
            rec.month = loan_date.strftime("%m")
            rec.year = loan_date.strftime('%Y')

    @api.multi
    def open_old_loans(self):
        return {
            'domain': [('employee_id', '=', self.employee_id.id),('state', '=', 'GM Approve')],
            'name': _('Old Loans'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'loan.advance.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {"search_default_loan_request_loan":1}
        }

    @api.depends('employee_id')
    def _compute_contract(self):
        for rec in self:
            rec.branch_id = rec.employee_id.branch_id
            rec.department_id = rec.employee_id.department_id
            rec.job_id = rec.employee_id.job_id
            rec.country_id = rec.employee_id.country_id
            rec.gender = rec.employee_id.gender

            contracts = self.env['hr.contract'].search([('employee_id', '=', rec.employee_id.id), ('active', '=', True)])
            if len(contracts):
                rec.contract_id = contracts[0].id

            # Get Old Loans
            if not rec.id:
                old_loans = self.env['loan.advance.request'].search([('employee_id', '=', rec.employee_id.id)])
            else:
                old_loans = self.env['loan.advance.request'].search([('employee_id', '=', rec.employee_id.id), ('id', '!=', rec.id)])
            rec.request_ids = old_loans

    def _default_another_loan_before_pay(self):
        return True

    @api.depends('general_manager_approval', 'paid_amount')
    def _compute_remaining_amount(self):
        for rec in self:
            self.remaining_amount = self.general_manager_approval - self.paid_amount

    @api.one
    def action_officer_approve(self):
        self.state = 'Payroll Officer Approval'
        body = "Document Approved By Hr Officer"
        self.message_post(body=body, message_type='email')

    @api.multi
    def action_hr_approve(self):
        for record in self:
            if record.type == 'Loan':
                if record.hr_manager_approval <= 0 or record.hr_manager_approval > record.loan_amount:
                    raise exceptions.ValidationError(
                        _("Amount error! Hr approval amount must be greater than zero and less than or equal to the request loan amount."))
            record.write({'state': 'HR Manager Approve'})
            body = "Document Approved By Hr Manager"
            self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def action_financial_approve(self):
        for record in self:
            if record.type == 'Loan':
                if record.financial_manager_approval <= 0 or record.financial_manager_approval > record.loan_amount:
                    raise exceptions.ValidationError(
                        _("Amount error! Financial approval amount must be greater than zero and less than or equal to the request loan amount."))
            record.write({'state': 'Financial Manager Approve'})
            body = "Document Approved By Financial Manager"
            self.message_post(body=body, message_type='email')

            if record.type == 'Salary In Advance':
                record.write({'state': 'GM Approve'})
                body2 = "Document Status changed to General Manager Approve"
                self.message_post(body=body2, message_type='email')

        return {}

    @api.multi
    def action_gm_approve(self):
        for record in self:
            if record.type == 'Loan':
                if record.general_manager_approval <= 0 or record.general_manager_approval > record.loan_amount:
                    raise exceptions.ValidationError(
                        _(
                            "Amount error! Genral Manager approval amount must be greater than zero and less than or equal to the request loan amount."))
            if record.loan_type.type == "Loan" and record.is_installment:
                if not record.installment_ids:
                    record.generate_installment()
                record.gm_installment_validation()
            record.write({'state': 'GM Approve'})
            body = "Document Approved By General Manager"
            self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def action_cancel_loan(self):
        for record in self:
            for lines in record.installment_ids:
                if lines.remaining > 0:
                    lines.state = 'Refused'
            # record.state = 'cancelled'

    @api.multi
    def action_refuse(self):
        for record in self:
            if record.state == 'GM Approve':
                raise ValidationError("Not allowed !!")
            else:
                record.action_refuse_confirm()

    @api.one
    def action_refuse_confirm(self):
        self.state = 'Refused'
        body = "Document Refused"
        self.message_post(body=body, message_type='email')

    #  @api.onchange('employee_id')
    # def get_employee_domain(self):
    #     employees = self.env['hr.employee'].search([])
    #
    #     if self.env.user.has_group('hr.group_hr_user'):
    #         return {'domain': {'employee_id': [('id', 'in', employees.ids)]}}
    #     elif self.env.user.has_group('saudi_hr_employee.group_hr_department_manager'):
    #         return {'domain': {'employee_id': [('department_id', 'in',  self.env['hr.department'].search(
    #             [('manager_id.user_id', '=', self.env.user.id)]) )]}}
    #     elif self.env.user.has_group('saudi_hr_employee.group_hr_direct_manager'):
    #         return {'domain': {'employee_id': [('id', 'child_of', self.env.user.employee_ids.ids)]}}
    #     else:
    #         return {'domain': {'employee_id': [('user_id', '=', self.env.user.id)]}}

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].sudo().next_by_code('loan.advance.request')
        res = super(loan_advance_request, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        # Write your logic here
        for rec in self:
            if 'state' in vals:
                for installment in rec.installment_ids:
                    installment.state = vals['state']
        res = super(loan_advance_request, self).write(vals)
        # Write your logic here
        return res

    @api.one
    def gm_installment_validation(self):
        if not self.expected_payment:
            message = "Attention !! \n You forget to select the date which the employee will receive the approved amount"
            raise ValidationError(message)
        if self.installment_ids:
            total_installment = 0
            for line in self.installment_ids:
                total_installment += line.monthly_installment

    @api.one
    def generate_installment(self):
        if self.installment_number <= 0:
            message = "Not allowed!! \n cannot Auto generate installments because number of installments which you insert is incorrect."
            raise ValidationError(message)
        if not (self.installment_start_month and self.installment_start_year):
            self.get_month_year()
        if not (self.installment_start_month and self.installment_start_year):
            message = "Attention !! \n Your system can not find the starting month to create installment, kindly select the (Start Deduction From - Month and year)."
            raise ValidationError(message)
        # ////////////////// Delete Old Lines if no paid lines ////////////////////////////////
        if self.installment_ids:
            for line in self.installment_ids:
                if line.paid != 0:
                    message = "Not allowed!! \n Our Historical data indicates that you already deducted some installments from employee salary, Auto generate installments is not allowed in this case, you can do it manually by trying to edit / remove / add new installment lines."
                    raise ValidationError(message)

            for line in self.installment_ids:
                line.unlink()
        # //////////////// Generate Lines ////////////////////////////////////////////////////
        month = self.installment_start_month
        year = self.installment_start_year
        lines = []
        loan_amount = self.loan_amount
        if self.general_manager_approval != 0:
            loan_amount = self.general_manager_approval
        elif self.financial_manager_approval != 0:
            loan_amount = self.financial_manager_approval
        elif self.hr_manager_approval != 0:
            loan_amount = self.hr_manager_approval
        division_remaining = loan_amount % self.installment_number
        monthly_installment = (loan_amount - division_remaining) / self.installment_number
        last_month_installment = monthly_installment + division_remaining
        for x in range(0, self.installment_number):
            start_end = calendar.monthrange(year, int(month))
            deduction_date = str(year) + '-' + month + '-' + str(start_end[1])
            if x == self.installment_number - 1:
                res = {
                    'employee_id': self.employee_id.id,
                    'loan_request_id': self.id,
                    'month': month,
                    'year': year,
                    'deduction_date': deduction_date,
                    'monthly_installment': last_month_installment,
                }
            else:
                res = {
                    'employee_id': self.employee_id.id,
                    'loan_request_id': self.id,
                    'month': month,
                    'year': year,
                    'deduction_date': deduction_date,
                    'monthly_installment': monthly_installment,
                }
            lines.append(res)
            # //////  Get next Month , Year /////////////////////////
            next_month_year = self.get_next_month_year(month, year)[0]
            month = next_month_year['month']
            year = next_month_year['year']

        for installment in lines:
            self.env['loan.installment'].create(installment)

    @api.one
    def get_next_month_year(self, month, year):
        if month == '12':
            return {'month': '01', 'year': year + 1}
        elif month in ['09', '10', '11']:
            return {'month': str(int(month) + 1), 'year': year}
        else:
            return {'month': '0' + str(int(month) + 1), 'year': year}


class LoanRequestAttaches(models.Model):
    _name = "loan.advance.request.attaches"
    _description = "Loan Request Attaches"

    request_id = fields.Many2one('loan.advance.request', 'Request')
    file = fields.Binary('File', attachment=True, )
    file_name = fields.Char('File name')
    name = fields.Char('Description')
    note = fields.Char('Notes')


class hr_employee(models.Model):
    _inherit = "hr.employee"

    request_loan = fields.Boolean(_('Can request a loan / advance'), default=True)
    loans_count = fields.Float('Loans count', compute='get_loans_count')

    @api.one
    def get_loans_count(self):
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.id), ('active', '=', True)])
        if len(contracts):
            contract = contracts[0]
            self.loans_count = contract.remaining_amount
        else:
            self.loans_count = 0

    @api.multi
    def action_loans(self):
        return {
            'domain': "[('employee_id','in',[" + ','.join(map(str, self.ids)) + "])]",
            'name': _('Employee Loans'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'loan.advance.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    count_absence = fields.Float('Number of Absence Report', compute='get_count_absence')

    @api.one
    def get_count_absence(self):
        self.count_absence = self.env['employee.absence.line'].search_count([('employee_id', '=', self.id), ('state', '=', 'Confirmed')])

    @api.multi
    def open_absence_report(self):
        return {
            'domain': [('employee_id', '=', self.id), ('state', '=', 'Confirmed')],
            'name': _('Absence Report'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'employee.absence.line',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }


class hr_contract(models.Model):
    _inherit = "hr.contract"

    loans = fields.One2many('loan.advance.request', 'contract_id', readonly=True, string=_('Loan Details'),
                            domain=[('type', '=', 'Loan'), ('state', 'in', ['GM Approve', 'Loan Fully Paid'])])
    total_loans = fields.Float(string=_('Total Loans'), compute="_compute_total_loans", readonly=True)
    total_loans_copy = fields.Float(string=_('Total Loans'), related="total_loans", readonly=True)
    paid_amounts = fields.One2many('hr.contract.loan.payment', 'contract_id', readonly=True, string=_('Paid Amounts'))
    loans_total_paid_amount = fields.Float(string=_('Total Paid Amount'), compute="_compute_loans_total_paid_amount", readonly=True)
    total_paid_amount_copy = fields.Float(string=_('Total Paid Amount'), related="loans_total_paid_amount", readonly=True)
    remaining_amount = fields.Float(string=_('Remaining Amount'), compute="_compute_remaining_amount", readonly=True)

    @api.depends('loans')
    def _compute_total_loans(self):
        for rec in self:
            approved_loans = self.env['loan.advance.request'].search(
                [('contract_id', '=', rec.id), ('type', '=', 'Loan'), ('state', 'in', ['GM Approve', 'Loan Fully Paid'])])
            total_loan = 0
            for loan in approved_loans:
                total_loan += loan.general_manager_approval
            rec.total_loans = total_loan

    @api.depends('paid_amounts')
    def _compute_loans_total_paid_amount(self):
        for rec in self:
            total_amount = 0
            for amount in rec.paid_amounts:
                total_amount += amount.paid_amount
            rec.loans_total_paid_amount = total_amount

    @api.depends('total_loans', 'loans_total_paid_amount')
    def _compute_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = round(rec.total_loans - rec.loans_total_paid_amount, 2)


class hr_contract_loan_payment(models.Model):
    _name = 'hr.contract.loan.payment'
    _description = "hr.contract.loan.payment"

    contract_id = fields.Many2one('hr.contract', string=_('Contract'), readonly=True)
    ref = fields.Many2one('hr.payslip', string=_('Payment Reference'), readonly=True)
    payment_date = fields.Date(string=_('Payment Date'), readonly=True)
    paid_amount = fields.Float(string=_('Paid Amount'), readonly=True)
    notes = fields.Text(string=_('Notes'))


class hr_payslip_run(models.Model):
    _inherit = 'hr.payslip.run'

    reviewed_payslip_ids = fields.One2many('hr.payslip', 'patch_reviewed_id', 'Payslips To review')
    payslip_reviewed = fields.Boolean('Payslip reviewed')

    @api.onchange('payslip_reviewed')
    def onchange_payslip_reviewed(self):
        for payslip in self.reviewed_payslip_ids:
            payslip.loans_data_reviewed = self.payslip_reviewed

    @api.one
    def _compute_reviewed_payslips(self):
        for payslip in self.slip_ids:
            if payslip.current_remaining_amount > 0 or payslip.remaining > 0 or payslip.remaining_rewards > 0 or payslip.total_absence or payslip.days_in_payslip != 30 or payslip.rule_net < 0:
                payslip.patch_reviewed_id = self.id

    @api.one
    def confirm_payslip_run(self):
        if self.slip_ids:
            for slip in self.slip_ids:
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

        if self.reviewed_payslip_ids and not self.payslip_reviewed:
            raise UserError(_(
                "Dear Payroll team !! \n We found that there is some payslips which requires a special review, these payslips contains Loans or Violations or Rewards or Absence deduction which requires a special review, kindly make sure to review all payslip and check the ( Payslip reviewed ) field. "))

        self.write({'state': 'done', 'confirmed_by': self.env.uid, 'confirmation_date': datetime.now().strftime('%Y-%m-%d')})
        body = "Document Confirmed"
        self.message_post(body=body, message_type='email')
        return {}


class hr_payslip_employees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    @api.one
    def compute_sheet(self):
        res = super(hr_payslip_employees, self).compute_sheet()
        run_pool = self.env['hr.payslip.run']
        context = self.env.context.copy()
        batch = context and context.get('active_id', False) and run_pool.browse(context.get('active_id')) or None
        if batch:
            batch._compute_reviewed_payslips()
        return res


class hr_payslip(models.Model):
    _inherit = "hr.payslip"

    current_total_loans = fields.Float(string=_('Total Loans'), related="contract_id.total_loans", readonly=True)
    current_total_paid_amount = fields.Float(string=_('Total paid'), related="contract_id.loans_total_paid_amount", readonly=True)
    current_remaining_amount = fields.Float(string=_('Remaining Amount'), related="contract_id.remaining_amount", readonly=True)
    remaining_loans = fields.Float('Remaining Loans', compute="_compute_remaining_loans")
    loan_next_month_balance = fields.Float(string=_('Next Month Balance'), compute="_compute_loan_next_month_balance")
    loan_next_month_balance_history = fields.Float(string=_('Next Month Balance'))
    salary_advance_id = fields.Many2one('loan.advance.request', 'Salary in advance request')
    absence_ids = fields.One2many('employee.absence.line', 'payslip_m2o_id', _('Absence deduction report'))
    total_absence = fields.Float('Total absence deduction', compute='_compute_total_absence')
    absence_eduction_remove = fields.Float('Remove this amount from absence deduction')
    net_absence_deduction = fields.Float('Net absence deduction', compute='_compute_total_absence')
    patch_reviewed_id = fields.Many2one('hr.payslip.run', 'Patch Reviewed payslip')
    loan_fixed_amount = fields.Boolean('Loan Fixed Amount')

    @api.model
    def absence_deduction_rule(self):
        return self.net_absence_deduction * -1

    @api.model
    def total_deductions(self):
        res = super(hr_payslip, self).total_deductions()
        return res + self.absence_deduction_rule()

    @api.one
    def _compute_remaining_loans(self):
        if self.state == 'done':
            self.remaining_loans = self.remaining_amount
        else:
            self.remaining_loans = self.current_remaining_amount

    # /////////////////// Smart Buttons /////////////////////////////////////////////////////////////
    count_absence = fields.Float('Number of Absence Report', compute='get_count_smart_buttons')

    @api.one
    def get_count_smart_buttons(self):
        self.count_absence = self.env['employee.absence.line'].search_count(
            [('employee_id', '=', self.employee_id.id), ('year', '=', self.year), ('month', '=', self.month), ('payslip_id', 'in', [self.id])])

    @api.multi
    def open_payslip(self):
        return {
            'name': _('Payslip'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {},
            'flags': {'form': {'options': {'mode': 'view'}}}
        }

    @api.multi
    def open_absence_report(self):
        return {
            'domain': [('employee_id', '=', self.employee_id.id), ('year', '=', self.year), ('month', '=', self.month),
                       ('payslip_id', 'in', [self.id])],
            'name': _('Absence Report'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'employee.absence.line',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    # ///////////////////////////////////////////////////////////////////////////////////////////////////

    @api.one
    def _compute_absence(self):
        if self.employee_id and self.month and self.year and self.state != 'Final Reviewed':
            for abs in self.absence_ids:
                if not abs.paid:
                    abs.payslip_m2o_id = False
            absences = self.env['employee.absence.line'].search(
                [('employee_id', '=', self.employee_id.id), ('paid', '=', False), ('absence_date', '<=', __(self.date_to)),
                 ('payslip_id', 'in', [self.id, False]), ('leave_reconciliation_id', '=', False), ('state', '=', 'Confirmed')])
            for absence in absences:
                absence.payslip_m2o_id = self.id

    @api.one
    @api.depends('absence_ids')
    def _compute_total_absence(self):
        total_absence = 0
        for absence in self.absence_ids:
            total_absence += absence.deduction_amount
        self.total_absence = total_absence
        self.net_absence_deduction = self.total_absence - self.absence_eduction_remove

    @api.model
    def create(self, vals):
        res = super(hr_payslip, self).create(vals)
        res._compute_absence()
        return res

    @api.multi
    def write(self, vals):
        # Write your logic here
        res = super(hr_payslip, self).write(vals)
        for rec in self:
            rec._compute_absence()
        # Write your logic here
        return res

    @api.depends('current_remaining_amount', 'deduct_this_month')
    def _compute_loan_next_month_balance(self):
        for rec in self:
            rec.loan_next_month_balance = rec.current_remaining_amount - rec.deduct_this_month

    @api.multi
    def action_payslip_done(self):
        for rec in self:
            if not rec.negative_salary and rec.rule_net < 0:
                message = _(
                    "Not Allowed !! \n Employee ( %s  )  payslip number ( %s ) net salary is ( %s ) Net salary is not allowed to be in minus. If you want to continue this process with a negative Net salary, you have to go to ( Other payment and deductions ) Tab, and tell your system that you (Accept negative net salary) Usually this field appears to HR manager only.") % (
                              rec.employee_id.name, rec.number, rec.rule_net)
                raise exceptions.ValidationError(message)
            if rec.current_remaining_amount > 0:
                if not rec.loans_data_reviewed:
                    message = _(
                        "Attention!! \n This employee ( %s  ) had old loans or deductions or rewards which is not fully paid before confirm this payslip. kindly go to ( other payment / deduction) tab,  and make sure that you checked (other payments / deduction reviewed).") % rec.employee_id.name
                    raise exceptions.ValidationError(message)
                if rec.deduct_this_month > 0:
                    months = {
                        '01': 'January',
                        '02': 'February',
                        '03': 'March',
                        '04': 'April',
                        '05': 'May',
                        '06': 'June',
                        '07': 'July',
                        '08': 'August',
                        '09': 'September',
                        '10': 'October',
                        '11': 'November',
                        '12': 'December',
                    }
                    total_loans = rec.current_total_loans
                    total_paid_amount = rec.current_total_paid_amount
                    remaining_amount = rec.current_remaining_amount
                    loan_next_month_balance = rec.loan_next_month_balance
                    notes = _("خصم جزء من القرض عن شهر   %s") % (_(months[rec.month]))
                    payment_vals = {
                        'contract_id': rec.contract_id.id,
                        'ref': rec.id,
                        'payment_date': __(rec.date_from),
                        'paid_amount': rec.deduct_this_month,
                        'notes': notes,
                    }
                    payment_id = self.env['hr.contract.loan.payment'].create(payment_vals)
                    rec.total_loans = total_loans
                    rec.total_paid_amount = total_paid_amount
                    rec.remaining_amount = remaining_amount
                    rec.loan_next_month_balance_history = loan_next_month_balance
                    # /////////// Installment ////////////////////////
                    domain = [
                        ('employee_id', '=', rec.employee_id.id),
                        ('state', '=', 'GM Approve'),
                        ('remaining', '!=', 0),
                    ]
                    confirmed_installments = self.env['loan.installment'].search(domain, order="deduction_date asc")
                    if confirmed_installments:
                        installment_deduction = rec.deduct_this_month
                        for confirmed_installment in confirmed_installments:
                            deducted = 0
                            if installment_deduction <= 0:
                                break
                            if confirmed_installment.remaining > 0:
                                if installment_deduction < confirmed_installment.remaining:
                                    deducted = installment_deduction
                                else:
                                    deducted = confirmed_installment.remaining
                                # Create payment to installment with deduction
                                payment_vals = {
                                    'installment_id': confirmed_installment.id,
                                    'payslip_id': rec.id,
                                    'paid': deducted,
                                }
                                payment_id = self.env['loan.installment.payment'].create(payment_vals)
                                installment_deduction -= deducted

            # ////////////////// Absence Report ///////////////////////////////////////
            for absence in rec.absence_ids:
                absence.paid = True
                if not absence.payslip_id:
                    absence.payslip_id = rec.id
                    absence.absence_id.check_status()
                if not absence.patch_id and rec.payslip_run_id:
                    absence.patch_id = rec.payslip_run_id.id
            # ////////////////////////////////////////////////////////////////////////
        # self.compute_sheet()
        self.write({'state': 'done', 'confirmed_by': self.env.uid, 'confirmation_date': datetime.now().strftime('%Y-%m-%d')})
        body = "Document Confirmed"
        self.message_post(body=body, message_type='email')
        return super(hr_payslip, self.with_context(dict(self._context, without_compute_sheet=True))).action_payslip_done()

    @api.multi
    def compute_sheet(self):

        res = super(hr_payslip, self).compute_sheet()
        self._compute_absence()

        for rec in self:
            if rec.current_remaining_amount > 0 and rec.deduct_this_month == 0 and not rec.loan_fixed_amount:
                # ////////////////////////// Installments ////////////////////////////////////////////////////
                domain = [
                    ('employee_id', '=', rec.employee_id.id),
                    ('deduction_date', '<=', __(rec.date_to)),
                    ('state', '=', 'GM Approve'),
                ]
                confirmed_installments = self.env['loan.installment'].search(domain)
                if confirmed_installments:
                    rec.deduct_this_month = sum([c.remaining for c in confirmed_installments])

            # /////////////// Deductions ///////////////////////////////
            if not rec.deduction_fixed_amount:
                deductions = self.env["employee.deductions.violations"].search([
                    ('state', '=', 'confirmed'),
                    ('employee_id', '=', rec.employee_id.id),
                    ('deduction_date', '<=', __(rec.date_to)),
                    ('remaining_amount', '>', 0),
                ])
                if deductions:
                    rec.deduct_this_month_ = sum([d.remaining_amount for d in deductions])

            # /////////////// Compute rewards ///////////////////////////////
            if not rec.reward_pay_this_month and not rec.reward_fixed_amount:
                rec.reward_pay_this_month = rec.remaining_rewards

            # ///////////////////////// Automatic Data Reviewed ///////////////////////////
            if not ((rec.current_remaining_amount > 0 and rec.deduct_this_month == 0) or (
                    rec.remaining > 0 and rec.deduct_this_month_ == 0 and rec.remove_from_employee == 0) or (
                            rec.remaining_rewards > 0 and rec.reward_pay_this_month == 0 and rec.reward_remove_amount == 0)):
                rec.loans_data_reviewed = True

        return res


class employee_absence_line(models.Model):
    _name = 'employee.absence.line'
    _description = "Employee Absence Record"
    _inherit = 'mail.thread'
    _order = "id desc"

    payslip_m2o_id = fields.Many2one('hr.payslip', "Payslip")
    employee_id = fields.Many2one('hr.employee', "Employee")
    employee_english_name = fields.Char('Employee English Name', related='employee_id.employee_english_name', readonly=True)
    absence_days = fields.Float('Absence days')
    absence_hours = fields.Float('Absence Hours')
    absence_minutes = fields.Float('Absence Minutes')
    deduction_amount = fields.Float('Absence Deduction Amount', compute='_compute_deduction_amount', store=True)
    config_based_on = fields.Selection([('basic', 'Basic Salary'),
                                        ('basic_house', 'Basic + House'),
                                        ('basic_house_trans', 'Basic + House + Transportation'),
                                        ('basic_house_trans_phone', 'Basic + House + Transportation + Phone'),
                                        ('total', 'Total salary')]
                                       , 'Employee absence deduction based on', compute='_compute_config_based_on')

    absence_date = fields.Date('Absence date')
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
    month = fields.Selection(_PERIOD, _('Will be deducted on'), default=lambda self: self.env.context.get('month', False))
    year = fields.Integer('Year', default=lambda self: self.env.context.get('year', False))
    patch_id = fields.Many2one('hr.payslip.run', 'Payslip batch')
    payslip_id = fields.Many2one('hr.payslip', 'Employee Payslip')
    note = fields.Char('Absence notes')
    department_id = fields.Many2one('hr.department', 'Department', related='employee_id.department_id', store=True, readonly=True)
    job_id = fields.Many2one('hr.job', 'Job', related='employee_id.job_id', store=True, readonly=True)
    country_id = fields.Many2one('res.country', 'Nationality', related='employee_id.country_id', store=True, readonly=True)
    nationality_type = fields.Selection([('Native', 'Native'),
                                         ('Non-native', 'Non-native')], related='employee_id.nationality_type', store=True, readonly=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender', related='employee_id.gender', store=True, readonly=True)
    marital = fields.Selection([('single', 'Single'), ('married', 'Married')], 'Marital Status', related='employee_id.marital', store=True,
                               readonly=True)
    branch_id = fields.Many2one('hr.branch', 'branch', related='employee_id.branch_id', store=True, readonly=True)
    paid = fields.Boolean('Paid')
    violation_type = fields.Many2one('deduction.violation.type', 'Violation Type',
                                     domain=[('state', '=', 'confirmed'), ('used_for_absence', '=', True)])
    auto_created_violation = fields.Many2one('employee.deductions.violations', 'Auto Created Violation')
    violation_status = fields.Selection([
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('confirmed', 'Confirmed'),
        ('refused', 'Refused'),
    ], string='Violation Status', related='auto_created_violation.state', readonly=True)
    previous_violations = fields.Integer('Previous violations', related='auto_created_violation.previous_violations', readonly=True)
    violation_amount = fields.Float('Violation Amount', related='auto_created_violation.amount', readonly=True)
    total = fields.Float('Total Absence + Violation', compute='_compute_total', store=True)
    no_create_violation = fields.Boolean("Don't Create A Violation")
    state = fields.Selection([
        ('New', 'New'),
        ('Reviewed', 'Reviewed'),
        ('Confirmed', 'Confirmed'),
        ('Refused', 'Refused'),
    ], string='Status', default='New')
    leave_reconciliation_id = fields.Many2one('hr.leave.reconciliation', 'Leave Reconciliation')

    @api.one
    @api.depends('violation_amount', 'deduction_amount')
    def _compute_total(self):
        self.total = self.violation_amount + self.deduction_amount

    @api.one
    def create_violation(self):
        if not self.violation_type:
            message = "Dear HR, Your system will automatically create a violation, kindly select the type of violation which will be assigned to this employee ( %s  ), If you want not to create a violation for this absence, kindly check this field ( Don't create a violation )" % self.employee_id.name
            raise exceptions.ValidationError(message)

        deduction_model = self.env['employee.deductions.violations']

        res = {
            'desc': 'Auto Absence violation',
            'employee_id': self.employee_id.id,
            'deduction_date': __(self.absence_date),
            'deduction_reason': 'violation',
            'violation_type_id': self.violation_type.id,
            'absence_record': self.id,
            'deduction_value': False,
            'deduction_type': False,
            'deduction_based_on': False,
            'decision': False,
            'template_id': False,
            'deduction_percentage': False,
            'other_action': False,
            'action_desc': False,
            'amount': 0,
        }

        # ////////////////  Implement Onchange violation_type_id ////////////////////////////////////
        specs = deduction_model._onchange_spec()
        updates = deduction_model.onchange(res, ['violation_type_id'], specs)
        value = updates.get('value', {})
        for name, val in value.iteritems():
            if isinstance(val, tuple):
                value[name] = val[0]
        res.update(value)

        # ////////////////  Implement Onchange deduction_percentage ////////////////////////////////////
        specs = deduction_model._onchange_spec()
        updates = deduction_model.onchange(res, ['deduction_percentage'], specs)
        value = updates.get('value', {})
        for name, val in value.iteritems():
            if isinstance(val, tuple):
                value[name] = val[0]
        res.update(value)

        violation = deduction_model.create(res)
        self.auto_created_violation = violation.id
        self._compute_total()

    @api.one
    def action_review(self):
        self.state = 'Reviewed'
        if not self.no_create_violation:
            self.create_violation()
        body = "Document Reviewed"
        self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def action_confirm(self):
        self.state = 'Confirmed'
        body = "Document Confirmed"
        self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def action_set_draft(self):
        self.state = 'New'
        body = "Document Set To New"
        self.message_post(body=body, message_type='email')
        return {}

    @api.one
    def action_refuse(self):
        self.state = 'Refused'
        body = "Document Refused"
        self.message_post(body=body, message_type='email')
        return {}

    @api.onchange('absence_date')
    def onchange_absence_date(self):
        if not self.env.context.get('year', False) and __(self.absence_date):
            absence_date = datetime.strptime(__(self.absence_date), "%Y-%m-%d")
            self.year = absence_date.strftime("%Y")
            self.month = absence_date.strftime("%m")

    @api.one
    @api.depends('employee_id', 'absence_days', 'absence_hours', 'absence_minutes')
    def _compute_deduction_amount(self):
        absence_based_on = self.env['ir.default'].get('hr.loans.config.settings', 'absence_based_on')
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('active', '=', True)])
        if len(contracts):
            contract = contracts[0]
            based_on = contract.basic_salary + contract.house_allowance_amount + contract.transportation_allowance_amount
            self.deduction_amount = (based_on / 30) * self.absence_days + (based_on / (30 * 8)) * self.absence_hours + (based_on / (
                    30 * 8 * 60)) * self.absence_minutes

    @api.multi
    @api.depends('employee_id')
    def name_get(self):
        res = []
        for rec in self:
            name = "Employee Absence Report For %s" % rec.employee_id.name
            res += [(rec.id, name)]
        return res


class LoanInstallment(models.Model):
    _name = "loan.installment"
    _inherit = 'mail.thread'
    _description = "Loan Installment"

    employee_id = fields.Many2one('hr.employee', string=_('Employee'))
    loan_request_id = fields.Many2one('loan.advance.request', string=_('Loan Request'), domain=[('type', '=', 'Loan')])
    department_id = fields.Many2one('hr.department', string=_('Department'), related="employee_id.department_id", store=True, readonly=True)
    job_id = fields.Many2one('hr.job', string=_('Job Title'), related="employee_id.job_id", store=True, readonly=True)
    country_id = fields.Many2one('res.country', 'Nationality', related='employee_id.country_id', store=True, readonly=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender', related='employee_id.gender', store=True, readonly=True)
    installment_number = fields.Integer('Number of installments')
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

    month = fields.Selection(_PERIOD, _('Month'))
    year = fields.Integer(_('Year'))
    deduction_date = fields.Date('Deduction Day')
    monthly_installment = fields.Float('Monthly Installment')
    paid = fields.Float('Paid', compute='_compute_paid', store=True)
    remaining = fields.Float('Remaining', compute='_compute_remaining', store=True)
    note = fields.Html('Notes')
    attachment_ids = fields.One2many('loan.installment.attaches', 'installment_id', 'Attachments')
    payment_ids = fields.One2many('loan.installment.payment', 'installment_id', 'Payment details')
    state = fields.Selection( [
        ('New', 'New'),
        ('Payroll Officer Approval', 'Payroll Officer Approval'),
        ('HR Manager Approve', 'HR Manager Approve'),
        ('Financial Manager Approve', 'Financial Manager Approve'),
        ('GM Approve', 'CEO / GM approval'),
        ('Loan Fully Paid', 'Loan Fully Paid'),
        ('Refused', 'Refused'),
    ], string='Status', readonly=True)
    branch_id = fields.Many2one('hr.branch', string='Branch', related="employee_id.branch_id", readonly=True, store=True)

    @api.one
    @api.depends('payment_ids')
    def _compute_paid(self):
        paid = 0
        for payment in self.payment_ids:
            paid += payment.paid
        self.paid = paid

    @api.one
    @api.depends('monthly_installment', 'paid')
    def _compute_remaining(self):
        self.remaining = round(self.monthly_installment - self.paid, 2)

    @api.model
    def create(self, vals):
        res = super(LoanInstallment, self).create(vals)
        if not res.employee_id:
            res.employee_id = res.loan_request_id.employee_id.id
        return res

    @api.onchange('loan_request_id')
    def _onchange_loan_request_id(self):
        self.employee_id = self.loan_request_id.employee_id

    @api.onchange('month', 'year')
    def _compute_deduction_date(self):
        if self.month and self.year:
            start_end = calendar.monthrange(self.year, int(self.month))
            self.deduction_date = str(self.year) + '-' + self.month + '-' + str(start_end[1])

    @api.one
    def unlink(self):
        if not self.env.user.has_group('saudi_hr_employee.group_loan_ceo_approval'):
            if self.paid or self.state in ['Loan Fully Paid', 'GM Approve']:
                raise ValidationError(_("Not allowed!! \n\
                    Not Allowed to delete Loan Installment witch had paid amount or in states (Loan Fully Paid,GM Approve) "))
            return super(LoanInstallment, self).unlink()


class InstallmentPayment(models.Model):
    _name = "loan.installment.payment"
    _description = "Loan Installment Payment"

    installment_id = fields.Many2one('loan.installment', "Installment")
    payslip_id = fields.Many2one('hr.payslip', 'Payslip')
    leave_reconciliation_id = fields.Many2one('hr.leave.reconciliation', 'Leave Reconciliation')
    paid = fields.Float('Paid Amount')
    note = fields.Char('Notes')


class InstallmentAttaches(models.Model):
    _name = "loan.installment.attaches"
    _description = "Loan Installment Attaches"

    installment_id = fields.Many2one('loan.installment', "Installment")
    file = fields.Binary('File', attachment=True, )
    file_name = fields.Char('File name')
    name = fields.Char('Description')
    note = fields.Char('Notes')
