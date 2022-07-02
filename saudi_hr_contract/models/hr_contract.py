# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import __


class hr_employee(models.Model):
    _inherit = "hr.employee"

    employee_english_name = fields.Char(_('Employee English Name'))
    employee_number = fields.Char(_('Employee Number'))
    branch_id = fields.Many2one('hr.branch', 'branch name')


class hr_contract(models.Model):
    _inherit = "hr.contract"

    _ALLOWANCE = [
        ('none', 'None'),
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage from Basic'),
    ]
    contract_date = fields.Date('Contract date')
    employee_eng_name = fields.Char('Employee arabic name', related='employee_id.employee_english_name', readonly=True)
    employee_number = fields.Char('employee number', related='employee_id.employee_number', readonly=True)
    active = fields.Boolean(_('Active'), default=True)
    nationality = fields.Many2one('res.country', 'Nationality', related="employee_id.country_id", readonly=True, store=True)
    nationality_type = fields.Selection([('Native', 'Native'),
                                         ('Non-native', 'Non-native')], _('Nationality type'), related="employee_id.nationality_type", readonly=True)
    trial_wage = fields.Float(_('trial Basic Salary'))
    trial_house_allowance_type = fields.Selection(_ALLOWANCE, _('trial House Allowance'), default='none')
    trial_house_allowance = fields.Float(_('trial House Allowance'))
    trial_house_allowance_amount = fields.Float(_('trial House Allowance'), compute='_get_trial_allowance')
    trial_transportation_allowance_type = fields.Selection(_ALLOWANCE, _('trial Transportation Allowance'), default='none')
    trial_transportation_allowance = fields.Float(_('trial Transportation Allowance'))
    trial_transportation_allowance_amount = fields.Float(_('trial Transportation Allowance'), compute='_get_trial_allowance')
    trial_phone_allowance_type = fields.Selection(_ALLOWANCE, _('trial Phone Allowance'), default='none')
    trial_phone_allowance = fields.Float(_('trial Phone Allowance'))
    trial_phone_allowance_amount = fields.Float(_('trial Phone Allowance'), compute='_get_trial_allowance')
    trial_food_allowance_type = fields.Selection(_ALLOWANCE, _('trial Food Allowance'), default='none')
    trial_food_allowance = fields.Float(_('trial Food Allowance'))
    trial_food_allowance_amount = fields.Float(_('trial Food Allowance'), compute='_get_trial_allowance')
    trial_insurance = fields.Boolean(_('Trial Medical Insurance Covered'), default=True)
    trial_commission = fields.Selection([('illegible', 'Illegible'), ('not_illegible', 'Not Illegible')], _('trial Commission'),
                                        default='not_illegible')
    trial_other_allowance = fields.Float(_('Other Allowance'))
    trial_other_allowance_name = fields.Char(_('Other Allowance Name'))
    trial_total = fields.Float(_('Total'), compute='_get_trial_total', readonly=True)
    date_end = fields.Date('End Date', readonly=True, compute='_compute_date_end')
    duration_type = fields.Selection([('Limited Time Contract', 'Limited Time Contract'),
                                      ('Unlimited Time Contract', 'Unlimited Time Contract')], string='Duration Type')
    duration_months = fields.Float(string="Duration In Months")
    total_contract_duration = fields.Char(string='Total Contract Duration', readonly=True, compute='_compute_total_contract_duration', multi=True,
                                          store=True)
    total_contract_remaining = fields.Char(string='Remaining before expiry', readonly=True, compute='_compute_total_contract_duration', multi=True)
    last_active_duration = fields.Char(string='Total Contract Duration', readonly=True)
    job_id = fields.Many2one('hr.job', 'Job Title', related='employee_id.job_id', readonly=True)
    marital = fields.Selection([('single', 'Single'), ('married', 'Married')], 'Single / Married')
    # end_reminder = fields.Integer('Reminder To Review Before End On Contractual Year',help='If = 3, this mean that your system will send a notification and Email to the employee and HR manager to re-check the contract renewing 3 months before the end of contractual year.')
    renewal_type = fields.Selection([('auto', 'Auto renewal, no need for any action from HR department'),
                                     ('manual', 'Manual renewal, HR department must renew the contract')], string='Renewal Type')

    state = fields.Selection(
        [('draft', 'New'), ('open', 'Running'), ('pending', 'To Renew'), ('close', 'Expired'), ('closed', 'Closed')],
    )
    working_hours = fields.Many2one('resource.calendar', ondelete="restrict")
    hr_approval = fields.Boolean('HR Manager Approval')
    end_trial_period_approved = fields.Boolean('End of trial period. Approved contract')

    branch_id = fields.Many2one('hr.branch', string='Branch', related="employee_id.branch_id", readonly=True, store=True)

    salary_scale_id = fields.Char('Salary scale')
    salary_level_id = fields.Char('Salary level')
    salary_degree_id = fields.Char('Salary degree')

    @api.one
    def end_trial_period_approve(self):
        self.end_trial_period_approved = True
        # body = "End of trial period process completed, Estimated End of trial period date was ( %s ) Actual End of trial period date is ( %s )" %\
        #        (old_trial_date_end,actual_date)
        # self.message_post(body=body, message_type='email')

    @api.one
    def hr_approve(self):
        self.hr_approval = True
        self.update_state_single()

    @api.model
    def update_state(self):
        for contract in self.search([('active', '=', True)]):
            contract.update_state_single()

    @api.one
    def update_state_single(self):
        if not self.department_id:
            self.department_id = self.employee_id.department_id.id
        if __(self.date_end) and __(self.start_work) and self.hr_approval:
            if self.state == 'draft':
                self.state = 'open'

    @api.model
    def create(self, vals):
        res = super(hr_contract, self).create(vals)

        # /////////////  send mail custom notification  /////////////////////////////////////////////
        partners_ids = [8]

        body_html = '''
            <p style="margin-block-start:0px;direction: rtl;"><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">تمت اضافة عقد جديد للموظف </span><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">( </span><span style="font-family: Arial; text-align: right; white-space: pre-wrap;"> </span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="font-family: Arial; font-size: 18px; text-align: right;">&nbsp;</span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><u>${object.employee_id.name}</u></strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;"> </span><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">)</span><span style="font-family: Arial; text-align: right; white-space: pre-wrap;"> .. يرجى الدخول على النظام وتأكيد عقد الموظف. حيث انه لن يتم اصدار رواتب للموظف إلا بعد تأكيد العقد.</span><br></p><p style="margin-block-start:0px;"></p><p style="margin-block-start:0px;"></p><p style="margin-block-start:0px;"></p><div style="direction: ltr;"><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;">Contract has been created for employee </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;">( </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;"> </span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; font-size: 18px; text-align: right;">&nbsp;</span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><u>${object.employee_id.employee_english_name}</u></strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;"> </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;">) , you are requested to login to the system and approve this contract in order to avoid salary blocking</span></div>
            '''
        body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
            body_html, 'hr.contract', [res.id], )
        body = body and body[res.id] or False

        # res.message_post(
        #     subject='تأكيد عقد Contract approval',
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
    def write(self, vals):

        old_active = self.active
        # Write your logic here
        res = super(hr_contract, self).write(vals)

        new_active = self.active
        if old_active and not new_active:
            self.last_active_duration = self.total_contract_duration

        # Write your logic here
        return res

    @api.depends('trial_date_start', 'date_start', 'date_end')
    def _compute_total_contract_duration(self):
        for rec in self:
            rec._compute_date_end()
            now = datetime.now()
            if rec.date_start:
                start_date = datetime.strptime(__(rec.date_start), "%Y-%m-%d")
            if rec.trial_date_start:
                start_date = datetime.strptime(__(rec.trial_date_start), "%Y-%m-%d")
            if rec.date_end:
                end_date = datetime.strptime(__(rec.date_end), "%Y-%m-%d")
            if rec.date_start and rec.date_end:
                duration = relativedelta(end_date, start_date)
                remaining = relativedelta(end_date, now)
                rec.total_contract_duration = self.alphabet_date(duration)
                rec.total_contract_remaining = self.alphabet_date(remaining)

    @api.model
    def alphabet_date(self, datetime):
        total_str = ''
        if datetime.years:
            total_str += _('%s years, ' % (datetime.years))
        if datetime.months:
            total_str += _('%s months, ' % (datetime.months))
        if datetime.days:
            total_str += _('%s days' % (datetime.days))
        return total_str

    @api.multi
    @api.depends('duration_type', 'duration_months', 'date_start')
    def _compute_date_end(self):
        for rec in self:
            if rec.duration_type != "Limited Time Contract":
                rec.duration_months = 1000
            duration_months = rec.duration_months
            number_dec = duration_months - int(duration_months)
            int_duration_months = int(duration_months)
            int_days = int(number_dec * 30)
            if __(rec.date_start):
                date_start = datetime.strptime(__(rec.date_start), "%Y-%m-%d")
                end_date = date_start + relativedelta(months=int_duration_months, days=int_days - 1)
                rec.date_end = end_date.strftime("%Y-%m-%d")

    @api.multi
    @api.depends('trial_wage', 'trial_house_allowance_amount', 'trial_transportation_allowance_amount', 'trial_phone_allowance_amount',
                 'trial_food_allowance_amount', 'trial_other_allowance')
    def _get_trial_total(self):
        for record in self:
            record.trial_total = record.trial_wage + record.trial_house_allowance_amount + record.trial_transportation_allowance_amount + \
                                 record.trial_phone_allowance_amount + record.trial_other_allowance + record.trial_food_allowance_amount

    @api.multi
    @api.depends('trial_wage', 'trial_house_allowance_type', 'trial_house_allowance', 'trial_transportation_allowance_type',
                 'trial_transportation_allowance', 'trial_phone_allowance_type', 'trial_phone_allowance', 'trial_food_allowance_type', 'trial_food_allowance')
    def _get_trial_allowance(self):
        for record in self:
            if record.trial_house_allowance_type == 'none':
                record.trial_house_allowance_amount = record.trial_house_allowance = 0.0
            elif record.trial_house_allowance_type == 'fixed':
                record.trial_house_allowance_amount = record.trial_house_allowance
            else:
                record.trial_house_allowance_amount = record.trial_house_allowance * record.trial_wage / 100.0

            if record.trial_transportation_allowance_type == 'none':
                record.trial_transportation_allowance_amount = record.trial_transportation_allowance = 0.0
            elif record.trial_transportation_allowance_type == 'fixed':
                record.trial_transportation_allowance_amount = record.trial_transportation_allowance
            else:
                record.trial_transportation_allowance_amount = record.trial_transportation_allowance * record.trial_wage / 100.0

            if record.trial_phone_allowance_type == 'none':
                record.trial_phone_allowance_amount = record.trial_phone_allowance = 0.0
            elif record.trial_phone_allowance_type == 'fixed':
                record.trial_phone_allowance_amount = record.trial_phone_allowance
            else:
                record.trial_phone_allowance_amount = record.trial_phone_allowance * record.trial_wage / 100.0

            if record.trial_food_allowance_type == 'none':
                record.trial_food_allowance_amount = record.trial_food_allowance = 0.0
            elif record.trial_food_allowance_type == 'fixed':
                record.trial_food_allowance_amount = record.trial_food_allowance
            else:
                record.trial_food_allowance_amount = record.trial_food_allowance * record.trial_wage / 100.0

    basic_salary = fields.Float(_('Basic Salary'))
    house_allowance_type = fields.Selection(_ALLOWANCE, _('House Allowance type'), default='none')
    house_allowance = fields.Float(_('House Allowance'))
    house_allowance_amount = fields.Float(_('House Allowance amount'), compute='_get_allowance')
    transportation_allowance_type = fields.Selection(_ALLOWANCE, _('Transportation Allowance'), default='none')
    transportation_allowance = fields.Float(_('Transportation Allowance'))
    transportation_allowance_amount = fields.Float(_('Transportation Allowance'), compute='_get_allowance')
    phone_allowance_type = fields.Selection(_ALLOWANCE, _('Phone Allowance'), default='none')
    phone_allowance = fields.Float(_('Phone Allowance'))
    phone_allowance_amount = fields.Float(_('Phone Allowance'), compute='_get_allowance')
    food_allowance_type = fields.Selection(_ALLOWANCE, _('food Allowance'), default='none')
    food_allowance = fields.Float(_('food Allowance'))
    food_allowance_amount = fields.Float(_('food Allowance'), compute='_get_allowance')
    insurance = fields.Boolean(_('Medical Insurance Covered'), default=True)
    commission = fields.Selection([('illegible', 'Illegible'),
                                   ('not_illegible', 'Not Illegible')], _('Commission'), default='not_illegible')
    other_allowance = fields.Float(_('Other Allowance'))
    other_allowance_name = fields.Char(_('Other Allowance Name'))
    total = fields.Float(_('Total'), compute='_get_total', readonly=True, store=True)
    current_version = fields.Integer('Current Version', default=1)

    trial_date_start = fields.Date('Trial Start Date')
    trial_date_end = fields.Date('Trial End Date', compute='_compute_trial_date_end', store=True)
    trial_duration = fields.Integer('Trial period duration')
    approved_record = fields.Boolean('Approved Record', compute='_compute_approved_record', search='_search_aapproved_record')

    @api.one
    @api.depends('name')
    def _compute_approved_record(self):
        if self.env.user.has_group('saudi_hr_employee.group_hr_contract_create') or self.employee_id.user_id.id == self.env.user.id:
            self.approved_record = True
        else:
            self.approved_record = False
        self.approved_record = True

    def _search_aapproved_record(self, operator, value):
        contracts = self.search([])
        if self.env.user.has_group('saudi_hr_employee.group_hr_contract_create'):
            return [('id', 'in', contracts.ids)]
        else:
            return [('employee_id.user_id', '=', self.env.user.id)]

    @api.one
    @api.depends('trial_date_start', 'trial_duration')
    def _compute_trial_date_end(self):
        if self.trial_date_start and self.trial_duration:
            trial_date_start = datetime.strptime(__(self.trial_date_start), '%Y-%m-%d')
            trial_date_end = trial_date_start + relativedelta(days=self.trial_duration - 1)
            self.trial_date_end = trial_date_end.strftime('%Y-%m-%d')

    @api.multi
    @api.depends('basic_salary', 'house_allowance_amount', 'transportation_allowance_amount', 'phone_allowance_amount', 'food_allowance_amount',
                 'other_allowance')
    def _get_total(self):
        for record in self:
            record.total = record.basic_salary + record.house_allowance_amount + record.transportation_allowance_amount + record.phone_allowance_amount + \
                           record.food_allowance_amount + record.other_allowance

    @api.multi
    @api.depends('basic_salary', 'house_allowance_type', 'house_allowance', 'transportation_allowance_type', 'transportation_allowance',
                 'phone_allowance_type', 'phone_allowance', 'food_allowance_type', 'food_allowance')
    def _get_allowance(self):
        for record in self:
            record.wage = record.basic_salary
            if record.house_allowance_type == 'none':
                record.house_allowance_amount = record.house_allowance = 0.0
            elif record.house_allowance_type == 'fixed':
                record.house_allowance_amount = record.house_allowance
            else:
                record.house_allowance_amount = record.house_allowance * record.basic_salary / 100.0

            if record.transportation_allowance_type == 'none':
                record.transportation_allowance_amount = record.transportation_allowance = 0.0
            elif record.transportation_allowance_type == 'fixed':
                record.transportation_allowance_amount = record.transportation_allowance
            else:
                record.transportation_allowance_amount = record.transportation_allowance * record.basic_salary / 100.0

            if record.phone_allowance_type == 'none':
                record.phone_allowance_amount = record.phone_allowance = 0.0
            elif record.phone_allowance_type == 'fixed':
                record.phone_allowance_amount = record.phone_allowance
            else:
                record.phone_allowance_amount = record.phone_allowance * record.basic_salary / 100.0

            if record.food_allowance_type == 'none':
                record.food_allowance_amount = record.food_allowance = 0.0
            elif record.food_allowance_type == 'fixed':
                record.food_allowance_amount = record.food_allowance
            else:
                record.food_allowance_amount = record.food_allowance * record.basic_salary / 100.0


class Company(models.Model):
    _inherit = "res.company"
    print_config_id = fields.Many2one('print.contract.config', 'Print contract configuration')
