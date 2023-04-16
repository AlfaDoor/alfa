# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, QWebException
import time

import logging


# _logger = logging.getLogger(__name__)
# _logger.info(error_msg)

class account_move_line(models.Model):
    _inherit = "account.move.line"

    employee_id = fields.Many2one('hr.employee', 'Employee')