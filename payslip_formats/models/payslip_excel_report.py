from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError
import xlwt
import io
import base64
import calendar
from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta
import time


class BankTemplateReport(models.Model):
    _name = 'payslip.bank.report'

    _PERIOD = [
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')]

    name = fields.Char()
    month = fields.Selection(_PERIOD, _('Month'), default=lambda s: time.strftime("%m"))
    year = fields.Integer(_('Year'), default=lambda s: float(time.strftime('%Y')))
    date_from = fields.Date(required=True, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(required=True, default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    sponsor = fields.Many2many('hr.sponsors',string='Sponsors')
    payslip_report_line_id = fields.One2many('payslip.bank.report.line', 'payslip_report_id', string='Payslip Report Lines')
    report = fields.Binary('Excel File', filters='.xls', readonly=True)
    name_r = fields.Char('File Name', size=32)
    report_type = fields.Selection([('Salary Report','Salary Report'),('Overtime Report','Overtime Report')], default='Salary Report')

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = 'Bank Report of ' + str(record.year) + '/' + str(record.month)
            result.append((record.id, name))
        return result

    @api.model
    def create(self, vals):
        vals['name'] = 'Bank Report of ' + str(vals['year']) + '/' + str(vals['month'])
        sequence = self.env['payslip.bank.report'].search([('name','=',vals['name'])])
        if len(sequence) == 1:
            raise ValidationError(_("Bank Template Report for this duration ia already created, kindly modify that."))
        result = super(BankTemplateReport, self).create(vals)
        return result

    @api.onchange('month', 'year')
    def onchange_period(self):
        if self.month and self.year:
            start_end = calendar.monthrange(self.year, int(self.month))
            self.date_from = str(self.year) + '-' + self.month + '-01'
            self.date_to = str(self.year) + '-' + self.month + '-' + str(start_end[1])

    @api.multi
    def generate_report_lines(self):
        sponsors = []
        structure = []
        line = 0
        document_name = ''
        self.payslip_report_line_id = False
        self.name = 'Payslip Bank Report ' + str(self.id)
        payslips_record = self.env['hr.payslip'].search(
            [('date_from', '>=', (self.date_from-timedelta(days=10))), ('date_to', '<=', self.date_to),('state','in',['Final Reviewed','done']),('company_id','=',self.env.user.company_id.id)])
        for records in self.sponsor:
            sponsors.append(records.id)
        for rec in payslips_record:
            for items in sponsors:
                if rec.employee_id.coach_id.id == items:
                    line +=1
                    total_allowance = ((rec.rule_other_llowance)+(rec.rule_transportation_allowance)+(rec.rule_food_allowance)+(rec.rule_phone_allowance)+(rec.rule_employee_rewards)+(rec.rule_overtime))
                    total_deduction = ((abs(rec.rule_loan_deducted))+(abs(rec.rule_deductions_violations))+(abs(rec.rule_absence_deducted))+(abs(rec.rule_gosi_employee_share))+(abs(rec.rule_absence)))
                    self.env['payslip.bank.report.line'].create({'payslip_report_id': self.id,
                                                                 'sno': line,
                                                                 'employee_no': rec.employee_id.identification_id,
                                                                 'employee_id': rec.employee_id.id,
                                                                 'employee_bank': rec.employee_id.iban_number,
                                                                 'employee_bank_code': rec.employee_id.Bank_name_id.bic,
                                                                 'total_amount': (((rec.rule_basic) + (rec.rule_house_allowance) + total_allowance) - (total_deduction)),
                                                                 'basic_sal': rec.rule_basic,
                                                                 'house_allowance': rec.rule_house_allowance,
                                                                 'other_allowance': total_allowance,
                                                                 'deductions': total_deduction,
                                                                 'address':'',
                                                                 'status':'Active',
                                                                 'payment_reference': 'Salary of '+ str(rec.month),
                                                                 'currency':'SAR'})

    @api.multi
    def generate_xls_report(self):
        if len(self.payslip_report_line_id) < 1:
            raise UserError(_("Please Generate Report Lines."))
        self.ensure_one()
        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet('Payslip Detail')
        fp = io.BytesIO()

        sub_header_style = xlwt.easyxf("font: name Helvetica size 11 px, bold 1, height 200;"
                                       "align: vertical center, horizontal center, wrap on;"
                                       "borders: left thin, right thin, top thin, bottom thin;"
                                       "pattern: pattern solid, pattern_fore_colour green, pattern_back_colour green")
        line_content_style = xlwt.easyxf("font: name Helvetica, height 170;align: horiz center")
        row = 3
        col = 0
        ws1.write(0, 0, 'Type', sub_header_style)
        ws1.write(0, 1, 'Customer Name', sub_header_style)
        ws1.write(0, 2, 'Agreement Code', sub_header_style)
        ws1.write(0, 3, 'Funding Account', sub_header_style)
        ws1.write(0, 4, 'Branch No', sub_header_style)
        ws1.write(0, 5, 'Credit Date', sub_header_style)
        ws1.write(0, 6, 'Mins of Lab Establish Id', sub_header_style)
        ws1.write(0, 7, 'ECR ID', sub_header_style)
        ws1.write(0, 8, 'Bank Code', sub_header_style)
        ws1.write(0, 9, 'Currency', sub_header_style)
        ws1.write(0, 10, 'Batch', sub_header_style)
        ws1.write(0, 11, 'File Reference', sub_header_style)
        ws1.write(0, 12, '', sub_header_style)
        ws1.write(0, 13, '', sub_header_style)
        ws1.write(0, 14, '', sub_header_style)

        ws1.write(1, 0, str(111), line_content_style)
        ws1.write(1, 1, 'PAY34077', line_content_style)
        ws1.write(1, 2, 'PAY34077', line_content_style)
        ws1.write(1, 3, str(2123706259941), line_content_style)
        ws1.write(1, 4, '212', line_content_style)
        ws1.write(1, 5, str(fields.Date.today()), line_content_style)
        ws1.write(1, 6, '1-171109', line_content_style)
        ws1.write(1, 7, '7004337262', line_content_style)
        ws1.write(1, 8, 'RIBL', line_content_style)
        ws1.write(1, 9, 'SAR', line_content_style)
        ws1.write(1, 10, '', line_content_style)
        ws1.write(1, 11, '', line_content_style)
        ws1.write(1, 12, '', line_content_style)
        ws1.write(1, 13, '', line_content_style)
        ws1.write(1, 14, '', line_content_style)

        ws1.write(2, 0, 'SN', sub_header_style)
        ws1.write(2, 1, 'Beneficiary Ref', sub_header_style)
        ws1.write(2, 2, 'Employee Name', sub_header_style)
        ws1.write(2, 3,  'Account Number', sub_header_style)
        ws1.write(2, 4, 'Bank Code', sub_header_style)
        ws1.write(2, 5, 'Net Amount', sub_header_style)
        ws1.write(2, 6, 'Basic Salary', sub_header_style)
        ws1.write(2, 7, 'Housing Allowance', sub_header_style)
        ws1.write(2, 8, 'Other earning', sub_header_style)
        ws1.write(2, 9, 'Deductions', sub_header_style)
        ws1.write(2, 10, 'Address', sub_header_style)
        ws1.write(2, 11, 'Currency', sub_header_style)
        ws1.write(2, 12, 'Status', sub_header_style)
        ws1.write(2, 13, 'Payment Desc', sub_header_style)
        ws1.write(2, 14, 'Payment Ref', sub_header_style)

        for rec in self.payslip_report_line_id:
            ws1.write(row, col, rec.sno, line_content_style)
            ws1.write(row, col + 1, rec.employee_iqama if rec.employee_iqama else '', line_content_style)
            ws1.write(row, col + 2, rec.employee_id.name if rec.employee_id else '', line_content_style)
            ws1.write(row, col + 3, rec.employee_account_no if rec.employee_account_no else '', line_content_style)
            ws1.write(row, col + 4, rec.bank_code if rec.bank_code else '', line_content_style)
            ws1.write(row, col + 5, rec.total_amount, line_content_style)
            ws1.write(row, col + 6, rec.basic_sal, line_content_style)
            ws1.write(row, col + 7, rec.house_allowance, line_content_style)
            ws1.write(row, col + 8, rec.other_allowance, line_content_style)
            ws1.write(row, col + 9, rec.deductions, line_content_style)
            ws1.write(row, col + 10, rec.address, line_content_style)
            ws1.write(row, col + 11, rec.currency, line_content_style)
            ws1.write(row, col + 12, rec.status, line_content_style)
            ws1.write(row, col + 13, rec.payment_method if rec.payment_method else '', line_content_style)
            ws1.write(row, col + 14, rec.payment_reference, line_content_style)
            row += 1

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        self.write({'report': out, 'name_r': 'payslip_report.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payslip.bank.report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
        }


class SalesTax_report_line(models.Model):
    _name = 'payslip.bank.report.line'

    sno = fields.Integer('Sr')
    payslip_report_id = fields.Many2one('payslip.bank.report', string='Report Line')
    employee_id = fields.Many2one('hr.employee')
    employee_no = fields.Char(related='employee_id.employee_number')
    employee_iqama = fields.Char(related='employee_id.identification_id')
    employee_account_no = fields.Char(related='employee_id.iban_number')
    bank_code = fields.Char(related='employee_id.Bank_name_id.bic')
    basic_sal = fields.Float()
    house_allowance = fields.Float()
    other_allowance = fields.Float()
    deductions = fields.Float()
    total_amount = fields.Float()
    address = fields.Char()
    currency = fields.Char()
    status = fields.Char()
    payment_method = fields.Char()
    payment_reference = fields.Char()


