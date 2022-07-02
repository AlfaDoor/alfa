# -*- coding: utf-8 -*-

from odoo import models, fields, api , exceptions ,_
# import openerp.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from datetime import datetime,date ,timedelta



class report_identification(models.AbstractModel):
    _name = 'report.services_request.report_identification_view'

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('services_request.report_identification_view')
        records = self.env['service.request'].browse(self._ids)
        hr_departments = self.env['hr.department'].search([('type','=','HR Department')])
        hr_manager = False
        if hr_departments:
            hr_department = hr_departments[0]
            hr_manager = hr_department.manager_id
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': records,
        }
        if hr_manager:
            docargs['hr_manager'] = hr_manager
        return report_obj.render('services_request.report_identification_view', docargs)