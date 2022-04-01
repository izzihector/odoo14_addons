# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	pdc_account_id = fields.Many2one('account.account',string="PDC Receivable Account", related='company_id.pdc_account_id', readonly=False)
	pdc_account_creditors_id = fields.Many2one('account.account',string="PDC Payable Account", related='company_id.pdc_account_creditors_id', readonly=False)

	customer_notify_check = fields.Boolean(string="Customer Due Date Notification", related='company_id.customer_notify_check', readonly=False)
	vendor_notify_check = fields.Boolean(string="Vendor Due Date Notification", related='company_id.vendor_notify_check', readonly=False)


