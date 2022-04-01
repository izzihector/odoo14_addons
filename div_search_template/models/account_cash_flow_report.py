from odoo import models, fields, api, _

from dateutil.relativedelta import relativedelta

import copy


class AccountCashFlowReport(models.AbstractModel):
    _inherit = 'account.cash.flow.report'

