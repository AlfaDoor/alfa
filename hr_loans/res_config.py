# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo import api, exceptions, _


class hr_loans_configuration(models.TransientModel):
    _name = 'hr.loans.config.settings'
    _inherit = 'res.config.settings'

    integrate_with_finance = fields.Boolean('Integrate with finance', help="Integrate with finance")
    integrate_traffic_violation = fields.Boolean('Integrate with traffic violation system',
                                                         help="Integrate with traffic violation system")
    loans_deduction_percentage = fields.Float('Loans monthly deduction percentage from salary', default=25.0,
                                                      help="Loans monthly deduction percentage from salary ")
    violations_deduction_percentage = fields.Float('Violations monthly deduction percentage from salary',
                                                           help="Violations monthly deduction percentage from salary", default=100.0)
    previous_based_on = fields.Selection([('Basic Salary', 'Basic Salary'),
                                                  ('Total salary', 'Total salary')], 'Previous Percentage Based On',
                                                 help="previous percentage based on",  default='Total salary')
    absence_based_on = fields.Selection([('basic', 'Basic Salary'),
                                                 ('basic_house', 'Basic + House'),
                                                 ('basic_house_trans', 'Basic + House + Transportation'),
                                                 ('basic_house_trans_phone', 'Basic + House + Transportation + Phone'),
                                                 ('total', 'Total salary'), ],
                                                'Employee absence deduction based on', default_model='hr.loans.config.settings', default='total')
    reverse_deduction = fields.Boolean('Allow to reverse deductions - Violations - Rewards - loans ?',
                                               default=False, default_model='hr.loans.config.settings')
    reverse_deduction_within = fields.Integer('Allow to reverse deductions - Violations - Rewards within',
                                                      default=30, default_model='hr.loans.config.settings',
                                                      help='If = 30 days, HR manager will be allowed to cancel any deduction - violations if deduction or violation recorded in the past 30 days. If = 60 HR manager will be allowed to cancel any deduction - violations if deduction or violation recorded in the past 60 days.')
    default_reward_type_id = fields.Many2one('hr.reward.type', 'Default reward type', default_model='hr.employee.rewards')
    module_installment_menu = fields.Boolean('Show Installment Menu')

    @api.onchange('reverse_deduction')
    def onchange_default_reverse_deduction(self):
        self.reward_type = False
        if self.default_reverse_deduction:
            self.default_reverse_deduction_within = 30
        else:
            self.default_reverse_deduction_within = 0
