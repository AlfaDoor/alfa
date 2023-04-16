# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from .base_tech import *
from datetime import datetime
import logging
from odoo.addons.fingerprint_remote_sync.libraries.zk import ZK, const
import xmlrpc.client
from odoo import tools


def localize_dt(date, to_tz):
    from dateutil import tz
    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz(to_tz)
    utc = date
    if type(date) == str:
        utc = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    utc = utc.replace(tzinfo=from_zone)
    res = utc.astimezone(to_zone)
    return res.strftime('%Y-%m-%d %H:%M:%S')


def __(date, is_datetime=False, localize=False, to_tz=False):
    if date:
        try:
            res = date.strftime(is_datetime and "%Y-%m-%d %H:%M:%S" or "%Y-%m-%d")
            if localize:
                res = localize_dt(res, to_tz)
        except:
            datetime.strptime(date, is_datetime and "%Y-%m-%d %H:%M:%S" or "%Y-%m-%d")
            res = date
        return res
    else:
        return False


_logger = logging.getLogger(__name__)


# _logger.info(error_msg)


class fingerprint_device(models.Model):
    _name = "fingerprint.device"

    name = char_field('Name')
    ip = char_field('IP')
    port = integer_field('Port', default=4370)
    timeout = integer_field('timeout', default=5)
    firmware_version = char_field('firmware version')
    last_datetime = datetime_field('Last Sync datetime')
    user_ids = o2m_field('fingerprint.user', 'fingerprint_id', 'Fingerprint users')
    status_config_ids = o2m_field('fingerprint.status.config', 'fingerprint_id', 'Status Configuration')
    attendance_count = integer_field('Number of attendance', compute='get_attendance_count')
    active = bool_field('Active', default=True)
    attendance_ids = fields.One2many('fingerprint.data', 'fingerprint_id', 'Attendances')
    action_code = fields.Char(default='status')

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
        status_config = self.env['fingerprint.status.config'].search([('status', '=', status or 0),('fingerprint_id','=',self.id)])
        if status_config:
            if status_config.action == 'overtime_in':
                return 'sign_in'
            if status_config.action == 'overtime_out':
                return 'sign_out'
            return status_config.action
        else:
            raise ValidationError(
                _("Please configure state for number %s in Fingerprint device %s" % (status, self.name)))

    @api.one
    def update_actions(self):
        conn = self.conn()
        attendances = conn.get_attendance()
        states = list(set([att.punch for att in attendances]))
        states_exist = self.env['fingerprint.status.config'].search([('fingerprint_id', '=', self.id), ('status', 'in', states)]).ids
        for state in states:
            if state in states_exist: continue
            self.env['fingerprint.status.config'].create({'fingerprint_id': self.id, 'status': state})

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
            timestamp_original = att.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            timestamp = self.datetime_to_utc(timestamp_original, self.env.user.tz).strftime("%Y-%m-%d %H:%M:%S")
            if self.env['fingerprint.data'].search([('employee_no', '=', att.user_id), ('date', '=', timestamp)]):
                continue
            action = getattr(att, self.action_code or 'status')
            self.env['fingerprint.data'].create({
                'employee_no': att.user_id,
                'date': timestamp,
                'action': self.get_action_type(action),
                'action_device': action,
                'fingerprint_id': self.id,
                'done': False,
            })
            if not last_sync_time or att.timestamp.strftime("%Y-%m-%d %H:%M:%S") > last_sync_time:
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
            'res_model': 'fingerprint.data',
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
                    'privilege': user.privilege,
                    'password': str(user.password),
                    'user_id': str(user.user_id),
                    'name': str(user.name),
                    # 'group_id': user.group_id,
                    # 'employee_id': self.get_employee_by_fingerprint_no(user.user_id).id,
                })


class FingerprintData(models.Model):
    _name = "fingerprint.data"

    fingerprint_id = fields.Many2one('fingerprint.device', 'Device')
    employee_no = fields.Char('Employee No.')
    date = fields.Datetime('DateTime')
    action_device = fields.Char('Action(device)')
    action = fields.Char('Action')
    done = fields.Boolean()
    missing = fields.Boolean('Missing')

    @api.model
    def sync_remote_servers(self):
        server_domain = []
        if self._context.get('specified_servers', False):
            server_domain = [('id', 'in', self._context.get('specified_servers'))]
        for server in self.env['remote.server'].search(server_domain):
            values = []
            for fingerprint_data in self:
                values.append({
                    'id': str(fingerprint_data.id),
                    'employee_fingerprint_no': fingerprint_data.employee_no,
                    'fingerprint': fingerprint_data.fingerprint_id.name,
                    'datetime': __(fingerprint_data.date, True, True),
                    'action': fingerprint_data.action,
                })
                _logger.info("################################### Employee No.: %s, Time: %s #############" % (fingerprint_data.employee_no, __(fingerprint_data.date, True, True)))
            if server.test_connection():
                connection, uid = server.connect()
                res = connection.execute_kw(server.db, uid, server.password, 'hr.attendance', 'create_new_from_remote', [values])
                for data_id in res:
                    if not res[data_id]:
                        self.browse(int(data_id)).missing = True
                self.write({'done': True})

    @api.model
    def auto_sync_all(self, missing=False):
        domain = [('done', '=', False), ('missing', '=', False)]
        if self._context.get('missing', False) or missing:
            domain = [('missing', '=', True)]
        self.search(domain)[0:400].sync_remote_servers()
        # for data in self.search(domain)[0:100]:  # .sync_remote_servers()
        #     data.sync_remote_servers()


class fingerprint_user(models.Model):
    _name = "fingerprint.user"

    fingerprint_id = fields.Many2one('fingerprint.device', 'Fingerprint')

    uid = integer_field('UID')
    name = char_field('name')
    privilege = selection_field([
        (const.USER_DEFAULT, 'User'),
        (const.USER_ADMIN, 'Admin'),
    ], string='privilege', default=const.USER_DEFAULT)
    password = char_field('password')
    group_id = char_field('group_id')
    user_id = char_field('user_id')

    # employee_id = m2o_field('hr.employee', 'Employee')

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


class RemoteServer(models.Model):
    _name = "remote.server"

    name = fields.Char('Name')
    url = fields.Char('URL')
    db = fields.Char('Database')
    user = fields.Char('User name')
    password = fields.Char('Password')
    state = fields.Selection([('connected', 'Connected',), ('disconnected', 'Disconnected')], string='Status', compute='test_connection', store=True)
    active = fields.Boolean()

    @api.model
    def connect(self):
        url, db, username, password = self.url, self.db, self.user, self.password
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
        common.version()
        uid = common.authenticate(db, username, password, {})
        connection = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        return connection, uid

    def test_connection(self):
        connection, uid = self.connect()
        try:
            res = connection.execute_kw(self.db, uid, self.password, 'fingerprint.device', 'test_from_remote', [])
        except:
            self.state = 'disconnected'
            return False
        if res:
            self.state = 'connected'
            return True
