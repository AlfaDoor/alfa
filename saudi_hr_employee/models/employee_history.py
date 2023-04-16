# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import api, fields, models, _
from datetime import datetime


class Employee(models.Model):
    _inherit = "hr.employee"

    history_count = fields.Integer('History count', compute='get_history_count')
    history_ids = fields.One2many('employee.department.history', 'employee_id', 'Employee history')

    @api.depends()
    def get_history_count(self):
        self.history_count = len(self.history_ids)

    @api.multi
    def write(self, vals):
        if vals.get('department_id', False):
            self.env['employee.department.history'].create({
                'employee_id': self.id,
                'from_department_id': self.department_id.id,
                'to_department_id': vals.get('department_id', False),
            })
        return super(Employee, self).write(vals)

    @api.multi
    def open_employee_history(self):
        return {
            'domain': [('employee_id', '=', self.id)],
            'name': _('Employee History'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'employee.department.history',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'default_employee_id': self.id}
        }


class employee_department_history(models.Model):
    _name = "employee.department.history"
    _description = "Employee History"

    employee_id = fields.Many2one('hr.employee', 'Employee')
    from_department_id = fields.Many2one('hr.department', 'From department')
    to_department_id = fields.Many2one('hr.department', 'To department')
