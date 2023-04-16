# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from dateutil import relativedelta

from odoo import models, fields, api, exceptions, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError, QWebException
from odoo.tools.translate import _

class batch_generate_requests(models.TransientModel):

    _name ='air.ticket.batch.generate.requests'
    _description = 'Generate air ticket requests for all selected employees'


    employees_ids = fields.Many2many('hr.employee', string='Employees')

    @api.one
    def compute_sheet(self):
        if not self.employees_ids:
            raise ValidationError('Kindly select one employee at least')
        for employee in self.employees_ids:
            batch = self.env['air.ticket.request.batch'].browse(self._context.get('active_id', False))
            air_ticket_type = employee.contract_id.air_ticket_policy
            ctx = dict(self._context, skip_validation=True)
            air_ticket_request = self.with_context(ctx).env['air.ticket.request'].create({
                'description': "Auto- Air ticket cash allowance for %s" % (employee.name),
                'employee_id': employee.id,
                'request_reason': 'Air Ticket Cash Allowance',
                'request_date': batch.date,
                'reserve_ticket_for': 'Employee only',
                'i_want_to': 'Cash',
                'air_ticket_type': air_ticket_type.id,
                'batch_id': batch.id,
            })
            air_ticket_request.onchange_employee_id()
            air_ticket_request.get_old_tickets_request()
            air_ticket_request.get_remaining()
            # air_ticket_request.onchange_travel_date()
            # air_ticket_request.review()
        # pass
        # emp_pool = self.pool.get('hr.employee')
        # slip_pool = self.pool.get('hr.payslip')
        # run_pool = self.pool.get('hr.payslip.run')
        # slip_ids = []
        # if context is None:
        #     context = {}
        # data = self.read(cr, uid, ids, context=context)[0]
        # run_data = {}
        # if context and context.get('active_id', False):
        #     run_data = run_pool.read(cr, uid, [context['active_id']], ['date_start', 'date_end', 'credit_note'])[0]
        # from_date =  run_data.get('date_start', False)
        # to_date = run_data.get('date_end', False)
        # credit_note = run_data.get('credit_note', False)
        # if not data['employee_ids']:
        #     raise UserError(_("You must select employee(s) to generate payslip(s)."))
        # for emp in emp_pool.browse(cr, uid, data['employee_ids'], context=context):
        #     slip_data = slip_pool.onchange_employee_id(cr, uid, [], from_date, to_date, emp.id, contract_id=False, context=context)
        #     res = {
        #         'employee_id': emp.id,
        #         'name': slip_data['value'].get('name', False),
        #         'struct_id': slip_data['value'].get('struct_id', False),
        #         'contract_id': slip_data['value'].get('contract_id', False),
        #         'payslip_run_id': context.get('active_id', False),
        #         'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids', False)],
        #         'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids', False)],
        #         'date_from': from_date,
        #         'date_to': to_date,
        #         'credit_note': credit_note,
        #     }
        #     slip_ids.append(slip_pool.create(cr, uid, res, context=context))
        # slip_pool.compute_sheet(cr, uid, slip_ids, context=context)
        # return {'type': 'ir.actions.act_window_close'}
