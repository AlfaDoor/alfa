# coding:utf-8

from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import ValidationError


class LeaveAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    MONTHS_SELECTION = {'01': 'January', '02': 'February', '03': 'March', '04': 'April', '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                        '09': 'September', '10': 'October', '11': 'November', '12': 'December'}

    employee_id = fields.Many2one('hr.employee', "Employee", default=lambda self: self.env.user.employee_ids and self.env.user.employee_ids[0].id)

    holiday_status_id = fields.Many2one("hr.leave.type", "Leave Type",
                                        states={'draft': [('readonly', False)], 'validate': [('readonly', False)]},
                                        domain=[('state', 'in', ['Approved'])])
    holiday_status_type = fields.Selection([('Annual Leave', 'Annual Leave'),
                                            ('Non Annual Leave', '‫‪Non Annual Leave‬‬')], related='holiday_status_id.type', readonly=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', related="employee_id.contract_id", readonly=True, store=True)
    join_date = fields.Date('Join date', related='employee_id.contract_id.start_work', readonly=True)
    annual_leave_policy = fields.Many2one('hr.leave.type', string='Annual Leave Policy', related="contract_id.annual_leave_policy", readonly=True)
    allocation_date = fields.Date('Allocation Date')
    system_created = fields.Boolean('Created By The System', readonly=True)
    approved_by = fields.Many2one('res.users', string="Approved By", readonly=True)
    leave_automatic_allocation = fields.Many2one('leave.automatic.allocation', string="Leave Automatic Allocation", readonly=True)
    request_reason = fields.Selection([
        ('annual', 'annual leave'),
        ('non-annual', 'Non-annual leave'),
    ], string='Leave request reason')
    nationality_type = fields.Selection(related='employee_id.nationality_type', store=True, readonly=True)
    branch_id = fields.Many2one('hr.branch', string='Branch', related="employee_id.branch_id", readonly=True, store=True)
    department_id = fields.Many2one('hr.department', string='Department', related="employee_id.department_id", readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string='Job Title', related="employee_id.job_id", readonly=True, store=True)
    country_id = fields.Many2one('res.country', '‫‪Nationality‬‬', related="employee_id.country_id", readonly=True, store=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender', related='employee_id.gender', store=True, readonly=True)
    adjusted_date = fields.Date('Adjusted Date', related='contract_id.adjusted_date', readonly=True)
    by_eos = fields.Boolean('Through EOS')
    leave_days_ids = fields.One2many('leave.month.days', 'leave_id', 'Number of days per each month')
    is_init = fields.Boolean('This is begging allocation', default=False)

    _sql_constraints = [
        ('duration_check', "CHECK (1 = 1)", ""),
    ]

    @api.onchange('employee_id')
    def get_default_leave_type(self):
        self.holiday_status_id = self.contract_id.annual_leave_policy.id

    @api.model_cr
    def init(self):
        # drop hr_leave_allocation_duration_check constraint
        pass

    def action_reset(self):
        self.state = 'confirm'

    def action_validate(self):
        self.state = 'validate'
