# -*- coding: utf-8 -*-
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from .base_tech import *

import logging
from odoo.tools import __

# _logger = logging.getLogger(__name__)
# _logger.info(error_msg)


class GosiCalc(models.Model):
    _name = "gosi.calc"
    _description = "Gosi calc"

    contract_id = m2o_field('hr.contract', 'Contract')
    country_id = m2o_field('res.country', 'Country')
    gosi_for_this = selection_field([
        ('no', 'No'),
        ('yes', 'Yes'),
    ], string='GOSI for this nationality')
    gosi_calc_based_on = selection_field([
        ('basic', 'Basic Salary'),
        ('basic_house', 'Basic Salary + House allowance'),
        ('basic_house_transportation', 'Basic Salary + House allowance + transportation'),
        ('basic_house_transportation_phone', 'Basic salary + House + transportation + phone'),
        ('total', 'Total salary'),
        ('other', 'Other amount (will be defined manually in employee contract)'),
    ], string='Gosi Calculation based on')
    who_will_pay = selection_field([
        ('employee_salary', 'Deduct full Gosi amount from employee salary'),
        ('company', 'No deductions from employee salary (The company will pay the full Gosi amount)'),
        ('company_employee', 'Deduct from employee and from company'),
    ], string="Who will pay the GOSI")
    company_share = float_field('Company share')
    employee_share = float_field('Employee share')
    minimum_gosi_salary = float_field('Minimum Gosi Salary')
    manual_gosi_salary = float_field('Manual Gosi Salary')
    salary_for_gosi = float_field('Salary for GOSI', compute='get_salary_for')

    start_gosi_payslip_date = date_field('Start include GOSI in Payslip from')

    @api.onchange('who_will_pay')
    def onchange_company_share(self):
        if self.who_will_pay == 'employee_salary':
            self.company_share = 0
        if self.who_will_pay == 'company':
            self.employee_share = 0


class Countries(models.Model):
    _name = "res.country"
    _inherit = ["res.country", "gosi.calc"]

    note = html_field('Notes')


class Contract(models.Model):
    _name = "hr.contract"
    _inherit = ["hr.contract", "gosi.calc"]

    employee_amount = float_field('Employee amount', compute='get_employee_amount')
    company_amount = float_field('Company amount', compute='get_company_amount')
    gosi_number = fields.Char('Employee GOSI number')

    @api.one
    @api.depends('salary_for_gosi', 'company_share')
    def get_company_amount(self):
        self.company_amount = self.salary_for_gosi * (self.company_share / 100)

    @api.one
    @api.depends('salary_for_gosi', 'employee_share')
    def get_employee_amount(self):
        self.employee_amount = self.salary_for_gosi * (self.employee_share / 100)

    @api.one
    @api.depends('gosi_for_this', 'total', 'gosi_calc_based_on', 'manual_gosi_salary')  # , 'nationality'
    def get_salary_for(self):
        if self.gosi_for_this != 'yes':
            self.manual_gosi_salary = 0
            return
        salary_for_gosi = 0
        if self.gosi_calc_based_on == 'basic':
            salary_for_gosi = self.basic_salary
        if self.gosi_calc_based_on == 'basic_house':
            salary_for_gosi = self.basic_salary + self.house_allowance_amount
        if self.gosi_calc_based_on == 'basic_house_transportation':
            salary_for_gosi = self.basic_salary + self.house_allowance_amount + self.transportation_allowance_amount
        if self.gosi_calc_based_on == 'basic_house_transportation_phone':
            salary_for_gosi = self.basic_salary + self.house_allowance_amount + self.transportation_allowance_amount + \
                              self.phone_allowance_amount
        if self.gosi_calc_based_on == 'total':
            salary_for_gosi = self.total
        if self.gosi_calc_based_on == 'other':
            salary_for_gosi = self.manual_gosi_salary
        # if self.nationality.max_gosi_amount and self.nationality.max_gosi_amount < salary_for_gosi:
        #     self.salary_for_gosi = self.nationality.max_gosi_amount
        else:
            salary_for_gosi = salary_for_gosi
        self.salary_for_gosi = salary_for_gosi


class Payroll(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def gosi_employee_rule(self):
        employee_amount = self.contract_id.employee_amount
        return employee_amount

    @api.model
    def gosi_company_rule(self):
        company_amount = 0.0
        company_amount = self.contract_id.company_amount
        return company_amount

    @api.model
    def total_deductions(self):
        res = super(Payroll, self).total_deductions()
        return res - (self.gosi_employee_rule())
