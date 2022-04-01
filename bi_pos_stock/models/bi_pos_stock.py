# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import Warning
import random
from odoo.tools import float_is_zero
from datetime import date, datetime


class pos_config(models.Model):
	_inherit = 'pos.config'
	
	pos_display_stock = fields.Boolean(string='Display Stock in POS')
	pos_stock_type = fields.Selection([('onhand', 'Qty on Hand'), ('incoming', 'Incoming Qty'), ('outgoing', 'Outgoing Qty'), ('available', 'Qty Available')], string='Stock Type', help='Seller can display Different stock type in POS.')
	pos_allow_order = fields.Boolean(string='Allow POS Order When Product is Out of Stock')
	pos_deny_order = fields.Char(string='Deny POS Order When Product Qty is goes down to')   
	
	show_stock_location = fields.Selection([
		('all', 'All Warehouse'),
		('specific', 'Current Session Warehouse'),
		], string='Show Stock Of', default='all')
		

class stock_quant(models.Model):
	_inherit = 'stock.quant'


	def get_stock_location_qty(self, location):
		res = {}
		product_ids = self.env['product.product'].search([])
		for product in product_ids:
			quants = self.env['stock.quant'].search([('product_id', '=', product.id),('location_id', '=', location['id'])])
			if len(quants) > 1:
				quantity = 0.0
				for quant in quants:
					quantity += quant.quantity
				res.update({product.id : quantity})
			else:
				res.update({product.id : quants.quantity})
		return [res]

	def get_products_stock_location_qty(self, location,products):
		res = {}
		product_ids = self.env['product.product'].browse(products)
		for product in product_ids:
			quants = self.env['stock.quant'].search([('product_id', '=', product.id),('location_id', '=', location['id'])])
			if len(quants) > 1:
				quantity = 0.0
				for quant in quants:
					quantity += quant.quantity
				res.update({product.id : quantity})
			else:
				res.update({product.id : quants.quantity})
		return [res]

	def get_single_product(self,product, location):
		res = []
		pro = self.env['product.product'].browse(product)
		quants = self.env['stock.quant'].search([('product_id', '=', pro.id),('location_id', '=', location['id'])])
		if len(quants) > 1:
			quantity = 0.0
			for quant in quants:
				quantity += quant.quantity
			res.append([pro.id, quantity])
		else:
			res.append([pro.id, quants.quantity])
		return res


class product(models.Model):
	_inherit = 'product.product'
	
	available_quantity = fields.Float('Available Quantity')


	def get_stock_location_avail_qty(self, location):
		res = {}
		product_ids = self.env['product.product'].search([])
		for product in product_ids:
			quants = self.env['stock.quant'].search([('product_id', '=', product.id),('location_id', '=', location['id'])])
			outgoing = self.env['stock.move'].search([('product_id', '=', product.id),('location_id', '=', location['id'])])
			incoming = self.env['stock.move'].search([('product_id', '=', product.id),('location_dest_id', '=', location['id'])])
			qty=0.0
			product_qty = 0.0
			incoming_qty = 0.0
			if len(quants) > 1:
				for quant in quants:
					qty += quant.quantity

				if len(outgoing) > 0:
					for quant in outgoing:
						if quant.state not in ['done']:
							product_qty += quant.product_qty

				if len(incoming) > 0:
					for quant in incoming:
						if quant.state not in ['done']:
							incoming_qty += quant.product_qty
					product.available_quantity = qty-product_qty + incoming_qty
					# print("12345=========================",product.id ,product.available_quantity,qty,product_qty,incoming_qty)
					res.update({product.id : qty-product_qty + incoming_qty})
			else:
				if not quants:
					if len(outgoing) > 0:
						for quant in outgoing:
							if quant.state not in ['done']:
								product_qty += quant.product_qty

					if len(incoming) > 0:
						for quant in incoming:
							if quant.state not in ['done']:
								incoming_qty += quant.product_qty
					product.available_quantity = qty-product_qty + incoming_qty
					res.update({product.id : qty-product_qty + incoming_qty})
				else:
					if len(outgoing) > 0:
						for quant in outgoing:
							if quant.state not in ['done']:
								product_qty += quant.product_qty

					if len(incoming) > 0:
						for quant in incoming:
							if quant.state not in ['done']:
								incoming_qty += quant.product_qty
					product.available_quantity = quants.quantity - product_qty + incoming_qty
					res.update({product.id : quants.quantity - product_qty + incoming_qty})
		return [res]
	

