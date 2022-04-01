from odoo import fields, models, api, _


class AccountPDCPayment(models.Model):
    _name = "account.pdc.payment"
    _inherits = {'account.move': 'move_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "PDC Payments"
    _order = "date desc, name desc"
    _check_company_auto = True

    agent = fields.Char(string='Agent')
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry', required=True, readonly=True, ondelete='cascade',
        check_company=True)
    amount = fields.Monetary(currency_field='currency_id', string='Payment Amount')
    currency_id = fields.Many2one('res.currency', string='Currency', store=True, readonly=False,
                                  compute='_compute_currency_id',
                                  help="The payment's currency.")
    payment_type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], default='customer', tracking=True, required=True)
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method',
                                        readonly=False, store=True,
                                        compute='_compute_payment_method_id',
                                        domain="[('id', 'in', available_payment_method_ids)]",
                                        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
                                             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
                                             "Check: Pay bill by check and print it from Odoo.\n" \
                                             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
                                             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")
    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        compute='_compute_destination_account_id',
        domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
        check_company=True)
    is_internal_transfer = fields.Boolean(string="Is Internal Transfer",
                                          readonly=False, store=True,
                                          compute="_compute_is_internal_transfer")
    is_reconciled = fields.Boolean(string="Is Reconciled", store=True,
                                   compute='_compute_reconciliation_status',
                                   help="Technical field indicating if the payment is already reconciled.")
    is_matched = fields.Boolean(string="Is Matched With a Bank Statement", store=True,
                                compute='_compute_reconciliation_status',
                                help="Technical field indicating if the payment has been matched with a statement line.")
    due_date = fields.Date(string='Due Date', required=True, copy=False)
    cheque_reference = fields.Char(string='Cheque Ref')
    bank = fields.Char(string='Bank')
    communication = fields.Char()
    name = fields.Char(readonly=True, copy=False)
    pdc_account_id = fields.Many2one('account.account', string="PDC Receivable Account")
    pdc_account_creditors_id = fields.Many2one('account.account', string="PDC Payable Account")
    state = fields.Selection([('draft', 'Draft'),
                              ('collect_cash', 'Collect Cash'),
                              ('deposited', 'Deposited'),
                              ('bounced', 'Bounced'),
                              ('posted', 'Posted'),
                              ('returned', 'Returned'),
                              ('cancelled', 'Cancelled'),
                              ], readonly=True, default='draft', copy=False, string="Status")

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

    def button_journal_entries(self):
        return {
            'name': _('Journal Entries'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': ['|', ('name', '=', self.communication), ('ref', '=', self.communication)],
            'context': {
                'journal_id': self.journal_id.id,
            }
        }

    def button_journal_items(self):
        move_lines = self.mapped('move_line_ids')
        action = self.env['ir.actions.actions']._for_xml_id('account.action_account_moves_all')
        if len(move_lines) > 1:
            action['domain'] = [('id', 'in', move_lines.ids)]
        elif len(move_lines) == 1:
            form_view = [(self.env.ref('account.view_move_line_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = move_lines.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'journal_id': self.journal_id.id,
        }
        action['context'] = context
        return action

    move_line_ids = fields.One2many('account.move.line', 'pdc_payment_id', readonly=True, copy=False,
                                    ondelete='restrict')

    def action_set_to_pdc_draft(self):
        for rec in self:
            # rec.move_id.button_cancel()
            # rec.move_id.unlink()
            rec.move_id.button_draft()
            rec.write({
                'state': 'draft',
            })

    def action_invoice_cancel(self):
        for rec in self:
            for move in rec.move_line_ids.mapped('move_id'):
                # if rec.invoice_ids:
                #     move.line_ids.remove_move_reconcile()
                # if move.state != 'draft':
                #     move.button_cancel()
                move.button_cancel()
            rec.write({
                'state': 'cancelled',
            })

    def cash_returned_button(self):
        for rec in self:
            return rec.write({'state': 'returned'})

    def cash_bounced_button(self):
        for record in self:
            line_ids = []
            journal = record.journal_id
            # if not journal.secure_sequence_id:
            #     journal._create_secure_sequence(['secure_sequence_id'])
            # name = journal.with_context(ir_sequence_date=self.date).secure_sequence_id.next_by_id()
            move_dict = {
                # 'name': name,
                'date': fields.Date.today(),
                'ref': self.communication or '',
                'company_id': self.company_id.id,
                'journal_id': journal.id,
                'partner_id': record.partner_id.id,
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
                if record.move_id.ids:
                    move_line_name += ': '
                    for inv in record:
                        if inv.move_id:
                            move_line_name += inv.name + ', '
                    move_line_name = move_line_name[:len(move_line_name) - 2]

            if debit_account_id:
                debit_line = (0, 0, {
                    'partner_id': record.payment_type in ('inbound', 'outbound') and self.env[
                        'res.partner']._find_accounting_partner(self.partner_id).id or False,
                    'move_id': record.move_id,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'pdc_payment_id': self.id,
                    'journal_id': record.journal_id.id,
                    'account_id': debit_account_id,
                    'date': record.date,
                    'name': move_line_name
                })
                line_ids.append(debit_line)

            if credit_account_id:
                credit_line = (0, 0, {
                    'partner_id': record.payment_type in ('inbound', 'outbound') and self.env[
                        'res.partner']._find_accounting_partner(self.partner_id).id or False,
                    'move_id': record.move_id,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'pdc_payment_id': self.id,
                    'journal_id': record.journal_id.id,
                    'account_id': credit_account_id,
                    'date': record.date,
                    'name': move_line_name
                })
                line_ids.append(credit_line)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            move._post()
            return record.write({'state': 'bounced'})

    def cash_deposit_button(self):
        for record in self:
            line_ids = []
            journal = record.journal_id
            move_dict = {
                'date': fields.Date.today(),
                'ref': self.communication or '',
                'company_id': self.company_id.id,
                'journal_id': journal.id,
                'partner_id': record.partner_id.id,
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
                    'move_id': record.move_id,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'pdc_payment_id': self.id,
                    'journal_id': record.journal_id.id,
                    'account_id': debit_account_id,
                    'date': record.date,
                })
                line_ids.append(debit_line)

            if credit_account_id:
                credit_line = (0, 0, {
                    'partner_id': record.payment_type in ('inbound', 'outbound') and self.env[
                        'res.partner']._find_accounting_partner(self.partner_id).id or False,
                    'move_id': record.move_id,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'pdc_payment_id': self.id,
                    'journal_id': record.journal_id.id,
                    'account_id': credit_account_id,
                    'date': record.date,
                })
                line_ids.append(credit_line)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            move._post()
            return record.write({'state': 'deposited'})

    def _get_move_vals(self, journal=None):
        journal = journal or self.journal_id

        return {
            'date': fields.Date.today(),
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }

    def _get_counterpart_move_line_vals(self, invoice=False):
        if self.payment_type == 'transfer':
            name = self.name
        else:
            name = 'PDC Payment'
            if invoice:
                name += ': '
                for inv in invoice:
                    if inv:
                        name += inv.name + ', '
                name = name[:len(name) - 2]
        return {
            'name': name,
            'account_id': self.destination_account_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
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
            'pdc_payment_id': self.id,
            'journal_id': self.journal_id.id,
        }

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
            date=self.date)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)

        cash_move_id = self.env['account.move'].create(self._get_move_vals())
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, cash_move_id.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.move_id))
        pdc_pay_name = str('PDC Payment') + " : " + str(self.communication)
        counterpart_aml_dict.update({
            'currency_id': currency_id,
            'account_id': self.payment_type in ('outbound',
                                                'transfer') and self.journal_id.payment_debit_account_id.id or self.journal_id.payment_credit_account_id.id
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
                                                                               'transfer') and self.journal_id.payment_debit_account_id.id or self.journal_id.payment_credit_account_id.id})
                liquidity_aml_dict.update({'name': pdc_pay_name})
            aml_obj.create(liquidity_aml_dict)
        posted_entry = cash_move_id._post()
        if posted_entry:
            self.state = "posted"
        return posted_entry

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

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or {}

        if not self.journal_id.payment_debit_account_id or not self.journal_id.payment_credit_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set on the %s journal.",
                self.journal_id.display_name))

        # Compute amounts.
        write_off_amount_currency = write_off_line_vals.get('amount', 0.0)

        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
            write_off_amount_currency *= -1
        else:
            liquidity_amount_currency = write_off_amount_currency = 0.0

        write_off_balance = self.currency_id._convert(
            write_off_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        liquidity_balance = self.currency_id._convert(
            liquidity_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
        counterpart_balance = -liquidity_balance - write_off_balance
        currency_id = self.currency_id.id

        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                liquidity_line_name = _('Transfer to %s', self.journal_id.name)
            else:  # payment.payment_type == 'outbound':
                liquidity_line_name = _('Transfer from %s', self.journal_id.name)
        else:
            liquidity_line_name = self.payment_reference

        # Compute a default label to set on the journal items.

        payment_display_name = {
            'outbound-customer': _("Customer Reimbursement"),
            'inbound-customer': _("Customer Payment"),
            'outbound-supplier': _("Vendor Payment"),
            'inbound-supplier': _("Vendor Reimbursement"),
        }

        default_line_name = self.env['account.move.line']._get_default_line_name(
            _("Internal Transfer") if self.is_internal_transfer else payment_display_name[
                '%s-%s' % (self.payment_type, self.partner_type)],
            self.amount,
            self.currency_id,
            self.date,
            partner=self.partner_id,
        )

        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name or default_line_name,
                'date_maturity': self.date,
                'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.journal_id.payment_credit_account_id.id if liquidity_balance < 0.0 else self.journal_id.payment_debit_account_id.id,
            },
            # Receivable / Payable.
            {
                'name': self.payment_reference or default_line_name,
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
            },
        ]
        if not self.currency_id.is_zero(write_off_amount_currency):
            # Write-off line.
            line_vals_list.append({
                'name': write_off_line_vals.get('name') or default_line_name,
                'amount_currency': write_off_amount_currency,
                'currency_id': currency_id,
                'debit': write_off_balance if write_off_balance > 0.0 else 0.0,
                'credit': -write_off_balance if write_off_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': write_off_line_vals.get('account_id'),
            })
        return line_vals_list

    def _seek_for_lines(self):
        ''' Helper used to dispatch the journal items between:
        - The lines using the temporary liquidity account.
        - The lines using the counterpart account.
        - The lines being the write-off lines.
        :return: (liquidity_lines, counterpart_lines, writeoff_lines)
        '''
        self.ensure_one()

        liquidity_lines = self.env['account.move.line']
        counterpart_lines = self.env['account.move.line']
        writeoff_lines = self.env['account.move.line']

        for line in self.move_id.line_ids:
            if line.account_id in (
                    self.journal_id.default_account_id,
                    self.journal_id.payment_debit_account_id,
                    self.journal_id.payment_credit_account_id,
            ):
                liquidity_lines += line
            elif line.account_id.internal_type in (
                    'receivable', 'payable') or line.partner_id == line.company_id.partner_id:
                counterpart_lines += line
            else:
                writeoff_lines += line

        return liquidity_lines, counterpart_lines, writeoff_lines

    def _synchronize_to_moves(self, changed_fields):
        ''' Update the account.move regarding the modified account.payment.
        :param changed_fields: A list containing all modified fields on account.payment.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in (
                'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
                'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id', 'journal_id',
        )):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            # Make sure to preserve the write-off amount.
            # This allows to create a new payment with custom 'line_ids'.

            if liquidity_lines and counterpart_lines and writeoff_lines:

                counterpart_amount = sum(counterpart_lines.mapped('amount_currency'))
                writeoff_amount = sum(writeoff_lines.mapped('amount_currency'))

                # To be consistent with the payment_difference made in account.payment.register,
                # 'writeoff_amount' needs to be signed regarding the 'amount' field before the write.
                # Since the write is already done at this point, we need to base the computation on accounting values.
                if (counterpart_amount > 0.0) == (writeoff_amount > 0.0):
                    sign = -1
                else:
                    sign = 1
                writeoff_amount = abs(writeoff_amount) * sign

                write_off_line_vals = {
                    'name': writeoff_lines[0].name,
                    'amount': writeoff_amount,
                    'account_id': writeoff_lines[0].account_id.id,
                }
            else:
                write_off_line_vals = {}

            line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

            line_ids_commands = []
            if liquidity_lines:
                line_ids_commands.append((1, liquidity_lines.id, line_vals_list[0]))
            else:
                line_ids_commands.append((0, 0, line_vals_list[0]))
            if counterpart_lines:
                line_ids_commands.append((1, counterpart_lines.id, line_vals_list[1]))
            else:
                line_ids_commands.append((0, 0, line_vals_list[1]))

            for line in writeoff_lines:
                line_ids_commands.append((2, line.id))

            for extra_line_vals in line_vals_list[2:]:
                line_ids_commands.append((0, 0, extra_line_vals))

            # Update the existing journal items.
            # If dealing with multiple write-off lines, they are dropped and a new one is generated.

            pay.move_id.write({
                'partner_id': pay.partner_id.id,
                'currency_id': pay.currency_id.id,
                'partner_bank_id': pay.partner_bank_id.id,
                'line_ids': line_ids_commands,
            })

    def write(self, vals):
        # OVERRIDE
        res = super().write(vals)
        self._synchronize_to_moves(set(vals.keys()))
        return res

    def get_seq_name(self, payment_type, payment_date, partner_type):
        name = ''
        if payment_type == 'transfer':
            sequence_code = 'account.payment.transfer'
        else:
            if partner_type == 'customer':
                if payment_type == 'inbound':
                    sequence_code = 'account.payment.customer.invoice'
                if payment_type == 'outbound':
                    sequence_code = 'account.payment.customer.refund'
            if partner_type == 'supplier':
                if payment_type == 'inbound':
                    sequence_code = 'account.payment.supplier.refund'
                if payment_type == 'outbound':
                    sequence_code = 'account.payment.supplier.invoice'
        name = self.env['ir.sequence'].with_context(ir_sequence_date=payment_date).next_by_code(
            sequence_code)
        if not name and payment_type != 'transfer':
            raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

        return name

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        write_off_line_vals_list = []

        for vals in vals_list:

            # Hack to add a custom write-off line.
            write_off_line_vals_list.append(vals.pop('write_off_line_vals', None))

            # Force the move_type to avoid inconsistency with residual 'default_move_type' inside the context.
            vals['move_type'] = 'entry'
            vals['communication'] = vals['ref']

            # Force the computation of 'journal_id' since this field is set on account.move but must have the
            # bank/cash type.
            if 'journal_id' not in vals:
                vals['journal_id'] = self._get_default_journal().id

            # Since 'currency_id' is a computed editable field, it will be computed later.
            # Prevent the account.move to call the _get_default_currency method that could raise
            # the 'Please define an accounting miscellaneous journal in your company' error.
            if 'currency_id' not in vals:
                journal = self.env['account.journal'].browse(vals['journal_id'])
                vals['currency_id'] = journal.currency_id.id or journal.company_id.currency_id.id

            name = self.get_seq_name(vals['payment_type'], vals['date'], vals['partner_type'])
            if name:
                vals['name'] = name

        payments = super().create(vals_list)

        for i, pay in enumerate(payments):
            write_off_line_vals = write_off_line_vals_list[i]

            # Write payment_id on the journal entry plus the fields being stored in both models but having the same
            # name, e.g. partner_bank_id. The ORM is currently not able to perform such synchronization and make things
            # more difficult by creating related fields on the fly to handle the _inherits.
            # Then, when partner_bank_id is in vals, the key is consumed by account.payment but is never written on
            # account.move.
            to_write = {'pdc_payment_id': pay.id, }
            for k, v in vals_list[i].items():
                if k in self._fields and self._fields[k].store and k in pay.move_id._fields and pay.move_id._fields[
                    k].store:
                    if k == 'name' or k == 'state':
                        continue
                    to_write[k] = v

            if 'line_ids' not in vals_list[i]:
                to_write['line_ids'] = [(0, 0, line_vals) for line_vals in
                                        pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)]

            pay.move_id.write(to_write)

        return payments

    @api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency',
                 'move_id.line_ids.account_id')
    def _compute_reconciliation_status(self):
        ''' Compute the field indicating if the payments are already reconciled with something.
        This field is used for display purpose (e.g. display the 'reconcile' button redirecting to the reconciliation
        widget).
        '''
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            if not pay.currency_id or not pay.id:
                pay.is_reconciled = False
                pay.is_matched = False
            elif pay.currency_id.is_zero(pay.amount):
                pay.is_reconciled = True
                pay.is_matched = True
            else:
                residual_field = 'amount_residual' if pay.currency_id == pay.company_id.currency_id else 'amount_residual_currency'
                if pay.journal_id.default_account_id and pay.journal_id.default_account_id in liquidity_lines.account_id:
                    # Allow user managing payments without any statement lines by using the bank account directly.
                    # In that case, the user manages transactions only using the register payment wizard.
                    pay.is_matched = True
                else:
                    pay.is_matched = pay.currency_id.is_zero(sum(liquidity_lines.mapped(residual_field)))

                reconcile_lines = (counterpart_lines + writeoff_lines).filtered(lambda line: line.account_id.reconcile)
                pay.is_reconciled = pay.currency_id.is_zero(sum(reconcile_lines.mapped(residual_field)))

    def action_post(self):
        ''' draft -> posted '''
        self.move_id._post(soft=False)

    @api.depends('partner_id', 'destination_account_id', 'journal_id')
    def _compute_is_internal_transfer(self):
        for payment in self:
            is_partner_ok = payment.partner_id == payment.journal_id.company_id.partner_id
            is_account_ok = payment.destination_account_id and payment.destination_account_id == payment.journal_id.company_id.transfer_account_id
            payment.is_internal_transfer = is_partner_ok and is_account_ok

    @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        for pay in self:
            if pay.is_internal_transfer:
                pay.destination_account_id = pay.journal_id.company_id.transfer_account_id
            elif pay.partner_type == 'customer':
                # Receive money from invoice or send money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(
                        pay.company_id).property_account_receivable_id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        ('company_id', '=', pay.company_id.id),
                        ('internal_type', '=', 'receivable'),
                        ('deprecated', '=', False),
                    ], limit=1)
            elif pay.partner_type == 'supplier':
                # Send money to pay a bill or receive money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        ('company_id', '=', pay.company_id.id),
                        ('internal_type', '=', 'payable'),
                        ('deprecated', '=', False),
                    ], limit=1)

    @api.depends('payment_type', 'journal_id')
    def _compute_payment_method_id(self):
        ''' Compute the 'payment_method_id' field.
        This field is not computed in '_compute_payment_method_fields' because it's a stored editable one.
        '''
        for pay in self:
            if pay.payment_type == 'inbound':
                available_payment_methods = pay.journal_id.inbound_payment_method_ids
            else:
                available_payment_methods = pay.journal_id.outbound_payment_method_ids

            # Select the first available one by default.
            if pay.payment_method_id in available_payment_methods:
                pay.payment_method_id = pay.payment_method_id
            elif available_payment_methods:
                pay.payment_method_id = available_payment_methods[0]._origin
            else:
                pay.payment_method_id = False

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for pay in self:
            pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id
