# -*- coding: utf-8 -*-

from __future__ import division
from odoo import models, fields, api, exceptions, _
# import openerp.addons.decimal_precision as dp
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from odoo.tools import __
from odoo.exceptions import ValidationError


class LoanInstallment(models.Model):
    _inherit = "loan.installment"

    eos_id = fields.Many2one('employee.eos', 'EOS')


class hr_leave(models.Model):
    _inherit = "hr.leave"

    eos_id = fields.Many2one('employee.eos', 'Employee EOS request')


class AirTicketBalanceAllocation(models.Model):
    _inherit = "air.ticket.balance.allocation"

    eos_id = fields.Many2one('employee.eos', 'Employee EOS request')


class employeeAbsenceLine(models.Model):
    _inherit = "employee.absence.line"

    eos_id = fields.Many2one('employee.eos', 'Employee EOS request')


class res_country(models.Model):
    _inherit = "res.country"

    eos_notice_period = fields.Integer('EOS Notice period')

    @api.model
    def update_eos_notice_period(self):
        for country in self.search([]):
            if country.is_saudi:
                country.eos_notice_period = 30
            else:
                country.eos_notice_period = 60


class Contract(models.Model):
    _inherit = 'hr.contract'

    eos_notice_period = fields.Integer('EOS Notice period')

    @api.onchange('employee_id')
    def get_eos_notice_period(self):
        self.eos_notice_period = self.employee_id.country_id.eos_notice_period


class Employee(models.Model):
    _inherit = 'hr.employee'

    unpaid_before = fields.Integer('Unpaid leaves before using the system')
    eos_reason = fields.Many2one('eos.reason', 'EOS Reason')

    @api.model
    def employee_update_fields(self):
        for e in self.env['employee.eos'].search([('state', 'not in', ['Final Approved', 'Refused - Cancelled'])]):
            e._compute_last_working_day_remaining()
        res = super(Employee, self).employee_update_fields()
        return res


class eos_reason(models.Model):
    _name = 'eos.reason'
    _inherit = ['mail.thread']

    code = fields.Char('Code')
    name = fields.Char('EOS Reason Description In Arabic')
    english_name = fields.Char('EOS Reason Description In English')
    no_delete = fields.Boolean('Not allowed To Delete')
    calc_based_on = fields.Selection([
        ('no_eos', 'Zero - No End Of Services'),
        ('basic', 'Basic Salary'),
        ('basic_house', 'Basic + House allowance'),
        ('basic_house_trans', 'Basic + House + Transportation'),
        ('basic_house_trans_phone', 'Basic + House + Transportation + Phone'),
        ('total', '‫‪Total salary')], 'Calculation Based On')

    resignation = fields.Boolean('Resignation')
    annual_air_ticket_balance = fields.Selection([
        ('annual', 'Annual air tickets will be paid if the employee entitled to full ticket'),
        ('current', '‫‪Current air ticket balance will be paid ( ticket fractions will be paid')], 'If The Employee Have Annual Air Ticket Balance')
    relatives_air_ticket = fields.Selection([
        ('included', 'Will be included'),
        ('not_included', 'Will not be included')], 'Relatives Air Ticket')

    final_exit = fields.Selection([
        ('no', 'No air tickets for final exit'),
        ('always', 'Always create a final exit ticket'),
        ('if_no_air_ticket_balance', 'Create a final exit ticket if the employee did not have annual air ticket balance')],
        'For non-saudis, final exit ticket')

    exclude_unpaid = fields.Boolean('Exclude Unpaid leave from EOS calculation', default=True)
    active = fields.Boolean('Active', default=True)
    trial_0 = fields.Boolean('IF EOS during trial period, EOS = 0', default=True)
    law_calc = fields.Char('Labor law calculator')
    details = fields.Html('EOS Details')
    notes = fields.Html('Other Notes')
    attachment_ids = fields.One2many('eos.reason.attachment', 'eos_reason_id', 'Attachments')
    eos_ids = fields.One2many('employee.eos', 'reason_id', 'Employee end of services', )
    no_tickets_with_eos = fields.Boolean('No Annual air tickets with EOS')
    cash_air_tickets_allowance = fields.Boolean('Cash Air tickets allowance',
                                                help='if you select this option, this means that EOS will include current air ticket Cash balance. as long as employee contract (allows cash air tickets).')

    @api.onchange('no_tickets_with_eos')
    def empty_annual_air_ticket_balance(self):
        if self.no_tickets_with_eos:
            self.annual_air_ticket_balance = False
            self.relatives_air_ticket = 'not_included'

    # /////////////////// Smart Buttons /////////////////////////////////////////////////////////////
    count_eos = fields.Float('Number of eos', compute='get_count_smart_buttons')
    count_employees = fields.Float('Number of employees', compute='get_count_smart_buttons')

    @api.one
    def get_count_smart_buttons(self):
        self.count_eos = self.env['employee.eos'].search_count([('reason_id', '=', self.id)])
        self.count_employees = self.env['hr.employee'].search_count([('eos_reason', '=', self.id)])

    @api.multi
    def open_eos(self):
        return {
            'domain': [('reason_id', '=', self.id)],
            'name': _('Employee EOS'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'employee.eos',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    @api.multi
    def open_employees(self):
        return {
            'domain': [('eos_reason', '=', self.id)],
            'name': _('Resigned Employees'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.employee',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    state = fields.Selection([
        ('New', 'New'),
        ('Confirmed', 'Confirmed'),
    ], string='Status', index=True, default='New', track_visibility='onchange')

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].sudo().next_by_code('eos.reason')
        res = super(eos_reason, self).create(vals)
        return res

    @api.multi
    def copy(self):
        for rec in self:
            raise exceptions.ValidationError('Forbidden to duplicate')

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.no_delete:
                raise exceptions.ValidationError(
                    "Dear Hr, You are not allowed to delete this EOS reason, because they are mentioned in SAUDI LAWS. You can add new one as more reasons as you want.")
            if rec.state == 'Confirmed':
                raise exceptions.ValidationError("Not allowed to delete a confirmed transaction !!")
        return super(eos_reason, self).unlink()

    @api.multi
    def action_confirm(self):
        for record in self:
            record.write({'state': 'Confirmed'})
        return {}

    @api.multi
    def action_set_new(self):
        for record in self:
            record.write({'state': 'New'})
        return {}


class eosReasonAttaches(models.Model):
    _name = "eos.reason.attachment"
    _description = "EOS Reason Attaches"

    eos_reason_id = fields.Many2one('eos.reason', "EOS Reason")
    file = fields.Binary('File', attachment=True, )
    file_name = fields.Char('File name')
    name = fields.Char('Description')
    note = fields.Char('Notes')


class eos_motivation(models.Model):
    _name = 'eos.motivation'
    _inherit = ['mail.thread']

    code = fields.Char('Code')
    name = fields.Char('End of services Motivation in arabic')
    english_name = fields.Char('End of services Motivation in english')

    state = fields.Selection([
        ('New', 'New'),
        ('Confirmed', 'Confirmed'),
    ], string='Status', index=True, default='New', track_visibility='onchange')

    # /////////////////// Smart Buttons /////////////////////////////////////////////////////////////
    count_eos = fields.Float('Number of eos', compute='get_count_smart_buttons')
    count_employees = fields.Float('Number of employees', compute='get_count_smart_buttons')

    @api.one
    def get_count_smart_buttons(self):
        self.count_eos = self.env['employee.eos'].search_count([('motivation_id', '=', self.id)])
        self.count_employees = self.env['hr.employee'].search_count([('eos_motivation', '=', self.id)])

    @api.multi
    def open_eos(self):
        return {
            'domain': [('motivation_id', '=', self.id)],
            'name': _('Employee EOS'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'employee.eos',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    @api.multi
    def open_employees(self):
        return {
            'domain': [('eos_motivation', '=', self.id)],
            'name': _('Resigned Employees'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.employee',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].sudo().next_by_code('eos.motivation')
        res = super(eos_motivation, self).create(vals)
        return res

    @api.multi
    def copy(self):
        for rec in self:
            raise exceptions.ValidationError('Forbidden to duplicate')

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state == 'Confirmed':
                raise exceptions.ValidationError("Not allowed to delete a confirmed transaction !!")
        return super(eos_motivation, self).unlink()

    @api.multi
    def action_confirm(self):
        for record in self:
            record.write({'state': 'Confirmed'})
        return {}

    @api.multi
    def action_set_new(self):
        for record in self:
            record.write({'state': 'New'})
        return {}


class employee_eos(models.Model):
    _name = 'employee.eos'
    _inherit = ['mail.thread', 'employee.eos']
    _description = "EOS Record"
    _order = "id desc"

    code = fields.Char('Code')
    employee_id = fields.Many2one('hr.employee', 'Employee Arabic name')
    employee_english_name = fields.Char('Employee English Name', related='employee_id.employee_english_name', readonly=True)
    contract_id = fields.Many2one('hr.contract', 'Contract', compute="_compute_contract", store=True)
    reason_id = fields.Many2one('eos.reason', 'EOS Reason')
    motivation_ids = fields.Many2many('eos.motivation', 'eos_eos_motive_rel', 'eos_id', 'mot_id', 'EOS Motivation')
    first_hiring_date = fields.Date('First Hiring Date', related='employee_id.contract_id.start_work', store=True)
    request_date = fields.Date('Request Date', default=datetime.now().strftime("%Y-%m-%d"))
    eos_notice_period = fields.Integer('EOS Notice period')
    expected_last_working_day = fields.Date('Expected last working day', compute='_compute_expected_last_working_day', store=True)
    actual_last_working_day = fields.Date('Actual Last Working Day')
    actual_last_working_day_confirmed = fields.Boolean('Actual last working day confirmed')
    last_working_day_remaining = fields.Integer('Remaining before Actual last working day', compute='_compute_last_working_day_remaining', store=True)
    notice_period_difference = fields.Integer('Notice period difference', compute='_compute_notice_period_difference', store=True,
                                              help='To calculate Notice period difference \n 1 . = zero, if (the employee didn’t have any payslips) or ( actual last working day is equal to expected last working day ) \n 2 . = Negative if ( expected last working day is greater than actual last working day) \n 3 . Positive Notice period difference (actual last working day is greater than expected last working day ), your system will create individual payslip for this employee for the positive difference days.')
    total_work_duration = fields.Char('Total Work Duration', compute='_compute_total_work_duration', store=True)
    total_work_duration_years = fields.Integer('Total Work Duration Years', compute='_compute_total_work_duration')
    total_work_duration_months = fields.Integer('Total Work Duration Months', compute='_compute_total_work_duration')
    total_work_duration_days = fields.Integer('Total Work Duration Days', compute='_compute_total_work_duration')
    total_unpaid_leave_duration = fields.Integer('Total unpaid leave duration', compute='_compute_total_unpaid_leave_duration', store=True)
    total_unpaid_leaves_years = fields.Float('Total unpaid leaves in years', compute='_compute_total_unpaid_leave_duration', digits=(16, 4),
                                             store=True)
    total_number_of_years = fields.Float('Total Number of years', compute='_compute_total_work_duration', digits=(16, 4))
    net_years = fields.Float('Net years', compute='_compute_net_years', digits=(16, 4), store=True)
    calc_based_on = fields.Selection([
        ('no_eos', 'Zero - No End Of Services'),
        ('basic', 'Basic Salary'),
        ('basic_house', 'Basic + House allowance'),
        ('basic_house_trans', 'Basic + House + Transportation'),
        ('basic_house_trans_phone', 'Basic + House + Transportation + Phone'),
        ('total', '‫‪Total salary')], 'Calculation Based On', related='reason_id.calc_based_on', store=True, readonly=True)

    amount = fields.Float('EOS Amount', store=True)
    labor_row = fields.Char('Matching with labor law', related='reason_id.law_calc', readonly=True)
    remaining_loan_amount = fields.Float('Remaining loan amount', compute='_compute_remaining', store=True)
    remaining_deduction = fields.Float('Remaining Violations and deductions', compute='_compute_remaining', store=True)
    absence_deduction = fields.Float('Absence Deduction', )
    notice_period_deduction = fields.Float('Notice Period Deduction', compute='_compute_notice_period_deduction', store=True,
                                           help='To calculate Notice period Deduction \n 1 . = zero, if (Notice period difference= 0) \n 2 . = Negative if Notice period difference=  negative value) \n 3 . Positive >> ( this field can not be a positive, your system will automatically manage the positive difference in payslip).')
    rewards = fields.Float('Rewards', compute='_compute_remaining', store=True)
    manual_leave_balance = fields.Boolean('Manual Leave balance')
    leaves_count = fields.Float('Annual leave balance')
    leave_allocation = fields.Many2one('hr.leave', 'Leave Allocation')
    leave_balance_cash = fields.Float('Leave balance in cash', compute='_compute_leave_balance_cash', store=True)
    old_unreconciled_leaves = fields.Float('Old leave requests not fully reconciled', compute='_compute_old_unreconciled_leaves', store=True)
    annual_air_ticket_balance = fields.Float('Employee annual air ticket balance', compute='_compute_annual_air_ticket_balance', store=True)
    air_ticket_allocation = fields.Many2one('air.ticket.balance.allocation', 'Air ticket balance allocation')
    number_of_relatives = fields.Float('Number of Relatives', compute='_compute_number_of_relatives', store=True)
    air_ticket_one_way = fields.Float('Total air ticket value',
                                      help='Air ticket price one way * (number of relatives + the employee ) * Employee annual air ticket balance \n example \n if  air ticket price one way = 500 , employee relatives = 2, Employee annual air ticket balance = 1 ticket >>> so Total air ticket value one way = ( 500 * (2+1) * 1 ) = 1500 , If Cash Air tickets allowance is enabled for EOS reason.')
    air_ticket_price_one_way = fields.Float('air ticket price',
                                            help='Your system will read air ticket price one way from ( city >> Country >> contract ).')
    nationality_type = fields.Selection([('Native', 'Native'),
                                         ('Non-native', 'Non-native')], related='employee_id.nationality_type', store=True, readonly=True)
    final_exit = fields.Selection([
        ('Final Exit', 'Final Exit'),
        ('Transfer Sponsorship', 'Transfer Sponsorship'), ], 'Employee Final Exit', )
    reason_final_exit = fields.Selection([
        ('no', 'No air tickets for final exit'),
        ('always', 'Always create a final exit ticket'),
        ('if_no_air_ticket_balance', 'Create a final exit ticket if the employee did not have annual air ticket balance')],
        related='reason_id.final_exit',
        readonly=True)
    final_exit_request = fields.Selection([
        ('create', 'Create Final exit ticket'),
        ('no_create Sponsorship', 'Don\'t create final exit ticket')], 'Final exit air ticket request', )
    last_payslip = fields.Many2one('hr.payslip', 'Last Payslip', compute='_compute_last_payslip', store=True)
    payslip_amount = fields.Float('EOS Payslip Amount', compute='_compute_last_payslip')
    last_payslip_date = fields.Date('Last Payslip Date', related='last_payslip.date_to', readonly=True)
    other_payment = fields.Float('Other payment / deduction', compute='_compute_other_payment')
    net_eos_amount = fields.Float('NET End of services amount', compute='_compute_net_eos_amount')
    payment_ids = fields.One2many('employee.eos.payment.deduction', 'eos_id', 'Other payment / Deductions')

    # //////////////////////// Filtering Fields /////////////////////////////////////////////////////////
    department_id = fields.Many2one('hr.department', 'Department', related='employee_id.department_id', store=True, readonly=True)
    job_id = fields.Many2one('hr.job', 'Job', related='employee_id.job_id', store=True, readonly=True)
    country_id = fields.Many2one('res.country', 'Nationality', related='employee_id.country_id', store=True, readonly=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender', related='employee_id.gender', store=True, readonly=True)
    marital = fields.Selection([('single', 'Single'), ('married', 'Married')], 'Marital Status', related='employee_id.marital', store=True,
                               readonly=True)
    branch_id = fields.Many2one('hr.branch', 'branch', related='employee_id.branch_id', store=True, readonly=True)
    religion = fields.Selection([('Muslim', 'Muslim'), ('Non-Muslim', 'Non-Muslim'), ], related='employee_id.religion', store=True, readonly=True)
    identification_id = fields.Char('Iqama Number', related='employee_id.identification_id', store=True, readonly=True)
    iqama_expiry_date = fields.Date(string='Iqama Expiry Date', related='employee_id.iqama_expiry_date', store=True, readonly=True)
    passport_expiry_date = fields.Date(string='Passport Expiry Date', related='employee_id.passport_expiry_date', store=True, readonly=True)
    current_age = fields.Integer(string="Current Age", related='employee_id.current_age', store=True, readonly=True)
    state = fields.Selection([
        ('New', 'New'),
        ('Reviewed', 'Reviewed'),
        ('Confirmed', 'Confirmed'),
        ('Approved', 'Approved'),
        ('Final Approved', 'Final Approved'),
        ('Refused - Cancelled', 'Refused - Cancelled'),
    ], string='Status', index=True, default='New', track_visibility='onchange')

    report_other_earnings = fields.Float('other earnings', compute='_compute_report')
    report_other_deductions = fields.Float('other earnings', compute='_compute_report')
    report_total_earnings = fields.Float('total earnings', compute='_compute_report')
    report_total_deductions = fields.Float('total deductions', compute='_compute_report')
    report_net_earnings = fields.Float('net earnings', compute='_compute_report')
    report_payslip_percent = fields.Float(compute='_compute_last_payslip')
    deduct_gosi = fields.Boolean('Deduct Gosi', default=True)
    gosi_amount = fields.Float('GOSI amount')

    @api.one
    @api.depends('actual_last_working_day')
    def _compute_last_working_day_remaining(self):
        if __(self.actual_last_working_day):
            difference = datetime.strptime(__(self.actual_last_working_day), '%Y-%m-%d') - datetime.now()
            self.last_working_day_remaining = difference.days

    @api.onchange('deduct_gosi', 'employee_id')
    def get_gosi_amount(self):
        if not self.deduct_gosi:
            self.gosi_amount = 0
        else:
            self.gosi_amount = self.contract_id.employee_amount

    @api.one
    def _compute_report(self):
        self.report_other_deductions = sum(l.amount < 0 and l.amount for l in self.payment_ids) * -1
        self.report_other_earnings = sum(l.amount > 0 and l.amount for l in self.payment_ids) + self.rewards + self.old_unreconciled_leaves
        self.report_total_earnings = (
                                             self.contract_id.basic_salary + self.contract_id.house_allowance_amount + self.contract_id.phone_allowance_amount + self.contract_id.transportation_allowance_amount + self.contract_id.other_allowance) * self.report_payslip_percent + self.leave_balance_cash + self.amount + self.report_other_earnings + self.air_ticket_one_way
        self.report_total_deductions = self.remaining_loan_amount + self.remaining_deduction + self.absence_deduction + self.notice_period_deduction + self.gosi_amount + self.report_other_deductions
        self.report_net_earnings = self.report_total_earnings - self.report_total_deductions

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'Refused - Cancelled':
                raise exceptions.ValidationError(_("To delete EOS request, you must refuse - Cancel the EOS request."))
        return super(employee_eos, self).unlink()

    @api.multi
    def copy(self):
        for rec in self:
            raise exceptions.ValidationError(_('Forbidden to duplicate'))

    @api.one
    @api.depends('contract_id', 'employee_id')
    def _compute_remaining(self):
        self.remaining_loan_amount = self.contract_id.remaining_amount
        self.remaining_deduction = self.contract_id.remaining
        self.rewards = self.contract_id.remaining_rewards

    @api.onchange('contract_id', 'employee_id')
    def _compute_leaves_count(self):
        if not self.manual_leave_balance:
            self.leaves_count = self.employee_id.leaves_count

    @api.constrains('contract_id', 'employee_id')
    def check_contract(self):
        if not self.contract_id.id:
            raise ValidationError(_("Employee \"%s\" don't have active contract!" % self.employee_id.name))

    @api.multi
    def action_review(self):
        for rec in self:
            if not rec.reason_id:
                raise exceptions.ValidationError('Kindly select EOS reason!!')
            if not __(rec.actual_last_working_day):
                raise exceptions.ValidationError(
                    "Dear !! \n In order to review & Calculate EOS, your system need to know what is the actual last working day, So kindly make sure to select date on ( Actual last working day )")
            rec.recalculate_eos()
            error_msg_2 = _("Dear Hr team, !! \n Kindly be informed that Employee ( %s ) will be temporary inactive "
                            "until you finalize End Of Services process, salary and other benefits will not be calculated "
                            "during the normal system process, if all process are done and EOS status is Final approved, "
                            "Employee and his contract will be inactive. Payslip from last payslip date to the last "
                            "actual working day and other benefits will be calculated here in this form. ") % (rec.employee_id.name)
            return self.env.user.show_dialogue(error_msg_2, 'employee.eos', 'action_review_continue', rec.id)

    @api.one
    def action_review_continue(self):
        # raise ValidationError("aaaaaaaaaaaaaaaa")
        self.sudo().employee_id.eos = self.id
        self.state = 'Reviewed'
        # /////////////  send mail custom notification  /////////////////////////////////////////////
        # partners_ids = [6, 7]
        #
        # body_html = '''
        #     <p style="margin-block-start:0px;direction: rtl;"><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">برجاء الدخول على النظام ومراجعة طلب إنهاء الخدمات للموظف </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;">(  </span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; font-size: 18px; text-align: right;">&nbsp;</span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><u>${object.employee_id.name}</u></strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;"> ) </span><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">&nbsp;</span><br></p><p style="margin-block-start:0px;"></p><p style="margin-block-start:0px;"></p><p></p><div style="direction: ltr;"><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;">Kindly login to the system and review End Of Service request for employee&nbsp;</span><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">( </span><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;"></span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right;">&nbsp;</span><strong style="font-family: inherit; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-size: initial;"><u><font style="font-size: 14px;">${object.employee_id.employee_english_name}</font></u></strong><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">)</span></div>
        #     '''
        # body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
        #     body_html, 'employee.eos', [self.id], )
        # body = body and body[self.id] or False
        #
        # self.message_post(
        #     subject='مراجعة طلب نهاية الخدمه EOS Request',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=self.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)
        # /////////////////////////////////////////////////////////////
        body = "Record Reviewed."
        self.message_post(body=body, message_type='email')
        message_1 = 'Your System automatically deactivated this employee due to EOS Process at ( %s )' % (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.employee_id.message_post(body=message_1, message_type='email')

    @api.one
    def action_confirm(self):
        if not self.reason_id:
            raise exceptions.ValidationError('Kindly select EOS reason!!')
        if not __(self.actual_last_working_day):
            raise exceptions.ValidationError(
                "Dear !! \n In order to confirm & Calculate EOS, your system need to know what is the actual last working day, So kindly make sure to select date on ( Actual last working day )")
        self.recalculate_eos()
        self.state = 'Confirmed'
        # /////////////  send mail custom notification  /////////////////////////////////////////////
        # partners_ids = [6, 7]
        #
        # body_html = '''
        #     <p style="margin-block-start:0px;direction: rtl;"><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">برجاء الدخول على النظام ومراجعة طلب إنهاء الخدمات للموظف </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;">(  </span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; font-size: 18px; text-align: right;">&nbsp;</span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><u>${object.employee_id.name}</u></strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;"> ) </span><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">&nbsp;</span><br></p><p style="margin-block-start:0px;"></p><p style="margin-block-start:0px;"></p><p></p><div style="direction: ltr;"><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;">Kindly login to the system and review End Of Service request for employee&nbsp;</span><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">( </span><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;"></span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right;">&nbsp;</span><strong style="font-family: inherit; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-size: initial;"><u><font style="font-size: 14px;">${object.employee_id.employee_english_name}</font></u></strong><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">)</span></div>
        #     '''
        # body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
        #     body_html, 'employee.eos', [self.id], )
        # body = body and body[self.id] or False
        #
        # self.message_post(
        #     subject='مراجعة طلب نهاية الخدمه EOS Request',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=self.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)
        # /////////////////////////////////////////////////////////////
        body = "Record Confirmed."
        self.message_post(body=body, message_type='email')

    @api.multi
    def action_set_draft(self):
        for rec in self:
            error_msg_2 = _("Attention !! \n Employee ( %s ) will be active, are you sure that you want to continue? ") % (rec.employee_id.name)
            return self.env.user.show_dialogue(error_msg_2, 'employee.eos', 'action_set_draft_continue', rec.id)

    @api.one
    def action_set_draft_continue(self):
        if self.leave_allocation:
            ctx = dict(self._context.copy(), force_delete=True)
            self.sudo().leave_allocation.with_context(ctx).action_refuse()
            self.sudo().leave_allocation.with_context(ctx).action_draft()

            self.sudo().leave_allocation.with_context(ctx).unlink()
        if self.air_ticket_allocation:
            ctx = dict(self._context.copy(), force_delete=True)
            self.sudo().air_ticket_allocation.with_context(ctx).unlink()
        self.sudo().employee_id.active = True
        self.sudo().employee_id.eos = False
        self.state = 'New'
        body = "Record Reset To Draft."
        self.message_post(body=body, message_type='email')
        self.sudo()._compute_leaves_count()
        self.sudo()._compute_annual_air_ticket_balance()
        message_1 = 'Your System automatically re-activated this employee due to Refuse EOS Process at ( %s )' % (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.sudo().employee_id.message_post(body=message_1, message_type='email')

    @api.one
    def action_refuse(self):
        if self.leave_allocation:
            ctx = dict(self._context.copy(), force_delete=True)
            self.leave_allocation.with_context(ctx).unlink()
        if self.air_ticket_allocation:
            ctx = dict(self._context.copy(), force_delete=True)
            self.air_ticket_allocation.with_context(ctx).unlink()
        self.sudo().employee_id.eos = False
        self.state = 'Refused - Cancelled'
        body = "Record Refused - Cancelled"
        self.message_post(body=body, message_type='email')

    @api.multi
    def action_approve(self):
        if not self.reason_id:
            raise exceptions.ValidationError('Kindly select EOS reason!!')
        self.recalculate_eos()
        pending_transactions = self.get_pending_transactions()
        wizard = self.env['pending.transactions.wizard'].create({
            'line_ids': [(0, 0, x) for x in pending_transactions[0]],
        })
        return {
            'domain': "[]",
            'name': _('Pending Transactions'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pending.transactions.wizard',
            'view_id': self.env.ref('saudi_hr_eos.pending_transactions_wizard').id,
            'res_id': wizard.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.multi
    def action_approve_continue(self):
        for rec in self:
            contracts = self.env['hr.contract'].search([('employee_id', '=', rec.employee_id.id), ('active', '=', True)])
            if not len(contracts):
                raise exceptions.ValidationError(
                    "Dear !! \n After your approval, your system will prepare all pending transactions related to this employee , there is a lot of important information which is recorded in employee contract, unfortunately your system could not find an active contract for this employee, kindly review your data.")
            old_eos = self.env['employee.eos'].search(
                [('employee_id', '=', rec.employee_id.id), ('id', '!=', rec.id), ('state', '!=', 'Refused - Cancelled')])
            if old_eos:
                raise exceptions.ValidationError(
                    "Not Allowed !! \n You are not allowed to Approve this EOS  request for this employee because we found that there is another EOS request which is not ( Refused - cancelled ), in order to approve this transaction, you must (Refuse - cancel) all old EOS requests related to the same employee.")
            if not rec.actual_last_working_day or not rec.actual_last_working_day_confirmed:
                raise exceptions.ValidationError(
                    "Dear !! \n In order to Approve & Calculate EOS, your system need to know what is the actual last working day, So kindly make sure to select date on ( Actual last working day ) and flag that ( actual last working day confirmed).")
            msg = _("Attention !! \n You are about to approve EOS for employee ( %s ) ") % (rec.employee_id.name)
            return self.env.user.show_dialogue(msg, 'employee.eos', 'action_approve_confirm', rec.id)

    @api.one
    def action_approve_confirm(self):
        self.state = 'Approved'
        # /////////////  send mail custom notification  /////////////////////////////////////////////
        # partners_ids = [8]
        #
        # body_html = '''
        #     <p style="margin-block-start:0px;direction: rtl;"><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">برجاء الدخول على النظام ومراجعة طلب إنهاء الخدمات للموظف </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;">(  </span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; font-size: 18px; text-align: right;">&nbsp;</span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><u>${object.employee_id.name}</u></strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;"> ) </span><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">&nbsp;</span><br></p><p style="margin-block-start:0px;"></p><p style="margin-block-start:0px;"></p><p></p><div style="direction: ltr;"><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;">Kindly login to the system and review End Of Service request for employee&nbsp;</span><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">( </span><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;"></span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right;">&nbsp;</span><strong style="font-family: inherit; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-size: initial;"><u><font style="font-size: 14px;">${object.employee_id.employee_english_name}</font></u></strong><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">)</span></div>
        #     '''
        # body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
        #     body_html, 'employee.eos', [self.id], )
        # body = body and body[self.id] or False
        #
        # self.message_post(
        #     subject='مراجعة طلب نهاية الخدمه EOS Request',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=self.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)
        # /////////////////////////////////////////////////////////////
        body = "Record Approved"
        self.message_post(body=body, message_type='email')

    @api.multi
    def action_final_approve(self):
        for rec in self:
            rec.recalculate_eos()
            old_eos = self.env['employee.eos'].search(
                [('employee_id', '=', rec.employee_id.id), ('id', '!=', rec.id), ('state', '!=', 'Refused - Cancelled')])
            if old_eos:
                raise exceptions.ValidationError(
                    "Not Allowed !! \n You are not allowed to Approve this EOS  request for this employee because we found that there is another EOS request which is not ( Refused - cancelled ), in order to approve this transaction, you must (Refuse - cancel) all old EOS requests related to the same employee.")
            pending_transactions = rec.get_pending_transactions()
            wizard = self.env['pending.transactions.wizard'].create({
                'line_ids': [(0, 0, x) for x in pending_transactions[0]],
            })
            return {
                'domain': "[]",
                'name': _('Pending Transactions'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'pending.transactions.wizard',
                'view_id': self.env.ref('saudi_hr_eos.pending_transactions_wizard_final').id,
                'res_id': wizard.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    @api.one
    def action_final_approve_continue(self):
        self.cancel_pending_transactions()
        # ///////////////////// Handle Loans ///////////////////
        if self.remaining_loan_amount > 0 and self.contract_id:
            payment_vals = {
                'contract_id': self.contract_id.id,
                'payment_date': __(self.actual_last_working_day),
                'paid_amount': self.remaining_loan_amount,
                'notes': 'Paid through EOS',
            }
            payment_id = self.env['hr.contract.loan.payment'].create(payment_vals)
            domain = [
                ('employee_id', '=', self.employee_id.id),
                ('remaining', '>', 0),
            ]
            installments = self.env['loan.installment'].search(domain)
            for installment in installments:
                installment_payment_vals = {
                    'installment_id': installment.id,
                    'paid': installment.remaining,
                    'note': 'Paid through EOS',
                }
                self.env['loan.installment.payment'].create(installment_payment_vals)
                installment.eos_id = self.id
        # ///////////////////// Handle Deductions ///////////////////
        if self.remaining_deduction > 0 and self.contract_id:
            self.env['contract.paid.violation'].create({
                'contract_id': self.contract_id.id,
                'date': __(self.actual_last_working_day),
                'amount': self.remaining_deduction,
                'note': 'Paid through EOS',
            })
            # /////////// Register payments to deductions records ////////////////////
            deductions = self.env["employee.deductions.violations"].search([
                ('state', '=', 'confirmed'),
                ('employee_id', '=', self.employee_id.id),
                ('deduction_date', '<=', __(self.actual_last_working_day)),
                ('remaining_amount', '>', 0),
            ])
            if deductions:
                remaining_deduction = self.remaining_deduction
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
                            'eos_id': self.id,
                            'paid': deducted,
                        }
                        payment_id = self.env['employee.deductions.payment'].create(payment_vals)
                        remaining_deduction -= deducted
        # //////////////////////// Handle Absence //////////////
        absences = self.env['employee.absence.line'].search(
            [('employee_id', '=', self.employee_id.id), ('paid', '=', False), ('payslip_id', '=', False)])
        for absence in absences:
            absence.paid = True
            absence.eos_id = self.id
        # ///////////////////// Handle Rewards ///////////////////
        if self.rewards > 0 and self.contract_id:
            self.env['contract.paid.rewards'].create({
                'contract_id': self.contract_id.id,
                'date': __(self.actual_last_working_day),
                'amount': self.rewards,
                'note': 'Paid through EOS',
            })
        # ///////////////////// Handle Annual Leave Balance ///////////////////
        if self.employee_id.leaves_count > 0 and self.contract_id:
            leave_allocation_data = {
                'name': 'EOS',
                'holiday_status_id': self.contract_id.annual_leave_policy.id,
                'number_of_days': self.employee_id.leaves_count * -1,
                'holiday_type': 'employee',
                'employee_id': self.employee_id.id,
                'department_id': self.employee_id.job_id.department_id.id,
                'allocation_date': __(self.actual_last_working_day),
                'system_created': True,
                'by_eos': True,
                'eos_id': self.id,
                'allow_minus_value': True,
            }
            leave_allocation = self.env['hr.leave.allocation'].create(leave_allocation_data)
            leave_allocation.action_validate()

        # ///////////////////// Handle Old leave Requests not fully reconciled ///////////////////
        if self.old_unreconciled_leaves > 0 and self.contract_id:
            leave_requests = self.env['hr.leave'].search([
                ('state', '=', 'validate'),
                ('employee_id', '=', self.employee_id.id),
                ('remaining_amount', '>', 0),
            ])
            for leave_request in leave_requests:
                self.env['leave.reconciliation.paid.line'].create({
                    'request_id': leave_request.id,
                    'date': __(self.actual_last_working_day),
                    'amount': leave_request.remaining_amount,
                    'notes': 'Paid through EOS',
                    'eos': self.id,
                })
        # ///////////////////// Handle Employee Air ticket balance ///////////////////
        if self.annual_air_ticket_balance != 0 and self.contract_id:
            air_allocation_data = {
                'reason': 'End of services',
                'allocated_balance': self.annual_air_ticket_balance * -1,
                'employee_id': self.employee_id.id,
                'allocated_date': __(self.actual_last_working_day),
                'auto_create': True,
                'eos_id': self.id,
                'allow_minus_value': True,
                'by_eos': True,
            }
            air_allocation = self.env['air.ticket.balance.allocation'].create(air_allocation_data)
            air_allocation.confirm()
        # ///////////////////// Handle Employee And Relatives ///////////////////
        self.sudo().employee_id.eos = self.id
        self.sudo().employee_id.eos_date = __(self.actual_last_working_day)
        self.sudo().employee_id.eos_reason = self.reason_id.id
        self.sudo().employee_id.net_years = self.net_years
        self.sudo().employee_id.eos_amount = self.net_eos_amount
        self.sudo().employee_id.eos_motivation = self.motivation_ids
        self.sudo().employee_id.active = False
        # self.actual_last_working_day = 0

        for employee_relative in self.employee_id.relatives:
            employee_relative.sudo().active = False

        if self.contract_id.remaining_amount > 0 or self.contract_id.remaining > 0 or self.contract_id.remaining_rewards > 0:
            raise exceptions.ValidationError(
                "Not Allowed !! \n Not allowed to inactive (%s) contract, because we found that their is (%s) Loans not paid, ( %s ) deductions not paid, (%s ) Rewards not paid. before deactivating this contract, you must close all pending amounts" % (
                    self.employee_id.name, self.remaining_loan_amount, self.remaining_deduction, self.rewards))
        self.sudo().contract_id.active = False
        self.sudo().contract_id.state = 'closed'
        self.state = 'Final Approved'
        body = "Record Final Approved"
        self.message_post(body=body, message_type='email')

    @api.one
    def cancel_pending_transactions(self):
        payslips_ids = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id), ('state', 'not in', ['cancel', 'done'])])
        if payslips_ids:
            payslips_ids.action_payslip_cancel()

        # iqama_renewal_ids = self.env['iqama.renewal'].search(
        #     [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['Confirmed', 'Refused'])])
        # if iqama_renewal_ids:
        #     iqama_renewal_ids.action_refuse()

        effective_notice_ids = self.env['effective.notice'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['Refused', 'HR department approval'])])
        if effective_notice_ids:
            effective_notice_ids.action_Refuse()

        hr_leave_ids = self.env['hr.leave'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['cancel', 'refuse', 'validate'])])
        if hr_leave_ids:
            hr_leave_ids.action_refuse()

        leave_reconciliation_ids = self.env['hr.leave.reconciliation'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['refused', 'approved'])])
        if leave_reconciliation_ids:
            leave_reconciliation_ids.action_refuse()

        air_ticket_request_ids = self.env['air.ticket.request'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['refused', 'approved'])])
        if air_ticket_request_ids:
            air_ticket_request_ids.refuse()

        # hr_exit_entry_request_ids = self.env['hr.exit.entry.request'].search(
        #     [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['confirmed'])])
        # if hr_exit_entry_request_ids:
        #     hr_exit_entry_request_ids.unlink()

        loan_ids = self.env['loan.advance.request'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['GM Approve', 'Loan Fully Paid', 'Refused'])])
        if loan_ids:
            loan_ids.action_refuse()

        deduction_ids = self.env['employee.deductions.violations'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['refused', 'confirmed'])])
        if deduction_ids:
            deduction_ids.refuse()

        absence_ids = self.env['employee.absence.line'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['Refused', 'Confirmed'])])
        if absence_ids:
            absence_ids.action_refuse()

        rewards_ids = self.env['hr.employee.rewards'].search([('employee_id', '=', self.employee_id.id), ('state', 'not in', ['confirmed'])])
        if rewards_ids:
            rewards_ids.unlink()

    @api.one
    def get_pending_transactions(self):
        payslips_ids = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id), ('state', 'not in', ['cancel', 'done'])]).ids
        # iqama_renewal_ids = self.env['iqama.renewal'].search(
        #     [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['Confirmed', 'Refused'])]).ids
        effective_notice_ids = self.env['effective.notice'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['Refused', 'HR department approval'])]).ids
        hr_leave_ids = self.env['hr.leave'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['cancel', 'refuse', 'validate'])]).ids
        leave_reconciliation_ids = self.env['hr.leave.reconciliation'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['refused', 'approved'])]).ids
        air_ticket_request_ids = self.env['air.ticket.request'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['refused', 'approved'])]).ids
        # hr_exit_entry_request_ids = self.env['hr.exit.entry.request'].search(
        #     [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['confirmed'])]).ids
        loan_ids = self.env['loan.advance.request'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['Loan Fully Paid', 'Refused', 'GM Approve'])]).ids
        deduction_ids = self.env['employee.deductions.violations'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['refused', 'confirmed'])]).ids
        absence_ids = self.env['employee.absence.line'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'not in', ['Refused', 'Confirmed'])]).ids
        rewards_ids = self.env['hr.employee.rewards'].search([('employee_id', '=', self.employee_id.id), ('state', 'not in', ['confirmed'])]).ids
        return [
            {'name': 'Employee Payslip', 'model': 'hr.payslip', 'count': len(payslips_ids), 'domain': payslips_ids, },
            # {'name': 'Employee Iqama renewal', 'model': 'iqama.renewal', 'domain': iqama_renewal_ids, 'count': len(iqama_renewal_ids)},
            {'name': 'Effective notice', 'model': 'effective.notice', 'domain': effective_notice_ids, 'count': len(effective_notice_ids)},
            {'name': 'Leave request', 'model': 'hr.leave', 'domain': hr_leave_ids, 'count': len(hr_leave_ids)},
            {'name': 'Leave Reconciliation', 'model': 'hr.leave.reconciliation', 'domain': leave_reconciliation_ids,
             'count': len(leave_reconciliation_ids)},
            {'name': 'Airticket request', 'model': 'air.ticket.request', 'domain': air_ticket_request_ids, 'count': len(air_ticket_request_ids)},
            # {'name': 'Exit and re entry request', 'model': 'hr.exit.entry.request', 'domain': hr_exit_entry_request_ids,
            #  'count': len(hr_exit_entry_request_ids)},
            {'name': 'Loan request', 'model': 'loan.advance.request', 'domain': loan_ids, 'count': len(loan_ids)},
            {'name': 'Employee Violation / deduction', 'model': 'employee.deductions.violations', 'domain': deduction_ids,
             'count': len(deduction_ids)},
            {'name': 'Employee absence report', 'model': 'employee.absence.line', 'domain': absence_ids, 'count': len(absence_ids)},
            {'name': 'Employee Rewards', 'model': 'hr.employee.rewards', 'domain': rewards_ids, 'count': len(rewards_ids)},
        ]

    @api.one
    @api.depends('payment_ids')
    def _compute_other_payment(self):
        self.other_payment = sum([l.amount for l in self.payment_ids])

    @api.multi
    def recalculate_eos_wizard(self):
        for rec in self:
            if not rec.reason_id:
                raise exceptions.ValidationError(
                    'Data Error !! \n For Employee (%s) In Order to calculate EOS elements, Kindly select EOS reason!!' % rec.employee_id.name)
            if not __(rec.actual_last_working_day):
                raise exceptions.ValidationError(
                    'Not Allowed !! \n In Order to calculate EOS for Employee (%s) you must select the actual last working day. ' % rec.employee_id.name)
            else:
                msg = _("Attention !! \n You are about to Re-calculate EOS Formula for Employee  ( %s ) "
                        "Actual last working day is ( %s ) , you must know that EOS amount and other elements may be changed"
                        " after Re-calculating End of services value due to the following reasons. \n"
                        "- Your system will re-compute all elements which may affect EOS amounts ( Remaining loan amount	-  "
                        "Remaining Violations and deductions - Absence Deduction - Notice Period Deduction - Rewards - Annual leave balance"
                        " - Leave balance in cash - Old leave requests not fully reconciled - Employee annual air ticket balance - "
                        "Last Payslip Date - GOSI …. and any other elements which may affect the equation.) \n"
                        "- If you changed the Actual last working day, EOS amount and other elements Values may be changed. \n"
                        "- if you created a payslip for this employee after creating employee EOS, your system will recalculate the all other amounts. \n"
                        "- ….. any other factors which may affect EOS will be re-computed. ") % (
                          rec.employee_id.name, __(rec.actual_last_working_day))
                return self.env.user.show_dialogue(msg, 'employee.eos', 'recalculate_eos', rec.id)

    @api.one
    def recalculate_eos(self):
        self.sudo().compute_leave_air_allocation()
        self.sudo()._compute_contract()
        self.sudo()._compute_remaining()
        self.sudo()._compute_expected_last_working_day()
        self.sudo()._compute_notice_period_difference()
        self.sudo()._compute_total_work_duration()
        self.sudo()._compute_total_unpaid_leave_duration()
        self.sudo()._compute_net_years()
        self.sudo()._compute_amount()
        self.sudo()._compute_notice_period_deduction()
        self.sudo()._compute_leave_balance_cash()
        self.sudo()._compute_old_unreconciled_leaves()
        self.sudo()._compute_leaves_count()
        self.sudo()._compute_annual_air_ticket_balance()
        self.sudo()._compute_number_of_relatives()
        self.sudo()._compute_last_payslip()
        self.sudo().get_air_ticket_price_one_way()
        self.sudo().get_absence_deduction()

    @api.one
    @api.depends('first_hiring_date')
    def _compute_first_hiring_date(self):
        if __(self.first_hiring_date):
            difference = datetime.now() - datetime.strptime(__(self.first_hiring_date), '%Y-%m-%d') 
            self.first_hiring_date = self.first_hiring_date


    @api.one
    def compute_leave_air_allocation(self):
        if self.leave_allocation:
            ctx = dict(self._context.copy(), force_delete=True)
            self.leave_allocation.with_context(ctx).action_refuse()
            self.leave_allocation.with_context(ctx).action_draft()
            self.leave_allocation.with_context(ctx).unlink()
        if self.air_ticket_allocation:
            ctx = dict(self._context.copy(), force_delete=True)
            self.air_ticket_allocation.with_context(ctx).unlink()
        # ///////////////// Handle Leave Allocations /////////////////////////
        if not self.contract_id.annual_leave_policy:
            raise exceptions.ValidationError(
                'Your system is trying to create leave allocation, there is no annual leave policy defined in the employee contract.')
        last_allocation = self.env['hr.leave.allocation'].search(
            [('state', '=', 'validate'), ('employee_id', '=', self.employee_id.id),
             ('holiday_status_id', '=', self.contract_id.annual_leave_policy.id)],
            order="allocation_date desc", limit=1)
        if last_allocation and __(last_allocation.allocation_date) and not self.leave_allocation:
            last_allocation_date = datetime.strptime(__(last_allocation.allocation_date), "%Y-%m-%d")
            actual_last_working_day = datetime.strptime(__(self.actual_last_working_day), "%Y-%m-%d")
            diff_days = relativedelta(actual_last_working_day, last_allocation_date)
            diff_months = diff_days.years * 12 + diff_days.months + (diff_days.days / 30)
            if diff_months != 0:
                if self.contract_id.annual_leave_policy.lines:
                    start_work = datetime.strptime(__(self.contract_id.start_work), "%Y-%m-%d")
                    delta = relativedelta(actual_last_working_day - start_work)
                    total_months = delta.years * 12 + delta.months + (delta.days / 30)
                    last_line = self.contract_id.annual_leave_policy.lines.search(
                        [('leave_type_id', '=', self.contract_id.annual_leave_policy.id), ('less_than', '<=', total_months),
                         ('greater_than', '>=', total_months)])
                    if not last_line:
                        last_line = self.contract_id.annual_leave_policy.lines.search(
                            [('leave_type_id', '=', self.contract_id.annual_leave_policy.id)],
                            order="greater_than asc", limit=1)
                    factor = last_line.monthly_balance
                else:
                    factor = 2.75
                allocation_days = round(diff_months * factor, 2)
                leave_allocation_data = {
                    'name': 'Auto leaves through EOS',
                    'type': 'add',
                    'holiday_status_id': self.contract_id.annual_leave_policy.id,
                    'number_of_days': allocation_days,
                    'holiday_type': 'employee',
                    'employee_id': self.employee_id.id,
                    'allocation_date': __(self.actual_last_working_day),
                    'system_created': True,
                    'eos_id': self.id,
                    'allow_minus_value': True,
                    'by_eos': True,
                }
                
                leave_allocation = self.env['hr.leave'].create(leave_allocation_data)
                leave_allocation.action_validate()
                leave_allocation.check_adjust_day()
                # leave_allocation.holidays_validate()
                leave_allocation.set_approved_by()
                self.leave_allocation = leave_allocation.id

        # ///////////////// Handle Air Tickets Allocations /////////////////////////
        if not self.contract_id.air_ticket_policy:
            raise exceptions.ValidationError(
                'Your system is trying to calculate air ticket balance for this employee, unfortunately, there is no annual air ticket policy defined in the employee contract.')
        last_air_allocation = self.env['air.ticket.balance.allocation'].search(
            [('state', '=', 'confirmed'), ('employee_id', '=', self.employee_id.id)],
            order="allocated_date desc", limit=1)
        if last_air_allocation and __(last_air_allocation.allocated_date) and not self.air_ticket_allocation:
            last_air_allocation_date = datetime.strptime(__(last_air_allocation.allocated_date), "%Y-%m-%d")
            actual_last_working_day = datetime.strptime(__(self.actual_last_working_day), "%Y-%m-%d")
            diff_days = (actual_last_working_day - last_air_allocation_date).days
            if diff_days != 0 and self.contract_id.air_ticket_policy.frequency_air_ticket == 'one time each':
                air_allocation_days = round(diff_days / 30, 2)
                air_allocation_data = {
                    'reason': 'End of services',
                    'allocated_balance': air_allocation_days,
                    'employee_id': self.employee_id.id,
                    'allocated_date': __(self.actual_last_working_day),
                    'auto_create': True,
                    'eos_id': self.id,
                    'allow_minus_value': True,
                    'by_eos': True,
                }
                air_allocation = self.env['air.ticket.balance.allocation'].create(air_allocation_data)
                air_allocation.confirm()
                self.air_ticket_allocation = air_allocation.id

    @api.one
    @api.depends('amount', 'remaining_loan_amount', 'remaining_deduction', 'absence_deduction', 'notice_period_deduction', 'rewards',
                 'leave_balance_cash',
                 'old_unreconciled_leaves', 'air_ticket_one_way', 'payslip_amount', 'other_payment', 'gosi_amount')
    def _compute_net_eos_amount(self):
        print("self.amount",self.amount)
        print("self.remaining_loan_amount",self.remaining_loan_amount)
        print("self.remaining_deduction",self.remaining_deduction)
        print("self.absence_deduction",self.absence_deduction)
        print("self.notice_period_deduction",self.notice_period_deduction)
        print("self.rewards",self.rewards)
        print("self.leave_balance_cash",self.leave_balance_cash)
        print("self.old_unreconciled_leaves",self.old_unreconciled_leaves)
        print("self.air_ticket_one_way",self.air_ticket_one_way)
        print("self.payslip_amount",self.payslip_amount)
        print("self.other_payment",self.other_payment)
        print("self.gosi_amount",self.gosi_amount)
        self.net_eos_amount = self.amount - self.remaining_loan_amount - self.remaining_deduction - self.absence_deduction + self.notice_period_deduction + self.rewards + self.leave_balance_cash + self.old_unreconciled_leaves + self.air_ticket_one_way + self.payslip_amount + self.other_payment - self.gosi_amount

    @api.one
    @api.depends('reason_id', 'contract_id', 'employee_id', 'request_date', 'actual_last_working_day')
    def _compute_last_payslip(self):
        domain = [('employee_id', '=', self.employee_id.id), ('state', 'in', ['done', 'Final Reviewed']), ]
        last_payslip = self.env['hr.payslip'].search(domain, order="date_to desc", limit=1)
        self.last_payslip = last_payslip.id
        if __(self.actual_last_working_day):
            start_date = self.last_payslip.date_to or self.first_hiring_date or self.actual_last_working_day
            difference = self.actual_last_working_day - start_date
            self.payslip_amount = difference.days / 30 * self.contract_id.total
            self.report_payslip_percent = difference.days / 30

    @api.onchange('nationality_type', 'final_exit', 'reason_final_exit', 'annual_air_ticket_balance')
    def empty_final_exit_request(self):
        self.final_exit_request = False

    @api.onchange('reason_id', 'contract_id', 'employee_id', 'request_date', 'actual_last_working_day', )
    def get_air_ticket_price_one_way(self):
        price = 0
        if self.employee_id.city_id and self.employee_id.city_id.one_way_price:
            price = self.employee_id.city_id.one_way_price
        elif self.employee_id.country_id and self.employee_id.country_id.one_way_price:
            price = self.employee_id.country_id.one_way_price
        else:
            price = 0
        if price:
            self.air_ticket_price_one_way = price

    @api.onchange('reason_id', 'contract_id', 'employee_id', 'request_date', 'actual_last_working_day', 'number_of_relatives',
                  'annual_air_ticket_balance',
                  'air_ticket_price_one_way')
    def get_air_ticket_one_way(self):
        self.air_ticket_one_way = self.air_ticket_price_one_way * (self.number_of_relatives + 1) * self.annual_air_ticket_balance

    @api.one
    @api.depends('reason_id', 'contract_id', 'employee_id', 'request_date', 'actual_last_working_day')
    def _compute_number_of_relatives(self):
        if not self.reason_id or not self.contract_id:
            self.number_of_relatives = 0
        else:
            if self.reason_id.relatives_air_ticket == 'not_included':
                self.number_of_relatives = 0
            if self.reason_id.relatives_air_ticket == 'included':
                if not self.contract_id.marital or self.contract_id.marital == 'single':
                    self.number_of_relatives = 0
                if self.contract_id.marital == 'married':
                    contract_relatives = self.contract_id.total_relatives
                    wifes = self.env['employee.relative'].search([
                        ('employee_id', '=', self.employee_id.id),
                        ('type', '=', 'Wife / Husband'),
                    ])
                    sons = self.env['employee.relative'].search([
                        ('employee_id', '=', self.employee_id.id),
                        ('type', 'in', ['Son', 'Daughter']),
                        ('date_of_birth_18', '>=', datetime.now().strftime('%Y-%m-%d')),
                    ])
                    included_relatives = len(sons)
                    if wifes:
                        included_relatives += 1
                    if contract_relatives < included_relatives:
                        self.number_of_relatives = contract_relatives
                    else:
                        self.number_of_relatives = included_relatives

    @api.one
    @api.depends('reason_id', 'contract_id', 'employee_id')
    def _compute_annual_air_ticket_balance(self):
        if not self.reason_id or not self.contract_id or not self.contract_id.air_ticket_policy:
            self.amount = 0
            return
        if self.reason_id.cash_air_tickets_allowance:
            self.annual_air_ticket_balance = self.employee_id.air_ticket_balance_button
            return
        frequency_air_ticket = self.contract_id.air_ticket_policy.frequency_air_ticket
        if frequency_air_ticket == 'One time per contract':
            requests = self.env['air.ticket.request'].search([
                ('employee_id', '=', self.employee_id.id),
                ('contract_id', '=', self.contract_id.id),
                ('state', '=', 'approved'),
                ('air_ticket_policy', '=', self.contract_id.air_ticket_policy.id),
            ])
            if requests:
                self.annual_air_ticket_balance = 0
            else:
                self.annual_air_ticket_balance = 1
        if frequency_air_ticket in ['Not allowed', 'Unlimited air tickets based on request condition']:
            self.annual_air_ticket_balance = 0
        if frequency_air_ticket == 'one time each':
            if self.employee_id.air_ticket_balance_button <= 0:
                self.annual_air_ticket_balance = self.employee_id.air_ticket_balance_button
            else:
                if self.reason_id.annual_air_ticket_balance == 'annual':
                    self.annual_air_ticket_balance = int(self.employee_id.air_ticket_balance_button)
                if self.reason_id.annual_air_ticket_balance == 'current':
                    self.annual_air_ticket_balance = self.employee_id.air_ticket_balance_button
                if not self.reason_id.annual_air_ticket_balance:
                    self.annual_air_ticket_balance = 0

    @api.one
    @api.depends('employee_id', 'contract_id')
    def _compute_old_unreconciled_leaves(self):
        leave_requests = self.env['hr.leave'].search([
            ('state', '=', 'validate'),
            ('employee_id', '=', self.employee_id.id),
            ('remaining_amount', '>', 0),
        ])
        if leave_requests:
            self.old_unreconciled_leaves = sum([l.remaining_amount for l in leave_requests])
        else:
            self.old_unreconciled_leaves = 0

    @api.one
    @api.depends('employee_id', 'contract_id', 'leaves_count', 'actual_last_working_day')
    def _compute_leave_balance_cash(self):
        if self.contract_id:
            based_on_value = 0
            if self.contract_id.annual_leave_policy.reconciliation_based_on == 'basic':
                based_on_value = self.contract_id.basic_salary
            if self.contract_id.annual_leave_policy.reconciliation_based_on == 'basic_house':
                based_on_value = self.contract_id.basic_salary + self.contract_id.house_allowance_amount
            if self.contract_id.annual_leave_policy.reconciliation_based_on == 'basic_house_transportation':
                based_on_value = self.contract_id.basic_salary + self.contract_id.house_allowance_amount + self.contract_id.transportation_allowance_amount
            if self.contract_id.annual_leave_policy.reconciliation_based_on == 'basic_house_transportation_phone':
                based_on_value = self.contract_id.basic_salary + self.contract_id.house_allowance_amount + self.contract_id.transportation_allowance_amount + self.contract_id.phone_allowance_amount
            if self.contract_id.annual_leave_policy.reconciliation_based_on == 'total':
                based_on_value = self.contract_id.total
            self.leave_balance_cash = (based_on_value / 30) * (self.leaves_count)
        else:
            self.leave_balance_cash = 0

    @api.one
    @api.depends('employee_id', 'contract_id', 'actual_last_working_day', 'notice_period_difference')
    def _compute_notice_period_deduction(self):
        if self.contract_id and self.notice_period_difference <= 0:
            self.notice_period_deduction = self.notice_period_difference * self.contract_id.total / 30
        else:
            self.notice_period_deduction = 0

    @api.onchange('employee_id')
    def get_absence_deduction(self):
        absences = self.env['employee.absence.line'].search(
            [('employee_id', '=', self.employee_id.id), ('paid', '=', False), ('payslip_id', '=', False), ('state', '=', 'Confirmed'),
             ('leave_reconciliation_id', '=', False)])
        if absences:
            self.absence_deduction = sum([l.deduction_amount for l in absences])
        else:
            self.absence_deduction = 0

    @api.onchange('first_hiring_date', 'reason_id', 'contract_id', 'calc_based_on', 'actual_last_working_day', 'net_years', 'total_number_of_years')
    def _compute_amount(self):
        if not __(self.first_hiring_date) or not self.reason_id or not self.calc_based_on or self.calc_based_on == 'no_eos' or not self.contract_id:
            self.amount = 0
            return
        based_on = 0
        if self.calc_based_on == 'basic':
            based_on = self.contract_id.basic_salary
        if self.calc_based_on == 'basic_house':
            based_on = self.contract_id.basic_salary + self.contract_id.house_allowance_amount
        if self.calc_based_on == 'basic_house_trans':
            based_on = self.contract_id.basic_salary + self.contract_id.house_allowance_amount + self.contract_id.transportation_allowance_amount
        if self.calc_based_on == 'basic_house_trans_phone':
            based_on = self.contract_id.basic_salary + self.contract_id.house_allowance_amount + self.contract_id.transportation_allowance_amount + \
                       self.contract_id.phone_allowance_amount
        if self.calc_based_on == 'total':
            based_on = self.contract_id.total

        if self.reason_id.trial_0:
            trial_date_end = __(self.contract_id.trial_date_end)
            if not self.actual_last_working_day:
                raise ValidationError(_("Please select Actual Last Working Day !!"))
            if trial_date_end and __(self.actual_last_working_day) <= trial_date_end:
                self.amount = 0
                return
        if self.reason_id.exclude_unpaid:
            years = self.net_years
        else:
            years = self.total_number_of_years
        years_amount = 0
        if years <= 0:
            self.amount = 0
            return
        if years < 5:
            years_amount = round((years * based_on / 2), 4)
        else:
            first_five_years_amount = round((5 * based_on / 2), 4)
            after_five_years = years - 5
            after_five_years_amount = round((after_five_years * based_on), 4)
            years_amount = first_five_years_amount + after_five_years_amount
        if self.reason_id.resignation:
            resignation_years_amount = 0
            if years < 2:
                self.amount = 0
            elif years <= 5:
                self.amount = round((years_amount / 3), 4)
            elif years <= 10:
                self.amount = round((years_amount * 2 / 3), 4)
            elif years > 10:
                self.amount = years_amount

        else:
            self.amount = years_amount

    @api.one
    @api.depends('total_unpaid_leaves_years', 'total_number_of_years')
    def _compute_net_years(self):
        self.net_years = self.total_number_of_years - self.total_unpaid_leaves_years

    @api.one
    @api.depends('employee_id')
    def _compute_total_unpaid_leave_duration(self):
        requests = self.env['hr.leave'].search([
            ('state', '=', 'validate'),
            ('employee_id', '=', self.employee_id.id),
            ('holiday_status_id.type', '=', 'Non Annual Leave'),
            ('holiday_status_id.non_annual_type', '=', 'Unpaid Leave'),
        ])
        total_unpaid_days = 0
        for request in requests:
            total_unpaid_days += request.number_of_days
        self.total_unpaid_leave_duration = self.employee_id.unpaid_before + total_unpaid_days
        total_unpaid_leaves_years = total_unpaid_days / 360
        self.total_unpaid_leaves_years = round(total_unpaid_leaves_years, 4)

    @api.one
    @api.depends('actual_last_working_day', 'first_hiring_date')
    def _compute_total_work_duration(self):
        if __(self.actual_last_working_day) and __(self.first_hiring_date):
            actual_last_working_day = datetime.strptime(__(self.actual_last_working_day), '%Y-%m-%d')
            first_hiring_date = datetime.strptime(__(self.first_hiring_date), '%Y-%m-%d')
            duration = relativedelta(actual_last_working_day, first_hiring_date)
            text = _('%s years , %s Months , %s Days') % (duration.years, duration.months, duration.days + 1)
            self.total_work_duration = text
            self.total_work_duration_years = duration.years
            self.total_work_duration_months = duration.months
            self.total_work_duration_days = duration.days + 1
            total_number_of_years = duration.years + duration.months / 12 + ((duration.days + 1) / 360)
            self.total_number_of_years = round(total_number_of_years, 4)

    @api.one
    @api.depends('employee_id', 'actual_last_working_day', 'expected_last_working_day')
    def _compute_notice_period_difference(self):
        if __(self.actual_last_working_day) and __(self.expected_last_working_day):
            difference = datetime.strptime(__(self.actual_last_working_day), '%Y-%m-%d') - datetime.strptime(__(self.expected_last_working_day),
                                                                                                             '%Y-%m-%d')
            self.notice_period_difference = difference.days

    @api.one
    @api.depends('employee_id', 'request_date', 'eos_notice_period')
    def _compute_expected_last_working_day(self):
        if self.eos_notice_period > 0:
            expected_last_working_day = datetime.strptime(__(self.request_date), '%Y-%m-%d') + timedelta(days=self.eos_notice_period)
            self.expected_last_working_day = expected_last_working_day.strftime('%Y-%m-%d')

    @api.onchange('employee_id')
    def _get_eos_notice_period(self):
        self.actual_last_working_day = False
        self.reason_id = False
        self.final_exit = False
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('active', '=', True)])
        if len(contracts):
            self.eos_notice_period = contracts[0].eos_notice_period
        else:
            self.eos_notice_period = 0

    @api.depends('employee_id')
    def _compute_contract(self):
        for rec in self:
            contracts = self.env['hr.contract'].search([('employee_id', '=', rec.employee_id.id), ('active', '=', True)])
            if len(contracts):
                rec.contract_id = contracts[0].id

    @api.multi
    @api.depends('employee_id')
    def name_get(self):
        res = []
        for rec in self:
            name = "EOS For %s" % rec.employee_id.name
            res += [(rec.id, name)]
        return res

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].sudo().next_by_code('employee.eos')
        res = super(employee_eos, self).create(vals)

        # /////////////  send mail custom notification  /////////////////////////////////////////////
        # partners_ids = [6, 7]
        #
        # body_html = '''
        #     <p style="margin-block-start:0px;direction: rtl;"><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">برجاء الدخول على النظام ومراجعة طلب إنهاء الخدمات للموظف </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;">(  </span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; font-size: 18px; text-align: right;">&nbsp;</span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><u>${object.employee_id.name}</u></strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;"> ) </span><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">&nbsp;</span><br></p><p style="margin-block-start:0px;"></p><p style="margin-block-start:0px;"></p><p></p><div style="direction: ltr;"><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;">Kindly login to the system and review End Of Service request for employee&nbsp;</span><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">( </span><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;"></span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right;">&nbsp;</span><strong style="font-family: inherit; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-size: initial;"><u><font style="font-size: 14px;">${object.employee_id.employee_english_name}</font></u></strong><span style="color: initial; font-family: Arial; font-size: 14px; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">)</span></div>
        #     '''
        # body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
        #     body_html, 'employee.eos', [res.id], )
        # body = body and body[res.id] or False
        #
        # res.message_post(
        #     subject='مراجعة طلب نهاية الخدمه  EOS Request',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=res.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)
        # /////////////////////////////////////////////////////////////
        return res


class employee_eos_payment_deduction(models.Model):
    _name = 'employee.eos.payment.deduction'
    _description = "EOS Record Payment Deduction"

    name = fields.Char('Description')
    amount = fields.Float('Amount ( Positive - Negative )')
    note = fields.Char('Notes')
    eos_id = fields.Many2one('employee.eos', 'EOS')


class EmployeeDeductionsPayment(models.Model):
    _inherit = "employee.deductions.payment"

    eos_id = fields.Many2one('employee.eos', 'EOS')


class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    eos_id = fields.Many2one('employee.eos', 'EOS transaction')
    actual_last_working_day = fields.Date('Actual Last Working Day')
    show_last_payslip_message = fields.Boolean(compute='_compute_show_last_payslip_message')

    @api.one
    def _compute_show_last_payslip_message(self):
        if self.eos_id and __(self.eos_id.actual_last_working_day) <= __(self.date_to) and __(self.eos_id.actual_last_working_day) >= __(
                self.date_from):
            self.show_last_payslip_message = True
        else:
            self.show_last_payslip_message = False

    @api.onchange('eos_id')
    def get_actual_last_working_day(self):
        self.actual_last_working_day = __(self.eos_id.actual_last_working_day)

    @api.onchange('employee_id')
    def get_eos_id(self):
        if self.eos_id:
            self.actual_last_working_day = __(self.eos_id.actual_last_working_day)

    @api.multi
    def compute_sheet(self):
        for rec in self:
            rec.get_eos_id()
            # rec.get_actual_last_working_day()
        res = super(hr_payslip, self).compute_sheet()
        return res
