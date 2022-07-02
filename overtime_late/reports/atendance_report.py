# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import __


class attendance_report(models.TransientModel):
    _name = "attendance.report"

    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    department_ids = fields.Many2many('hr.department', string='Departments')
    branch_ids = fields.Many2many('hr.branch', string='Branches')

    @api.multi
    def print_report(self):
        data = {
            'date_from': __(self.date_from),
            'date_to': __(self.date_to),
            'employee_ids': self.employee_ids.ids,
            'branch_ids': self.branch_ids.ids,
            'department_ids': self.department_ids.ids,
        }
        return self.env.ref('overtime_late.attendance_report').report_action(self, data=data)


class attendance_report_(models.AbstractModel):
    _name = "report.overtime_late.report_attendance"

    @api.model
    def to_minute(self, float_min):
        return "%s:%s" % (int(float_min), int((float_min - int(float_min)) * 60))

    @api.multi
    def _get_report_values(self, docids, data=None):
        domain = [('date', '>=', data.get('date_from', False)), ('date', '<=', data.get('date_to', False)), ]
        if data.get('employee_ids', False):
            domain += [('employee_id', 'in', data.get('employee_ids', False))]
        if data.get('department_ids', False):
            domain += [('employee_id.department_id', 'in', data.get('department_ids', False))]
        if data.get('branch_ids', False):
            domain += [('employee_id.branch_id', 'in', data.get('branch_ids', False))]
        working_day_ids = self.env['working.days'].search(domain)  # .ids
        report_data = {}
        for work_day in working_day_ids:
            if not report_data.get(work_day.employee_id.id, False):
                report_data[work_day.employee_id.id] = {
                    'lines': [],
                    'absence_count': 0,
                    'delay_count': 0,
                    'total_delay': 0,
                    'total_working': 0,
                }
            report_data[work_day.employee_id.id]['lines'].append(work_day)
            report_data[work_day.employee_id.id]['absence_count'] += work_day.absence and 1 or 0
            report_data[work_day.employee_id.id]['delay_count'] += work_day.morning_delay and 1 or 0
            report_data[work_day.employee_id.id]['delay_count'] += work_day.exit_delay and 1 or 0
            report_data[work_day.employee_id.id]['total_delay'] += work_day.delay_minutes
            report_data[work_day.employee_id.id]['total_working'] += work_day.total_working_minutes

        values = {'working_day_ids': working_day_ids}
        values['report_data'] = report_data
        active_obj = self.env['attendance.report'].browse(data['context']['active_id'])
        values['date_from'] = __(active_obj.date_from)
        values['date_to'] = __(active_obj.date_to)
        values['company'] = self.env.user.company_id
        values['to_minute'] = self.to_minute
        return values
        return self.env['report'].render('overtime_late.report_attendance', values=values)
