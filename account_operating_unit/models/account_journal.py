# © 2019 ForgeFlow S.L.
# © 2019 Serpent Consulting Services Pvt. Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        domain="[('user_ids', '=', uid)]",
        help="Operating Unit that will be used in payments, "
        "when this journal is used.",
    )

    operating_unit_id2 = fields.Many2one('operating.unit', compute='_getOU')

    def _getOU(self):
        for move in self:
            move.operating_unit_id = move.move_id.operating_unit_id

    @api.constrains("type")
    def _check_ou(self):
        for journal in self:
            if (
                journal.type in ("bank", "cash")
                and journal.company_id.ou_is_self_balanced
                and not journal.operating_unit_id
            ):
                raise UserError(
                    _(
                        "Configuration error. If defined as "
                        "self-balanced at company level, the "
                        "operating unit is mandatory in bank "
                        "journal."
                    )
                )
