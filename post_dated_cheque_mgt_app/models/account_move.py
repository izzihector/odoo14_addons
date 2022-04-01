from odoo import fields, models, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    pdc_payment_id = fields.Many2one(
        index=True,
        comodel_name='account.pdc.payment',
        string="PDC Payment", copy=False, check_company=True)

    def action_register_pdc_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        return {
            'name': _('Register PDC Payment'),
            'res_model': 'account.pdc.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _get_reconciled_pdc_payments(self):
        """Helper used to retrieve the reconciled payments on this journal entry"""
        reconciled_lines = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        reconciled_amls = reconciled_lines.mapped('matched_debit_ids.debit_move_id') + \
                          reconciled_lines.mapped('matched_credit_ids.credit_move_id')
        return reconciled_amls.move_id.pdc_payment_id

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
        res = super(AccountMove, self)._compute_amount()
        for move in self:
            currencies = move._get_lines_onchange_currency().currency_id
            currency = len(currencies) == 1 and currencies or move.company_id.currency_id
            if move.is_invoice(include_receipts=True) and move.state == 'posted':

                if currency.is_zero(move.amount_residual):
                    reconciled_payments = move._get_reconciled_payments()
                    reconciled_pdc_payments = move._get_reconciled_pdc_payments()
                    if (not reconciled_payments or all(payment.is_matched for payment in reconciled_payments)) and (
                            not reconciled_pdc_payments or all(
                            pdc_payment.is_matched for pdc_payment in reconciled_pdc_payments)):
                        new_pmt_state = 'paid'
                    else:
                        new_pmt_state = move._get_invoice_in_payment_state()
                # elif currency.compare_amounts(total_to_pay, total_residual) != 0:
                #     new_pmt_state = 'partial'

                    move.payment_state = new_pmt_state
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    pdc_payment_id = fields.Many2one('account.pdc.payment', index=True, store=True,
                                     string="PDC Payment",
                                     help="The PDC payment that created this entry")

    def _compute_amount_fields(self, amount, src_currency, company_currency):
        """ Helper function to compute value for fields debit/credit/amount_currency based on an amount and the currencies given in parameter"""
        amount_currency = False
        currency_id = False
        date = self.env.context.get('date') or fields.Date.today()
        company = self.env.context.get('company_id')
        company = self.env['res.company'].browse(company) if company else self.env.user.company_id
        if src_currency and src_currency != company_currency:
            amount_currency = amount
            amount = src_currency._convert(amount, company_currency, company, date)
            currency_id = src_currency.id
        debit = amount > 0 and amount or 0.0
        credit = amount < 0 and -amount or 0.0
        return debit, credit, amount_currency, currency_id
