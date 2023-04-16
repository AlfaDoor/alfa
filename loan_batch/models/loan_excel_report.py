from odoo import models, fields, api
import xlwt
import io
import base64
from io import StringIO
from datetime import datetime

class LoanReport(models.Model):
    _name = 'loan.bank.report'

    name = fields.Char('name')
    date_from = fields.Date(string='Date From', required=1)
    date_to = fields.Date(string='Date To', required=1)
    sponsor = fields.Many2many('hr.sponsors', string='Sponsors')
    loan_report_line_id = fields.One2many('loan.report.line', 'loan_report_id', string='Loan Report Lines')
    report = fields.Binary('Excel File', filters='.xls', readonly=True)
    name_r = fields.Char('File Name', size=32)

    @api.multi
    def generate_loan_report_lines(self):

        sponsors = []
        line = 0
        document_name = ''
        self.loan_report_line_id = False
        self.name = 'Loan Report ' + str(self.id)
        loan_record = self.env['loan.advance.request'].search(
            [('loan_date_from', '>=', self.date_from), ('loan_date_from', '<=', self.date_to),('state','ilike','GM Approve')])
        if not loan_record:
            loan_record = self.env['loan.advance.request'].search(
            [('date', '>=', self.date_from), ('date', '<=', self.date_to),('state','ilike','GM Approve')])

        for records in self.sponsor:
            sponsors.append(records.id)

        for rec in loan_record:
            for items in sponsors:
                if rec.employee_id.coach_id.id == items:
                    line +=1
                    self.env['loan.report.line'].create({'loan_report_id':self.id,
                                                                 'sno':line,
                                                                 'employee_id':rec.employee_id.id,
                                                                 'basic_sal':rec.loan_amount,
                                                                 'house_allowance':0.0,
                                                                 'other_allowance':0.0,
                                                                 'deductions':0.0,
                                                                 'total_amount':rec.loan_amount})


    @api.multi
    def generate_xls_report(self):

        self.ensure_one()
        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet('Loan Detail')
        fp = io.BytesIO()
        sub_header_style = xlwt.easyxf("font: name Helvetica size 11 px, bold 1, height 200; align: horiz center")
        line_content_style = xlwt.easyxf("font: name Helvetica, height 170;align: horiz center")
        row = 1
        col = 0
        ws1.write(0, 0,'Employee ID/Iqama', sub_header_style)
        ws1.write(0, 1, 'Employee Account No/IBAN', sub_header_style)
        ws1.write(0, 2, 'Employee Name', sub_header_style)
        ws1.write(0, 3, 'Bank Code', sub_header_style)
        ws1.write(0, 4, 'Basic Salary', sub_header_style)
        ws1.write(0, 5, 'House Allowance', sub_header_style)
        ws1.write(0, 6, 'Other Allowance', sub_header_style)
        ws1.write(0, 7, 'Deduction', sub_header_style)
        ws1.write(0, 8, 'Total Amount', sub_header_style)

        for rec in self.loan_report_line_id:
            ws1.write(row, col, rec.employee_iqama, line_content_style)
            ws1.write(row, col + 1, rec.employee_account_no, line_content_style)
            ws1.write(row, col + 2, rec.employee_id.name, line_content_style)
            ws1.write(row, col + 3, rec.bank_code, line_content_style)
            ws1.write(row, col + 4, rec.basic_sal, line_content_style)
            ws1.write(row, col + 5, rec.house_allowance, line_content_style)
            ws1.write(row, col + 6, rec.other_allowance, line_content_style)
            ws1.write(row, col + 7, rec.deductions, line_content_style)
            ws1.write(row, col + 8, rec.total_amount, line_content_style)
            row += 1

        wb1.save(fp)
        out = base64.encodestring(fp.getvalue())
        self.write({'report': out, 'name_r': 'loan_report.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'loan.bank.report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
        }


class SalesTax_report_line(models.Model):
    _name = 'loan.report.line'

    sno = fields.Integer('Sr')
    loan_report_id = fields.Many2one('loan.bank.report', string='Report Line')
    employee_id = fields.Many2one('hr.employee')
    employee_iqama = fields.Char(related='employee_id.identification_id')
    employee_account_no = fields.Char(related='employee_id.bank_account_id.acc_number')
    bank_code = fields.Char(related='employee_id.bank_account_id.bank_id.bank_code')
    basic_sal = fields.Float()
    house_allowance = fields.Float()
    other_allowance = fields.Float()
    deductions = fields.Float()
    total_amount = fields.Float()


