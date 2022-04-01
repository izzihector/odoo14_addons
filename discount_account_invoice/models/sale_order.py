from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    global_discount_type = fields.Selection([('fixed', 'Fixed'),
                                             ('percent', 'Percent')],
                                            string="Discount Type", default="percent", tracking=True)
    global_order_discount = fields.Float(
        string='Global Discount', store=True, tracking=True)
    total_discount = fields.Monetary(string='Discount', store=True,
                                     readonly=True, default=0, tracking=True)
    amount_undisc = fields.Monetary(string='Undiscount Amount', store=True, readonly=True, default=0, tracking=True,
                                    compute='_amount_all')

    # total_global_discount = fields.Monetary(string='Total Global Discount',
    #                                         store=True, readonly=True, default=0)
    # total_discount = fields.Monetary(string='Discount', store=True,
    #                                  readonly=True, default=0, tracking=True)

    @api.depends('order_line.price_total', 'global_discount_type', 'global_order_discount')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        discount_amount_total = 0.0
        total_discount = 0.0
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal - (
                    line.discount if line.discount_type == 'fixed' else (line.price_unit * line.product_uom_qty) * (
                        line.discount / 100))
                amount_tax += line.price_tax

                if line.discount_type == 'fixed':
                    total_discount += line.discount
                else:
                    total_discount += (line.price_unit *
                                       line.product_uom_qty) * (line.discount / 100)

            if order.global_discount_type and order.global_order_discount:
                discTax = self.env['ir.config_parameter'].sudo(
                ).get_param('account.global_discount_tax')
                if not discTax:
                    discTax = 'untax'

                if discTax == 'untax':
                    if order.global_discount_type == 'fixed':
                        amount_untaxed -= order.global_order_discount
                        total_discount += order.global_order_discount
                    else:
                        total_discount += (amount_untaxed *
                                           (order.global_order_discount / 100))
                        amount_untaxed -= (amount_untaxed *
                                           (order.global_order_discount / 100))
                else:
                    if order.global_discount_type == 'fixed':
                        discount_amount_total = order.global_order_discount
                        total_discount += discount_amount_total
                    else:
                        discount_amount_total = (
                            amount_untaxed + amount_tax) * (order.global_order_discount / 100)
                        total_discount += discount_amount_total

            amount_total = amount_untaxed + amount_tax - discount_amount_total

            order.update({
                'amount_undisc': amount_untaxed + total_discount,
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_total,
                'total_discount': total_discount,
            })

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'global_discount_type': self.global_discount_type,
            'global_order_discount': self.global_order_discount,
        })
        return invoice_vals


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    discount_type = fields.Selection([('fixed', 'Fixed'),
                                      ('percent', 'Percent')],
                                     string="Discount Type", default="percent")

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'discount_type')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            if line.discount_type == 'fixed':
                price = line.price_unit - \
                    ((line.discount / line.product_uom_qty) or 0.0)
            else:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'] + (line.price_unit - price) * line.product_uom_qty,
                'price_subtotal': taxes['total_excluded'] + (line.price_unit - price) * line.product_uom_qty,
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_id.invalidate_cache(
                    ['invoice_repartition_line_ids'], [line.tax_id.id])

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(
            **optional_values)
        res.update({
            'discount_type': self.discount_type,
        })
        return res
