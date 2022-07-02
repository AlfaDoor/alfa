# -*- coding: utf-8 -*-

# Api V7 Imports
from odoo import fields, models,api
import base64
import os
import os.path
from odoo.tools import config, human_size, ustr, html_escape

import logging
_logger = logging.getLogger(__name__)


class ir_attachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _file_read(self, fname, bin_size=False):
        full_path = self._full_path(fname)
        r = ''
        try:
            if bin_size:
                if os.path.isfile(full_path):
                    r = human_size(os.path.getsize(full_path))
            else:
                r = base64.b64encode(open(full_path,'rb').read())
        except (IOError, OSError):
            _logger.info("_read_file reading %s", full_path, exc_info=True)
        return r

