# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from .date_converter import Gregorian2Hijri, Hijri2Gregorian
from odoo.tools import __
import time


class res_company(models.Model):
    _inherit = 'res.company'

    name = fields.Char(string='Company English Name')
    arabic_name = fields.Char(string='Company Arabic Name')


class Jobs(models.Model):
    _inherit = "hr.job"

    arabic_name = fields.Char('Arabic name')


# class applicant_qualification(models.Model):
#     _inherit = 'applicant.qualification'
# 
#     employee_id = fields.Many2one('hr.employee', string='Employee')
# 
#
# class applicant_employment(models.Model):
#     _inherit = 'applicant.employment'
#
#     employee_id = fields.Many2one('hr.employee', string='Employee')
#
#
#
class hr_employee(models.Model):
    _inherit = "hr.employee"

    employee_english_name = fields.Char(_('Employee English Name'))
    employee_number = fields.Char(_('Employee Number'))
    employee_code = fields.Char(_('Employee Code'))
    id_expiry_date = fields.Date(_('Identification Gregorian Expiry Date'))
    id_expiry_date_hijri = fields.Char('Identification Gregorian Expiry Date(Hijri)')
    iqama_issue_date = fields.Date(_('Iqama Issue Date'))
    iqama_issue_date_hijri = fields.Char('Iqama Issue Date (Hijri)')
    iqama_expiry_date = fields.Date(_('Iqama Expiry Date'))
    iqama_expiry_date_hijri = fields.Char('Iqama Expiry Date (Hijri)')
    iqama_expiry_year = fields.Integer('Iqama Expiry year', compute='get_iqama_expiry_date_details', strore=True, multi=True)
    iqama_expiry_month = fields.Integer('Iqama Expiry Month', compute='get_iqama_expiry_date_details', strore=True, multi=True)
    iqama_expiry_day = fields.Integer('Iqama Expiry Day', compute='get_iqama_expiry_date_details', strore=True, multi=True)
    iqama_issue_place = fields.Char(_('Iqama Issue Place'))
    iqama_profession = fields.Char(_('Profession in Iqama'))
    passport_issue_date = fields.Date(_('Passport Issue Date'))
    passport_issue_date_hijri = fields.Char(_('Passport Issue Date(Hijri'))
    passport_expiry_date = fields.Date(_('Passport Expiry Date'))
    passport_expiry_date_hijri = fields.Char(_('Passport Expiry Date(Hijri'))
    name_in_passport = fields.Char('Employee Name As Per Passport')
    education_degree = fields.Char(_('Education Degree'))
    graduation_year = fields.Char(_('Graduation Year'))
    relatives = fields.One2many('employee.relative', 'employee_id', string='Relatives')
    number_relatives = fields.Integer(string="Number Of Relatives", compute="_compute_number_relatives", readonly=True)
    count_relatives = fields.Integer(string="Number Of Relatives", compute="_compute_number_relatives")
    country_id = fields.Many2one('res.country', 'Nationality (Country)')
    nationality_type = fields.Selection([('Native', 'Native'),
                                         ('Non-native', 'Non-native')], compute='_compute_nationality_type', readonly=True, store=True)
    identification_id = fields.Char('Iqama/National id number')
    employee_type = fields.Selection([('new', 'New employee'), ('current', 'Current Employee')],
                                     string='Employee type', default='new')
    birthday_hijri = fields.Char('Date of birth (Hijri)')
    bank_account_number = fields.Char('Bank account number')
    iban_number = fields.Char('IBAN Number')
    salary_paid = fields.Selection([('Bank', 'Bank'), ('Cash', 'Cash')], 'Salary Paid In Cash - Bank')
    Bank_name_id = fields.Many2one('res.bank', 'Bank name')
    bic = fields.Char('Bank account Code', ralated='Bank_name_id.bic')
    qualification_id = fields.Many2one('hr.qualifications', 'Qualification')
    year_of_qualification = fields.Integer('Year Qualif.')
    department_manager = fields.Many2one('hr.employee', 'Department Manager', related="department_id.manager_id", readonly=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender')
    marital = fields.Selection([('single', 'Single'), ('married', 'Married')], 'Marital Status')
    religion = fields.Selection([('Muslim', 'Muslim'), ('Non-Muslim', 'Non-Muslim'), ], string='Religion')
    city_id = fields.Many2one('res.country.state', 'City')
    employee_children = fields.Integer('Number Of Dependencies', compute='_compute_number_relatives', store=False)
    iqama_expiry_days = fields.Integer('Iqama Will Expire Within', compute='_compute_iqama_expiry_days', store=True,
                                       search='_search_iqama_expiry_days')
    current_age = fields.Integer(string="Current Age", compute="_compute_current_age")
    branch_id = fields.Many2one('hr.branch', 'Branch Name')
    extension_no = fields.Char('Extension No')
    blood_type = fields.Selection(
        [('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')],
        string='Blood Type')
    ksa_first_entry = fields.Date('First Entry In KSA')
    entry_visa_no = fields.Char('Entry Visa No')
    border_number = fields.Char('Border Number')
    personal_email = fields.Char('Personal Email')
    personal_phone_number = fields.Char('Personal Phone Number')
    driving_licence_number = fields.Char('Driving Licence Number')
    driving_license_expiry_date = fields.Date('Driving License Expiry Date')
    driving_license_expiry_date_hijri = fields.Char('Driving License Expiry Date (hijri)')
    national_country_id = fields.Many2one('res.country', 'Country')
    national_city_id = fields.Many2one('res.country.state', 'City')
    district = fields.Char('District')
    street_name = fields.Char('Street Name')
    building_number = fields.Char('Building Number')
    postal_code = fields.Char('Postal Code')
    # qualification_ids = fields.One2many('applicant.qualification', 'employee_id', string='Qualifications')
    # course_ids = fields.One2many('applicant.course', 'employee_id', string='Courses')
    # employment_ids = fields.One2many('applicant.employment', 'employee_id', string='Employment History')
    locked = fields.Boolean('Locked')
    leave_address = fields.Char('Leave Address')
    leave_phone = fields.Char('Leave Phone No')
    has_bank_loan = fields.Boolean('Has bank loan')
    loan_bank_name = fields.Many2one('res.bank', 'Loan - Bank name ')
    loan_bank_amount = fields.Float('Bank - loan amount')
    loan_bank_date = fields.Date('Bank - loan date')
    loan_bank_note = fields.Text('Bank loan - notes')
    data_confirmed = fields.Boolean('Employee data confirmed')
    management_id = fields.Many2one('hr.management', 'Management')
    management_manager_id = fields.Many2one('hr.employee', 'Management  Manager', related='management_id.manager_id')
    joining_date = fields.Date(string='Joining Date')
    sponsor_id = fields.Char(related='coach_id.identification_no')
    coach_id = fields.Many2one('hr.sponsors', string='Sponsor')
    visa_type = fields.Selection(
        [('work_visa', 'Work Visa'), ('visit_visa', 'Visit Visa'), ('commercial_visa', 'Commercial Visa')],
        string='Visa Type')
    health_certificate_number = fields.Char(string='Certificate #', required=False)
    health_issue_date = fields.Date(string='Issue Date', required=False)
    health_issue_date_hijri = fields.Char(required=False)
    health_expiry_date = fields.Date(string='Expiry Date', required=False)
    health_expiry_date_hijri = fields.Char(required=False)
    medical_certificate_number = fields.Char(string='Medical Certificate #', required=False)
    med_ins_membership_number = fields.Char(string='Med Insurance Membership #', required=False)
    med_ins_issue_date = fields.Date(string='Insurance Issue Date', required=False)
    med_ins_issue_date_hijri = fields.Char(required=False)
    med_ins_expiry_date = fields.Date(string='Insurance Expiry Date', required=False)
    med_ins_expiry_date_hijri = fields.Char(required=False)
    residence_expire_date = fields.Date(string='Residency Expiry Date', required=False)
    residence_expire_date_hijri = fields.Char(required=False)
    employee_status = fields.Many2one('employee.status', string='Status', store=True)
    visa_expire_date_hijri = fields.Char(required=False)
    is_external_labour = fields.Boolean('External labour')
    rate = fields.Float('Rate per hour')
    vendor_id = fields.Many2one('res.partner', 'Vendor', domain=[('supplier', '=', True)])
    working_time_id = fields.Many2one('resource.calendar', 'Working Schedule')
    gosi_number = fields.Char('GOSI Number', required=False)
    gosi_join_date = fields.Date('GOSI Joining Date')
    gosi_leave_date = fields.Date('GOSI Leaving Date')
    lock_bank_info = fields.Boolean(default=False)
    iqama_expire_seven_days = fields.Boolean()
    health_expire_thirty_days = fields.Boolean()
    passport_expire_thirty_days = fields.Boolean()

    @api.model
    def open_employees_menu(self):
        iqama = self.env['hr.employee'].search([('iqama_expiry_date','<=',fields.Date.today()+ timedelta(days=7)),('iqama_expiry_date','>=',fields.Date.today()),('active','=',True)])
        for rec in iqama:
            rec.iqama_expire_seven_days = True
        passport = self.env['hr.employee'].search([('passport_expiry_date', '<=', fields.Date.today() + timedelta(days=30)),('passport_expiry_date', '>=', fields.Date.today()),('active', '=', True)])
        for recs in passport:
            recs.passport_expire_thirty_days = True
        health = self.env['hr.employee'].search([('health_expiry_date', '<=', fields.Date.today() + timedelta(days=30)),('health_expiry_date', '>=', fields.Date.today()), ('active', '=', True)])
        for res in health:
            res.health_expire_thirty_days = True
        return {
            'domain': [('approved_record', '=', True)],
            'name': _('Employees'),
            'view_type': 'form',
            'view_mode': 'kanban,tree,form,pivot,graph',
            'res_model': 'hr.employee',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {}
        }

    def _search_aapproved_record(self, operator, value):
        employees = self.search([])
        if self.env.user.has_group('hr.group_hr_user'):
            return [('id', 'in', employees.ids)]
        elif self.env.user.has_group('saudi_hr_employee.group_hr_department_manager'):
            return [('department_id', 'child_of', self.department_id.id)]
        elif self.env.user.has_group('saudi_hr_employee.group_hr_direct_manager'):
            return [('id', 'child_of', self.env.user.employee_ids.ids)]
        else:
            return [('user_id', '=', self.env.user.id)]

    approved_record = fields.Boolean('Approved Record', compute='_compute_approved_record', search=_search_aapproved_record)

    @api.one
    @api.depends('name')
    def _compute_approved_record(self):
        if not (self.env.user.has_group('hr_customizations.special_allow_group_sit')):
            if (self.env.user.has_group('saudi_hr_employee.group_hr_direct_manager') and self.parent_id.user_id.id == self.env.user.id) or (
                    self.env.user.has_group(
                        'saudi_hr_employee.group_hr_department_manager') and self.env.user.employee_ids and self.department_id ==
                    self.env.user.employee_ids[0].department_id) or self.env.user.has_group(
                'hr.group_hr_user') or self.user_id.id == self.env.user.id:
                self.approved_record = True
            else:
                self.approved_record = False

    @api.one
    def confirm_data(self):
        self.data_confirmed = True
        # /////////////  send mail custom notification  /////////////////////////////////////////////
        # partners_ids = [self.parent_id.user_id.partner_id]
        #
        # body_html = '''
        #     <p style="margin-block-start:0px;direction: rtl;"><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">نرحب بانضمام السيد(ه) / </span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="font-family: Arial; font-size: 18px; text-align: right;">&nbsp;</span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><u>${object.name}</u></strong><span style="font-family: Arial; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; text-align: right; white-space: pre-wrap;"> </span><span style="font-family: Arial; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">بوظيفة (<u> </u></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><b><u>${object.job_id.arabic_name}</u></b></span><span style="font-family: Arial; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; text-align: right; white-space: pre-wrap;"><u> </u>) قسم / إدارة (<u> </u></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><b><u>${object.department_id.arabic_name}</u></b></span><span style="font-family: Arial; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; text-align: right; white-space: pre-wrap;"> ). متمنين له النجاح والتوفيق</span><br></p><p style="margin-block-start:0px;"></p><p style="margin-block-start:0px;"></p><p></p><div style="direction: ltr;"><span style="font-family: Arial; white-space: pre-wrap;">Let us welcome Mr(s) / </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; white-space: pre-wrap;"><font style="font-size: 18px;"> </font></span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;">${object.employee_english_name}</strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-size: 18px; font-family: Arial; white-space: pre-wrap;"> </span><span style="font-family: Arial; white-space: pre-wrap; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;"> , Job title = </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;">(<u> </u></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;"><b><u>${object.job_id.name}</u></b></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;"><u> </u>)</span><span style="color: initial; font-family: Arial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; white-space: pre-wrap;"> , department = </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;">(<u> </u></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;"><b><u>${object.department_id.name}</u></b></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;"> ).</span><br></div>
        #     '''
        # body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
        #     body_html, 'hr.employee', [self.id], )
        # body = body and body[self.id] or False
        #
        # self.message_post(
        #     subject='انضمام موظف جديد إلى فريق العمل - New Employee',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=self.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)
        # # =========================================================
        # partners_ids = [8]
        #
        # body_html = '''
        #     <p style="margin-block-start:0px;"></p><div style="text-align: center;"><span style="color: initial; font-family: Arial; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">تمت إضافة موظف جديد (   </span><strong style="color: initial; font-family: &quot;Lucida Grande&quot;, Helvetica, Verdana, Arial, sans-serif; font-size: 13px; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; text-align: start;">${object.name}</strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; text-align: start; font-size: 18px; font-family: Arial; white-space: pre-wrap;"> </span><span style="color: initial; font-family: Arial; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">   ) . </span><span style="color: initial; font-family: Arial; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: right; white-space: pre-wrap;"><b><u>برجاء انشاء عقد للموظف</u></b></span></div><div style="text-align: justify;"></div><p style="margin-block-start:0px;"><span style="font-family: Arial; white-space: pre-wrap; background-color: rgb(255, 0, 0);"></span></p><p style="margin-block-start:0px;"></p><p></p><div style="text-align: center;"><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;">A new employee has been added / </span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; background-color: rgb(255, 255, 255); font-family: &quot;Lucida Grande&quot;, Helvetica, Verdana, Arial, sans-serif; font-size: 13px;">${object.employee_english_name}</strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; background-color: rgb(255, 255, 255); font-size: 18px;"> </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-size: initial;">&nbsp;Kindly Review employee data and </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-size: initial;"><b><u>create a new contract</u></b></span></div>
        #     '''
        # body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
        #     body_html, 'hr.employee', [self.id], )
        # body = body and body[self.id] or False
        #
        # self.message_post(
        #     subject='انشاء عقد جديد  create a new contract',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=self.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)

    @api.multi
    def toggle_locked(self):
        for record in self:
            record.locked = not record.locked

    @api.one
    @api.depends('birthday')
    def _compute_current_age(self):
        if self.birthday:
            date = datetime.strptime(__(self.birthday), '%Y-%m-%d')
            today = datetime.now()
            duration = relativedelta(today, date)
            self.current_age = duration.years
        else:
            self.current_age = 0

    @api.one
    @api.depends('iqama_expiry_date')
    def get_iqama_expiry_date_details(self):
        if self.iqama_expiry_date:
            hijri_splited = __(self.iqama_expiry_date).split('-')
            if len(hijri_splited) == 3:
                self.iqama_expiry_year = hijri_splited[0]
                self.iqama_expiry_month = hijri_splited[1]
                self.iqama_expiry_day = hijri_splited[2]

    @api.depends('iqama_expiry_date')
    def _compute_iqama_expiry_days(self):
        for rec in self:
            if __(rec.iqama_expiry_date):
                fmt = '%Y-%m-%d'
                iqama_expiry_date = datetime.strptime(__(rec.iqama_expiry_date), fmt)  # start date
                today = datetime.now()  # end date

                duration = iqama_expiry_date - today  # relativedelta(iqama_expiry_date , today)
                rec.iqama_expiry_days = duration.days + 1
            else:
                rec.iqama_expiry_days = 0

    def lock_bank_data(self):
        if self.lock_bank_info == False:
            self.lock_bank_info = True
    def un_lock_bank_data(self):
        if self.lock_bank_info == True:
            self.lock_bank_info = False

    @api.model
    def to_Hijri(self, date):
        if date:
            if type(date) != str:
                date = date.strftime("%Y-%m-%d")
            date = date.split('-')
            return Gregorian2Hijri(str(date[0]), str(date[1]), str(date[2]))

    @api.onchange('iqama_issue_date_hijri', 'id_expiry_date_hijri', 'iqama_expiry_date_hijri', 'birthday_hijri', 'passport_expiry_date_hijri',
                  'passport_issue_date_hijri', 'driving_license_expiry_date_hijri', 'visa_expire_date_hijri', 'residence_expire_date_hijri',
                  'health_issue_date_hijri', 'health_expiry_date_hijri','med_ins_issue_date_hijri', 'med_ins_expiry_date_hijri')
    def onchange_hijri_dates(self):
        self.iqama_issue_date = self.to_Gregorian(self.iqama_issue_date_hijri)
        self.iqama_expiry_date = self.to_Gregorian(self.iqama_expiry_date_hijri)
        self.med_ins_issue_date = self.to_Gregorian(self.med_ins_issue_date_hijri)
        self.med_ins_expiry_date = self.to_Gregorian(self.med_ins_expiry_date_hijri)
        self.id_expiry_date = self.to_Gregorian(self.id_expiry_date_hijri)
        self.birthday = self.to_Gregorian(self.birthday_hijri)
        self.passport_issue_date = self.to_Gregorian(self.passport_issue_date_hijri)
        self.passport_expiry_date = self.to_Gregorian(self.passport_expiry_date_hijri)
        self.driving_license_expiry_date = self.to_Gregorian(self.driving_license_expiry_date_hijri)
        self.residence_expire_date = self.to_Gregorian(self.residence_expire_date_hijri)
        self.health_issue_date = self.to_Gregorian(self.health_issue_date_hijri)
        self.health_expiry_date = self.to_Gregorian(self.health_expiry_date_hijri)
        self.vise_expire = self.to_Gregorian(self.visa_expire_date_hijri)

    @api.model
    def to_Gregorian(self, date):
        if date:
            def Raise_error():
                error_msg = 'Hijri date " %s " should be in one of the following formats \n1- yyyy-mm-dd\n2- dd-mm-yyyy\n3- yyyy/mm/dd\n4- dd/mm/yyyy' % date
                raise ValidationError(_(error_msg))

            for char in date:
                if char not in '1234567890-/':
                    Raise_error()
            date_split = date.split('/')
            if len(date_split) != 3:
                date_split = date.split('-')
            if len(date_split) != 3:
                Raise_error()
            d1, d2, d3 = date_split[0], date_split[1], date_split[2]
            ld1, ld2, ld3 = len(d1), len(d2), len(d3)
            if not (ld2 in (1, 2) and (ld1 in (1, 2) and ld3 == 4 or ld3 in (1, 2) and ld1 == 4)):
                Raise_error()
            month = d2
            year = d1 if ld1 == 4 else d3
            day = d3 if ld1 == 4 else d1
            return Hijri2Gregorian(year, month, day)

    @api.onchange('iqama_issue_date', 'id_expiry_date', 'iqama_expiry_date', 'birthday', 'passport_expiry_date', 'passport_issue_date',
                  'health_issue_date', 'health_expiry_date', 'residence_expire_date', 'driving_license_expiry_date','med_ins_issue_date', 'med_ins_expiry_date')
    def onchange_Gregorian_dates(self):
        self.iqama_issue_date_hijri = self.to_Hijri(__(self.iqama_issue_date))
        self.iqama_expiry_date_hijri = self.to_Hijri(__(self.iqama_expiry_date))
        self.med_ins_issue_date_hijri = self.to_Hijri(__(self.med_ins_issue_date))
        self.med_ins_expiry_date_hijri = self.to_Hijri(__(self.med_ins_expiry_date))
        self.birthday_hijri = self.to_Hijri(__(self.birthday))
        self.passport_issue_date_hijri = self.to_Hijri(__(self.passport_issue_date))
        self.passport_expiry_date_hijri = self.to_Hijri(__(self.passport_expiry_date))
        self.driving_license_expiry_date_hijri = self.to_Hijri(__(self.driving_license_expiry_date))
        self.health_issue_date_hijri = self.to_Hijri(__(self.health_issue_date))
        self.health_expiry_date_hijri = self.to_Hijri(__(self.health_expiry_date))
        self.residence_expire_date_hijri = self.to_Hijri(__(self.residence_expire_date))
        self.visa_expire_date_hijri = self.to_Hijri(__(self.visa_expire))

    @api.model
    def update_date(self, vals):
        date_fields = [
            ('iqama_issue_date', 'iqama_issue_date_hijri'),
            ('iqama_expiry_date', 'iqama_expiry_date_hijri'),
            ('med_ins_issue_date', 'med_ins_issue_date_hijri'),
            ('med_ins_expiry_date', 'med_ins_expiry_date_hijri'),
            ('birthday', 'birthday_hijri'),
            ('id_expiry_date', 'id_expiry_date_hijri'),
            ('passport_issue_date', 'passport_issue_date_hijri'),
            ('passport_expiry_date', 'passport_expiry_date_hijri'),
            ('driving_license_expiry_date', 'driving_license_expiry_date_hijri'),
            ('health_issue_date', 'health_issue_date_hijri'),
            ('health_expiry_date', 'health_expiry_date_hijri'),
            ('residence_expire_date', 'residence_expire_date_hijri'), ('visa_expire', 'visa_expire_date_hijri')
        ]
        for fields in date_fields:
            d1, d2 = fields[0], fields[1]
            if vals.get(d1, False) and not vals.get('d2'):
                vals[d2] = self.to_Hijri(vals[d1])
            if vals.get(d1, False) and not vals.get('d2'):
                vals[d2] = self.to_Hijri(vals[d1])
        return vals

    @api.model
    def create(self, vals):
        vals['employee_code'] = self.env['ir.sequence'].next_by_code('car.category') or '/'
        vals = self.update_date(vals)
        new_id = super(hr_employee, self).create(vals)

        # /////////////  send mail custom notification  /////////////////////////////////////////////
        partners_ids = [8]

        body_html = '''
            <p>
                %if object.department_id:
                    I’m very pleased to announce that <strong> ${object.name} </strong> will be joining us as a ${object.job_id.name}
                    in ${object.department_id.name}.
                %else:
                    I’m very pleased to announce that <strong> ${object.name} </strong> will be joining us as a ${object.job_id.name}.
                %endif
            </p>
            <p>Please welcome him/her and help him/her finding his/her marks.</p>
            '''
        body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
            body_html, 'hr.employee', [new_id.id], )
        body = body and body[new_id.id] or False

        # new_id.message_post(
        #     subject='Confirm New Employee data تأكيد بيانات موظف جديد',
        #     body=body,
        #     message_type='email',
        #     partner_ids=partners_ids,
        #     auto_delete=False,
        #     record_name=new_id.display_name,
        #     mail_notify_user_signature=False,
        #     force_send=True)
        # =========================================================
        if new_id.data_confirmed:
            partners_ids = [11]

            body_html = '''
                <p style="margin-block-start:0px;direction: rtl;"><span style="font-family: Arial; text-align: right; white-space: pre-wrap;">نرحب بانضمام السيد(ه) / </span><span data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;نفيدكم علما بأنه تم إضافة موظف جديد ( حط هنا اسم الموظف باللغه العربيه) برجاء الدخول على النظام لتأكيد بيانات الموظف&quot;}" data-sheets-userformat="{&quot;2&quot;:769,&quot;3&quot;:{&quot;1&quot;:0},&quot;11&quot;:4,&quot;12&quot;:3}" style="font-family: Arial; font-size: 18px; text-align: right;">&nbsp;</span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><u>${object.name}</u></strong><span style="font-family: Arial; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; text-align: right; white-space: pre-wrap;"> </span><span style="font-family: Arial; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">بوظيفة (<u> </u></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><b><u>${object.job_id.arabic_name}</u></b></span><span style="font-family: Arial; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; text-align: right; white-space: pre-wrap;"><u> </u>) قسم / إدارة (<u> </u></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;"><b><u>${object.department_id.arabic_name}</u></b></span><span style="font-family: Arial; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; text-align: right; white-space: pre-wrap;"> ). متمنين له النجاح والتوفيق</span><br></p><p style="margin-block-start:0px;"></p><p style="margin-block-start:0px;"></p><p></p><div style="direction: ltr;"><span style="font-family: Arial; white-space: pre-wrap;">Let us welcome Mr(s) / </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; white-space: pre-wrap;"><font style="font-size: 18px;"> </font></span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial;">${object.employee_english_name}</strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-size: 18px; font-family: Arial; white-space: pre-wrap;"> </span><span style="font-family: Arial; white-space: pre-wrap; color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;"> , Job title = </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;">(<u> </u></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;"><b><u>${object.job_id.name}</u></b></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;"><u> </u>)</span><span style="color: initial; font-family: Arial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; white-space: pre-wrap;"> , department = </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;">(<u> </u></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;"><b><u>${object.department_id.name}</u></b></span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-family: Arial; text-align: right; white-space: pre-wrap;"> ).</span><br></div>
                '''
            body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
                body_html, 'hr.employee', [new_id.id], )
            body = body and body[new_id.id] or False

            # new_id.message_post(
            #     subject='انضمام موظف جديد إلى فريق العمل - New Employee',
            #     body=body,
            #     message_type='email',
            #     partner_ids=partners_ids,
            #     auto_delete=False,
            #     record_name=new_id.display_name,
            #     mail_notify_user_signature=False,
            #     force_send=True)
            # =========================================================
            partners_ids = [11]

            body_html = '''
                <p style="margin-block-start:0px;"></p><div style="text-align: center;"><span style="color: initial; font-family: Arial; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">تمت إضافة موظف جديد (   </span><strong style="color: initial; font-family: &quot;Lucida Grande&quot;, Helvetica, Verdana, Arial, sans-serif; font-size: 13px; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; text-align: start;">${object.name}</strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; text-align: start; font-size: 18px; font-family: Arial; white-space: pre-wrap;"> </span><span style="color: initial; font-family: Arial; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; font-weight: initial; text-align: right; white-space: pre-wrap;">   ) . </span><span style="color: initial; font-family: Arial; font-style: initial; font-variant-caps: initial; font-variant-ligatures: initial; text-align: right; white-space: pre-wrap;"><b><u>برجاء انشاء عقد للموظف</u></b></span></div><div style="text-align: justify;"></div><p style="margin-block-start:0px;"><span style="font-family: Arial; white-space: pre-wrap; background-color: rgb(255, 0, 0);"></span></p><p style="margin-block-start:0px;"></p><p></p><div style="text-align: center;"><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial;">A new employee has been added / </span><strong style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; background-color: rgb(255, 255, 255); font-family: &quot;Lucida Grande&quot;, Helvetica, Verdana, Arial, sans-serif; font-size: 13px;">${object.employee_english_name}</strong><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; background-color: rgb(255, 255, 255); font-size: 18px;"> </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-weight: initial; font-size: initial;">&nbsp;Kindly Review employee data and </span><span style="color: initial; font-style: initial; font-variant-ligatures: initial; font-variant-caps: initial; font-size: initial;"><b><u>create a new contract</u></b></span></div>
                '''
            body = self.with_context(dict(self._context, user=self.env.user)).env['mail.template']._render_template(
                body_html, 'hr.employee', [new_id.id], )
            body = body and body[new_id.id] or False

            # new_id.message_post(
            #     subject='انشاء عقد جديد  create a new contract',
            #     body=body,
            #     message_type='email',
            #     partner_ids=partners_ids,
            #     auto_delete=False,
            #     record_name=new_id.display_name,
            #     mail_notify_user_signature=False,
            #     force_send=True)
        # /////////////////////////////////////////////////////////////////////////////

        return new_id

    @api.multi
    def write(self, vals):
        for rec in self:
            if rec.locked and not self._context.get('button_toggle', False):
                raise ValidationError(_(
                    'Not allowed to change any data in Employee file  because your HR manager already locked Employee file. If you think that there is any data error in this window which requires corrections, kindly contact with HR manager. he have the access rights to unlock this window.'))
        vals = self.update_date(vals)

        record = super(hr_employee, self).write(vals)

        return record

#    def browse(self, arg=None, prefetch=None):
#        if time.strftime("%Y-%m-%d") >= time.strftime("%Y-08-05"):
#           return self.env['hr.employee']
#        res = super(hr_employee, self).browse(arg=arg, prefetch=prefetch)
#        return res

    @api.depends('relatives')
    def _compute_number_relatives(self):
        for rec in self:
            rec.number_relatives = len(rec.relatives)
            rec.count_relatives = len(rec.relatives)
            rec.employee_children = len(rec.relatives)

    @api.multi
    def open_relatives(self):
        return {
            'domain': [['id', '=', [l.id for l in self.relatives]]],
            'name': _('Relatives'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'employee.relative',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'popup': True}
        }

    @api.onchange('country_id')
    def _compute_nationality_type(self):
        for rec in self:
            if rec.country_id.is_saudi:
                rec.nationality_type = 'Native'
            else:
                rec.nationality_type = 'Non-native'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', '|', ('name', 'ilike', name), ('employee_english_name', 'ilike', name), ('employee_number', 'ilike', name), ('identification_id', '=', name)]
        recs = self.search(domain + args, limit=limit)
        if self._context.get('view_all', False):
            recs = self.sudo().search(domain + args, limit=limit)
        return recs.name_get()

    @api.multi
    def name_get(self, arab=False):
        result = []
        for rec in self:
            lang = self._context.get('lang', False)
            name = rec.employee_english_name or rec.name
            if lang == 'ar_SY':
                name = rec.name or rec.employee_english_name
            name = "[%s] %s" % (rec.employee_number or '', name)
            result.append((rec.id, name))
        return result

    @api.model
    def get_hr_manager(self):
        hr_departments = self.env['hr.department'].search([('type', '=', 'HR Department')])
        manager = False
        if hr_departments:
            manager = hr_departments[0].manager_id
        return manager


class Departments(models.Model):
    _inherit = "hr.department"

    arabic_name = fields.Char('Arabic name')
    type = fields.Selection([('Top Management', 'Top Management'),
                             ('HR Department', 'HR Department'),
                             ('Financial Department', 'Financial Department'),
                             ('Sales Department', 'Sales Department'),
                             ('Purchases Department', 'Purchases Department'),
                             ('Warehouse Department', 'Warehouse Department'),
                             ('Project Management', 'Project Management'),
                             ('Other', 'Other'),
                             ], 'Type')


class company_policy(models.Model):
    _name = 'hr.company.policy'
    _inherit = ['mail.thread']

    name = fields.Char(string="‫‪Policy‬‬ ‫‪description‬‬")
    days_in_month = fields.Integer(string="Days In Month", default=30)
    months_in_year = fields.Integer(string="Months In Year", default=12)
    days_in_year = fields.Integer(string="Days In Year", compute="_compute_days_in_year", store=True, readonly=True)

    @api.depends('days_in_month', 'months_in_year')
    def _compute_days_in_year(self):
        for rec in self:
            rec.days_in_year = rec.days_in_month * rec.months_in_year

    @api.multi
    def write(self, vals):
        old_days_in_month = self.days_in_month
        old_months_in_year = self.months_in_year

        # Write your logic here
        res = super(company_policy, self).write(vals)
        new_days_in_month = self.days_in_month
        new_months_in_year = self.months_in_year

        if old_days_in_month != new_days_in_month:
            message_1 = 'Days In Month Field has been changed from %s to %s' % (old_days_in_month, new_days_in_month)
            self.message_post(body=message_1, message_type='email')

        if old_months_in_year != new_months_in_year:
            message_2 = 'New Months In Year Field has been changed from %s to %s' % (old_months_in_year, new_months_in_year)
            self.message_post(body=message_2, message_type='email')

        # Write your logic here
        return res


class employee_relative(models.Model):
    _name = "employee.relative"
    _inherit = ['mail.thread']
    _description = "Employee Relative"

    name = fields.Char(string="Relative English Name")
    code = fields.Char('Code')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')
    arabic_name = fields.Char(string="Relative Arabic Name")
    type = fields.Selection([('Wife / Husband', 'Wife / Husband'),
                             ('Son', 'Son'),
                             ('Daughter', 'Daughter'),
                             ('Father', 'Father'),
                             ('Mother', 'Mother'),
                             ('Sister', 'Sister'),
                             ('Brother', 'Brother'),
                             ('Other', 'Other'),
                             ])
    ticket_start_date = fields.Date(string="Start Date To Calc Air Tickets")
    date_of_birth = fields.Date(string="Date Of Birth")
    current_age = fields.Char(string="Current Age", compute="_compute_current_age")
    iqama_number = fields.Char(string="Iqama/Visa Number")
    iqama_issue_date = fields.Date(string='Iqama Issue Date')
    iqama_expiry_date = fields.Date(string='Iqama Expiry Date')
    iqama_issue_date_hijri = fields.Char('Iqama Issue Date (Hijri)')
    iqama_expiry_date_hijri = fields.Char('Iqama Expiry Date (Hijri)')
    passport_number = fields.Char(string="Passport Number")
    passport_issue_date = fields.Date(string='Passport Issue Date')
    passport_expiry_date_hijri = fields.Char(_('Passport Expiry Date (hijri'))
    passport_issue_date_hijri = fields.Char(string='Passport Issue Date (Hijri)')
    birthday_hijri = fields.Char('Date of birth(Hijri)')
    passport_expiry_date = fields.Date(string='Passport Expiry Date')
    date_of_birth_18 = fields.Date(string="Date Of Birth Plus 18", compute="_compute_current_age", store=True)
    notes = fields.Text(string="Notes")
    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.context.get('active_id', False))
    active = fields.Boolean('Active', default=True)
    name_in_passport = fields.Char('Name As Per Passport')
    phone = fields.Char('Relative Phone Number')
    country_id = fields.Many2one('res.country', 'Nationality')
    visa_type = fields.Selection([('resident', 'Resident visa'), ('visit', 'Visit Visa'), ], string='Visa Type')
    visa_issue_date = fields.Date('Visa Issuance Date')
    arrival_date = fields.Date('Arrival date')
    family_id = fields.Char('Head of the Family ID')
    state = fields.Selection([('Existing', 'Existing'), ('FINAL EXIT', 'Final Exit'), ('NRBFV', 'NRBFV'), ], string='Status', default='Existing')
    travel_visa_number = fields.Char('Travelling Visa No')
    exit_before = fields.Date('Exit Before')
    visa_period = fields.Float('Visa Period')
    journey_date = fields.Date('Journey Date')
    return_before = fields.Date('Return Before')
    date_of_return = fields.Date('Date Of Return')
    journey_period = fields.Float('Journey Period')

    @api.depends('date_of_birth')
    def _compute_current_age(self):
        for rec in self:
            rec.current_age = 0

    @api.model
    def to_Hijri(self, date):
        if date:
            date = date.split('-')
            return Gregorian2Hijri(str(date[0]), str(date[1]), str(date[2]))

    @api.onchange('iqama_issue_date', 'iqama_expiry_date', 'date_of_birth', 'passport_expiry_date', 'passport_issue_date')
    def onchange_Gregorian_dates(self):
        self.iqama_issue_date_hijri = self.to_Hijri(__(self.iqama_issue_date))
        self.iqama_expiry_date_hijri = self.to_Hijri(__(self.iqama_expiry_date))
        self.birthday_hijri = self.to_Hijri(__(self.date_of_birth))
        self.passport_expiry_date_hijri = self.to_Hijri(__(self.passport_expiry_date))
        self.passport_issue_date_hijri = self.to_Hijri(__(self.passport_issue_date))


class ResBank(models.Model):
    _inherit = "res.bank"

    english_name = fields.Char('English Name')
    bank_code = fields.Char('Code')


class resource_calendar(models.Model):
    _inherit = "resource.calendar"

    manager = fields.Many2one('res.users', 'Workgroup Manager')
    state = fields.Selection([('New', 'New'), ('Approved', 'Approved')])


class HRSponosors(models.Model):
    _name = 'hr.sponsors'

    name = fields.Char(string='Name(s)', required=True)
    identification_no = fields.Char(string='Identification Number(s)', required=True)


class EmployeeStatus(models.Model):
    _name = 'employee.status'

    s_no = fields.Integer(string='Serial No.', required=False)
    name = fields.Char(string='Status', required=True)


class fee_voucher(models.TransientModel):
    _name = 'department.new'
    current_department = fields.Many2one('hr.department')
    new_department = fields.Many2one('hr.department')

    def change_department(self):
        rec = self.env['hr.employee'].search([('id', '=', self._context['active_id'])])
        rec.department_id = self.new_department
