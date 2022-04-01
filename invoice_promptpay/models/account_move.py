from odoo import fields, models, api
from promptpay import qrcode


class AccountMove(models.Model):
    _inherit = 'account.move'

    def promptpayPayload(self, data):
        promptpay_id = self.env['ir.config_parameter'].sudo().get_param('invoice_promptpay.promptpay_id')
        qr_code_promptpay = self.env['ir.config_parameter'].sudo().get_param('invoice_promptpay.qr_code_promptpay')
        if promptpay_id and qr_code_promptpay:
            return qrcode.generate_payload(promptpay_id, float(data))

        return False