from odoo import models, fields, api, _

class InheritPayroll(models.TransientModel):
    _name = 'payslips.report'
    date_from = fields.Date()
    date_to = fields.Date()

    def get_employee_non_payslips(self):

        payslip_employees = []
        datas = []
        employee_all = []
        payslips_record = self.env['hr.payslip'].search([('date_from','>=',self.date_from),('date_to','<=',self.date_to)])
        for rec in payslips_record:
            payslip_employees.append(rec.employee_id.id)

        employee_record = self.env['hr.employee'].search([])
        for records in employee_record:
            employee_all.append(records.id)

        result = [value for value in employee_all if value not in payslip_employees]
        for emp in result:
            employee_rec = self.env['hr.employee'].search([('id','=',emp)])
            datas.append({'name':employee_rec.name,
                          'number':employee_rec.employee_number,
                          'department':employee_rec.department_id.name,
                          'job':employee_rec.job_id.name,
                          'sponsor':employee_rec.coach_id.name})

            res = {
            'start_date': self.date_from,
            'end_date': self.date_to,
            'employee': datas
            }

        data = {
            'form': res,
            }
        return self.env.ref('hr_customizations.report_payslip_sit').report_action([], data=data)
