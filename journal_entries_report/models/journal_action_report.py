from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    def group_account(self):
        new_line = []
        for move in self:
            for line in move.line_ids.account_id:
                debit = sum(x.debit for x in move.line_ids if x.account_id.id == line.id)
                credit = sum(x.credit for x in move.line_ids if x.account_id.id == line.id)
                data = {
                    'account': line,
                    'debit': debit,
                    'credit': credit,
                }
                new_line.append(data)
            return new_line