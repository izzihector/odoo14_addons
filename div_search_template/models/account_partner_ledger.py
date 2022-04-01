from odoo import models, api, _, fields
from odoo.tools.misc import formatLang
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta
from collections import defaultdict


class ReportPartnerLedger(models.AbstractModel):
    _inherit = 'account.partner.ledger'
    filter_div = True

