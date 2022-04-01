from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError, ValidationError


class UoMCategory(models.Model):
    _inherit = 'uom.category'

