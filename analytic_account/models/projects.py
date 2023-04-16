# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from .base_tech import *


class Project(models.Model):
    _inherit = "project.project"
