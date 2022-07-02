# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from .base_tech import *


class change_working_hours(models.Model):
    _name = "change.working.hours"
    _inherit = "mail.thread"
    _rec_name = "calender_id"

    date_from = date_field('Date from')
    date_to = date_field('Date to')
    employee_ids = m2m_field('hr.employee', 'change_working_hours_hr_employee_rel', 'change_working_hours_id', 'hr_employee_id', string='Employees')
    calender_id = m2o_field('resource.calendar', 'working time')
    state = selection_field([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='new')

    @api.one
    def action_confirm(self):
        self.state = 'confirmed'
