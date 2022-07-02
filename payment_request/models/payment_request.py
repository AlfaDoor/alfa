# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PaymentRequest(models.Model):
    _name = "payment.request"

    date = fields.Date('Date', default=fields.Date.context_today)
    due_date = fields.Date('Due date', default=fields.Date.context_today)
    amount = fields.Float('Amount')
    ref = fields.Char('Reference')
    partner_id = fields.Many2one('res.partner', 'Vendor')
    invoice_ids = fields.Many2many('account.invoice', string='Invoices')
    state = fields.Selection([('new', 'New'), ('reviewed', 'Reviewed'), ('confirmed', 'Confirmed'), ('done', 'Done')], string='Status', default='new')
    note = fields.Html('Notes')
    payment_detail_ids = fields.One2many('payment.detail', 'request_id', 'Payment details')
    amount_approved = fields.Float('Approved Amount', compute='get_amount_approved')

    @api.multi
    def create_payment(self):
        return {
            'name': _('Payment'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('account.view_account_payment_form').id,
            'context': {
                'default_payment_type': 'outbound',
                'default_partner_type': 'supplier',
                'default_partner_id': self.partner_id.id,
                'default_invoice_ids': self.invoice_ids.ids,
            },
            'target': 'new',
            'domain': [('id', 'in', self.invoice_ids.ids)]
        }

    @api.one
    def get_amount_approved(self):
        self.amount_approved = sum([d.amount for d in self.payment_detail_ids if d.state == 'confirmed'])

    @api.onchange('partner_id')
    def onchange_partner(self):
        self.invoice_ids = [(5,)]

    @api.onchange('invoice_ids')
    def onchange_partner(self):
        self.amount = sum([i.residual for i in self.invoice_ids])

    # @api.onchange('payment_detail_ids')
    # def onchange_payment_detail_ids(self):
    #     if not self.payment_detail_ids:
    #         raise ValidationError(_("Please select Vendor !!"))

    @api.one
    def action_review(self):
        if self.amount <= 0:
            raise ValidationError(_("Amount can not be zero !"))
        self.state = 'reviewed'

    @api.one
    def action_confirm(self):
        self.state = 'confirmed'

    @api.one
    def name_get(self):
        return (self.id, "%s [%s]" % (self.partner_id.name, self.amount))


class PaymentDetails(models.Model):
    _name = "payment.detail"

    request_id = fields.Many2one('payment.request', 'Payment request')
    department_id = fields.Many2one('hr.department', 'Department')
    responsible_id = fields.Many2one('hr.employee', 'Responsible')
    responsible_user_id = fields.Many2one('res.users', 'Responsible user', related='responsible_id.user_id')
    partner_id = fields.Many2one('res.partner', 'Vendor', related='request_id.partner_id')
    ref = fields.Char('Reference', related='request_id.ref')
    amount = fields.Float('Amount')
    invoice_ids = fields.Many2many('account.invoice', string='Invoices')
    date = fields.Date('Date', default=fields.Date.context_today)
    note = fields.Html('Notes')
    state = fields.Selection([('new', 'New'), ('reviewed', 'Reviewed'), ('confirmed', 'Confirmed')], default='new', string='Status')
    invoices_count = fields.Integer('Invoices count', compute='get_invoices_count')

    @api.onchange('department_id')
    def onchange_department_id(self):
        self.responsible_id = self.department_id.manager_id.id

    @api.one
    def get_invoices_count(self):
        self.invoices_count = len(self.invoice_ids)

    @api.multi
    def open_invoices(self):
        return {
            'name': _('Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'context': {},
            'target': 'current',
            'domain': [('id', 'in', self.invoice_ids.ids)]
        }

    @api.one
    def action_review(self):
        self.state = 'reviewed'

    @api.one
    def action_confirm(self):
        self.state = 'confirmed'

    @api.one
    def name_get(self):
        return (self.id, "%s [%s]" % (self.partner_id.name, self.amount))
