from odoo import models, api, _, fields


class report_account_consolidated_journal(models.AbstractModel):
    _inherit = "account.consolidated.journal"

    filter_div = True
