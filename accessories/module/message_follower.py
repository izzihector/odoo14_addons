from odoo import fields, models, api


class message(models.Model):
    _name = "account.account"
    _inherit = ['account.account', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char("Account Name", tracking=True)
