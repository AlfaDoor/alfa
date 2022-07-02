# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
# import openerp.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
from odoo.tools import __

class service_request_config(models.Model):
    _name = 'service.request.config'
    _description = "Request for a service Configuration"
    _inherit = 'mail.thread'

    code = fields.Char('Service Code', readonly=True)
    name = fields.Char('Service Description in Arabic')
    english_name = fields.Char('Service Description in English')
    active = fields.Boolean('Active', default=True)
    type = fields.Selection([('Identification Certificate with total salary', 'Identification Certificate with total salary'),
                             ('Identification Certificate without total salary', 'Identification Certificate without total salary'),
                             ('Identification Certificate with salary details', 'Identification Certificate with salary details'),
                             ('Salary Transfer Request', 'Salary Transfer Request')], 'Service Type')
    benefit_name = fields.Boolean('Employee should write the beneficiary name ?')
    attach_doc = fields.Boolean('Employee should attach documents in order to perform this service')
    attach_num = fields.Integer('Number of attachments')
    is_print = fields.Boolean('Print is available for this service ?', default=True)
    print_for = fields.Integer('Print is available for')
    allow_in_trial = fields.Boolean('Allow to request in trial period ?',
                                    help='If = yes, employee will be able to request for this service even if he still in trial period')
    change_bank_info = fields.Boolean('Automatically change bank information ?',
                                      help='If = yes, after approving Salary Transfer Request, your system will automatically update bank information on employee profile. if = no, HR team must change bank information manually.')
    terms_condition = fields.Text('Service terms and condition')
    request_ids = fields.One2many('service.request', 'config_id', 'Requests')
    state = fields.Selection([
        ('New', 'New'),
        ('Approved', 'Approved'),
    ], string='Status', readonly=True, index=True, default='New', )
    service_request_count = fields.Float('Request for a service count', compute='get_request_services_count')
    responsible_id = fields.Many2one('res.users', 'Approvals Responsible User')

    @api.one
    def get_request_services_count(self):
        self.service_request_count = self.env['service.request'].search_count([('config_id', '=', self.id)])

    @api.multi
    def action_request_services(self):
        return {
            'domain': [('config_id', '=', self.id)],
            'name': _('Request For Services'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'service.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.one
    def unlink(self):
        if self.state == 'Approved':
            raise ValidationError('Not allowed to delete approved transaction')
        if self.request_ids:
            raise ValidationError('Not allowed to delete transaction , there is employee requests with this type')

    @api.one
    def action_set_new(self):
        self.state = 'New'
        body = "Document Set To New"
        self.message_post(body=body, message_type='email')

    @api.one
    def action_approve(self):
        self.state = 'Approved'
        body = "Document Approved"
        self.message_post(body=body, message_type='email')

    @api.onchange('attach_doc')
    def onchange_attach_doc(self):
        self.attach_num = 0

    @api.onchange('is_print')
    def onchange_is_print(self):
        if self.is_print:
            self.print_for = 7
        else:
            self.print_for = 0

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].sudo().next_by_code('service.request.config')
        res = super(service_request_config, self).create(vals)
        return res


class ServiceRequestAttaches(models.Model):
    _name = "service.request.attaches"
    _description = "service request Attaches"

    request_id = fields.Many2one('service.request', 'Request')
    file = fields.Binary('File', attachment=True, )
    file_name = fields.Char('File name')
    name = fields.Char('Description')
    note = fields.Char('Notes')


class service_request(models.Model):
    _name = 'service.request'
    _description = "Request for a service"
    _inherit = 'mail.thread'

    code = fields.Char('Code', readonly=True)
    employee_id = fields.Many2one('hr.employee', "Employee", default=lambda self: self.env.user.employee_ids and self.env.user.employee_ids[0].id)
    employee_number = fields.Char(related='employee_id.employee_number', store=True, readonly=True)
    nationality_type = fields.Selection([('Native', 'Native'),
                                         ('Non-native', 'Non-native')], )
    branch_id = fields.Many2one('hr.branch', string='Branch')
    department_id = fields.Many2one('hr.department', string='Department')
    job_id = fields.Many2one('hr.job', string='Job Title')
    country_id = fields.Many2one('res.country', '‫‪Nationality‬‬')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender')
    contract_id = fields.Many2one('hr.contract', string='Contract', compute="_compute_contract", readonly=True, store=True)
    config_id = fields.Many2one('service.request.config', 'What is the requested service ?', domain=[('state', '=', 'Approved')])
    type = fields.Selection([('Identification Certificate with total salary', 'Identification Certificate with total salary'),
                             ('Identification Certificate without total salary', 'Identification Certificate without total salary'),
                             ('Identification Certificate with salary details', 'Identification Certificate with salary details'),
                             ('Salary Transfer Request', 'Salary Transfer Request')], 'Service Type')
    benefit_name = fields.Char('Beneficiary name in arabic')
    benefit_name_english = fields.Char('Beneficiary name in english')
    is_benefit = fields.Boolean(related='config_id.benefit_name', store=True, readonly=True)
    new_bank = fields.Many2one('res.bank', 'Name of new Bank')
    new_iban_number = fields.Char('New Iban number')
    current_bank = fields.Many2one('res.bank', string='Current Bank')
    current_account_number = fields.Char(string='Current account number')
    has_bank_loan = fields.Boolean('Has Bank Loan')
    loan_bank_name = fields.Many2one('res.bank', 'Loan - Bank name')
    loan_bank_amount = fields.Float('Bank - loan amount')
    loan_bank_date = fields.Date('Bank - loan date')
    loan_bank_note = fields.Text('Bank loan - notes')
    attachment_ids = fields.One2many('service.request.attaches', 'request_id', 'Attachments')
    terms_condition = fields.Text('Service terms and condition')
    started_by = fields.Many2one('res.users', string="Process started by")
    started_on = fields.Date('Process started on')
    done_by = fields.Many2one('res.users', string="Done / Service performed by")
    done_on = fields.Date('Done / Services performed on')
    printed_by = fields.Many2one('res.users', string="Last printed by")
    printed_on = fields.Date('Last print on')
    state = fields.Selection([
        ('New', 'New'),
        ('Process Started', 'Process Started'),
        ('Done / Service performed', 'Done / Service performed'),
        ('Refused', 'Refused'),
    ], string='Status', readonly=True, index=True, default='New', )
    show_print = fields.Boolean('Show Print Button', compute='_compute_show_print')
    show_buttons = fields.Boolean(compute='compute_show_buttons')

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

    @api.one
    def compute_show_buttons(self):
        if self.env.user.has_group('hr.group_hr_manager') or self.env.user.id == self.config_id.responsible_id.id:
            self.show_buttons = True
        else:
            self.show_buttons = False

    @api.one
    def unlink(self):
        if self.state != 'New':
            raise ValidationError("You can delete only new requests.")
        return super(service_request, self).unlink()

    @api.multi
    def copy(self):
        for rec in self:
            raise ValidationError('Forbidden to duplicate')

    @api.multi
    def action_print(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.printed_by = self.env.uid
        self.printed_on = datetime.now().strftime('%Y-%m-%d')
        return self.env.ref('services_request.report_identification').report_action(self.id)

    @api.one
    def _compute_show_print(self):
        if self.started_on:
            date_available = datetime.strptime(__(self.started_on), '%Y-%m-%d') + timedelta(days=self.config_id.print_for)
            if self.config_id.is_print and __(self.started_on) <= datetime.now().strftime('%Y-%m-%d') and date_available.strftime(
                    '%Y-%m-%d') >= datetime.now().strftime('%Y-%m-%d'):
                self.show_print = True
            else:
                self.show_print = False
        else:
            self.show_print = False

    @api.one
    def action_set_new(self):
        self.state = 'New'
        body = "Record Reset To New "
        self.message_post(body=body, message_type='email')

    @api.one
    def action_refuse(self):
        self.state = 'Refused'

    @api.onchange('config_id')
    def get_related_config_fields(self):
        self.terms_condition = self.config_id.terms_condition
        self.type = self.config_id.type

    @api.onchange('employee_id')
    def get_related_fields(self):
        self.nationality_type = self.employee_id.nationality_type
        self.branch_id = self.employee_id.branch_id
        self.department_id = self.employee_id.department_id
        self.job_id = self.employee_id.job_id
        self.country_id = self.employee_id.country_id
        self.gender = self.employee_id.gender
        self.current_bank = self.employee_id.Bank_name_id
        self.current_account_number = self.employee_id.bank_account_number
        self.has_bank_loan = self.employee_id.has_bank_loan
        self.loan_bank_name = self.employee_id.loan_bank_name
        self.loan_bank_amount = self.employee_id.loan_bank_amount
        self.loan_bank_date = __(self.employee_id.loan_bank_date)
        self.loan_bank_note = self.employee_id.loan_bank_note

    @api.one
    def action_done(self):
        self.state = 'Done / Service performed'
        self.done_by = self.env.uid
        self.done_on = datetime.now().strftime('%Y-%m-%d')
        if self.type == 'Salary Transfer Request' and self.config_id.change_bank_info:
            old_Bank_name_id = self.employee_id.Bank_name_id
            old_iban_number = self.employee_id.iban_number
            self.employee_id.with_context({'button_toggle': True}).Bank_name_id = self.new_bank.id
            self.employee_id.with_context({'button_toggle': True}).iban_number = self.new_iban_number
            body2 = "Bank information changed, Old bank account = ( %s ), Old IBAN number = ( %s ), New bank account = ( %s ) New IBAN number = ( %s )" % (
            old_Bank_name_id.name, old_iban_number, self.new_bank.name, self.new_iban_number)
            self.employee_id.with_context({'button_toggle': True}).message_post(body=body2, message_type='email')

    @api.multi
    def action_start(self):
        for rec in self:
            error_msg = _("Are you sure that the process already started ? \n Before performing this service, kindly review terms and conditions. \n %s") % (
            rec.terms_condition)
            return self.env.user.show_dialogue(error_msg, 'service.request', 'action_start_confirm', rec.id)

    @api.one
    def action_start_confirm(self):
        self.state = 'Process Started'
        self.started_by = self.env.uid
        self.started_on = datetime.now().strftime('%Y-%m-%d')
        body = "This Record Started "
        self.message_post(body=body, message_type='email')

    @api.multi
    @api.depends('employee_id')
    def name_get(self):
        res = []
        for rec in self:
            name = "Request Service For %s" % rec.employee_id.name
            res += [(rec.id, name)]
        return res

    @api.onchange('type')
    def empty_new_bank(self):
        self.new_bank = False
        self.new_iban_number = False

    @api.onchange('config_id')
    def onchange_config_id(self):
        if self.config_id.terms_condition:
            res = {'warning': {
                'title': _('service terms and condition'),
                'message': self.config_id.terms_condition
            }}
            return res

    @api.depends('employee_id')
    def _compute_contract(self):
        for rec in self:
            contracts = self.env['hr.contract'].search([('employee_id', '=', rec.employee_id.id), ('active', '=', True)])
            if len(contracts):
                rec.contract_id = contracts[0].id

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].sudo().next_by_code('service.request')
        res = super(service_request, self).create(vals)
        return res


class hr_employee(models.Model):
    _inherit = "hr.employee"

    service_request_count = fields.Float('Request for a service count', compute='get_request_services_count')

    @api.one
    def get_request_services_count(self):
        self.service_request_count = self.env['service.request'].search_count([('employee_id', '=', self.id)])

    @api.multi
    def action_request_services(self):
        return {
            'domain': [('employee_id', '=', self.id)],
            'name': _('Employee request For Services'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'service.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
