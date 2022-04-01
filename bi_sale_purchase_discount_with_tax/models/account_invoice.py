# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class account_invoice(models.Model):
    _inherit = 'account.move'

    def calc_discount(self):
        self._calculate_discount()

    @api.depends('discount_amount')
    def _calculate_discount(self):
        res = discount = 0.0
        for self_obj in self:
            if self_obj.discount_type == 'global':
                if self_obj.discount_method == 'fix':
                    res = self_obj.discount_amount
                elif self_obj.discount_method == 'per':
                    res = self_obj.amount_untaxed * (self_obj.discount_amount / 100)
            else:
                res = discount
        return res

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount(self):
        super(account_invoice, self)._compute_amount()
        for move in self:
            if move.payment_state == 'invoicing_legacy':
                # invoicing_legacy state is set via SQL when setting setting field
                # invoicing_switch_threshold (defined in account_accountant).
                # The only way of going out of this state is through this setting,
                # so we don't recompute it here.
                move.payment_state = move.payment_state
                continue

            if move.is_invoice(include_receipts=True):
                move.discount_amt_line = sum(line.discount_amt for line in move.invoice_line_ids)

                if move.discount_type == 'line':
                    move.discount_amt = sum(line.discount_amount for line in move.invoice_line_ids)
                else:
                    res = 0.0
                    if move.discount_method == 'fix':
                        res = move.discount_amount
                    elif move.discount_method == 'per':
                        res = move.amount_untaxed * (move.discount_amount / 100.0)
                    else:
                        res = 0.0
                    move.discount_amt = res

                sums = 0

                res_config = move.env['res.config.settings'].sudo().search([], order="id desc", limit=1)
                if res_config:
                    if res_config.tax_discount_policy == 'tax':
                        if move.discount_type == 'line':
                            move.amount_total = move.amount_tax + move.amount_untaxed - move.discount_amt_line
                        elif move.discount_type == 'global':
                            if move.discount_method == 'fix':
                                move.discount_amt = move.discount_amount
                                move.amount_total = move.amount_tax + move.amount_untaxed - move.discount_amt
                            elif move.discount_method == 'per':
                                move.discount_amt = (move.amount_untaxed + move.amount_tax) * (
                                        move.discount_amount / 100.0)
                                move.amount_total = move.amount_tax + move.amount_untaxed - move.discount_amt
                            else:
                                move.amount_total = move.amount_tax + move.amount_untaxed
                    elif res_config.tax_discount_policy == 'untax':
                        if move.discount_type == 'line':
                            move.amount_total = move.amount_tax + move.amount_untaxed - move.discount_amt_line
                        elif move.discount_type == 'global':
                            if move.discount_method == 'fix':
                                if move.invoice_line_ids:
                                    for line in move.invoice_line_ids:
                                        if line.tax_ids:
                                            if move.amount_untaxed:
                                                final_discount = ((
                                                                          move.discount_amt * line.price_subtotal) / move.amount_untaxed)
                                                discount = (line.price_unit * line.quantity) - final_discount
                                                taxes = line.tax_ids.compute_all(discount, move.currency_id, 1.0,
                                                                                 line.product_id, move.partner_id)
                                                sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                                move.amount_total = sums + move.amount_untaxed - move.discount_amt
                                move.amount_tax = sums
                            elif move.discount_method == 'per':
                                if move.invoice_line_ids:
                                    for line in move.invoice_line_ids:
                                        if line.tax_ids:
                                            final_discount = ((move.discount_amount * line.price_subtotal) / 100.0)
                                            discount = (line.price_unit * line.quantity) - final_discount
                                            taxes = line.tax_ids.compute_all(discount, move.currency_id, 1.0,
                                                                             line.product_id, move.partner_id)
                                            sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                                move.amount_total = sums + move.amount_untaxed - move.discount_amt
                                move.amount_tax = sums
                            else:
                                move.amount_total = move.amount_tax + move.amount_untaxed
                        else:
                            move.amount_total = move.amount_tax + move.amount_untaxed
                    else:
                        move.amount_total = move.amount_tax + move.amount_untaxed

                    if res_config:
                        if move.discount_amt_line or move.discount_amt:
                            if move.move_type in ('out_invoice', 'out_refund'):
                                if res_config.sale_account_id:
                                    move.discount_account_id = res_config.sale_account_id.id
                                else:
                                    account_id = False
                                    account_id = move.env['account.account'].search(
                                        [('user_type_id.name', '=', 'Expenses'), ('discount_account', '=', True)],
                                        limit=1)
                                    if not account_id:
                                        raise UserError(_('Please define an sale discount account for this company.'))
                                    else:
                                        move.discount_account_id = account_id.id
                            if move.move_type in ('in_invoice', 'in_refund'):
                                if res_config.purchase_account_id:
                                    move.discount_account_id = res_config.purchase_account_id.id
                                else:
                                    account_id = False
                                    account_id = move.env['account.account'].search(
                                        [('user_type_id.name', '=', 'Income'), ('discount_account', '=', True)],
                                        limit=1)
                                    if not account_id:
                                        raise UserError(
                                            _('Please define an purchase discount account for this company.'))
                                    else:
                                        move.discount_account_id = account_id.id

        # round_curr = self.currency_id.round
        # self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        # self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
        # self.amount_total = self.amount_untaxed + self.amount_tax
        # self.discount_amt_line = sum(line.discount_amt for line in self.invoice_line_ids)
        # 
        # if self.discount_type == 'line':
        #     self.discount_amt = sum(line.discount_amount for line in self.invoice_line_ids)
        # else:
        #     res = 0.0
        #     if self.discount_method == 'fix':
        #         res = self.discount_amount
        #     elif self.discount_method == 'per':
        #         res = self.amount_untaxed * (self.discount_amount / 100.0)
        #     else:
        #         res = 0.0
        #     self.discount_amt = res
        # 
        # sums = 0
        # 
        # amount_total_company_signed = self.amount_total
        # amount_untaxed_signed = self.amount_untaxed
        # if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
        #     currency_id = self.currency_id
        #     rate_date = self._get_currency_rate_date() or fields.Date.today()
        #     amount_total_company_signed = currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, rate_date)
        #     amount_untaxed_signed = currency_id._convert(self.amount_untaxed, self.company_id.currency_id, self.company_id, rate_date)
        # sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        # self.amount_total_company_signed = amount_total_company_signed * sign
        # self.amount_untaxed_signed = amount_untaxed_signed * sign
        # 
        # 
        # res_config= self.env['res.config.settings'].sudo().search([],order="id desc", limit=1)
        # if res_config:            
        #     if res_config.tax_discount_policy == 'tax':
        #         if self.discount_type == 'line':
        #             self.amount_total = self.amount_tax + self.amount_untaxed - self.discount_amt_line
        #         elif self.discount_type == 'global':
        #             if self.discount_method == 'fix':
        #                 self.discount_amt = self.discount_amount
        #                 self.amount_total = self.amount_tax + self.amount_untaxed - self.discount_amt
        #             elif self.discount_method == 'per':
        #                 self.discount_amt = (self.amount_untaxed + self.amount_tax) * (self.discount_amount / 100.0)
        #                 self.amount_total = self.amount_tax + self.amount_untaxed - self.discount_amt
        #             else:
        #                 self.amount_total = self.amount_tax + self.amount_untaxed
        #         else:
        #             self.amount_total = self.amount_tax + self.amount_untaxed
        #     elif res_config.tax_discount_policy == 'untax':
        #         if self.discount_type == 'line':
        #             self.amount_total = self.amount_tax + self.amount_untaxed - self.discount_amt_line
        #         elif self.discount_type == 'global':
        #             if self.discount_method == 'fix':
        #                 if self.invoice_line_ids:
        #                     for line in self.invoice_line_ids:
        #                         if line.invoice_line_tax_ids:
        #                             if self.amount_untaxed:
        #                                 final_discount = ((self.discount_amt*line.price_subtotal)/self.amount_untaxed)
        #                                 discount = (line.price_unit * line.quantity) - final_discount
        #                                 taxes = line.invoice_line_tax_ids.compute_all(discount, self.currency_id, 1.0,
        #                                                                 line.product_id,self.partner_id)
        #                                 sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
        #                 self.amount_total = sums + self.amount_untaxed - self.discount_amt
        #                 self.amount_tax = sums
        #             elif self.discount_method == 'per':
        #                 if self.invoice_line_ids:
        #                     for line in self.invoice_line_ids:
        #                         if line.invoice_line_tax_ids:
        #                             final_discount = ((self.discount_amount*line.price_subtotal)/100.0)
        #                             discount = (line.price_unit * line.quantity) - final_discount
        #                             taxes = line.invoice_line_tax_ids.compute_all(discount, self.currency_id, 1.0,
        #                                                             line.product_id,self.partner_id)
        #                             sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
        #                 self.amount_total = sums + self.amount_untaxed - self.discount_amt
        #                 self.amount_tax = sums
        #         else:
        #             self.amount_total = self.amount_tax + self.amount_untaxed
        #     else:
        #         self.amount_total = self.amount_tax + self.amount_untaxed
        # else:
        #     self.amount_total = self.amount_tax + self.amount_untaxed
        # 
        # if res_config:
        #     if self.discount_amt_line or self.discount_amt:
        #         if self.type in ('out_invoice','out_refund'):
        #             if res_config.sale_account_id:
        #                 self.discount_account_id = res_config.sale_account_id.id
        #             else:
        #                 account_id = False
        #                 account_id = self.env['account.account'].search([('user_type_id.name','=','Expenses'), ('discount_account','=',True)],limit=1)
        #                 if not account_id:
        #                     raise UserError(_('Please define an sale discount account for this company.'))
        #                 else:
        #                     self.discount_account_id = account_id.id
        #         if self.type in ('in_invoice','in_refund'):
        #             if res_config.purchase_account_id:
        #                 self.discount_account_id = res_config.purchase_account_id.id
        #             else:
        #                 account_id = False
        #                 account_id = self.env['account.account'].search([('user_type_id.name','=','Income'), ('discount_account','=',True)],limit=1)
        #                 if not account_id:
        #                     raise UserError(_('Please define an purchase discount account for this company.'))
        #                 else:
        #                     self.discount_account_id = account_id.id
        # 
        # self.amount_total_signed = self.amount_total * sign

    discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], 'Discount Method')
    discount_amount = fields.Float('Discount Amount')
    discount_amt = fields.Float(string='- Discount', readonly=True, compute='_compute_amount')
    amount_untaxed = fields.Float(string='Subtotal', digits=dp.get_precision('Account'), store=True, readonly=True,
                                  compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Tax', digits=dp.get_precision('Account'), store=True, readonly=True,
                              compute='_compute_amount')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'), store=True, readonly=True,
                                compute='_compute_amount')
    discount_type = fields.Selection([('line', 'Order Line'), ('global', 'Global')], default='global',
                                     string='Discount Applies to', )
    discount_amt_line = fields.Float(compute='_compute_amount', string='- Line Discount',
                                     digits=dp.get_precision('Discount'), store=True, readonly=True)
    discount_account_id = fields.Many2one('account.account', 'Discount Account', compute='_compute_amount', store=True)

    @api.model
    def _move_autocomplete_invoice_lines_create(self, vals_list):
        for val in vals_list:
            if val.get('discount_amt') > 0.0 or val.get('discount_amt_line') > 0.0:
                val['invoice_line_ids'] += self.discount_line_move_line_get(val)
        res = super(account_invoice, self)._move_autocomplete_invoice_lines_create(vals_list)
        return res

    def _get_refund_common_fields(self):
        res = super(account_invoice, self)._get_refund_common_fields()
        res += ["discount_method", "discount_amount", "discount_type"]
        return res

    def _prepare_invoice_line_from_po_line(self, line):
        if line.product_id.purchase_method == 'purchase':
            qty = line.product_qty - line.qty_invoiced
        else:
            qty = line.qty_received - line.qty_invoiced
        if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
            qty = 0.0
        taxes = line.taxes_id
        invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id,
                                                                        line.order_id.partner_id)
        invoice_line = self.env['account.move.line']
        date = self.date or self.date_invoice
        data = {
            'purchase_line_id': line.id,
            'name': line.order_id.name + ': ' + line.name,
            'origin': line.order_id.origin,
            'uom_id': line.product_uom.id,
            'product_id': line.product_id.id,
            'account_id': invoice_line.with_context(
                {'journal_id': self.journal_id.id, 'type': 'in_invoice'})._default_account(),
            'price_unit': line.order_id.currency_id._convert(
                line.price_unit, self.currency_id, line.company_id, date or fields.Date.today(), round=False),
            'quantity': qty,
            'discount': 0.0,
            'discount_method': line.discount_method,
            'discount_amount': line.discount_amount,
            'discount_amt': line.discount_amt,
            'account_analytic_id': line.account_analytic_id.id,
            'analytic_tag_ids': line.analytic_tag_ids.ids,
            'invoice_line_tax_ids': invoice_line_tax_ids.ids
        }
        account = invoice_line.get_invoice_line_account('in_invoice', line.product_id, line.order_id.fiscal_position_id,
                                                        self.env.user.company_id)
        if account:
            data['account_id'] = account.id
        return data

    @api.onchange('purchase_id')
    def purchase_order_change(self):
        if not self.purchase_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.purchase_id.partner_id.id

        new_lines = self.env['account.move.line']
        for line in self.purchase_id.order_line - self.invoice_line_ids.mapped('purchase_line_id'):
            data = self._prepare_invoice_line_from_po_line(line)
            new_line = new_lines.new(data)
            new_line._set_additional_fields(self)
            new_lines += new_line

        self.invoice_line_ids += new_lines
        self.payment_term_id = self.purchase_id.payment_term_id
        self.discount_amount = self.purchase_id.discount_amount
        self.discount_method = self.purchase_id.discount_method
        self.discount_amt = self.purchase_id.discount_amt
        self.discount_amt_line = self.purchase_id.discount_amt_line
        self.discount_type = self.purchase_id.discount_type
        self.discount_account_id = self.purchase_id.discount_account_id.id or False
        self.env.context = dict(self.env.context, from_purchase_order_change=True)
        self.purchase_id = False
        return {}

    # Load all Vendor Bill lines
    @api.onchange('vendor_bill_id')
    def _onchange_vendor_bill(self):
        if not self.vendor_bill_id:
            return {}
        self.currency_id = self.vendor_bill_id.currency_id
        new_lines = self.env['account.move.line']
        for line in self.vendor_bill_id.invoice_line_ids:
            new_lines += new_lines.new(line._prepare_invoice_line())
        self.invoice_line_ids += new_lines
        self.discount_amount = self.vendor_bill_id.discount_amount
        self.discount_method = self.vendor_bill_id.discount_method
        self.discount_amt = self.vendor_bill_id.discount_amt
        self.discount_type = self.vendor_bill_id.discount_type
        self.discount_amt_line = self.vendor_bill_id.discount_amt_line
        self.discount_account_id = self.vendor_bill_id.discount_account_id.id or False
        self.payment_term_id = self.vendor_bill_id.payment_term_id
        self.vendor_bill_id = False
        return {}

    @api.onchange('vendor_bill_purchase_id')
    def _onchange_bill_purchase_order(self):
        self.discount_method = self.vendor_bill_purchase_id.purchase_order_id.discount_method
        self.discount_amount = self.vendor_bill_purchase_id.purchase_order_id.discount_amount
        self.discount_type = self.vendor_bill_purchase_id.purchase_order_id.discount_type
        self.discount_amt_line = self.vendor_bill_purchase_id.purchase_order_id.discount_amt_line
        self.discount_account_id = self.vendor_bill_purchase_id.purchase_order_id.discount_account_id.id or False
        return super(account_invoice, self)._onchange_bill_purchase_order()

    @api.onchange('amount_total')
    def _onchange_amount_total(self):
        for inv in self:
            if float_compare(inv.amount_total, 0.0, precision_rounding=inv.currency_id.rounding) == -1:
                pass
                # raise Warning(_('You cannot validate an invoice with a negative total amount. You should create a credit note instead.'))

    @api.onchange('invoice_line_ids', 'discount_amount', 'discount_method')
    def _onchange_invoice_line_ids(self):
        super(account_invoice, self)._onchange_invoice_line_ids()
        return

    @api.model
    def discount_line_move_line_get(self, val):
        # self._compute_amount()
        res = []
        account_id = False
        value = 0.0
        if val.get('discount_type') == 'line':
            if val.get('discount_amt_line'):
                if val.get('discount_account_id'):
                    account_id = val.get('discount_account_id')
                value = val.get('discount_amt_line')
        elif val.get('discount_type') == 'global':
            if val.get('discount_amt'):
                if val.get('discount_account_id'):
                    account_id = val.get('discount_account_id')
                value = val.get('discount_amt')
        res.append({
            # 'name': self.discount_account_id.display_name or '',
            'price_unit': -value,
            'quantity': 1,
            # 'price': -value,
            'account_id': account_id or False,
        })
        return res

    # def action_move_create(self):
    #     """ Creates invoice related analytics and financial move lines """
    #     account_move = self.env['account.move']
    # 
    #     for inv in self:
    #         if not inv.journal_id.sequence_id:
    #             raise UserError(_('Please define sequence on the journal related to this invoice.'))
    #         if not inv.invoice_line_ids.filtered(lambda line: line.account_id):
    #             raise UserError(_('Please add at least one invoice line.'))
    #         if inv.move_id:
    #             continue
    # 
    #         if not inv.date_invoice:
    #             inv.write({'date_invoice': fields.Date.context_today(self)})
    #         if not inv.date_due:
    #             inv.write({'date_due': inv.date_invoice})
    #         company_currency = inv.company_id.currency_id
    # 
    #         # create move lines (one per invoice line + eventual taxes and analytic lines)
    #         iml = inv.invoice_line_move_line_get()
    #         iml += inv.tax_line_move_line_get()
    #         if inv.discount_amt or inv.discount_amt_line:
    #             iml += inv.discount_line_move_line_get()
    # 
    #         diff_currency = inv.currency_id != company_currency
    #         # create one move line for the total and possibly adjust the other lines amount
    #         total, total_currency, iml = inv.compute_invoice_totals(company_currency, iml)
    # 
    #         name = inv.name or ''
    #         if inv.payment_term_id:
    #             totlines = \
    #                 inv.payment_term_id.with_context(currency_id=company_currency.id).compute(total, inv.date_invoice)[
    #                     0]
    #             res_amount_currency = total_currency
    #             for i, t in enumerate(totlines):
    #                 if inv.currency_id != company_currency:
    #                     amount_currency = company_currency._convert(t[1], inv.currency_id, inv.company_id,
    #                                                                 inv._get_currency_rate_date() or fields.Date.today())
    #                 else:
    #                     amount_currency = False
    # 
    #                 # last line: add the diff
    #                 res_amount_currency -= amount_currency or 0
    #                 if i + 1 == len(totlines):
    #                     amount_currency += res_amount_currency
    # 
    #                 iml.append({
    #                     'type': 'dest',
    #                     'name': name,
    #                     'price': t[1],
    #                     'account_id': inv.account_id.id,
    #                     'date_maturity': t[0],
    #                     'amount_currency': diff_currency and amount_currency,
    #                     'currency_id': diff_currency and inv.currency_id.id,
    #                     'move_id': inv.id
    #                 })
    #         else:
    #             iml.append({
    #                 'type': 'dest',
    #                 'name': name,
    #                 'price': total,
    #                 'account_id': inv.account_id.id,
    #                 'date_maturity': inv.date_due,
    #                 'amount_currency': diff_currency and total_currency,
    #                 'currency_id': diff_currency and inv.currency_id.id,
    #                 'move_id': inv.id
    #             })
    #         part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
    #         line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
    #         line = inv.group_lines(iml, line)
    # 
    #         line = inv.finalize_invoice_move_lines(line)
    # 
    #         date = inv.date or inv.date_invoice
    #         move_vals = {
    #             'ref': inv.reference,
    #             'line_ids': line,
    #             'journal_id': inv.journal_id.id,
    #             'date': date,
    #             'narration': inv.comment,
    #         }
    #         move = account_move.create(move_vals)
    #         # Pass invoice in method post: used if you want to get the same
    #         # account move reference when creating the same invoice after a cancelled one:
    #         move.post(invoice=inv)
    #         # make the invoice point to that move
    #         vals = {
    #             'move_id': move.id,
    #             'date': date,
    #             'move_name': move.name,
    #         }
    #         inv.write(vals)
    #     return True
    # 
    #     if self.company_id.anglo_saxon_accounting and self.type in ('out_invoice', 'out_refund'):
    #         for i_line in self.invoice_line_ids:
    #             res.extend(self._anglo_saxon_sale_move_lines(i_line))
    # 
    #     if self.env.user.company_id.anglo_saxon_accounting:
    #         if self.type in ['in_invoice', 'in_refund']:
    #             for i_line in self.invoice_line_ids:
    #                 res.extend(self._anglo_saxon_purchase_move_lines(i_line, res))
    #     return res

    # @api.onchange('invoice_line_ids', 'discount_amount', 'discount_method')
    # def _onchange_invoice_line_ids(self):
    #     taxes_grouped = self.get_taxes_values()
    #     tax_lines = self.tax_line_ids.filtered('manual')
    #     for tax in taxes_grouped.values():
    #         tax_lines += tax_lines.new(tax)
    #     self.tax_line_ids = tax_lines
    #     return

    def get_taxes_values(self):
        tax_grouped = {}
        round_curr = self.currency_id.round
        order_discount = 0.0
        res_config = self.env['res.config.settings'].sudo().search([], order="id desc", limit=1)
        if res_config:
            if res_config.tax_discount_policy == 'untax':
                if self.discount_type == 'global':
                    if self.discount_method == 'fix':
                        order_discount = self.discount_amount
                        # amount_after_discount = self.amount_untaxed - order_discount
                        if self.invoice_line_ids:
                            for line in self.invoice_line_ids:
                                if line.invoice_line_tax_ids:
                                    if self.amount_untaxed != 0.0:
                                        final_discount = (
                                                (self.discount_amt * line.price_subtotal) / self.amount_untaxed)
                                    else:
                                        final_discount = ((self.discount_amt * line.price_subtotal) / 1.0)
                                    discount = line.price_subtotal - round_curr(final_discount)
                                    taxes = \
                                        line.invoice_line_tax_ids.compute_all(round_curr(discount), self.currency_id,
                                                                              1.0,
                                                                              line.product_id, self.partner_id)['taxes']
                                    # sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                                    for tax in taxes:
                                        val = self._prepare_tax_line_vals(line, tax)
                                        key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)
                                        if key not in tax_grouped:
                                            tax_grouped[key] = val
                                            tax_grouped[key]['base'] = round_curr(val['base'])
                                        else:
                                            tax_grouped[key]['amount'] += val['amount']
                                            tax_grouped[key]['base'] += round_curr(val['base'])
                    elif self.discount_method == 'per':
                        order_discount = self.amount_untaxed * (self.discount_amount / 100)
                        # amount_after_discount = self.amount_untaxed - order_discount
                        if self.invoice_line_ids:
                            for line in self.invoice_line_ids:
                                if line.invoice_line_tax_ids:
                                    final_discount = ((self.discount_amount * line.price_subtotal) / 100.0)
                                    discount = line.price_subtotal - final_discount
                                    taxes = line.invoice_line_tax_ids.compute_all(discount, self.currency_id, 1.0,
                                                                                  line.product_id, self.partner_id)[
                                        'taxes']
                                    for tax in taxes:
                                        val = self._prepare_tax_line_vals(line, tax)
                                        key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)
                                        if key not in tax_grouped:
                                            tax_grouped[key] = val
                                            tax_grouped[key]['base'] = round_curr(val['base'])
                                        else:
                                            tax_grouped[key]['amount'] += val['amount']
                                            tax_grouped[key]['base'] += round_curr(val['base'])
                elif self.discount_type == 'line':
                    for line in self.invoice_line_ids:
                        if not line.account_id:
                            continue
                        if line.discount_method == 'fix':
                            price = (line.price_unit * line.quantity) - line.discount_amount
                            taxes = line.invoice_line_tax_ids.compute_all(price, self.currency_id, 1.0,
                                                                          line.product_id, self.partner_id)['taxes']
                        elif line.discount_method == 'per':
                            price = (line.price_unit * line.quantity) * (1 - (line.discount_amount or 0.0) / 100.0)
                            taxes = line.invoice_line_tax_ids.compute_all(price, self.currency_id, 1.0,
                                                                          line.product_id, self.partner_id)['taxes']
                        else:
                            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity,
                                                                          line.product_id, self.partner_id)['taxes']
                        for tax in taxes:
                            val = self._prepare_tax_line_vals(line, tax)
                            key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                            if key not in tax_grouped:
                                tax_grouped[key] = val
                                tax_grouped[key]['base'] = round_curr(val['base'])
                            else:
                                tax_grouped[key]['amount'] += val['amount']
                                tax_grouped[key]['base'] += round_curr(val['base'])
                else:
                    for line in self.invoice_line_ids:
                        if not line.account_id:
                            continue
                        price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity,
                                                                      line.product_id, self.partner_id)['taxes']
                        for tax in taxes:
                            val = self._prepare_tax_line_vals(line, tax)
                            key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                            if key not in tax_grouped:
                                tax_grouped[key] = val
                                tax_grouped[key]['base'] = round_curr(val['base'])
                            else:
                                tax_grouped[key]['amount'] += val['amount']
                                tax_grouped[key]['base'] += round_curr(val['base'])
            else:
                for line in self.invoice_line_ids:
                    if not line.account_id:
                        continue
                    price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = \
                        line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity,
                                                              line.product_id,
                                                              self.partner_id)['taxes']
                    for tax in taxes:
                        val = self._prepare_tax_line_vals(line, tax)
                        key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                        if key not in tax_grouped:
                            tax_grouped[key] = val
                            tax_grouped[key]['base'] = round_curr(val['base'])
                        else:
                            tax_grouped[key]['amount'] += val['amount']
                            tax_grouped[key]['base'] += round_curr(val['base'])
        else:
            for line in self.invoice_line_ids:
                if not line.account_id:
                    continue
                price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = \
                    line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id,
                                                          self.partner_id)['taxes']
                for tax in taxes:
                    val = self._prepare_tax_line_vals(line, tax)
                    key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                    if key not in tax_grouped:
                        tax_grouped[key] = val
                        tax_grouped[key]['base'] = round_curr(val['base'])
                    else:
                        tax_grouped[key]['amount'] += val['amount']
                        tax_grouped[key]['base'] += round_curr(val['base'])
        return tax_grouped


class account_invoice_line(models.Model):
    _inherit = 'account.move.line'

    discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], 'Discount Method')
    discount_type = fields.Selection(related='move_id.discount_type', string="Discount Applies to")
    discount_amount = fields.Float('Discount Amount')
    discount_amt = fields.Float('Discount Final Amount')

    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
                 'product_id', 'move_id.partner_id', 'move_id.currency_id', 'move_id.company_id',
                 'move_id.date_invoice', 'move_id.date', 'discount_method', 'discount_type', 'discount_amount')
    def _compute_price(self):
        currency = self.move_id and self.move_id.currency_id or None
        price = taxes = price_subtotal_signed = False

        res_config = self.env['res.config.settings'].sudo().search([], order="id desc", limit=1)
        if res_config:
            if res_config.tax_discount_policy == 'untax':
                if self.discount_type == 'line':
                    price_x = 0.0
                    if self.discount_method == 'fix':
                        price = (self.price_unit * self.quantity) - self.discount_amount
                        self.discount_amt = self.discount_amount
                        price_x = self.discount_amount
                        if self.invoice_line_tax_ids:
                            taxes = self.invoice_line_tax_ids.compute_all(price, currency, 1, product=self.product_id,
                                                                          partner=self.move_id.partner_id)
                    elif self.discount_method == 'per':
                        price = (self.price_unit * self.quantity) * (1 - (self.discount_amount or 0.0) / 100.0)
                        price_x = ((self.price_unit * self.quantity) - (
                                (self.price_unit * self.quantity) * (1 - (self.discount_amount or 0.0) / 100.0)))
                        self.discount_amt = price_x
                        if self.invoice_line_tax_ids:
                            taxes = self.invoice_line_tax_ids.compute_all(price, currency, 1, product=self.product_id,
                                                                          partner=self.move_id.partner_id)
                    else:
                        price = self.price_unit
                        if self.invoice_line_tax_ids:
                            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity,
                                                                          product=self.product_id,
                                                                          partner=self.move_id.partner_id)

                    self.price_subtotal = price_subtotal_signed = (taxes['total_excluded'] + price_x) if taxes else (
                            (self.quantity * price) + price_x)
                    self.price_total = (taxes['total_included'] + price_x) if taxes else (self.price_subtotal + price_x)
                else:
                    price = self.price_unit
                    if self.invoice_line_tax_ids:
                        taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity,
                                                                      product=self.product_id,
                                                                      partner=self.move_id.partner_id)

                    self.price_subtotal = price_subtotal_signed = taxes[
                        'total_excluded'] if taxes else self.quantity * price
                    self.price_total = taxes['total_included'] if taxes else self.price_subtotal
            elif res_config.tax_discount_policy == 'tax':
                price_x = 0.0
                taxes = {}
                if self.discount_type == 'line':
                    price = self.price_unit
                    if self.invoice_line_tax_ids:
                        taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity,
                                                                      product=self.product_id,
                                                                      partner=self.move_id.partner_id)
                    if len(taxes) != 0:
                        if self.discount_method == 'fix':
                            price_x = (taxes['total_included']) - (taxes['total_included'] - self.discount_amount)
                        elif self.discount_method == 'per':
                            price_x = (taxes['total_included']) - (
                                    taxes['total_included'] * (1 - (self.discount_amount or 0.0) / 100.0))
                        else:
                            price_x = self.price_unit
                    else:
                        if self.discount_method == 'fix':
                            price_x = (price * self.quantity) - ((price * self.quantity) - self.discount_amount)
                        elif self.discount_method == 'per':
                            price_x = (price * self.quantity) - (
                                    (price * self.quantity) * (1 - (self.discount_amount or 0.0) / 100.0))
                        else:
                            price_x = self.price_unit
                    self.discount_amt = price_x
                    self.price_subtotal = price_subtotal_signed = (taxes['total_excluded']) if taxes else (
                        (self.quantity * price))
                    self.price_total = (taxes['total_included']) if taxes else (self.price_subtotal)
                else:
                    price = self.price_unit
                    if self.invoice_line_tax_ids:
                        taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity,
                                                                      product=self.product_id,
                                                                      partner=self.move_id.partner_id)

                    self.price_subtotal = price_subtotal_signed = taxes[
                        'total_excluded'] if taxes else self.quantity * price
                    self.price_total = taxes['total_included'] if taxes else self.price_subtotal
            else:
                price = self.price_unit
                if self.invoice_line_tax_ids:
                    taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity,
                                                                  product=self.product_id,
                                                                  partner=self.move_id.partner_id)

                self.price_subtotal = price_subtotal_signed = taxes[
                    'total_excluded'] if taxes else self.quantity * price
                self.price_total = taxes['total_included'] if taxes else self.price_subtotal
        else:
            price = self.price_unit
            if self.invoice_line_tax_ids:
                taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id,
                                                              partner=self.move_id.partner_id)

            self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
            self.price_total = taxes['total_included'] if taxes else self.price_subtotal

        if self.move_id.currency_id and self.move_id.currency_id != self.move_id.company_id.currency_id:
            currency = self.move_id.currency_id
            date = self.move_id._get_currency_rate_date()
            price_subtotal_signed = currency._convert(price_subtotal_signed, self.move_id.company_id.currency_id,
                                                      self.company_id or self.env.user.company_id,
                                                      date or fields.Date.today())
        sign = self.move_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign

    def _prepare_invoice_line(self):
        data = {
            'name': self.name,
            'origin': self.origin,
            'uom_id': self.uom_id.id,
            'product_id': self.product_id.id,
            'account_id': self.account_id.id,
            'price_unit': self.price_unit,
            'quantity': self.quantity,
            'discount': self.discount,
            'discount_method': self.discount_method,
            'discount_amount': self.discount_amount,
            'discount_amt': self.discount_amt,
            'account_analytic_id': self.account_analytic_id.id,
            'analytic_tag_ids': self.analytic_tag_ids.ids,
            'invoice_line_tax_ids': self.invoice_line_tax_ids.ids
        }
        return data


class StockMoveInherit(models.Model):
    _inherit = 'stock.move'

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id,
                                       credit_account_id):
        # This method returns a dictonary to provide an easy extension hook to modify the valuation lines (see purchase for an example)
        self.ensure_one()

        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')

        # new_id = self.env[active_model].browse(active_id)
        final_discount = 0
        if self.purchase_line_id:
            for line in self.purchase_line_id:
                if line.product_id == self.product_id:
                    if self.purchase_line_id.order_id.discount_type == 'global':
                        if self.purchase_line_id.order_id.discount_method == 'fix':
                            if self.purchase_line_id.order_id.discount_amount != 0.0:
                                discount = ((
                                                    self.purchase_line_id.order_id.discount_amt * line.price_subtotal) / self.purchase_line_id.order_id.amount_untaxed)
                                final_discount = discount
                        elif self.purchase_line_id.order_id.discount_method == 'per':
                            if self.purchase_line_id.order_id.discount_amount != 0.0:
                                final_discount = ((
                                                          self.purchase_line_id.order_id.discount_amount * line.price_subtotal) / 100.0)
                        else:
                            final_discount = 0
                    elif self.purchase_line_id.order_id.discount_type == 'line':
                        if line.discount_method == 'fix':
                            final_discount = line.discount_amt
                        elif line.discount_method == 'per':
                            final_discount = line.discount_amt
                        else:
                            final_discount, = 0

        if self._context.get('forced_ref'):
            ref = self._context['forced_ref']
        else:
            ref = self.picking_id.name

        if debit_value > 0:
            debit_value = debit_value - final_discount
        if credit_value > 0:
            credit_value = credit_value - final_discount

        debit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': ref,
            'partner_id': partner_id,
            'debit': debit_value if debit_value > 0 else 0,
            'credit': -debit_value if debit_value < 0 else 0,
            'account_id': debit_account_id,
        }

        credit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': ref,
            'partner_id': partner_id,
            'credit': credit_value if credit_value > 0 else 0,
            'debit': -credit_value if credit_value < 0 else 0,
            'account_id': credit_account_id,
        }

        rslt = {'credit_line_vals': credit_line_vals, 'debit_line_vals': debit_line_vals}
        if credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = self.product_id.property_account_creditor_price_difference

            if not price_diff_account:
                price_diff_account = self.product_id.categ_id.property_account_creditor_price_difference_categ
            if not price_diff_account:
                raise UserError(
                    _('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))

            rslt['price_diff_line_vals'] = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': ref,
                'partner_id': partner_id,
                'credit': diff_amount > 0 and diff_amount or 0,
                'debit': diff_amount < 0 and -diff_amount or 0,
                'account_id': price_diff_account.id,
            }
        return rslt
