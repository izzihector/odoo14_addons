from odoo import fields, models, api


class AccountChartOfAccountReport(models.AbstractModel):
    _inherit = "account.coa.report"

    filter_div = True
