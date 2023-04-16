# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
# import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from datetime import datetime, date, timedelta
import copy
import pytz
from .base_tech import *
from dateutil.relativedelta import relativedelta
from .overtime_calc import over_time_calc
