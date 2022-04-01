from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    qr_code_promptpay = fields.Boolean("Use PromptPay QR code")
    promptpay_id = fields.Char(
        string="PromptPay ID",
        help="13 digits for company's tax ID or 10 digits for mobile phone number",
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        res['qr_code_promptpay'] = self.env['ir.config_parameter'].sudo().get_param(
            'invoice_promptpay.qr_code_promptpay')
        res['promptpay_id'] = self.env['ir.config_parameter'].sudo().get_param(
            'invoice_promptpay.promptpay_id')

        return res

    @api.model
    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param('invoice_promptpay.qr_code_promptpay', self.qr_code_promptpay)
        self.env['ir.config_parameter'].sudo().set_param('invoice_promptpay.promptpay_id', self.promptpay_id)

        super(ResConfigSettings, self).set_values()
