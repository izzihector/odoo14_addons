from this import d
from odoo import models, fields, api


class sale_discount(models.Model):
    _inherit = "sale.order.line"
    discount_type = fields.Selection(
        [('fixed', 'Fixed'), ('percent', 'Percent')])

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'discount_type')
    def _compute_amount(self):
        for line in self:
            if(line.discount_type == 'fixed'):
                price = line.price_unit-(line.discount/line.product_uom_qty)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                product=line.product_id, partner=line.order_id.partner_shipping_id)
            elif(line.discount_type == 'percent'):
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                product=line.product_id, partner=line.order_id.partner_shipping_id)
            else:
                price = line.price_unit
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
