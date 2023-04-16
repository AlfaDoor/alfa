# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _, SUPERUSER_ID
from datetime import datetime
from odoo.tools import __
from odoo.exceptions import ValidationError


class national_holiday(models.Model):
    _name = "hr.national.holiday"
    _inherit = "mail.thread"

    name = fields.Char('Description')
    code = fields.Char('Code')
    year = fields.Integer(string="Year")
    start_date = fields.Date(string="Holiday Start Date")
    end_date = fields.Date(string="Holiday End Date")
    duration = fields.Integer(string="Holiday Duration", compute="_compute_duration")
    duration_in_leave_request = fields.Selection([
        ('yes', 'yes'),
        ('No', 'No'),
    ], string='Include Holiday duration in leave request calculation', default='No',
        help="Example :You have a national holiday between 05/10/2017 to 09/10/2017 ( 5 days ), an employee requested for a leave between 01/10/2017 and 30/10/2017, if you select yes, leave request duration will be 30 days, if you select no, leave request duration will be 25 days.")
    notes = fields.Html(string="Notes")
    state = fields.Selection([
        ('New', 'New'),
        ('Confirmed', 'Confirmed'),
    ], string='Status', index=True, default='New', )

    @api.constrains('end_date', 'start_date')
    def check_duration(self):
        if __(self.end_date) < __(self.start_date):
            raise ValidationError(_("Sorry! Holiday Start Date can not be less than  Holiday End Date."))

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].sudo().next_by_code('national.holiday')
        res = super(national_holiday, self).create(vals)
        return res

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and __(rec.end_date):
                start_date = datetime.strptime(__(rec.start_date), "%Y-%m-%d")
                end_date = datetime.strptime(__(rec.end_date), "%Y-%m-%d")
                timedelta = end_date - start_date
                rec.duration = timedelta.days + 1

    @api.multi
    def send_mail_to_employee(self):
        for record in self:
            raise exceptions.ValidationError("Under development.")
        return {}

    @api.model
    def day_in_national_holiday(self, date):
        n = self.search([('start_date', '<=', date), ('end_date', '>=', date)], limit=1)
        if len(n) > 0:
            return True
        return False

    @api.multi
    def action_confirm(self):
        for record in self:
            old_holidays = self.env['hr.national.holiday'].search([])
            for old_holiday in old_holidays:
                if __(old_holiday.end_date) < __(record.start_date) or __(old_holiday.start_date) > __(record.end_date):
                    continue
                elif old_holiday.id == record.id:
                    continue
                else:
                    raise exceptions.ValidationError(" Data Error!! \n This Holiday conflicts with another Holiday.")
            record.write({'state': 'Confirmed'})
            body = "This Record Confirmed"
            self.message_post(body=body, message_type='email')
        return {}

    @api.multi
    def action_set_new(self):
        for record in self:
            record.write({'state': 'New'})
            body = "This Record Set To New"
            self.message_post(body=body, message_type='email')
        return {}
