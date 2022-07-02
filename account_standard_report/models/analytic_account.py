# -*- coding: utf-8 -*-from .

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError, QWebException


class AnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

