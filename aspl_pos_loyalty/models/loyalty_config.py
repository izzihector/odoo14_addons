# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import fields, models, api, _
import logging

_logger = logging.getLogger(__name__)

class LoyaltyConfiguration(models.Model):
    _name = 'loyalty.config.settings'
    _inherit = 'res.config.settings'

    @api.model
    def get_values(self):
        res = super(LoyaltyConfiguration, self).get_values()
        param_obj = self.env['ir.config_parameter']
        res.update({
            'points_based_on': param_obj.sudo().get_param('aspl_pos_loyalty.points_based_on'),
            'minimum_purchase': float(param_obj.sudo().get_param('aspl_pos_loyalty.minimum_purchase')),
            'point_calculation': float(param_obj.sudo().get_param('aspl_pos_loyalty.point_calculation')),
            'points': int(param_obj.sudo().get_param('aspl_pos_loyalty.points')),
            'to_amount': float(param_obj.sudo().get_param('aspl_pos_loyalty.to_amount')),
        })
        return res

    def set_values(self):
        res = super(LoyaltyConfiguration, self).set_values()
        param_obj = self.env['ir.config_parameter']
        param_obj.sudo().set_param('aspl_pos_loyalty.points_based_on', self.points_based_on)
        param_obj.sudo().set_param('aspl_pos_loyalty.minimum_purchase', float(self.minimum_purchase))
        param_obj.sudo().set_param('aspl_pos_loyalty.point_calculation', float(self.point_calculation))
        param_obj.sudo().set_param('aspl_pos_loyalty.points', int(self.points))
        param_obj.sudo().set_param('aspl_pos_loyalty.to_amount', float(self.to_amount))
        return res

    points_based_on = fields.Selection([
        ('product', "Product"),
        ('order', "Order")
    ], string="Points Based On",
        help='Loyalty points calculation can be based on products or order')

    minimum_purchase = fields.Float("Minimum Purchase")
    point_calculation = fields.Float("Point Calculation (%)")
    points = fields.Integer("Points")
    to_amount = fields.Float("To Amount")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: