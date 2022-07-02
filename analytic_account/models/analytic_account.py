# -*- coding: utf-8 -*-


from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError, QWebException
import time
from .base_tech import *


class AnalyticAccount(models.Model):
    _inherit = "account.analytic.account"
    type = selection_field([
        ('view', 'Main Account'),
        ('cost', 'Cost Center'),
        ('revenue', 'Revenue Center'),
        ('cost_revenue', 'Cost + Revenue'),
        ('contract', 'Contract'),
        ('other', 'Other'),
    ], string="Type")
    arabic_name = char_field('Arabic name', )
    parent_id = m2o_field('account.analytic.account', 'What\'s the main account')
    code = char_field('New account code', digits=3)
    code_main = char_field('Main account code', related='parent_id.final_code', store=True)
    final_code = char_field('Final code', compute="_final_code", store=True)
    active = bool_field('Active', default=True)
    note = html_field('Notes')
    # project_id = m2o_field('project.project', 'Project', ondelete="set null")
    currency_id = m2o_field(string="Accounting Currency")
    distribute_percentage = float_field('Distribution percentage')
    parent_ids_str = fields.Char('Parent ids (,) joined', compute='get_parent_ids_str', store=True)
    account_type = fields.Selection([('operational', 'Operational'), ('administrative', 'Administrative')], string='account type')

    @api.one
    @api.depends('parent_id', 'parent_id.parent_ids_str')
    def get_parent_ids_str(self):
        res = ";%s;" % self.id
        parent = self.parent_id
        while parent.id:
            res += "%s;" % parent.id
            parent = parent.parent_id
        self.parent_ids_str = res


    _sql_constraints = [
        ('unique_name', "unique(name, company_id)", "Name must be unique."),
        ('unique_arabic_name', "unique(arabic_name, company_id)", "Arabic name must be unique."),
        # ('unique_final_code', "unique(final_code, company_id)", "Final code must be unique."),
        # ('unique_final_code_', "unique(parent_id,code, company_id)", "Final code must be unique."),
    ]

    @api.one
    @api.constrains('parent_id')
    def check_NotParentInItsSelf(self):
        if self.id == self.parent_id.id:
            raise ValidationError(_("Analytic account can not be parent to it's self"))

    @api.model
    def get_all_child_ids(self):
        child_ids = []
        childes = self.with_context(dict(self._context, active_test=False)).search([('parent_id', '=', self.id)])
        child_ids.append(self.id)
        for child in childes:
            child_ids.append(child.id)
            CH = child.get_all_child_ids()
            if CH:
                child_ids += CH
        return child_ids

    @api.multi
    def get_ledger(self):
        ids = self.get_all_child_ids()
        return {
            'domain': [['analytic_account_id', 'in', ids]],
            'name': _('Analytic ledger'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {},
        }

    @api.one
    @api.constrains('code')
    def check_code(self):
        for c in self.code:
            if str(c) not in '0987654321':
                raise ValidationError(_("New account code should contain only numbers"))
        # if len(str(self.code)) > 4:
        #     raise ValidationError(_("In order to make your accounts code simple and traceable, it is highly recommended to make a short code (maximum) 3\
        #                             numbers for each account and its sub accounts"))

    @api.one
    @api.depends('code', 'parent_id', 'parent_id.code', 'parent_id.final_code', 'code_main')
    def _final_code(self):
        if self.code:
            self.final_code = "%s%s" % (str(self.code_main or ''), str(self.code or ''))
        else:
            self.final_code = ''

    @api.one
    @api.depends('parent_id')
    def _main_code(self):
        code_main = False
        if self.parent_id.id:
            code_main = self.parent_id.final_code
        self.code_main = code_main

    @api.onchange('code')
    def _onchange_code(self):
        code = ''
        no_c = ''
        for c in str(self.code or ''):
            if c in '0123456789':
                code += c
            else:
                no_c += c
        self.code = code
        if no_c:
            return {'warning': {
                'title': _("Code Warning"),
                'message': _("Code can contain only numbers")
            }}

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        view_domain = not self.env.context.get('view', False)
        if name:
            domain = ['|', '|',
                      ('name', 'ilike', name),
                      ('arabic_name', 'ilike', name),
                      ('final_code', 'ilike', name),
                      ]
        if view_domain:
            domain = (domain and ['&'] or []) + domain + [('type', '!=', 'view')]
        accounts = self.search(domain + args, limit=limit, order='final_code')
        return accounts.name_get()

    @api.one
    def name_get(self):
        return (self.id, "[%s] %s" % (self.final_code, self.name))

    @api.onchange('parent_id')
    def onchange_parent(self):
        if self.parent_id:
            childs = self.search([['parent_id', '=', self.parent_id.id]])
            max_code = 0
            if childs:
                max_code = max([int(a.code or 0) for a in childs])
            if max_code == 999:
                raise ValidationError(_("In order to keep the control your accounts code simple and traceable,\n\
                it is highly recommended to make a short code (maximum) 3 numbers for each account and its sub accounts"))
            self.code = int(max_code) + 1
            # while len(self.code) < 3:
            #     self.code = "0" + str(self.code)

    @api.one
    def unlink(self):
        if self.search([['parent_id', '=', self.id]]):
            raise ValidationError(_(
                "It is not logic to delete a main account which have sub-accounts, in order to delete this main account\
                , you have to delete all sub accounts, or link them with another main account"))
        # if self.env['project.project'].search([['analytic_account_id', '=', self.id]]):
        #     raise ValidationError(_("Not allowed to delete this Analytical account, because it is linked with a project, if it is necessary to delete this \
        #         analytical account, Open project management window and archive the project."))
        return super(AnalyticAccount, self).unlink()

    @api.one
    def copy(self):
        raise ValidationError(_("Duplicate Disabled in this window"))

    @api.multi
    def write(self, vals):
        for rec in self:
            if vals.get('actieve', False):
                if self.browse(rec.id).parent_id.id and not self.browse(rec.id).parent_id.active:
                    raise ValidationError(_("You can't active Analytic account while it's parent is not active"))
        return super(AnalyticAccount, self).write(vals)

    @api.model
    def create(self, vals):
        ctx = self._context.copy() or {}
        if ctx.get('default_type', False):
            vals['type'] = ctx.get('default_type')
        if ctx.get('arabic_name', False):
            vals['arabic_name'] = ctx.get('arabic_name')
        return super(AnalyticAccount, self).create(vals)


class Move(models.Model):
    _inherit = "account.move"
    payment_id = m2o_field('account.payment')


class account_move_line(models.Model):
    _inherit = "account.move.line"

    analytic_parent_ids_str = fields.Char(related='analytic_account_id.parent_ids_str', store=True, string="analytic parent ids str")
