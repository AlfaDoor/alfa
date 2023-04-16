# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, QWebException
import time

import logging


# _logger = logging.getLogger(__name__)
# _logger.info(error_msg)


class PayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    move_id = fields.Many2one('account.move', 'Journal entry')
    journal_id = fields.Many2one('account.journal', 'Journal')

    @api.multi
    def account_move_create(self):
        if not self.journal_id:
            raise ValidationError(_("Please select Journal to create jourlnal entry !"))
        dic = {}
        all_salary_rules = self.env['hr.salary.rule'].sudo().search([])

        account_move = self.env['account.move'].create({
            'name': self.name,
            'journal_id': self.journal_id.id,
            'ref': self.name,
            'date': time.strftime("%Y-%m-%d")
        })
        self.overtime_lines(account_move.id)
        self.move_id = account_move.id
        aml = self.with_context(dict(self._context.copy(), check_move_validity=False)).env['account.move.line']
        for rule in all_salary_rules:
            dic[rule.id] = 0

        salary_rules_codes = ['BSC', 'HOUSEALL', 'TRANSALL', 'PHOALL', 'FODALL', 'OTHERALL', 'GOSIE', 'ABS', 'TRNS_DED', 'HOUS_DED', 'REWARD', 'DEDUCT','OVT']
        rules = self.env['hr.salary.rule'].search(
            [('category_id', 'in', [self.env.ref('hr_payroll.BASIC').id, self.env.ref('saudi_hr_payroll.HOUSEALL').id, self.env.ref('saudi_hr_payroll.TRANSEALL').id])])
        salary_rules_codes += [r.code for r in rules]
        salary_rules_codes = list(set(salary_rules_codes))
        lines = {}
        for slip in self.slip_ids:
            # ===== Rewards =======
            total_rewards = 0
            remain_reward = slip.rule_employee_rewards
            rewards = self.env['hr.employee.rewards'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('reward_date', '>=', slip.date_from),
                ('reward_date', '<=', slip.date_to),
                ('state', '=', 'confirmed'),
                ('account_id', '!=', False),
            ])
            for r in rewards:
                if not remain_reward: break
                reward_amount = min(abs(r.amount), remain_reward)
                remain_reward -= reward_amount
                key = "%s-%s-%s" % ('REWARD', r.account_id.id, r.account_id.name)
                if not lines.get(key):
                    lines[key] = {
                        'sequence': 60,
                        'name': "REWARD FOR %s" % (r.account_id.name),
                        'account_id': r.account_id.id,
                        'debit': 0.0,
                        'credit': 0.0,
                        'journal_id': self.journal_id.id,
                        'move_id': account_move.id,
                        'analytic_account_id': slip.employee_id.department_id.analytic_account_id.id,
                    }
                # debit = line.salary_rule_id.account_debit.id and
                # credit = line.salary_rule_id.account_credit.id and abs(r.amount)
                lines[key]['debit'] += reward_amount
                # lines[key]['credit'] += credit
                total_rewards += reward_amount
            for line in slip.line_ids:
                if line.salary_rule_id.code in salary_rules_codes:
                    analytic_account_id = slip.employee_id.department_id.analytic_account_id.id
                    key = '%s-%s' % (line.salary_rule_id.code, analytic_account_id)
                    if not lines.get(key):
                        lines[key] = {
                            'sequence': line.salary_rule_id.sequence,
                            'name': "%s for %s" % (line.salary_rule_id.name, slip.employee_id.department_id.name),
                            'account_id': line.salary_rule_id.account_debit.id or line.salary_rule_id.account_credit.id,
                            'debit': 0.0,
                            'credit': 0.0,
                            'journal_id': self.journal_id.id,
                            'move_id': account_move.id,
                            'analytic_account_id': slip.employee_id.department_id.analytic_account_id.id,
                        }
                    line_total = abs(line.total)
                    if line.salary_rule_id.code == 'REWARD':
                        line_total -= total_rewards
                    debit = line.salary_rule_id.account_debit.id and line_total
                    credit = line.salary_rule_id.account_credit.id and line_total
                    lines[key]['debit'] += debit
                    lines[key]['credit'] += credit
                if line.salary_rule_id.code == "NET_RULE":
                    key = '%s' % (line.salary_rule_id.code)
                    if not lines.get(key):
                        lines[key] = {
                            'sequence': 200,
                            'name': line.salary_rule_id.name,
                            'account_id': line.salary_rule_id.account_debit.id or line.salary_rule_id.account_credit.id,
                            'debit': 0.0,
                            'credit': 0.0,
                            'journal_id': self.journal_id.id,
                            'move_id': account_move.id,
                            'analytic_account_id': slip.employee_id.department_id.analytic_account_id.id,
                        }
                    lines[key]['debit'] += line.salary_rule_id.account_debit.id and line.total or 0.0
                    lines[key]['credit'] += line.salary_rule_id.account_credit.id and line.total or 0.0
                if line.salary_rule_id.code == "LOAN":
                    key = '%s-%s' % (line.salary_rule_id.code, slip.employee_id.id)
                    if not lines.get(key):
                        lines[key] = {
                            'sequence': 90,
                            'name': "Loan installment for %s" % (slip.employee_id.name),
                            'account_id': line.salary_rule_id.account_debit.id or line.salary_rule_id.account_credit.id,
                            'debit': line.salary_rule_id.account_debit.id and abs(line.total) or 0.0,
                            'credit': line.salary_rule_id.account_credit.id and abs(line.total) or 0.0,
                            'journal_id': self.journal_id.id,
                            'move_id': account_move.id,
                            'analytic_account_id': False,
                            'employee_id': slip.employee_id.id,
                        }
        for l in lines:
            if lines[l]['debit'] or lines[l]['credit']:
                aml.create(lines[l])

    def overtime_lines(self, move_id):
        employee_ids = [l.employee_id.id for l in self.slip_ids]
        overtime_lines = {}
        aml = self.with_context(dict(self._context.copy(), check_move_validity=False)).env['account.move.line']
        for report in self.sheet_report_id.employee_report_ids:
            if report.employee_id.id in employee_ids:
                overtimes = self.env['overtime.assignment'].search(
                    [('employee_id', '=', report.employee_id.id), ('date', '>=', report.overtime_date_from),
                     ('date', '<=', report.overtime_date_to), ])
                for day in report.overtime_day_ids:
                    overtime = day.overtime_assignment_id
                    if overtime and overtime.state == 'confirmed':
                        aa = overtime.analytic_account_id.id or overtime.employee_id.department_id.analytic_account_id.id or False
                        if aa not in overtime_lines:
                            overtime_lines[aa] = {'debit': 0, 'analytic_account_id': aa}
                        overtime_lines[aa]['debit'] += overtime.overtime_calc
        account_id = self.env['hr.salary.rule'].search([('code', '=', 'OVT')], limit=1).account_debit.id
        for line in overtime_lines:
            aml.create({
                'sequence': 90,
                'name': "Overtime",
                'account_id': account_id,
                'debit': overtime_lines[line]['debit'],
                'credit': 0.0,
                'journal_id': self.journal_id.id,
                'move_id': move_id,
                'analytic_account_id': overtime_lines[line]['analytic_account_id'],
            })

    # @api.model_cr
    # def init(self):
    #     for payslip in self.env['hr.payslip'].search([('remaining_rewards', '!=', 0)]):
    #         if payslip.remaining_rewards - payslip.reward_pay_this_month < 1:
    #             payslip.reward_pay_this_month = payslip.remaining_rewards


class Department(models.Model):
    _inherit = "hr.department"
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic account')


class PayslipRule(models.Model):
    _name = 'hr.salary.rule'
    _inherit = 'hr.salary.rule'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    account_tax_id = fields.Many2one('account.tax', 'Tax')
    account_debit = fields.Many2one('account.account', 'Debit Account', domain=[('deprecated', '=', False)])
    account_credit = fields.Many2one('account.account', 'Credit Account', domain=[('deprecated', '=', False)])


class EmployeeRewards(models.Model):
    _inherit = "hr.employee.rewards"

    account_id = fields.Many2one('account.account', 'Account')
