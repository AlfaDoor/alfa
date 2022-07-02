# -*- coding: utf-8 -*-

from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
import time
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from .date_converter import Gregorian2Hijri, Hijri2Gregorian


class applicant_course(models.Model):
    _name = 'applicant.course'

    employee_id = fields.Many2one('hr.employee', string='Employee')

    applicant_id = fields.Many2one('hr.applicant', string='Applicant')
    name = fields.Many2one('hr.employee.course',string='Course Name')
    desc = fields.Char('Course description')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    duration = fields.Integer('Duration')
    days_months = fields.Selection([('Days', 'Days'), ('Months', 'Months')],'Days / Months')
    country_id = fields.Many2one('res.country', 'Country')
    city_id = fields.Many2one('res.country.state', 'City')
    type = fields.Selection([('Attend course', 'Attend course'), ('Pass an exam', 'Pass an exam')],'Course Type')
    attachment = fields.Binary('Attachments',attachment=True)
    file_name = fields.Char('File name')
    note = fields.Char('Notes')

class applicant_qualification(models.Model):
    _inherit = 'applicant.qualification'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant')


class applicant_employment(models.Model):
    _inherit = 'applicant.employment'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant')

    @api.one
    @api.depends('date_from', 'date_to')
    def _compute_duration(self):
        if self.date_from and self.date_to:
            start_date = datetime.strptime(self.date_from, "%Y-%m-%d")
            end_date = datetime.strptime(self.date_to, "%Y-%m-%d")
            duration = relativedelta(end_date, start_date)
            total_str = ''
            months = 0
            if duration.years:
                total_str += _('%s years, ' % (duration.years))
            if duration.months:
                months += duration.months
            if duration.days > 15:
                months += 1
            if months:
                total_str += _('%s months, ' % (months))
            self.duration = total_str


class hr_terms_conditions(models.Model):
    _name = 'hr.terms.conditions'

    name = fields.Char(string='Terms and Conditions')
    applicant_id = fields.Many2one('hr.applicant', string='Applicant')


class Jobs(models.Model):
    _inherit = "hr.job"

    arabic_name = fields.Char('Arabic name')


class hr_employee(models.Model):
    _inherit = "hr.employee"

    branch_id = fields.Many2one('hr.branch', 'branch name')
