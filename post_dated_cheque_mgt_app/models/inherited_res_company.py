# -*- coding: utf-8 -*-


from odoo import fields, models

class Company(models.Model):
	_inherit = 'res.company'

	pdc_account_id = fields.Many2one('account.account',string="PDC Receivable Account")
	pdc_account_creditors_id = fields.Many2one('account.account',string="PDC Payable Account")

	customer_notify_check = fields.Boolean('Customer Due Date Notification')
	vendor_notify_check = fields.Boolean('Vendor Due Date Notification')

	
