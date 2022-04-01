# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ReportAccountFinancialReport(models.Model):
    _name = "div.search.template"

    div_name = fields.Char(String="Div name", readonly=True, compute='_cumpute_div_name')
    show_div_filter = fields.Integer('Allow filtering by div', default=1)

    @api.depends('show_div_filter')
    def _cumpute_div_name(self):
        for rec in self:
            if rec.show_div_filter >= 1:
                rec.div_name = '1:' + str(rec.show_div_filter)
            else:
                raise UserError(_('please not input for zero'))

    # @api.model
    # def create(self, vals):
    #     value = self.show_div_filter
    #     vals['div_name'] = "1:" + str(value)
