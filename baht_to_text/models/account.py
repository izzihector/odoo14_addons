from odoo import models
from .bahttext import bahttext

class AccountMove(models.Model):
    _inherit = 'account.move'

    def baht_to_text(self, baht):
        return bahttext(baht)

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def baht_to_text(self, baht):
        return bahttext(baht)