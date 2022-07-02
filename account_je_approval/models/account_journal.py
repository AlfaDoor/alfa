# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    need_second_approval = fields.Boolean("Approval Needed ?")


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.multi
    def action_post(self):
        if self.journal_id.need_second_approval and not\
                self.env.user.has_group('account_je_approval.res_groups_account_je_approver'):
            raise ValidationError(_(
                "You are not allowed to Post Entries for this Journal."))
        return super(AccountMove, self).action_post()

    @api.multi
    def assert_balanced(self):
        if not self.ids:
            return True
        prec = self.env.user.company_id.currency_id.decimal_places

        self._cr.execute("""\
            SELECT      move_id
            FROM        account_move_line
            WHERE       move_id in %s
            GROUP BY    move_id
            HAVING      abs(sum(debit) - sum(credit)) > %s
            """, (tuple(self.ids), 10 ** (-max(5, prec))))
        if len(self._cr.fetchall()) != 0:
            raise UserError(_("Cannot create unbalanced journal entry."))
        return True

