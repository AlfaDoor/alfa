import locale
from datetime import datetime,date, timedelta,time
from odoo import api, fields, models,tools, exceptions, _
from odoo.exceptions import UserError
import babel


class HrLoanBatchEmployees(models.TransientModel):
    _name = 'loan.batches.employees'
    _description = 'Generate Loan Requests for all selected employees'

    employee_loan_ids = fields.Many2many('hr.employee', 'employee_loan_detail_rel' , 'employee_id' , 'loan_id')

    @api.multi
    def create_loans(self):
        loan_slips = self.env['loan.advance.request']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['loan.batches'].browse(active_id).read(['date_start', 'date_end'])
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not data['employee_loan_ids']:
            raise UserError(_("You must select employee(s) to generate loan requests."))

        for employee in self.env['hr.employee'].browse(data['employee_loan_ids']):
            contract = self.env['hr.contract'].search([('employee_id','=',employee.id),('state','=','open')],limit=1)
            if not contract:
                raise UserError(_("You must define the contract of %s, and make sure it is running state")%(employee.name))
            loan_type = self.env['hr_loans.loan_advance'].search([('name','ilike','Advance Salary')],limit=1)
            print(loan_type)
            if not loan_type:
                raise UserError(_("You must define the Loan/Advance type of name 'Advance Salary'"))
            res = {
                'employee_id': employee.id,
                'loan_batch_id':active_id,
                'loan_date_from':from_date,
                'loan_date_to':to_date,
                'loan_amount':contract.basic_salary,
                'reason':'Advance Salary',
                'loan_type': loan_type.id,
                'state':'New',
                'name':_(('Loan Request of %s') % (employee.name))
            }
            loan_slips += self.env['loan.advance.request'].create(res)
        return {'type': 'ir.actions.act_window_close'}
