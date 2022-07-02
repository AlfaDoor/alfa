# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
from odoo.tools import __


class effective_notice(models.Model):
    _name = 'effective.notice'
    _description = "Effective Notice"
    _inherit = ['mail.thread']
    _order = "id desc"
    _rec_name = 'desc'

    name = fields.Char('Code', readonly=True)
    desc = fields.Char('Description', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
                                  default=lambda self: self.env.context.get('active_id', False) or self.env.user.employee_ids and
                                                       self.env.user.employee_ids[0].id)
    employee_number = fields.Char('Employee Number', related="employee_id.employee_number", readonly=True, store=True)
    department_id = fields.Many2one('hr.department', string='Department', related="employee_id.department_id", readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string='Job Title', related="employee_id.job_id", readonly=True, store=True)
    country_id = fields.Many2one('res.country', '‫‪Nationality‬‬', related="employee_id.country_id", readonly=True, store=True)
    start_work = fields.Date(string="Starting Work at", required=True)
    start_work_day = fields.Char('Starting Work at Day', compute='get_date_day')
    payslip_date = fields.Date(string="Payslip Date")
    type = fields.Selection([('New Employee', 'New Employee'),], 'Effective Notice Type', required=True)
    created_by = fields.Many2one('res.users', default=lambda self: self.env.uid, readonly=True, string="Created By")
    notes = fields.Text(string="Notes")

    state = fields.Selection([
        ('New', 'New'),
        ('Department manager approval', 'Department manager approval'),
        ('HR department approval', 'HR department approval'),
        ('Refused', 'Refused'),
    ], string='Status', index=True, default='New', track_visibility='always')

    return_justification = fields.Text('Delay / Early Return Justification')
    hide_return_justification = fields.Boolean(compute='_compute_hide_return_justification')
    department_approved_by = fields.Many2one('res.users', string="Department Approved By")
    department_approved_date = fields.Date('Department Approved Date')
    hr_approved_by = fields.Many2one('res.users', string="HR Approved By")
    hr_approved_date = fields.Date('HR Approved Date')
    refused_by = fields.Many2one('res.users', string="Refused By")
    refused_date = fields.Date('Refused Date')
    report_employee_is_manager = fields.Boolean(compute='_compute_employee_is_manager')
    branch_id = fields.Many2one('hr.branch', string='Branch', related="employee_id.branch_id", readonly=True, store=True)

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

    @api.multi
    def copy(self):
        for rec in self:
            raise ValidationError(_('Forbidden to duplicate'))

    @api.one
    @api.depends('employee_id')
    def _compute_employee_is_manager(self):
        branches = self.env['hr.branch'].search([('manager_id', '=', self.employee_id.id)])
        departments = self.env['hr.department'].search([('manager_id', '=', self.employee_id.id)])
        if departments or branches:
            self.report_employee_is_manager = True
        else:
            self.report_employee_is_manager = False

    @api.one
    @api.depends('start_work')
    def get_date_day(self):
        if self.start_work:
            self.start_work_day = self.get_week_day(__(self.start_work), 'date')

    def get_week_day(self, some_date, type):
        week_day = {'Monday': 'Monday / الإثنين', 'Tuesday': 'Tuesday / الثلاثاء', 'Wednesday': 'Wednesday / الأربعاء', 'Thursday': 'Thursday / الخميس',
                    'Friday': 'Friday / الجمعة', 'Saturday': 'Saturday / السبت', 'Sunday': 'Sunday / الأحَد'}
        if type == 'datetime':
            some_date_datetime = datetime.strptime(some_date, "%Y-%m-%d %H:%M:%S")
        elif type == 'date':
            some_date_datetime = datetime.strptime(some_date, "%Y-%m-%d")
        else:
            return ''
        some_date_day = calendar.day_name[some_date_datetime.weekday()]
        return week_day[some_date_day]

    @api.multi
    def action_department_manager_approval(self):
        for record in self:
            if record.employee_id.department_manager.user_id.id != self.env.uid and record.employee_id.parent_id.user_id.id != self.env.uid and not self.env.user.has_group(
                    'saudi_hr_employee.group_effective_bypass_department_approvals'):
                raise ValidationError(
                    'Not Allowed !! \n You did not have the permission to click on ( Department manager approval ) for this employee ( %s ), only His / Her Department manager  ( %s ) can click on this button, (or) you must have access to (Bypass Department manager approval)' % (
                        record.employee_id.name, record.employee_id.department_manager.name))
            record.sudo().write({'state': 'Department manager approval', 'department_approved_by': self.env.uid,
                                 'department_approved_date': datetime.now().strftime('%Y-%m-%d')})
        return {}

    @api.multi
    def action_hr_department_approval(self):
        for record in self:
            return record.hr_department_approval()

    @api.multi
    def hr_department_approval(self):
        for record in self:
            record.write({'state': 'HR department approval'})
            record.hr_approved_by = self.env.uid
            record.hr_approved_date = datetime.now().strftime('%Y-%m-%d')
        return {}

    @api.multi
    def action_Refuse(self):
        for record in self:
            record.write({'state': 'Refused'})
            self.refused_by = self.env.uid
            self.refused_date = datetime.now().strftime('%Y-%m-%d')
            body = "This Record Refused"
            self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def action_set_to_new(self):
        for record in self:
            record.write({'state': 'New'})
            body = "This Record Set To New"
            self.message_post(body=body, message_type='email')
        return {}

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].sudo().next_by_code('effective.notice')
        res = super(effective_notice, self).create(vals)
        return res

    @api.onchange('type')
    def onchange_type(self):
        self.start_work = False
        self.payslip_date = False


class hr_contract(models.Model):
    _inherit = "hr.contract"

    first_effective_notice = fields.Many2one('effective.notice', string='First Effective Notice')
    start_work = fields.Date(string="Join Date")
