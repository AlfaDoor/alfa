# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from .base_tech import *
from datetime import datetime

import logging
from odoo.addons.fingerprint_sync.libraries.zk import ZK, const
from odoo.tools import __

_logger = logging.getLogger(__name__)


# _logger.info(error_msg)

class hr_attendance(models.Model):
    _inherit = "hr.attendance"

    source = char_field('Source', default='manual')
    fingerprint_id = m2o_field('fingerprint.device', 'Fingerprint')
    sync_time = datetime_field('Sync time')
    date = date_field('Date', compute='get_date')

    @api.one
    @api.depends('check_in', 'check_out')
    def get_date(self):
        date = __(self.check_in, True) or __(self.check_out, True)
        self.date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")

    @api.model
    def create(self, vals):
        res = super(hr_attendance, self).create(vals)
        return res

    @api.model
    def create_new_from_remote(self, values):
        res = {}
        for vals in values:
            employee = self.env['fingerprint.device'].get_employee_by_fingerprint_no(vals['employee_fingerprint_no'])
            if employee:
                if 'fingerprint.device' in self.env:
                    fingerprint = self.env['fingerprint.device'].search([('name', '=', vals['fingerprint'])], limit=1)
                exist_rec = self.search([('employee_id', '=', employee.id), ('name', '=', vals['datetime'])])
                if not exist_rec:
                    _logger.info("Create attendance from RS Employee: %s ,Time: %s, Action: %s" % (employee.name, vals['datetime'], vals['action']))
                    self.create({
                        'employee_id': employee.id,
                        'name': vals['datetime'],
                        'action': vals['action'],
                        'action_compute': vals['action'],
                        'fingerprint_id': fingerprint and fingerprint.id or False,
                    })
                    res[vals['id']] = True
                else:
                    _logger.info("Record {Employee: %s, Time: %s} is exist before" % (employee.name, vals['datetime']))
            else:
                _logger.info("No Employee with fingerprint number %s" % (vals['employee_fingerprint_no']))
                res[vals['id']] = False
        return res


class Employee(models.Model):
    _inherit = "hr.employee"

    fingerprint_no = char_field('fingerprint number')


class fingerprint_device(models.Model):
    _name = "fingerprint.device"

    name = char_field('Name')
    ip = char_field('IP')
    port = integer_field('Port', default=4370)
    timeout = integer_field('timeout', default=5)
    firmware_version = char_field('firmware version')
    last_datetime = datetime_field('Last Sync datetime')
    user_ids = o2m_field('fingerprint.user', 'fingerprint_id', 'Fingerprint users')
    attendance_ids = o2m_field('hr.attendance', 'fingerprint_id', 'Attendances')
    status_config_ids = o2m_field('fingerprint.status.config', 'fingerprint_id', 'Status Configuration')
    attendance_count = integer_field('Number of attendance', compute='get_attendance_count')
    active = bool_field('Active', default=True)

    @api.multi
    def conn(self, _raise=True):
        zk = ZK(self.ip, port=self.port, timeout=self.timeout)
        try:
            conn = zk.connect()
        except:
            if _raise:
                raise ValidationError(_("Connection failed !!"))
            else:
                return False
        return conn

    @api.one
    def testConn(self):
        conn = self.conn()
        self.firmware_version = conn.get_firmware_version()
        conn.test_voice()
        raise ValidationError(_("Connection Successful"))

    @api.one
    def poweroff(self):
        conn = self.conn()
        conn.power_off()

    @api.one
    def restart(self):
        conn = self.conn()
        conn.restart()

    @api.multi
    def get_action_type(self, status):
        status_config = self.env['fingerprint.status.config'].search([('status', '=', status or 0)])
        if status_config:
            if status_config.action == 'overtime_in':
                return 'sign_in'
            if status_config.action == 'overtime_out':
                return 'sign_out'
            return status_config.action
        else:
            raise ValidationError(
                _("Please configure state for number %s in Fingerprint device %s" % (status, self.name)))

    @api.model
    def datetime_to_utc(self, date_time, tz):
        import pytz, datetime
        local = pytz.timezone(tz)
        naive = datetime.datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
        local_dt = local.localize(naive, is_dst=None)
        return local_dt.astimezone(pytz.utc)

    @api.one
    def sync(self):
        conn = self.conn(_raise=False)
        if not conn:
            return
        attendances = conn.get_attendance()
        last_sync_time = __(self.last_datetime)
        for att in attendances:
            employee = self.get_employee_by_fingerprint_no(att.user_id)
            timestamp_original = att.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            timestamp = self.datetime_to_utc(timestamp_original, self.env.user.tz).strftime("%Y-%m-%d %H:%M:%S")
            if not employee:
                _logger.warning(_("No employee for fingerprint user ID %s" % att.user_id))
                continue
            if self.env['hr.attendance'].search([('name', '=', timestamp), ('employee_id', '=', employee.id)]):
                continue
            self.env['hr.attendance'].create({
                'employee_id': employee.id,
                'name': timestamp,
                'action': self.get_action_type(att.status),
                'fingerprint_id': self.id,
                'sync_time': time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            if att.timestamp.strftime("%Y-%m-%d %H:%M:%S") > last_sync_time:
                last_sync_time = att.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        self.last_datetime = last_sync_time

    @api.model
    def sync_all(self):
        for f in self.search([('active', '=', True)]):
            f.sync()

    @api.multi
    def get_employee_by_fingerprint_no(self, no):
        return self.env['hr.employee'].search([('fingerprint_no', '=', no)])

    @api.multi
    def get_fingerprint_atts(self):
        return {
            'domain': [['fingerprint_id', '=', self.id]],
            'name': _('Attendances'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.attendance',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {},
        }

    @api.one
    @api.depends()
    def get_attendance_count(self):
        self.attendance_count = len(self.attendance_ids)

    @api.multi
    def update_firmware(self):
        conn = self.conn(False)
        if conn and not self._context.get('no_update', False):
            self.with_context(dict(self._context, no_update=True)).firmware_version = conn.get_firmware_version()

    @api.model
    def create(self, vals):
        res = super(fingerprint_device, self).create(vals)
        res.update_firmware()
        return res

    @api.multi
    def write(self, vals):
        self.update_firmware()
        return super(fingerprint_device, self).write(vals)

    @api.multi
    def update_users(self):
        conn = self.conn(False)
        if conn:
            self.user_ids.unlink()
            for user in conn.get_users():
                self.with_context(dict(self._context.copy(), create=False)).env['fingerprint.user'].create({
                    'fingerprint_id': self.id,
                    'uid': user.uid,
                    # 'name': str(user.name),
                    'privilege': user.privilege,
                    'password': str(user.password),
                    # 'group_id': user.group_id,
                    'user_id': str(user.user_id),
                    'employee_id': self.get_employee_by_fingerprint_no(user.user_id).id,
                })

    @api.model
    def test_from_remote(self):
        return True


class fingerprint_user(models.Model):
    _name = "fingerprint.user"

    fingerprint_id = m2o_field('fingerprint.device', 'Fingerprint')

    uid = integer_field('UID')
    name = char_field('name')
    privilege = selection_field([
        (const.USER_DEFAULT, 'User'),
        (const.USER_ADMIN, 'Admin'),
    ], string='privilege', default=const.USER_DEFAULT)
    password = char_field('password')
    group_id = char_field('group_id')
    user_id = char_field('user_id')
    employee_id = m2o_field('hr.employee', 'Employee')

    @api.model
    def create(self, vals):
        conn = self.env['fingerprint.device'].search([('id', '=', vals['fingerprint_id'])]).conn(False)
        if conn and self._context.get('create', True):
            conn.set_user(uid=int(vals['user_id']), user_id=str(vals['user_id']), name=str(vals['name']),
                          privilege=const.USER_DEFAULT)  # vals['privilege']
        return super(fingerprint_user, self).create(vals)


class fingerprint_status_config(models.Model):
    _name = "fingerprint.status.config"

    fingerprint_id = m2o_field('fingerprint.device', 'Fingerprint')
    status = integer_field('Status number')
    action = selection_field([
        ('sign_in', 'Sign in'),
        ('sign_out', 'Sign out'),
        ('overtime_in', 'Overtime in'),
        ('overtime_out', 'Overtime out'),
    ])
