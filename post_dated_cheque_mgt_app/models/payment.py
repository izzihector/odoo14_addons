# -*- coding: utf-8 -*-

import math

from odoo import models, fields, api, _
from odoo.tools import float_round, float_is_zero
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}
# Since invoice amounts are unsigned, this is how we know if money comes in or goes out
MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': 1,
    'in_invoice': -1,
    'out_refund': -1,
}


# class AccountInvoice(models.Model):
#     _inherit = "account.move"
# 
#     def action_invoice_pdc_register_payment(self):
#         return self.env['pdc.account.payment'] \
#             .with_context(active_ids=self.ids, active_model='account.move', active_id=self.id) \
#             .action_register_payment()
# 
#     def register_payment(self, payment_line, writeoff_acc_id=False, writeoff_journal_id=False):
#         """ Reconcile payable/receivable lines from the invoice with payment_line """
#         line_to_reconcile = self.env['account.move.line']
#         for inv in self:
#             line_to_reconcile += inv._get_aml_for_register_payment()
#         return (line_to_reconcile + payment_line).reconcile()
# 
#     def _get_aml_for_register_payment(self):
#         """ Get the aml to consider to reconcile in register payment """
#         self.ensure_one()
#         return self.line_ids.filtered(
#             lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    payment_pdc_id = fields.Many2one('pdc.account.payment', string="Originator PDC Payment",
                                     help="Payment that created this entry", copy=False)

    @api.model
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


class account_abstract_pdc_payment(models.AbstractModel):
    _name = "account.abstract.pdc.payment"
    _description = "Contains the logic shared between models which allows to register payments"

    invoice_ids = fields.Many2many('account.move', string='Invoices', copy=False)
    multi = fields.Boolean(string='Multi',
                           help='Technical field indicating if the user selected invoices from multiple partners or from different types.')

    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True)
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method Type',
                                        oldname="payment_method",
                                        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
                                             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
                                             "Check: Pay bill by check and print it from Odoo.\n" \
                                             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
                                             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")
    payment_method_code = fields.Char(related='payment_method_id.code',
                                      help="Technical field used to adapt the interface to the payment type selected.",
                                      readonly=True)

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')])
    partner_id = fields.Many2one('res.partner', string='Partner')

    amount = fields.Monetary(string='Payment Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    communication = fields.Char(string='Memo', required=True)
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True,
                                 domain=[('type', '=', 'bank')])

    hide_payment_method = fields.Boolean(compute='_compute_hide_payment_method',
                                         help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")
    payment_difference = fields.Monetary(compute='_compute_payment_difference', readonly=True)
    payment_difference_handling = fields.Selection([('open', 'Keep open'), ('reconcile', 'Mark invoice as fully paid')],
                                                   default='open', string="Payment Difference Handling", copy=False)
    writeoff_account_id = fields.Many2one('account.account', string="Difference Account",
                                          domain=[('deprecated', '=', False)], copy=False)
    writeoff_label = fields.Char(
        string='Journal Item Label',
        help='Change label of the counterpart that will hold the payment difference',
        default='Write-Off')
    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account")
    show_partner_bank_account = fields.Boolean(compute='_compute_show_partner_bank',
                                               help='Technical field used to know whether the field `partner_bank_account_id` needs to be displayed or not in the payments form views')

    bank = fields.Char(string='Bank')
    agent = fields.Char(string='Agent')
    cheque_reference = fields.Char(string='Cheque Ref')
    due_date = fields.Date(string='Due Date', required=True, copy=False)

    @api.model
    def default_get(self, fields):
        rec = super(account_abstract_pdc_payment, self).default_get(fields)
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec

        invoices = self.env['account.move'].browse(active_ids)

        # Check all invoices are open
        if any(invoice.state != 'posted' for invoice in invoices):
            raise UserError(_("You can only register payments for open invoices"))
        # Check all invoices have the same currency
        if any(inv.currency_id != invoices[0].currency_id for inv in invoices):
            raise UserError(_("In order to pay multiple invoices at once, they must use the same currency."))
        # Check if, in batch payments, there are not negative invoices and positive invoices
        dtype = invoices[0].move_type
        for inv in invoices[1:]:
            if inv.move_type != dtype:
                if ((dtype == 'in_refund' and inv.type == 'in_invoice') or
                        (dtype == 'in_invoice' and inv.type == 'in_refund')):
                    raise UserError(
                        _("You cannot register payments for vendor bills and supplier refunds at the same time."))
                if ((dtype == 'out_refund' and inv.type == 'out_invoice') or
                        (dtype == 'out_invoice' and inv.type == 'out_refund')):
                    raise UserError(
                        _("You cannot register payments for customer invoices and credit notes at the same time."))

        # Look if we are mixin multiple commercial_partner or customer invoices with vendor bills
        multi = any(inv.commercial_partner_id != invoices[0].commercial_partner_id
                    or MAP_INVOICE_TYPE_PARTNER_TYPE[inv.move_type] != MAP_INVOICE_TYPE_PARTNER_TYPE[
                        invoices[0].move_type]
                    # or inv.account_id != invoices[0].account_id
                    or inv.partner_bank_id != invoices[0].partner_bank_id
                    for inv in invoices)

        currency = invoices[0].currency_id

        total_amount = self._compute_payment_amount(invoices=invoices, currency=currency)
        communication = ' '.join([ref for ref in invoices.mapped('payment_reference') if ref])

        inv_ref = self.communication
        if len(invoices) == 1:
            inv_ref = invoices.name

        rec.update({
            'amount': abs(total_amount),
            'currency_id': currency.id,
            'payment_type': total_amount > 0 and 'inbound' or 'outbound',
            'partner_id': False if multi else invoices[0].commercial_partner_id.id,
            'partner_type': False if multi else MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type],
            'communication': inv_ref,
            'invoice_ids': [(6, 0, invoices.ids)],
            'multi': multi,
        })
        return rec

    @api.constrains('amount')
    def _check_amount(self):
        if not self.amount > 0.0:
            raise ValidationError(_('The payment amount must be strictly positive.'))

    @api.depends('payment_type', 'journal_id')
    def _compute_hide_payment_method(self):
        if not self.journal_id:
            self.hide_payment_method = True
            return
        journal_payment_methods = self.payment_type == 'inbound' and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
        self.hide_payment_method = len(journal_payment_methods) == 1 and journal_payment_methods[0].code == 'manual'

    @api.depends('payment_type', 'journal_id')
    def _compute_hide_payment_method(self):
        for payment in self:
            if not payment.journal_id or payment.journal_id.type not in ['bank', 'cash']:
                payment.hide_payment_method = True
                continue
            journal_payment_methods = payment.payment_type == 'inbound' \
                                      and payment.journal_id.inbound_payment_method_ids \
                                      or payment.journal_id.outbound_payment_method_ids
            payment.hide_payment_method = len(journal_payment_methods) == 1 and journal_payment_methods[
                0].code == 'manual'

    @api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id')
    def _compute_payment_difference(self):
        for pay in self.filtered(lambda p: p.invoice_ids):
            payment_amount = -pay.amount if pay.payment_type == 'outbound' else pay.amount
            pay.payment_difference = pay._compute_payment_amount() - payment_amount

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id:
            # Set default payment method (we consider the first to be the default one)
            payment_methods = self.payment_type == 'inbound' and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
            payment_methods_list = payment_methods.ids

            default_payment_method_id = self.env.context.get('default_payment_method_id')
            if default_payment_method_id:
                # Ensure the domain will accept the provided default value
                payment_methods_list.append(default_payment_method_id)
            else:
                self.payment_method_id = payment_methods and payment_methods[0] or False
            # Set payment method domain (restrict to methods enabled for the journal and to selected payment type)
            payment_type = self.payment_type in ('outbound', 'transfer') and 'outbound' or 'inbound'
            active_ids = self._context.get('active_ids')
            invoices = self.env['account.move'].browse(active_ids)
            self.amount = abs(self._compute_payment_amount(invoices, self.currency_id))
            return {'domain': {
                'payment_method_id': [('payment_type', '=', payment_type), ('id', 'in', payment_methods_list)]}}
        return {}

    def _get_invoices(self):
        """ Return the invoices of the payment. Must be overridden """
        raise NotImplementedError

    def _compute_journal_domain_and_types(self):
        journal_type = ['bank', 'cash']
        domain = []
        if self.currency_id.is_zero(self.amount) and hasattr(self, "has_invoices") and self.has_invoices:
            # In case of payment with 0 amount, allow to select a journal of type 'general' like
            # 'Miscellaneous Operations' and set this journal by default.
            journal_type = ['general']
            self.payment_difference_handling = 'reconcile'
        else:
            if self.payment_type == 'inbound':
                domain.append(('at_least_one_inbound', '=', True))
            else:
                domain.append(('at_least_one_outbound', '=', True))
        return {'domain': domain, 'journal_types': set(journal_type)}

    @api.onchange('amount', 'currency_id')
    def _onchange_amount(self):
        jrnl_filters = self._compute_journal_domain_and_types()
        journal_types = jrnl_filters['journal_types']
        domain_on_types = [('type', 'in', list(journal_types))]
        if self.journal_id.type not in journal_types:
            self.journal_id = self.env['account.journal'].search(domain_on_types, limit=1)
        return {'domain': {'journal_id': jrnl_filters['domain'] + domain_on_types}}

    @api.onchange('currency_id')
    def _onchange_currency(self):
        self.amount = abs(self._compute_payment_amount())

        # Set by default the first liquidity journal having this currency if exists.
        if self.journal_id:
            return
        journal = self.env['account.journal'].search(
            [('type', 'in', ('bank', 'cash')), ('currency_id', '=', self.currency_id.id)], limit=1)
        if journal:
            return {'value': {'journal_id': journal.id}}

    def _compute_payment_amount(self, invoices=None, currency=None):
        '''Compute the total amount for the payment wizard.

        :param invoices: If not specified, pick all the invoices.
        :param currency: If not specified, search a default currency on wizard/journal.
        :return: The total amount to pay the invoices.
        '''

        # Get the payment invoices
        if not invoices:
            invoices = self.invoice_ids

        # Get the payment currency
        if not currency:
            currency = self.currency_id or self.journal_id.currency_id or self.journal_id.company_id.currency_id or invoices and \
                       invoices[0].currency_id

        # Avoid currency rounding issues by summing the amounts according to the company_currency_id before
        invoice_datas = invoices.read_group(
            [('id', 'in', invoices.ids)],
            ['currency_id', 'move_type', 'amount_residual_signed'],
            ['currency_id', 'move_type'], lazy=False)
        total = 0.0
        for invoice_data in invoice_datas:
            amount_total = MAP_INVOICE_TYPE_PAYMENT_SIGN[invoice_data['move_type']] * invoice_data[
                'amount_residual_signed']
            payment_currency = self.env['res.currency'].browse(invoice_data['currency_id'][0])
            if payment_currency == currency:
                total += amount_total
            else:
                total += payment_currency._convert(amount_total, currency, self.env.user.company_id,
                                                   self.payment_date or fields.Date.today())
        return total


# pdc payment
class account_pdc_payment(models.Model):
    _name = "pdc.account.payment"
    _inherit = ['mail.thread', 'account.abstract.pdc.payment']
    _description = "Payments"
    _order = "payment_date desc, name desc"

    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)
    name = fields.Char(readonly=True, copy=False)  # The name is attributed upon post()
    
    payment_type = fields.Selection(selection_add=[('transfer', 'Internal Transfer')], ondelete={'transfer': 'cascade'})
    payment_reference = fields.Char(copy=False, readonly=True,
                                    help="Reference of the document used to issue this payment. Eg. check number, file name, etc.")
    move_name = fields.Char(string='Journal Entry Name', readonly=True,
                            default=False, copy=False,
                            help="Technical field holding the number given to the journal entry, automatically set when the statement line is reconciled then stored to set the same number again if the line is cancelled, set to draft and re-processed again.")

    # Money flows from the journal_id's default_debit_account_id or default_credit_account_id to the destination_account_id
    destination_account_id = fields.Many2one('account.account', compute='_compute_destination_account_id',
                                             readonly=True)
    # For money transfer, money goes from journal_id to a transfer account, then from the transfer account to destination_journal_id
    destination_journal_id = fields.Many2one('account.journal', string='Transfer To',
                                             domain=[('type', 'in', ('bank', 'cash'))])
    invoice_ids = fields.Many2many('account.move',
                                   help="""Technical field containing the invoices for which the payment has been generated.This does not especially correspond to the invoices reconciled with the payment,as it can have been generated first, and reconciled later""")
    reconciled_invoice_ids = fields.Many2many('account.move', string='Reconciled Invoices',
                                              compute='_compute_reconciled_invoice_ids',
                                              help="Invoices whose journal items have been reconciled with this payment's.")
    has_invoices = fields.Boolean(compute="_compute_reconciled_invoice_ids",
                                  help="Technical field used for usability purposes")

    # FIXME: ondelete='restrict' not working (eg. cancel a bank statement reconciliation with a payment)
    move_line_ids = fields.One2many('account.move.line', 'payment_pdc_id', readonly=True, copy=False,
                                    ondelete='restrict')
    move_reconciled = fields.Boolean(compute="_get_move_reconciled", readonly=True)
    account_move_id = fields.Many2one('account.move', string="Move Reference")
    pdc_account_id = fields.Many2one('account.account', string="PDC Receivable Account")
    pdc_account_creditors_id = fields.Many2one('account.account', string="PDC Payable Account")
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Number of Attachments')

    def _init_pdc_payments(self, to_process, edit_mode=False):
        """ Create the payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_get_batches').
        :param edit_mode:   Is the wizard in edition mode.
        """

        payments = self.env['pdc.account.payment'].create([x['create_vals'] for x in to_process])

        for payment, vals in zip(payments, to_process):
            vals['payment'] = payment

            # If payments are made using a currency different than the source one, ensure the balance match exactly in
            # order to fully paid the source journal items.
            # For example, suppose a new currency B having a rate 100:1 regarding the company currency A.
            # If you try to pay 12.15A using 0.12B, the computed balance will be 12.00A for the payment instead of 12.15A.
            if edit_mode:
                lines = vals['to_reconcile']

                # Batches are made using the same currency so making 'lines.currency_id' is ok.
                if payment.currency_id != lines.currency_id:
                    liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
                    source_balance = abs(sum(lines.mapped('amount_residual')))
                    payment_rate = liquidity_lines[0].amount_currency / liquidity_lines[0].balance
                    source_balance_converted = abs(source_balance) * payment_rate

                    # Translate the balance into the payment currency is order to be able to compare them.
                    # In case in both have the same value (12.15 * 0.01 ~= 0.12 in our example), it means the user
                    # attempt to fully paid the source lines and then, we need to manually fix them to get a perfect
                    # match.
                    payment_balance = abs(sum(counterpart_lines.mapped('balance')))
                    payment_amount_currency = abs(sum(counterpart_lines.mapped('amount_currency')))
                    if not payment.currency_id.is_zero(source_balance_converted - payment_amount_currency):
                        continue

                    delta_balance = source_balance - payment_balance

                    # Balance are already the same.
                    if self.company_currency_id.is_zero(delta_balance):
                        continue

                    # Fix the balance but make sure to peek the liquidity and counterpart lines first.
                    debit_lines = (liquidity_lines + counterpart_lines).filtered('debit')
                    credit_lines = (liquidity_lines + counterpart_lines).filtered('credit')

                    payment.move_id.write({'line_ids': [
                        (1, debit_lines[0].id, {'debit': debit_lines[0].debit + delta_balance}),
                        (1, credit_lines[0].id, {'credit': credit_lines[0].credit + delta_balance}),
                    ]})
        return payments

    @api.model
    def _get_line_batch_key(self, line):
        ''' Turn the line passed as parameter to a dictionary defining on which way the lines
        will be grouped together.
        :return: A python dictionary.
        '''
        return {
            'partner_id': line.partner_id.id,
            'account_id': line.account_id.id,
            'currency_id': (line.currency_id or line.company_currency_id).id,
            'partner_bank_id': (line.move_id.partner_bank_id or line.partner_id.commercial_partner_id.bank_ids[:1]).id,
            'partner_type': 'customer' if line.account_internal_type == 'receivable' else 'supplier',
            'payment_type': 'inbound' if line.balance > 0.0 else 'outbound',
        }

    def _get_batches(self):
        ''' Group the account.move.line linked to the wizard together.
        :return: A list of batches, each one containing:
            * key_values:   The key as a dictionary used to group the journal items together.
            * moves:        An account.move recordset.
        '''
        self.ensure_one()

        lines = self.move_line_ids._origin

        if len(lines.company_id) > 1:
            raise UserError(_("You can't create payments for entries belonging to different companies."))
        if not lines:
            raise UserError(
                _("You can't open the register payment wizard without at least one receivable/payable line."))

        batches = {}
        for line in lines:
            batch_key = self._get_line_batch_key(line)

            serialized_key = '-'.join(str(v) for v in batch_key.values())
            batches.setdefault(serialized_key, {
                'key_values': batch_key,
                'lines': self.env['account.move.line'],
            })
            batches[serialized_key]['lines'] += line
        return list(batches.values())

    @api.model
    def _get_wizard_values_from_batch(self, batch_result):
        ''' Extract values from the batch passed as parameter (see '_get_batches')
        to be mounted in the wizard view.
        :param batch_result:    A batch returned by '_get_batches'.
        :return:                A dictionary containing valid fields
        '''
        key_values = batch_result['key_values']
        lines = batch_result['lines']
        company = lines[0].company_id

        source_amount = abs(sum(lines.mapped('amount_residual')))
        if key_values['currency_id'] == company.currency_id.id:
            source_amount_currency = source_amount
        else:
            source_amount_currency = abs(sum(lines.mapped('amount_residual_currency')))

        return {
            'company_id': company.id,
            'partner_id': key_values['partner_id'],
            'partner_type': key_values['partner_type'],
            'payment_type': key_values['payment_type'],
            'source_currency_id': key_values['currency_id'],
            'source_amount': source_amount,
            'source_amount_currency': source_amount_currency,
        }

    def _create_pdc_payment_vals_from_batch(self, batch_result):
        batch_values = self._get_wizard_values_from_batch(batch_result)
        return {
            'date': self.payment_date,
            'amount': batch_values['source_amount_currency'],
            'payment_type': batch_values['payment_type'],
            'partner_type': batch_values['partner_type'],
            'ref': self._get_batch_communication(batch_result),
            'journal_id': self.journal_id.id,
            'currency_id': batch_values['source_currency_id'],
            'partner_id': batch_values['partner_id'],
            'partner_bank_id': batch_result['key_values']['partner_bank_id'],
            'payment_method_id': self.payment_method_id.id,
            'destination_account_id': batch_result['lines'][0].account_id.id
        }
    
    def _post_pdc_payments(self, to_process, edit_mode=False):
        """ Post the newly created payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_get_batches').
        :param edit_mode:   Is the wizard in edition mode.
        """
        payments = self.env['account.payment']
        for vals in to_process:
            payments |= vals['payment']
        payments.action_post()

    def _create_pdc_payments(self):
        self.ensure_one()
        batches = self._get_batches()
        # edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)
        to_process = []

        # if edit_mode:
        #     payment_vals = self._create_payment_vals_from_wizard()
        #     to_process.append({
        #         'create_vals': payment_vals,
        #         'to_reconcile': batches[0]['lines'],
        #         'batch': batches[0],
        #     })
        # else:
        # Don't group payments: Create one batch per move.
        # if not self.group_payment:
        new_batches = []
        for batch_result in batches:
            for line in batch_result['lines']:
                new_batches.append({
                    **batch_result,
                    'lines': line,
                })
        batches = new_batches

        for batch_result in batches:
            to_process.append({
                'create_vals': self._create_pdc_payment_vals_from_batch(batch_result),
                'to_reconcile': batch_result['lines'],
                'batch': batch_result,
            })

        payments = self._init_pdc_payments(to_process, edit_mode=edit_mode)
        self._post_pdc_payments(to_process, edit_mode=edit_mode)
        self._reconcile_payments(to_process, edit_mode=edit_mode)
        return payments


def _compute_attachment_number(self):
    Attachment = self.env['ir.attachment']
    for payment in self:
        payment.attachment_number = Attachment.search_count([
            ('res_model', '=', 'pdc.account.payment'), ('res_id', '=', payment.id),
        ])


def button_journal_items(self):
    return {
        'name': _('Journal Items'),
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'account.move.line',
        'view_id': False,
        'type': 'ir.actions.act_window',
        'domain': ['|', '|', ('move_id.ref', '=', self.communication),
                   ('move_id.name', '=', self.communication),
                   ('payment_pdc_id', 'in', self.ids)],
        'context': {
            'journal_id': self.journal_id.id,
        }
    }


def button_journal_entries(self):
    return {
        'name': _('Journal Entries'),
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'account.move',
        'view_id': False,
        'type': 'ir.actions.act_window',
        'domain': ['|', ('name', '=', self.communication), ('ref', '=', self.communication)],
        'context': {
            'journal_id': self.journal_id.id,
        }
    }


def action_register_payment(self):
    active_ids = self.env.context.get('active_ids')
    if not active_ids:
        return ''

    return {
        'name': _('PDC Payment'),
        'res_model': 'pdc.account.payment',
        'view_mode': 'form',
        'view_id': self.env.ref('post_dated_cheque_mgt_app.view_pdc_account_payment_invoice_form').id,
        'context': self.env.context,
        'target': 'new',
        'type': 'ir.actions.act_window',
    }


@api.onchange('due_date')
def check_pdc_account(self):
    if self.due_date:
        pdc_account_id = self.company_id.pdc_account_id
        if not pdc_account_id:
            raise UserError(
                _("Please configure Pdc Payment Account(100501) first, from Invoicing or Accounting setting."))
        pdc_account_creditors_id = self.company_id.pdc_account_creditors_id
        if not pdc_account_creditors_id:
            raise UserError(
                _("Please configure Pdc Payment Account(100502) first, from Invoicing or Accounting setting."))
        if self.due_date < fields.Date.today():
            raise UserError(_("Please select valid due date...!"))


def post(self):
    """ Create the journal items for the payment and update the payment's state to 'posted'.
        A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
        and another in the destination reconcilable account (see _compute_destination_account_id).
        If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
        If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
    """
    for rec in self:

        pdc_account_id = self.company_id.pdc_account_id and self.company_id.pdc_account_id.id
        if not pdc_account_id:
            raise UserError(
                _("Please configure pdc payment account for debtors first, from Invoicing or Accounting setting."))

        pdc_account_creditors_id = self.company_id.pdc_account_creditors_id and self.company_id.pdc_account_creditors_id.id
        if not pdc_account_creditors_id:
            raise UserError(
                _("Please configure pdc payment account for creditors first, from Invoicing or Accounting setting."))

        if rec.state != 'draft':
            raise UserError(_("Only a draft payment can be posted."))

        if any(inv.state != 'posted' for inv in rec.invoice_ids):
            raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

        # keep the name in case of a payment reset to draft
        if not rec.name:
            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
                sequence_code)
            if not rec.name and rec.payment_type != 'transfer':
                raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

        # Create the journal entry
        amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
        # move = rec._create_payment_entry(amount)
        move = rec._create_pdc_payments()
        persist_move_name = move.name

        # In case of a transfer, the first journal entry created debited the source liquidity account and credited
        # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
        if rec.payment_type == 'transfer':
            transfer_credit_aml = move.line_ids.filtered(
                lambda r: r.account_id == rec.company_id.transfer_account_id)
            transfer_debit_aml = rec._create_transfer_entry(amount)
            (transfer_credit_aml + transfer_debit_aml).reconcile()
            persist_move_name += self._get_move_name_transfer_separator() + transfer_debit_aml.move_id.name
        if self.payment_type == 'outbound':
            self.write({
                'state': 'collect_cash',
                'account_move_id': move.id,
                'communication': self.communication,
                'pdc_account_creditors_id': pdc_account_creditors_id,
                'move_name': persist_move_name
            })
        else:
            self.write({
                'state': 'collect_cash',
                'account_move_id': move.id,
                'communication': self.communication,
                'pdc_account_id': pdc_account_id,
                'move_name': persist_move_name
            })
    return True


# validate PDC Payment
# def validate_pdc_payment(self):
#     """ Posts a payment used to pay an invoice. This function only posts the
#     payment by default but can be overridden to apply specific post or pre-processing.
#     It is called by the "validate" button of the popup window
#     triggered on invoice form by the "Register Payment" button.
#     """
# 
#     if any(len(record.invoice_ids) != 1 for record in self):
#         # For multiple invoices, there is account.register.payments wizard
#         raise UserError(_("This method should only be called to process a single invoice's payment."))
#     return self.post()

def action_create_pdc_payments(self):
    payments = self._create_pdc_payments()

    if self._context.get('dont_redirect_to_payments'):
        return True

    action = {
        'name': _('Payments'),
        'type': 'ir.actions.act_window',
        'res_model': 'account.payment',
        'context': {'create': False},
    }
    if len(payments) == 1:
        action.update({
            'view_mode': 'form',
            'res_id': payments.id,
        })
    else:
        action.update({
            'view_mode': 'tree,form',
            'domain': [('id', 'in', payments.ids)],
        })
    return action


# collect cash done then generate journal entries
def cash_pdc_done_button(self):
    amount = self.amount
    pdc_account_id = self.company_id.pdc_account_id and self.company_id.pdc_account_id.id
    if not pdc_account_id:
        raise UserError(
            _("Please configure pdc payment account for debtors first, from Invoicing or Accounting setting."))

    pdc_account_creditors_id = self.company_id.pdc_account_creditors_id and self.company_id.pdc_account_creditors_id.id
    if not pdc_account_creditors_id:
        raise UserError(
            _("Please configure pdc payment account for creditors first, from Invoicing or Accounting setting."))

    aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
    debit, credit, amount_currency, currency_id = aml_obj.with_context(
        date=self.payment_date)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)

    cash_move_id = self.env['account.move'].with_context(check_move_validity=False).create(self._get_move_vals())
    counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, cash_move_id.id, False)
    counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
    pdc_pay_name = str('PDC Payment') + " : " + str(self.communication)
    counterpart_aml_dict.update({
        'currency_id': currency_id,
        'account_id': self.payment_type in ('outbound',
                                            'transfer') and self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id
    })
    if self.payment_type == 'outbound':
        counterpart_aml_dict.update({'account_id': pdc_account_creditors_id})
    counterpart_aml = aml_obj.create(counterpart_aml_dict)

    # Write counterpart lines
    if not self.currency_id.is_zero(self.amount):
        if not self.currency_id != self.company_id.currency_id:
            amount_currency = 0
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, cash_move_id.id,
                                                             False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals_collect_cash(-amount))
        liquidity_aml_dict.update({'name': pdc_pay_name})
        if self.payment_type == 'outbound':
            liquidity_aml_dict.update({'account_id': self.payment_type in ('outbound',
                                                                           'transfer') and self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id})
            liquidity_aml_dict.update({'name': pdc_pay_name})
        aml_obj.create(liquidity_aml_dict)
    posted_entry = cash_move_id.post()
    if posted_entry:
        self.state = "posted"
    return posted_entry


@api.model
def _get_move_name_transfer_separator(self):
    return '§§'


@api.depends('move_line_ids.reconciled')
def _get_move_reconciled(self):
    for payment in self:
        rec = True
        for aml in payment.move_line_ids.filtered(lambda x: x.account_id.reconcile):
            if not aml.reconciled:
                rec = False
        payment.move_reconciled = rec


def open_payment_matching_screen(self):
    # Open reconciliation view for customers/suppliers
    move_line_id = False
    for move_line in self.move_line_ids:
        if move_line.account_id.reconcile:
            move_line_id = move_line.id
            break;
    if not self.partner_id:
        raise UserError(_("Payments without a customer can't be matched"))
    action_context = {'company_ids': [self.company_id.id],
                      'partner_ids': [self.partner_id.commercial_partner_id.id]}
    if self.partner_type == 'customer':
        action_context.update({'mode': 'customers'})
    elif self.partner_type == 'supplier':
        action_context.update({'mode': 'suppliers'})
    if move_line_id:
        action_context.update({'move_line_id': move_line_id})
    return {
        'type': 'ir.actions.client',
        'tag': 'manual_reconciliation_view',
        'context': action_context,
    }


@api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
def _compute_destination_account_id(self):
    if self.invoice_ids:
        self.destination_account_id = self.invoice_ids.invoice_line_ids.account_id.id
    elif self.payment_type == 'transfer':
        if not self.company_id.transfer_account_id.id:
            raise UserError(
                _('There is no Transfer Account defined in the accounting settings. Please define one to be able to confirm this transfer.'))
        self.destination_account_id = self.company_id.transfer_account_id.id
    elif self.partner_id:
        if self.partner_type == 'customer':
            self.destination_account_id = self.partner_id.property_account_receivable_id.id
        else:
            self.destination_account_id = self.partner_id.property_account_payable_id.id
    elif self.partner_type == 'customer':
        default_account = self.env['ir.property'].get('property_account_receivable_id', 'res.partner')
        self.destination_account_id = default_account.id
    elif self.partner_type == 'supplier':
        default_account = self.env['ir.property'].get('property_account_payable_id', 'res.partner')
        self.destination_account_id = default_account.id


@api.depends('move_line_ids.matched_debit_ids', 'move_line_ids.matched_credit_ids')
def _compute_reconciled_invoice_ids(self):
    for record in self:
        record.reconciled_invoice_ids = (record.move_line_ids.mapped('matched_debit_ids.debit_move_id.invoice_id') |
                                         record.move_line_ids.mapped(
                                             'matched_credit_ids.credit_move_id.invoice_id'))
        record.has_invoices = bool(record.reconciled_invoice_ids)


@api.onchange('partner_type')
def _onchange_partner_type(self):
    self.ensure_one()
    # Set partner_id domain
    if self.partner_type:
        return {'domain': {'partner_id': [(self.partner_type, '=', True)]}}


@api.onchange('payment_type')
def _onchange_payment_type(self):
    if not self.invoice_ids:
        # Set default partner type for the payment type
        if self.payment_type == 'inbound':
            self.partner_type = 'customer'
        elif self.payment_type == 'outbound':
            self.partner_type = 'supplier'
        else:
            self.partner_type = False
    # Set payment method domain
    res = self._onchange_journal()
    if not res.get('domain', {}):
        res['domain'] = {}
    jrnl_filters = self._compute_journal_domain_and_types()
    journal_types = jrnl_filters['journal_types']
    journal_types.update(['bank', 'cash'])
    res['domain']['journal_id'] = jrnl_filters['domain'] + [('type', 'in', list(journal_types))]
    return res


@api.model
def resolve_2many_commands(self, field_name, commands, fields=None):
    """ Serializes one2many and many2many commands into record dictionaries
        (as if all the records came from the database via a read()).  This
        method is aimed at onchange methods on one2many and many2many fields.

        Because commands might be creation commands, not all record dicts
        will contain an ``id`` field.  Commands matching an existing record
        will have an ``id``.

        :param field_name: name of the one2many or many2many field matching the commands
        :type field_name: str
        :param commands: one2many or many2many commands to execute on ``field_name``
        :type commands: list((int|False, int|False, dict|False))
        :param fields: list of fields to read from the database, when applicable
        :type fields: list(str)
        :returns: records in a shape similar to that returned by ``read()``
            (except records may be missing the ``id`` field if they don't exist in db)
        :rtype: list(dict)
    """
    result = []  # result (list of dict)
    record_ids = []  # ids of records to read
    updates = defaultdict(dict)  # {id: vals} of updates on records

    for command in commands or []:
        if not isinstance(command, (list, tuple)):
            record_ids.append(command)
        elif command[0] == 0:
            result.append(command[2])
        elif command[0] == 1:
            record_ids.append(command[1])
            updates[command[1]].update(command[2])
        elif command[0] in (2, 3):
            record_ids = [id for id in record_ids if id != command[1]]
        elif command[0] == 4:
            record_ids.append(command[1])
        elif command[0] == 5:
            result, record_ids = [], []
        elif command[0] == 6:
            result, record_ids = [], list(command[2])

    # read the records and apply the updates
    field = self._fields[field_name]
    records = self.env[field.comodel_name].browse(record_ids)
    for data in records.read(fields):
        data.update(updates.get(data['id'], {}))
        result.append(data)

    return result


@api.model
def default_get(self, fields):
    rec = super(account_pdc_payment, self).default_get(fields)
    invoice_defaults = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'))
    if invoice_defaults and len(invoice_defaults) == 1:
        invoice = invoice_defaults[0]
        rec['communication'] = invoice['payment_reference'] or invoice['name']
        rec['currency_id'] = invoice['currency_id'][0]
        rec['payment_type'] = invoice['move_type'] in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
        rec['partner_type'] = MAP_INVOICE_TYPE_PARTNER_TYPE[invoice['move_type']]
        rec['partner_id'] = invoice['partner_id'][0]
        rec['amount'] = invoice['amount_residual']
    return rec


def create_payment(self):
    payment = self.env['account.payment'].create(self.get_payment_vals())
    payment.post()
    return {'type': 'ir.actions.act_window_close'}


def button_invoices(self):
    action = {
        'name': _('Paid Invoices'),
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'account.move',
        'view_id': False,
        'type': 'ir.actions.act_window',
        'domain': [('id', 'in', [x.id for x in self.reconciled_invoice_ids])],
    }
    if self.partner_type == 'supplier':
        action['views'] = [(self.env.ref('account.view_in_invoice_tree').id, 'tree'),
                           (self.env.ref('account.view_move_form').id, 'form')]
        action['context'] = {
            'journal_type': 'purchase',
            'type': 'in_invoice',
            'default_type': 'in_invoice',
        }
    else:
        action['views'] = [(self.env.ref('account.view_out_invoice_tree').id, 'tree'),
                           (self.env.ref('account.view_move_form').id, 'form')]
    return action


def button_dummy(self):
    return True


def action_invoice_cancel(self):
    for rec in self:
        for move in rec.move_line_ids.mapped('move_id'):
            if rec.invoice_ids:
                move.line_ids.remove_move_reconcile()
            if move.state != 'draft':
                move.button_cancel()
            move.unlink()
        rec.write({
            'state': 'cancelled',
            'move_name': '',
        })


def action_set_to_pdc_post(self):
    for rec in self:
        rec.account_move_id.button_cancel()
        rec.account_move_id.unlink()
        rec.write({
            'state': 'posted',
        })


def unlink(self):
    if any(bool(rec.move_line_ids) for rec in self):
        raise UserError(_("You cannot delete a payment that is already posted."))
    if any(rec.move_name for rec in self):
        raise UserError(
            _('It is not allowed to delete a payment that already created a journal entry since it would create a gap in the numbering. You should create the journal entry again and cancel it thanks to a regular revert.'))
    return super(account_pdc_payment, self).unlink()


def _create_payment_entry(self, amount):
    """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
        Return the journal entry.
    """
    pdc_account_id = self.company_id.pdc_account_id and self.company_id.pdc_account_id.id
    if not pdc_account_id:
        raise UserError(
            _("Please configure pdc payment account for debtors first, from Invoicing or Accounting setting."))

    pdc_account_creditors_id = self.company_id.pdc_account_creditors_id and self.company_id.pdc_account_creditors_id.id
    if not pdc_account_creditors_id:
        raise UserError(
            _("Please configure pdc payment account for creditors first, from Invoicing or Accounting setting."))

    aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
    invoice_currency = False
    if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
        # if all the invoices selected share the same currency, record the paiement in that currency too
        invoice_currency = self.invoice_ids[0].currency_id
    debit, credit, amount_currency, currency_id = aml_obj.with_context(
        date=self.payment_date)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)

    move = self.env['account.move'].with_context(default_move_type='entry').create(self._get_move_vals())
    pdc_pay_name = str(self.env['account.account'].browse(pdc_account_id).name) + " : " + str(self.name)
    # Write line corresponding to invoice payment
    counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
    counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
    counterpart_aml_dict.update({'currency_id': currency_id})
    counterpart_aml = aml_obj.create(counterpart_aml_dict)

    # Reconcile with the invoices
    if self.payment_difference_handling == 'reconcile' and self.payment_difference:
        writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
        amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(
            self.payment_difference, self.currency_id, self.company_id.currency_id)[2:]
        # the writeoff debit and credit must be computed from the invoice residual in company currency
        # minus the payment amount in company currency, and not from the payment difference in the payment currency
        # to avoid loss of precision during the currency rate computations. See revision 20935462a0cabeb45480ce70114ff2f4e91eaf79 for a detailed example.
        total_residual_company_signed = sum(invoice.residual_company_signed for invoice in self.invoice_ids)
        total_payment_company_signed = self.currency_id.with_context(date=self.payment_date).compute(self.amount,
                                                                                                     self.company_id.currency_id)
        if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
            amount_wo = total_payment_company_signed - total_residual_company_signed
        else:
            amount_wo = total_residual_company_signed - total_payment_company_signed
        # Align the sign of the secondary currency writeoff amount with the sign of the writeoff
        # amount in the company currency
        if amount_wo > 0:
            debit_wo = amount_wo
            credit_wo = 0.0
            amount_currency_wo = abs(amount_currency_wo)
        else:
            debit_wo = 0.0
            credit_wo = -amount_wo
            amount_currency_wo = -abs(amount_currency_wo)
        writeoff_line['name'] = _('Counterpart')
        writeoff_line['account_id'] = self.writeoff_account_id.id
        writeoff_line['debit'] = debit_wo
        writeoff_line['credit'] = credit_wo
        writeoff_line['amount_currency'] = amount_currency_wo
        writeoff_line['currency_id'] = currency_id
        writeoff_line = aml_obj.create(writeoff_line)
        if counterpart_aml['debit']:
            counterpart_aml['debit'] += credit_wo - debit_wo
        if counterpart_aml['credit']:
            counterpart_aml['credit'] += debit_wo - credit_wo
        counterpart_aml['amount_currency'] -= amount_currency_wo
    self.invoice_ids.register_payment(counterpart_aml)

    # Write counterpart lines
    if not self.currency_id != self.company_id.currency_id:
        amount_currency = 0
    liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
    liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
    if self.payment_type == 'outbound':
        pdc_pay_name = str(self.env['account.account'].browse(pdc_account_creditors_id).name) + " : " + str(
            self.name)
        liquidity_aml_dict.update({'account_id': pdc_account_creditors_id, 'name': pdc_pay_name})
    else:
        liquidity_aml_dict.update({'account_id': pdc_account_id, 'name': pdc_pay_name})
    aml_obj.create(liquidity_aml_dict)
    move.post()
    return move


def _create_transfer_entry(self, amount):
    """ Create the journal entry corresponding to the 'incoming money' part of an internal transfer, return the reconcilable move line
    """
    aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
    debit, credit, amount_currency, dummy = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(
        amount, self.currency_id, self.company_id.currency_id)
    amount_currency = self.destination_journal_id.currency_id and self.currency_id._convert(amount,
                                                                                            self.destination_journal_id.currency_id,
                                                                                            self.company_id,
                                                                                            self.payment_date or fields.Date.today()) or 0

    dst_move = self.env['account.move'].create(self._get_move_vals(self.destination_journal_id))

    dst_liquidity_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, dst_move.id)
    dst_liquidity_aml_dict.update({
        'name': _('Transfer from %s') % self.journal_id.name,
        'account_id': self.destination_journal_id.default_credit_account_id.id,
        'currency_id': self.destination_journal_id.currency_id.id,
        'journal_id': self.destination_journal_id.id})
    aml_obj.create(dst_liquidity_aml_dict)

    transfer_debit_aml_dict = self._get_shared_move_line_vals(credit, debit, 0, dst_move.id)
    transfer_debit_aml_dict.update({
        'name': self.name,
        'account_id': self.company_id.transfer_account_id.id,
        'journal_id': self.destination_journal_id.id})
    if self.currency_id != self.company_id.currency_id:
        transfer_debit_aml_dict.update({
            'currency_id': self.currency_id.id,
            'amount_currency': -self.amount,
        })
    transfer_debit_aml = aml_obj.create(transfer_debit_aml_dict)
    if not self.destination_journal_id.post_at_bank_rec:
        dst_move.post()
    return transfer_debit_aml


def _get_move_vals(self, journal=None):
    journal = journal or self.journal_id
    if not journal.check_sequence_id:
        raise UserError(_('Configuration Error !'),
                        _('The journal %s does not have a sequence, please specify one.') % journal.name)
    if not journal.check_sequence_id.active:
        raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
    name = self.move_name or journal.with_context(ir_sequence_date=self.payment_date).check_sequence_id.next_by_id()
    seq = journal.with_context(ir_sequence_date=self.payment_date).check_sequence_id.next_by_id()

    return {
        'name': seq or name,
        'date': fields.Date.today(),
        'ref': self.communication or '',
        'company_id': self.company_id.id,
        'journal_id': journal.id,
    }


def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id, invoice_id=False):
    """ Returns values common to both move lines (except for debit, credit and amount_currency which are reversed)
    """
    return {
        'partner_id': self.payment_type in ('inbound', 'outbound') and self.env[
            'res.partner']._find_accounting_partner(self.partner_id).id or False,
        # 'invoice_id': invoice_id and invoice_id.id or False,
        'move_id': move_id,
        'debit': debit,
        'credit': credit,
        'amount_currency': amount_currency or False,
        'payment_pdc_id': self.id,
        'journal_id': self.journal_id.id,
    }


def _get_counterpart_move_line_vals(self, invoice=False):
    if self.payment_type == 'transfer':
        name = self.name
    else:
        name = 'PDC Payment'
        if invoice:
            name += ': '
            for inv in invoice:
                if inv.id:
                    name += inv.name + ', '
            name = name[:len(name) - 2]
    return {
        'name': name,
        'account_id': self.destination_account_id.id,
        'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
    }


def _get_liquidity_move_line_vals_collect_cash(self, amount):
    name = self.name
    if self.payment_type == 'transfer':
        name = _('Transfer to %s') % self.destination_journal_id.name

    # pdc_account_id = int(self.env['ir.config_parameter'].sudo().get_param('post_dated_cheque_mgt_app.pdc_account_id'))
    pdc_account_id = self.company_id.pdc_account_id and self.company_id.pdc_account_id.id
    if not pdc_account_id:
        raise UserError(
            _("Please configure pdc payment account for debtors first, from Invoicing or Accounting setting."))
    vals = {
        'name': name,
        'account_id': pdc_account_id,
        'journal_id': self.journal_id.id,
        'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
    }

    # If the journal has a currency specified, the journal item need to be expressed in this currency
    if self.journal_id.currency_id and self.currency_id != self.journal_id.currency_id:
        amount = self.currency_id._convert(amount, self.journal_id.currency_id, self.company_id,
                                           self.payment_date or fields.Date.today())
        debit, credit, amount_currency, dummy = self.env['account.move.line'].with_context(
            date=self.payment_date)._compute_amount_fields(amount, self.journal_id.currency_id,
                                                           self.company_id.currency_id)
        vals.update({
            'amount_currency': amount_currency,
            'currency_id': self.journal_id.currency_id.id,
        })

    return vals


def _get_liquidity_move_line_vals(self, amount):
    name = self.name
    if self.payment_type == 'transfer':
        name = _('Transfer to %s') % self.destination_journal_id.name
    vals = {
        'name': name,
        'account_id': self.payment_type in ('outbound',
                                            'transfer') and self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id,
        'journal_id': self.journal_id.id,
        'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
    }

    # If the journal has a currency specified, the journal item need to be expressed in this currency
    if self.journal_id.currency_id and self.currency_id != self.journal_id.currency_id:
        amount = self.currency_id._convert(amount, self.journal_id.currency_id, self.company_id,
                                           self.payment_date or fields.Date.today())
        debit, credit, amount_currency, dummy = self.env['account.move.line'].with_context(
            date=self.payment_date)._compute_amount_fields(amount, self.journal_id.currency_id,
                                                           self.company_id.currency_id)
        vals.update({
            'amount_currency': amount_currency,
            'currency_id': self.journal_id.currency_id.id,
        })

    return vals


def _get_invoice_payment_amount(self, inv):
    """
    Computes the amount covered by the current payment in the given invoice.

    :param inv: an invoice object
    :returns: the amount covered by the payment in the invoice
    """
    self.ensure_one()
    return sum([
        data['amount']
        for data in inv._get_payments_vals()
        if data['account_payment_id'] == self.id
    ])


def cash_deposit_button(self):
    for record in self:
        line_ids = []
        journal = record.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'),
                            _('The journal %s does not have a sequence, please specify one.') % journal.name)
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'),
                            _('The sequence of journal %s is deactivated.') % journal.name)
        name = self.move_name or journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
        seq = journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
        move_dict = {
            'name': seq or name,
            'date': fields.Date.today(),
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }
        amount = record.amount
        if record.payment_type == 'outbound':
            debit_account_id = record.destination_account_id.id
            credit_account_id = record.pdc_account_creditors_id.id
        else:
            debit_account_id = record.pdc_account_id.id
            credit_account_id = record.destination_account_id.id

        if debit_account_id:
            debit_line = (0, 0, {
                'partner_id': record.payment_type in ('inbound', 'outbound') and self.env[
                    'res.partner']._find_accounting_partner(self.partner_id).id or False,
                'move_id': record.account_move_id,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'payment_pdc_id': self.id,
                'journal_id': record.journal_id.id,
                'account_id': debit_account_id,
                'date': record.payment_date,
            })
            line_ids.append(debit_line)

        if credit_account_id:
            credit_line = (0, 0, {
                'partner_id': record.payment_type in ('inbound', 'outbound') and self.env[
                    'res.partner']._find_accounting_partner(self.partner_id).id or False,
                'move_id': record.account_move_id,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'payment_pdc_id': self.id,
                'journal_id': record.journal_id.id,
                'account_id': credit_account_id,
                'date': record.payment_date,
            })
            line_ids.append(credit_line)
        move_dict['line_ids'] = line_ids
        move = self.env['account.move'].create(move_dict)
        move.post()
        return record.write({'state': 'deposited'})


def cash_bounced_button(self):
    for record in self:
        line_ids = []
        journal = record.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'),
                            _('The journal %s does not have a sequence, please specify one.') % journal.name)
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'),
                            _('The sequence of journal %s is deactivated.') % journal.name)
        name = self.move_name or journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
        seq = journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
        move_dict = {
            'name': seq or name,
            'date': fields.Date.today(),
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }
        amount = record.amount
        if record.payment_type == 'outbound':
            credit_account_id = record.destination_account_id.id
            debit_account_id = record.pdc_account_creditors_id.id
        else:
            debit_account_id = record.destination_account_id.id
            credit_account_id = record.pdc_account_id.id

        if record.payment_type == 'transfer':
            move_line_name = record.name
        else:
            move_line_name = _("PDC Payment")
            if record.invoice_ids:
                move_line_name += ': '
                for inv in record.invoice_ids:
                    if inv.move_id:
                        move_line_name += inv.number + ', '
                move_line_name = move_line_name[:len(move_line_name) - 2]

        if debit_account_id:
            debit_line = (0, 0, {
                'partner_id': record.payment_type in ('inbound', 'outbound') and self.env[
                    'res.partner']._find_accounting_partner(self.partner_id).id or False,
                'move_id': record.account_move_id,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'payment_pdc_id': self.id,
                'journal_id': record.journal_id.id,
                'account_id': debit_account_id,
                'date': record.payment_date,
                'name': move_line_name
            })
            line_ids.append(debit_line)

        if credit_account_id:
            credit_line = (0, 0, {
                'partner_id': record.payment_type in ('inbound', 'outbound') and self.env[
                    'res.partner']._find_accounting_partner(self.partner_id).id or False,
                'move_id': record.account_move_id,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'payment_pdc_id': self.id,
                'journal_id': record.journal_id.id,
                'account_id': credit_account_id,
                'date': record.payment_date,
                'name': move_line_name
            })
            line_ids.append(credit_line)
        move_dict['line_ids'] = line_ids
        move = self.env['account.move'].create(move_dict)
        move.post()
        return record.write({'state': 'bounced'})


def cash_returned_button(self):
    for rec in self:
        return rec.write({'state': 'returned'})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
