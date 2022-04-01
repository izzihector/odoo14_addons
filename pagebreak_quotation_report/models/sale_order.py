# -*- coding: utf-8 -*-
from odoo import api, models, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    page_break = fields.Boolean(
        string="Pagebreak", copy=False, default=False)
    display_title = fields.Boolean(
        string="display_title", copy=False, compute="check_prev_pagebreak")
    line_numb = fields.Integer(
        string="Line Numb", copy=False, compute="check_prev_pagebreak")

    def check_prev_pagebreak(self):
        counter = 0
        for lines in self:
            display_title = False
            counter = counter + 1
            lines.update({'line_numb': counter})
            if lines.page_break:
                display_title = True
            if display_title:
                lines.update({'display_title': display_title})
            else:
                lines.update({'display_title': display_title})
