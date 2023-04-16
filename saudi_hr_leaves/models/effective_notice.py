# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from odoo.tools import __


class effective_notice(models.Model):
    _inherit = 'effective.notice'

    # Leaves
    leave_request_id = fields.Many2one('hr.leave', string='Leave Request')
    leave_start_date = fields.Datetime('Leave Start Date', related="leave_request_id.date_from", readonly=True)
    leave_start_date_day = fields.Char('Leave Start Date Day', related="leave_request_id.date_from_day", readonly=True)
    leave_end_date = fields.Datetime('Leave End Date', related="leave_request_id.date_to", readonly=True)
    leave_end_date_day = fields.Char('Leave End Date Day', related="leave_request_id.date_to_day", readonly=True)
    expected_working_day = fields.Date('Expected working day', related="leave_request_id.expected_working_day", readonly=True)
    expected_working_week_day = fields.Char('Leave End Date Day', related="leave_request_id.expected_working_week_day", readonly=True)
    type = fields.Selection(selection_add=[('Return From Leave', 'Return From Leave')])

    @api.multi
    def hr_department_approval(self):
        super(effective_notice, self).hr_department_approval()
        for record in self:
            if record.type == 'Return From Leave':
                if record.leave_request_id.return_from_leave:
                    raise ValidationError(
                        "Not Allowed !! \n We found that the leave which you selected is already linked with another Return from leave, it is not logic to create 2 return from leave for the same leave request,  kindly review old return from leave  for the same employee.")
                else:
                    record.leave_request_id.return_from_leave = record.id

    @api.onchange('type')
    def onchange_type(self):
        self.leave_request_id = ''
        super(effective_notice, self).onchange_type()

    @api.one
    @api.depends('start_work', 'expected_working_day')
    def _compute_hide_return_justification(self):
        if self.start_work and self.expected_working_day and self.start_work != self.expected_working_day:
            self.hide_return_justification = False
            self.return_justification
        else:
            self.hide_return_justification = True
