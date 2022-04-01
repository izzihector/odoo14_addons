# -*- coding: utf-8 -*-

from odoo import models, fields, api
from .bahttext import bahttext


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    is_report_designer = fields.Boolean(string="Report created by Report Designer or not", default=False)


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    def get_baht_text(self):
        return bahttext(self.amount_total)


class IrActionsReportpayment (models.Model):
    _inherit = 'ir.actions.report'
    is_report_designer = fields.Boolean(string="Report created by Report Designer or not", default=False)


class AccountInvoicepayment (models.Model):
    _inherit = 'account.payment'

    def get_baht_text_payment(self):
        return bahttext(self.amount)
