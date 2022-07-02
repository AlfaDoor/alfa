# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
# import openerp.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta


class report_identification(models.AbstractModel):
    _name = 'report.services_request.report_identification_view'

    @api.multi
    def _get_report_values(self, docids, data=None):
        # report_obj = self.env['report']
        # report = report_obj._get_report_from_name('services_request.report_identification_view')
        records = self.env['service.request'].browse(self._ids)
        hr_departments = self.env['hr.department'].search([('type', '=', 'HR Department')])
        hr_manager = False
        if hr_departments:
            hr_department = hr_departments[0]
            hr_manager = hr_department.manager_id
        docargs = {
            'doc_ids': docids,
            'doc_model': 'service.request',
            'docs': self.env['service.request'].browse(docids)
        }
        if hr_manager:
            docargs['hr_manager'] = hr_manager
        return docargs
