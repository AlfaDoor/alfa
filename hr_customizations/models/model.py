from odoo import models, fields, api, _
from datetime import date, datetime, time
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import datetime
from datetime import timedelta


class InheritLeave(models.Model):
    _inherit = 'hr.leave'
    gurantees_ids = fields.One2many('employee.gurantee', 'employee_ids', string='Gurantee')

    def update_employee_status(self):
        date_now = str(date.today())
        leave_record = self.env['hr.leave'].search([('state', '=', 'validate')])
        for rec in leave_record:
            date_from = (rec.date_from).strftime('%Y-%m-%d')
            if date_from == date_now:
                rec.employee_id.employee_status = self.env['employee.status'].search([('s_no', '=', 13)])


class EffectiveNotice(models.Model):
    _inherit = 'effective.notice'

    @api.multi
    def action_hr_department_approval(self):
        if self.employee_id.employee_status.s_no == 14:
            self.employee_id.employee_status = self.env['employee.status'].search([('name', '=', 'ACTIVE')])
        return super(EffectiveNotice, self).action_hr_department_approval()

    @api.model
    def create(self, vals):
        employee_rec = self.env['hr.employee'].search([('id', '=', vals['employee_id'])])
        if not employee_rec.employee_status.s_no == 13:
            return super(EffectiveNotice, self).create(vals)
        else:
            employee_rec.employee_status = self.env['employee.status'].search([('s_no', '=', 14)])
        return super(EffectiveNotice, self).create(vals)


class EndOfService(models.Model):
    _inherit = 'employee.eos'

    payment_id = fields.Integer()
    is_payment = fields.Boolean(default=False)

    @api.one
    def action_final_approve_continue(self):
        if self.employee_id:
            self.employee_id.employee_status = self.env['employee.status'].search([('s_no', '=', 8)])
        return super(EndOfService, self).action_final_approve_continue()

    @api.multi
    def action_create_payment(self):
        partner = self.env['res.partner'].search([('name', 'like', 'Accrued Employee')], limit=1)
        if self.is_payment == True:
            raise UserError(_("Payment already created."))
        if not partner:
            raise UserError(_("There is no partner found with the Accrued Employee."))
        if self.net_eos_amount == 0.0:
            raise UserError(_("Payment could not suppose to be zero amount, please Enter the Amount."))
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'payment_method_id': 2,
            'partner_id': partner.id,
            'partner_type': 'supplier',
            'amount': self.net_eos_amount,
            'journal_id': 9,
            'payment_date': fields.Date.today(),
            'state': 'draft',
            'communication': 'End of Service',
            'employee': self.employee_id.id
        })
        self.payment_id = payment.id
        self.is_payment = True

    @api.multi
    def action_payment_view(self):
        return {
            'name': _('Payment'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', '=', self.payment_id)],
        }


class EmployeeGurantee(models.Model):
    _name = 'employee.gurantee'
    employee_ids = fields.Many2one('hr.leave')
    employees = fields.Many2one('hr.employee')
    amount = fields.Integer()
    is_deduction = fields.Boolean()
    loan_type = fields.Many2one('hr_loans.loan_advance')
    deduction_count = fields.Integer(default=0)

    @api.multi
    def make_deduction(self):
        if self.is_deduction == True:
            if self.deduction_count == 0:
                self.env['loan.advance.request'].create({'employee_id': self.employees.id,
                                                         'reason': self.employee_ids.name,
                                                         'loan_type': self.loan_type.id,
                                                         'date': date.today(),
                                                         'loan_amount': self.amount
                                                         })
                self.deduction_count += 1
            else:
                raise ValidationError(_('Deduction record already created for this line'))


class fee_voucher(models.TransientModel):
    _name = 'department.new'
    current_department = fields.Many2one('hr.department')
    new_department = fields.Many2one('hr.department')

    def change_department(self):
        rec = self.env['hr.employee'].search([('id', '=', self._context['active_id'])])
        rec.department_id = self.new_department


class InheritEmployee(models.Model):
    _inherit = 'hr.employee'
    responsible_emp = fields.Many2one('res.users')
    overtime_allow = fields.Boolean(default=False)

    # def check_mail_expiry_dates(self):
    #
    #     date_now = datetime.date.today() + timedelta(days=30)
    #     iqama_records = self.env['hr.employee'].search(
    #         [('iqama_expiry_date', '<=', date_now), ('iqama_expiry_date', '>=', datetime.date.today())])
    #     for rec in iqama_records:
    #         mail_content = "The Iqama of " + rec.name + "is going to expire on " + str(
    #             rec.iqama_expiry_date) + ".<br> Please renew it before expiry date"
    #         main_content = {
    #             'subject': _('Iqama Expiry'),
    #             'author_id': self.env.user.partner_id.id,
    #             'body_html': mail_content,
    #             'email_to': 'barrak@musaidalsayyarco.com,hradmin@musaidalsayyarco.com,a.aziz@musaidalsayyarco.com',
    #         }
    #         self.env['mail.mail'].create(main_content).send()
    #
    #     passport_records = self.env['hr.employee'].search(
    #         [('passport_expiry_date', '<=', date_now), ('passport_expiry_date', '>=', datetime.date.today())])
    #     for rec in passport_records:
    #         mail_content = "The Passport of " + rec.name + "is going to expire on " + str(
    #             rec.passport_expiry_date) + ".<br> Please renew it before expiry date"
    #         main_content = {
    #             'subject': _('Passport Expiry'),
    #             'author_id': self.env.user.partner_id.id,
    #             'body_html': mail_content,
    #             'email_to': 'barrak@musaidalsayyarco.com,hradmin@musaidalsayyarco.com,a.aziz@musaidalsayyarco.com',
    #         }
    #         self.env['mail.mail'].create(main_content).send()
    #
    #     insurance_records = self.env['hr.employee'].search(
    #         [('med_ins_expiry_date', '<=', date_now), ('med_ins_expiry_date', '>=', datetime.date.today())])
    #     for rec in insurance_records:
    #         mail_content = "The Medical Insurance of " + rec.name + "is going to expire on " + str(
    #             rec.med_ins_expiry_date) + ".<br> Please renew it before expiry date"
    #         main_content = {
    #             'subject': _('Insurance Expiry'),
    #             'author_id': self.env.user.partner_id.id,
    #             'body_html': mail_content,
    #             'email_to': 'barrak@musaidalsayyarco.com,hradmin@musaidalsayyarco.com,a.aziz@musaidalsayyarco.com',
    #         }
    #         self.env['mail.mail'].create(main_content).send()
    #
    #     health_records = self.env['hr.employee'].search(
    #         [('health_expiry_date', '<=', date_now), ('health_expiry_date', '>=', datetime.date.today())])
    #     for rec in insurance_records:
    #         mail_content = "The Health Certificate of " + rec.name + "is going to expire on " + str(
    #             rec.health_expiry_date) + ".<br> Please renew it before expiry date"
    #         main_content = {
    #             'subject': _('Health Certificate Expiry'),
    #             'author_id': self.env.user.partner_id.id,
    #             'body_html': mail_content,
    #             'email_to': 'barrak@musaidalsayyarco.com,hradmin@musaidalsayyarco.com,a.aziz@musaidalsayyarco.com',
    #         }
    #         self.env['mail.mail'].create(main_content).send()
    #

# class InheritSubscription(models.Model):
#     _inherit = 'sale.subscription'
#
#     def check_subscription(self):
#         date_now = datetime.date.today() + timedelta(days=15)
#         stages = self.env['sale.subscription.stage'].search([('name', '=', 'In Progress')])
#         subs_record = self.env['sale.subscription'].search(
#             [('recurring_next_date', '<=', date_now), ('recurring_next_date', '>=', datetime.date.today()),
#              ('stage_id', '=', stages.id)])
#         for rec in subs_record:
#             mail_content = "The Subscription of " + rec.display_name + "is going to expire on " + str(
#                 rec.recurring_next_date) + ".<br> Please renew it before expiry date"
#             main_content = {
#                 'subject': _('Subscription Expiry'),
#                 'author_id': self.env.user.partner_id.id,
#                 'body_html': mail_content,
#                 'email_to': 'barrak@musaidalsayyarco.com,hradmin@musaidalsayyarco.com,m.gad@musaidalsayyarco.com,rawan@musaidalsayyarco.com,hessa.m@musaidalsayyarco.com',
#             }
#             self.env['mail.mail'].create(main_content).send()
#

class InheritContract(models.Model):
    _inherit = 'hr.contract'

    manual_working_hours = fields.Boolean(default=False, string='Manual Working hours')
    working_hours_per_day = fields.Float(string='Working hours per day')
    wh_effective_from = fields.Date('Working hours Effective from')
    wh_effective_to = fields.Date('Working hours Effective to')

    # def check_contract_date(self):
    #
    #     date_now = datetime.date.today()
    #     contract_record_first = self.env['hr.contract'].search([('trial_duration', '<=', 90), ('state', '=', 'open')])
    #     for rec in contract_record_first:
    #         if rec.trial_date_end:
    #             if date_now == rec.trial_date_end - timedelta(days=25):
    #                 mail_content = "The trial duration of " + rec.name + " is " + str(
    #                     rec.trial_duration) + ", and it is going to end on " + str(
    #                     rec.trial_date_end) + ".<br> Please do needful before it ends"
    #                 main_content = {
    #                     'subject': _('Trial Period Expiry'),
    #                     'author_id': self.env.user.partner_id.id,
    #                     'body_html': mail_content,
    #                     'email_to': 'barrak@musaidalsayyarco.com,hradmin@musaidalsayyarco.com',
    #                 }
    #                 self.env['mail.mail'].create(main_content).send()
    #
    #     contract_record_second = self.env['hr.contract'].search([('trial_duration', '>', 90), ('state', '=', 'open')])
    #     for rec in contract_record_second:
    #         if rec.trial_date_end:
    #             if date_now == rec.trial_date_end - timedelta(days=25):
    #                 mail_content = "The trial duration of " + rec.name + " is " + str(
    #                     rec.trial_duration) + ", and it is going to end on " + str(
    #                     rec.trial_date_end) + ".<br> Please do needful before it ends"
    #                 main_content = {
    #                     'subject': _('Trial Period Expiry'),
    #                     'author_id': self.env.user.partner_id.id,
    #                     'body_html': mail_content,
    #                     'email_to': 'barrak@musaidalsayyarco.com,hradmin@musaidalsayyarco.com',
    #                 }
    #                 self.env['mail.mail'].create(main_content).send()

    # def check_contract_expiry(self):
    #
    #     date_now = datetime.date.today() + timedelta(days=30)
    #     contract_records = self.env['hr.contract'].search(
    #         [('date_end', '<=', date_now), ('date_end', '>=', datetime.date.today())])
    #     for rec in contract_records:
    #         if rec.date_end:
    #             if rec.date_end <= date_now and rec.date_end >= datetime.date.today():
    #                 mail_content = "The Contract of " + rec.name + "is going to expire on " + str(
    #                     rec.date_end) + ".<br> Please renew it before expiry date"
    #                 main_content = {
    #                     'subject': _('Contract Expiry'),
    #                     'author_id': self.env.user.partner_id.id,
    #                     'body_html': mail_content,
    #                     'email_to': 'barrak@musaidalsayyarco.com,hradmin@musaidalsayyarco.com',
    #                 }
    #                 self.env['mail.mail'].create(main_content).send()
    #
#
# class PayslipInherit(models.Model):
#     _inherit = 'hr.payslip'
#     working_h = fields.Many2one(related='contract_id.resource_calendar_id')
#     update_no = fields.Boolean(default=False)
#     no_of_hours_legal_n = fields.Float(compute='get_working_hours_do', store=True, string='Total Legal Working Hours')
#     no_of_hours_work_n = fields.Float(compute='get_working_hours_do', store=True)
#     no_of_overtime_hours_n = fields.Float(compute='get_working_hours_do', string='Total Overtime hours', store=True)
#     no_of_delay_hours_n = fields.Float(compute='get_working_hours_do', string='Total Delay hours', store=True)
#     amount_overtime_hours_n = fields.Float(compute='get_working_hours_do', store=True)
#     amount_delay_hours_n = fields.Float(compute='get_hours_rate', store=True)
#     no_of_work_days_n = fields.Integer(compute='get_working_hours_do', store=True)
#     no_of_work_days_att_n = fields.Integer(compute='get_working_hours_do', store=True)
#     total_absent_days_n = fields.Integer(compute='get_working_hours_do', store=True)
#     total_absent_hours_n = fields.Float(compute='get_working_hours_do', store=True)
#
#     @api.multi
#     @api.depends('date_from','date_to','employee_id.overtime_allow','contract_id.manual_working_hours','employee_id','name')
#     def get_working_hours_do(self):
#         for rec in self:
#             if rec.update_no == False:
#                 attendances = self.env['working.days'].search(
#                     [('employee_id', '=', rec.employee_id.id), ('date', '>=', rec.date_from),
#                      ('date', '<=', rec.date_to)])
#                 days_att = attendances.filtered(lambda x: x.att_count == 2 and x.is_manipulate == False)
#                 rec.no_of_work_days_att_n = len(days_att)
#                 if attendances:
#                     working = 0.0
#                     overtime = 0.0
#                     delay = 0.0
#                     for record in attendances:
#                         working += record.total_working_minutes
#                         overtime += record.overtime_minutes
#                         delay += record.delay_minutes
#                     rec.no_of_hours_work_n = working
#                     rec.no_of_delay_hours_n = delay
#                     if rec.employee_id.overtime_allow == True:
#                         rec.no_of_overtime_hours_n = overtime
#                     else:
#                         rec.no_of_overtime_hours_n = 0.0
#                     day_from = datetime.datetime.combine(fields.Date.from_string(rec.date_from), time.min)
#                     day_to = datetime.datetime.combine(
#                         fields.Date.from_string(attendances[-1].date), time.max)
#                     contract = rec.contract_id
#                     resource = contract.resource_calendar_id
#                     if resource:
#                         work_data = contract.employee_id.get_work_days_data(day_from, day_to, calendar=resource)
#                         rec.no_of_work_days_n = work_data['days']
#                         rec.total_absent_days_n = rec.no_of_work_days_n - rec.no_of_work_days_att_n
#                         if contract.manual_working_hours == False:
#                             rec.no_of_hours_legal_n = work_data['hours']
#                         else:
#                             if contract.wh_effective_from >= rec.date_from and contract.wh_effective_to > rec.date_to:
#                                 day_from_x = datetime.datetime.combine(
#                                     fields.Date.from_string(contract.wh_effective_from),
#                                     time.min)
#                                 day_to_x = datetime.datetime.combine(fields.Date.from_string(attendances[-1].date),
#                                                                      time.max)
#                                 work_data = contract.employee_id.get_work_days_data(day_from_x, day_to_x,
#                                                                                     calendar=resource)
#                                 wh_manual = work_data['days'] * contract.working_hours_per_day
#                                 day_from_xx = datetime.datetime.combine(fields.Date.from_string(rec.date_from),
#                                                                         time.min)
#                                 day_to_xx = datetime.datetime.combine(
#                                     fields.Date.from_string(contract.wh_effective_from - timedelta(days=1)), time.max)
#                                 wh_actual = contract.employee_id.get_work_days_data(day_from_xx, day_to_xx,
#                                                                                     calendar=resource)
#                                 rec.no_of_hours_legal_n = wh_actual['hours'] + wh_manual
#                             if contract.wh_effective_from <= rec.date_from and contract.wh_effective_to < rec.date_to:
#                                 day_from_x = datetime.datetime.combine(fields.Date.from_string(rec.date_from), time.min)
#                                 day_to_x = datetime.datetime.combine(fields.Date.from_string(contract.wh_effective_to),
#                                                                      time.max)
#                                 work_data = contract.employee_id.get_work_days_data(day_from_x, day_to_x,
#                                                                                     calendar=resource)
#                                 wh_manual = work_data['days'] * contract.working_hours_per_day
#                                 day_from_xx = datetime.datetime.combine(
#                                     fields.Date.from_string(contract.wh_effective_to + timedelta(days=1)), time.min)
#                                 day_to_xx = datetime.datetime.combine(fields.Date.from_string(attendances[-1].date),
#                                                                       time.max)
#                                 wh_actual = contract.employee_id.get_work_days_data(day_from_xx, day_to_xx,
#                                                                                     calendar=resource)
#                                 rec.no_of_hours_legal_n = wh_actual['hours'] + wh_manual
#                             if contract.wh_effective_from > rec.date_from and contract.wh_effective_to <= rec.date_to:
#                                 day_from_x = datetime.datetime.combine(
#                                     fields.Date.from_string(contract.wh_effective_from),
#                                     time.min)
#                                 day_to_x = datetime.datetime.combine(fields.Date.from_string(contract.wh_effective_to),
#                                                                      time.max)
#                                 work_data = contract.employee_id.get_work_days_data(day_from_x, day_to_x,
#                                                                                     calendar=resource)
#                                 wh_manual = work_data['days'] * contract.working_hours_per_day
#                                 day_from_xx = datetime.datetime.combine(fields.Date.from_string(rec.date_from),
#                                                                         time.min)
#                                 day_to_xx = datetime.datetime.combine(fields.Date.from_string(attendances[-1].date),
#                                                                       time.max)
#                                 wh_actual = contract.employee_id.get_work_days_data(day_from_xx, day_to_xx,
#                                                                                     calendar=resource)
#                                 per_day_actual = wh_actual['hours'] / wh_actual['days']
#                                 diff_days = wh_actual['days'] - work_data['days']
#                                 legal_wh = diff_days * per_day_actual
#                                 rec.no_of_hours_legal_n = legal_wh + wh_manual
#                             if contract.wh_effective_from == rec.date_from and contract.wh_effective_to == rec.date_to:
#                                 day_from_x = datetime.datetime.combine(
#                                     fields.Date.from_string(contract.wh_effective_from),
#                                     time.min)
#                                 day_to_x = datetime.datetime.combine(fields.Date.from_string(attendances[-1].date),
#                                                                      time.max)
#                                 work_data = contract.employee_id.get_work_days_data(day_from_x, day_to_x,
#                                                                                     calendar=resource)
#                                 wh_manual = work_data['days'] * contract.working_hours_per_day
#                                 rec.no_of_hours_legal_n = wh_manual
#                             if rec.date_to < contract.wh_effective_from:
#                                 day_from_x = datetime.datetime.combine(
#                                     fields.Date.from_string(rec.date_from),
#                                     time.min)
#                                 day_to_x = datetime.datetime.combine(fields.Date.from_string(attendances[-1].date),
#                                                                      time.max)
#                                 work_data = contract.employee_id.get_work_days_data(day_from_x, day_to_x,
#                                                                                     calendar=resource)
#                                 wh_manual = work_data['hours']
#                                 rec.no_of_hours_legal_n = wh_manual
#                     ######### for overtime amount ############
#                     day_from = datetime.datetime.combine(fields.Date.from_string(rec.date_from), time.min)
#                     day_to = datetime.datetime.combine(fields.Date.from_string(rec.date_to), time.max)
#                     contract = rec.contract_id
#                     resource = contract.resource_calendar_id
#                     basic = contract.basic_salary
#                     if resource:
#                         work_data = contract.employee_id.get_work_days_data(day_from, day_to, calendar=resource)
#                         total_hours = rec.no_of_hours_legal_n
#                         if total_hours:
#                             per_hour = basic / total_hours
#                             if rec.employee_id.overtime_allow == True:
#                                 rec.amount_overtime_hours_n = per_hour * rec.no_of_overtime_hours_n
#                             else:
#                                 rec.amount_overtime_hours_n = 0.0
#
#     @api.multi
#     @api.depends('date_from', 'date_to', 'employee_id.overtime_allow', 'contract_id.manual_working_hours','employee_id', 'name')
#     def get_hours_rate(self):
#         for rec in self:
#             contract = rec.contract_id
#             basic = contract.basic_salary
#             day_from = datetime.datetime.combine(fields.Date.from_string(rec.date_from), time.min)
#             day_to = datetime.datetime.combine(fields.Date.from_string(rec.date_to), time.max)
#             resource = contract.resource_calendar_id
#             if resource:
#                 work_data = contract.employee_id.get_work_days_data(day_from, day_to, calendar=resource)
#                 total_hours = rec.no_of_hours_legal_n
#                 if total_hours:
#                     per_hour = basic / total_hours
#                     rec.amount_delay_hours_n = per_hour * rec.no_of_delay_hours_n
