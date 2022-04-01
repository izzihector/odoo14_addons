from odoo import models, api, fields
from odoo.tools import safe_eval
from odoo.tools.translate import _
from odoo.exceptions import UserError, RedirectWarning
import re
from collections import defaultdict
from itertools import chain


class generic_tax_report(models.AbstractModel):
    _inherit = 'account.generic.tax.report'
    filter_div = True
