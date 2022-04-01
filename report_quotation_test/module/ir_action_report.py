# -*- coding: utf-8 -*-

from odoo import models, fields, api
from .bahttext import bahttext


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    is_report_designer = fields.Boolean(string="Report created by Report Designer or not", default=False)






class IrActionsReportsale(models.Model):
    _inherit = 'sale.order'


    def get_baht_text_sale(self):
        return bahttext(self.amount_total)
