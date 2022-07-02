from datetime import datetime,date, timedelta,time
from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError

class HrLoanBatches(models.Model):
    _name = 'loan.batches'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Loan Batches'

    name = fields.Char()
    loan_ids = fields.One2many('loan.advance.request', 'loan_batch_id', string='Attendance Sheets')
    state = fields.Selection( [
        ('new', 'New'),
        ('payroll_officer_approval', 'Payroll Officer Approval'),
        ('hr_manager_approve', 'HR Manager Approve'),
        ('financial_manager_approve', 'Financial Manager Approve'),
        ('gm_approve', 'CEO / GM approval'),
        ('loan_fully_paid', 'Loan Fully Paid'),
        ('refused', 'Refused'),
    ], string='Status',default='new')
    date_start = fields.Date(string='Date From')
    date_end = fields.Date(string='Date To')

    @api.multi
    def action_payroll_officer_approve(self):
        for record in self.loan_ids:
            record.state = 'Payroll Officer Approval'
        return self.write({'state': 'payroll_officer_approval'})

    @api.multi
    def action_hr_loan_batch_approve(self):
        for record in self.loan_ids:
            if not record.hr_manager_approval:
                record.hr_manager_approval = record.loan_amount
            record.state = 'HR Manager Approve'
        return self.write({'state': 'hr_manager_approve'})

    @api.multi
    def action_batch_financial_approve(self):
        for record in self.loan_ids:
            if not record.financial_manager_approval:
                record.financial_manager_approval = record.loan_amount
            record.state = 'Financial Manager Approve'
        return self.write({'state': 'financial_manager_approve'})

    @api.multi
    def action_batch_gm_approve(self):
        for record in self.loan_ids:
            if not record.general_manager_approval:
                record.general_manager_approval = record.loan_amount
            record.state = 'GM Approve'
        return self.write({'state': 'gm_approve'})

    @api.multi
    def action_batch_refuse(self):
        for record in self.loan_ids:
            if record.state == 'GM Approve':
                raise ValidationError("Not allowed !!")
            else:
                record.state = 'Refused'
        return self.write({'state': 'refused'})

    @api.multi
    def action_refuse_confirm_batch(self):
        for record in self.loan_ids:
            record.state = 'Refused'
        return self.write({'state': 'refused'})


class InheritLoan(models.Model):
    _inherit = 'loan.advance.request'
    loan_batch_id = fields.Many2one('laon.batches')
