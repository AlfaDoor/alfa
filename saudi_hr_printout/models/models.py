# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
# import openerp.addons.decimal_precision as dp
from odoo.exceptions import ValidationError


class LeaveReconciliationReport(models.AbstractModel):
    _name = 'report.saudi_hr_printout.reconciliation'

    @api.multi
    def _get_report_values(self, docids, data=None):
        # report_obj = self.env['report']
        # report = report_obj._get_report_from_name('saudi_hr_printout.reconciliation')
        records = self.env['hr.leave.reconciliation'].browse(docids)
        for record in records:
            if record.type == 'liquidation':
                raise ValidationError("Printing this report is only allowed with types (Leave Request reconciliation) and (Both)")
            if not record.leave_to_reconcile_ids:
                raise ValidationError("Can not print there is no leaves to reconcile")
        hr_departments = self.env['hr.department'].search([('type', '=', 'HR Department')])
        hr_manager = False
        if hr_departments:
            hr_department = hr_departments[0]
            hr_manager = hr_department.manager_id
        docargs = {
            'doc_ids': docids,
            'doc_model': 'hr.leave.reconciliation',
            'docs': records,
            'header_arabic': 'تسوية اجازة',
            'header_english': 'Vacation Settlement'
        }
        if hr_manager:
            docargs['hr_manager'] = hr_manager
        return docargs
        return report_obj.render('saudi_hr_printout.reconciliation', docargs)


class EOSReport(models.AbstractModel):
    _name = 'report.saudi_hr_printout.eos'

    @api.multi
    def _get_report_values(self, docids, data=None):
        # report_obj = self.env['report']
        # report = report_obj._get_report_from_name('saudi_hr_printout.eos')
        records = self.env['employee.eos'].browse(docids)
        hr_departments = self.env['hr.department'].search([('type', '=', 'HR Department')])
        hr_manager = False
        if hr_departments:
            hr_department = hr_departments[0]
            hr_manager = hr_department.manager_id

        docargs = {
            'doc_ids': docids,
            'doc_model': 'employee.eos',
            'docs': records,
            'header_arabic': 'تسوية نهاية الخدمة',
            'header_english': 'End Of Services Settlement'
        }
        if hr_manager:
            docargs['hr_manager'] = hr_manager
        return docargs
        return report_obj.render('saudi_hr_printout.eos', docargs)


class EffectiveNoticeReport(models.AbstractModel):
    _name = 'report.saudi_hr_printout.report_effective_notice_view'

    @api.multi
    def _get_report_values(self, docids, data=None):
        # report_obj = self.env['report']
        # report = report_obj._get_report_from_name('saudi_hr_printout.report_effective_notice_view')
        records = self.env['effective.notice'].browse(docids)
        hr_departments = self.env['hr.department'].search([('type', '=', 'HR Department')])
        hr_manager = False
        if hr_departments:
            hr_department = hr_departments[0]
            hr_manager = hr_department.manager_id
        for rec in records:
            if rec.type != 'New Employee':
                raise ValidationError("Printing this report is only allowed with type (New Employee)")
        docargs = {
            'doc_ids': docids,
            'doc_model': 'effective.notice',
            'docs': records,
            'header_arabic': 'نموذج مباشرة موظف',
            'header_english': 'EMPLOYEE WORK START FORM'
        }
        if hr_manager:
            docargs['hr_manager'] = hr_manager
        return docargs
        return report_obj.render('saudi_hr_printout.report_effective_notice_view', docargs)


class effective_notice(models.Model):
    _inherit = 'effective.notice'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(effective_notice, self).fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu)

        if view_type in ['form', 'tree']:
            return_from_leave_action = self.env.ref('saudi_hr_leaves.action_effective_notice')
            new_employee_action = self.env.ref('saudi_hr_employee.action_employee_effective_notice')
            if self.env.context.get('params', False) and self.env.context.get('params', False)['action']:
                current_action = self.env.context.get('params', False)['action']
                if new_employee_action.id != current_action:
                    if res.get('toolbar', False) and res.get('toolbar').get('print', False):
                        reports = res.get('toolbar').get('print')
                        for report in reports:
                            if report.get('report_file', False) and report.get('report_file') == 'report_effective_notice':
                                res['toolbar']['print'].remove(report)
                if return_from_leave_action.id != current_action:
                    if res.get('toolbar', False) and res.get('toolbar').get('print', False):
                        reports = res.get('toolbar').get('print')
                        for report in reports:
                            if report.get('report_file', False) and report.get('report_file') == 'report_return_from_leave':
                                res['toolbar']['print'].remove(report)

        return res


class hr_leave(models.Model):
    _inherit = 'hr.leave'

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(hr_leave, self).fields_view_get(
    #         view_id=view_id,
    #         view_type=view_type,
    #         toolbar=toolbar,
    #         submenu=submenu)
    #     if view_type in ['tree', 'form']:
    #         action = self.env.ref('hr_holidays.hr_leave_action_new_request')
    #         if self.env.context.get('params', False) and self.env.context.get('params', False)['action']:
    #             current_action = self.env.context.get('params', False)['action']
    #             # active_id = self.env.context.get('params', False)['id']
    #             # type = self.env['effective.notice'].browse(active_id).type
    #             if action.id != current_action:
    #                 if res.get('toolbar', False) and res.get('toolbar').get('print', False):
    #                     reports = res.get('toolbar').get('print')
    #                     for report in reports:
    #                         if report.get('report_file', False) and report.get('report_file') == 'report_leave_request':
    #                             res['toolbar']['print'].remove(report)
    #     return res


# class LeaveRequestReport(models.AbstractModel):
#     _name = 'report.saudi_hr_printout.report_leave_request_temp'
#
#     @api.multi
#     def _get_report_values(self, docids, data=None):
#         # report_obj = self.env['report']
#         # report = report_obj._get_report_from_name('saudi_hr_printout.report_leave_request_temp')
#         records = self.env['hr.leave'].browse(docids)
#         # for rec in records:
#         #     if rec.request_reason != 'annual':
#         #         raise ValidationError("Printing this report is only allowed with type (Annual Leave)")
#         docargs = {
#             'doc_ids': records,
#             'doc_model': 'hr.leave',
#             'docs': records,
#         }
#         return docargs
#         return report_obj.render('saudi_hr_printout.report_leave_request_temp', docargs)


class ReturnFormLeaveReport(models.AbstractModel):
    _name = 'report.saudi_hr_printout.report_return_from_leave_temp'

    @api.multi
    def _get_report_values(self, docids, data=None):
        # report_obj = self.env['report']
        # report = report_obj._get_report_from_name('saudi_hr_printout.report_return_from_leave_temp')
        records = self.env['effective.notice'].browse(docids)
        for rec in records:
            if rec.type != 'Return From Leave':
                raise ValidationError("Printing this report is only allowed with type (Return From Leave)")
        docargs = {
            'doc_ids': docids,
            'doc_model': 'effective.notice',
            'docs': records,
        }
        return docargs
        return report_obj.render('saudi_hr_printout.report_return_from_leave_temp', docargs)


class MissionReport(models.AbstractModel):
    _name = 'report.saudi_hr_printout.report_mission_temp'

    @api.multi
    def _get_report_values(self, docids, data=None):
        # report_obj = self.env['report']
        # report = report_obj._get_report_from_name('saudi_hr_printout.report_mission_temp')
        records = self.env['hr.mission'].browse(docids)
        hr_departments = self.env['hr.department'].search([('type', '=', 'HR Department')])
        hr_manager = False
        if hr_departments:
            hr_department = hr_departments[0]
            hr_manager = hr_department.manager_id
        docargs = {
            'doc_ids': docids,
            'doc_model': 'hr.mission',
            'docs': records,
            'header_arabic': 'طلب خروج أثناء الدوام الرسمي',
            'header_english': 'Permission During Working Day Request'
        }
        if hr_manager:
            docargs['hr_manager'] = hr_manager
        return docargs
        return report_obj.render('saudi_hr_printout.report_mission_temp', docargs)
