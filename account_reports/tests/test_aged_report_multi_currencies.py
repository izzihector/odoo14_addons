# -*- coding: utf-8 -*-
from .common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAgedReportMultiCurrencies(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_category_a = cls.env['res.partner.category'].create({'name': 'partner_categ_a'})
        cls.partner_a = cls.env['res.partner'].create({'name': 'partner_a', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_a.id])]})

        company = cls.company_data['company']
        company_currency = cls.company_data['currency']
        receivable = cls.company_data['default_account_receivable']
        misc = cls.company_data['default_account_revenue']
        sale_journal = cls.company_data['default_journal_sale']
        bank_journal = cls.company_data['default_journal_bank']

        # Test will use the following dates:
        # As of                  2017-02-01
        # 1 - 30:   2017-01-31 - 2017-01-02
        # 31 - 60:  2017-01-01 - 2016-12-03
        # 61 - 90:  2016-12-02 - 2016-11-03
        # 91 - 120: 2016-11-02 - 2016-10-04
        # Older:    2016-10-03

        test_currency = cls.env['res.currency'].create({
            'name': "TST",
            'symbol': 'T',
        })
        cls.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': 1.0,
            'currency_id': company_currency.id,
            'company_id': company.id
        })
        cls.env['res.currency.rate'].create({
            'name': '2017-01-01',
            'rate': 1.1,
            'currency_id': company_currency.id,
            'company_id': company.id
        })
        cls.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': 0.9,
            'currency_id': test_currency.id,
            'company_id': company.id
        })
        cls.env['res.currency.rate'].create({
            'name': '2017-01-01',
            'rate': 0.8,
            'currency_id': test_currency.id,
            'company_id': company.id
        })

        # ==== Journal entries for partner_a in company currency ====
        move_1 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2016-11-11',
            'invoice_date': '2016-11-11',
            'journal_id': sale_journal.id,
            'partner_id': cls.partner_a.id,
            'currency_id': company_currency.id,
            'line_ids': [
                (0, 0, {'account_id': receivable.id, 'partner_id': cls.partner_a.id, 'debit': 200.0, 'credit': 0.0}),
                (0, 0, {'account_id': misc.id, 'partner_id': cls.partner_a.id, 'debit': 0.0, 'credit': 200.0}),
            ],
        })
        move_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-19',
            'journal_id': bank_journal.id,
            'partner_id': cls.partner_a.id,
            'currency_id': company_currency.id,
            'line_ids': [
                (0, 0, {'account_id': receivable.id, 'partner_id': cls.partner_a.id, 'debit': 0.0, 'credit': 198.0}),
                (0, 0, {'account_id': misc.id, 'partner_id': cls.partner_a.id, 'debit': 198.0, 'credit': 0.0}),
            ],
        })
        (move_1 + move_2).action_post()
        (move_1 + move_2).line_ids.filtered(lambda line: line.account_id == receivable).reconcile()

        # ==== Journal entries for partner_a in another currency ====
        move_3 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2016-12-12',
            'invoice_date': '2016-12-12',
            'journal_id': sale_journal.id,
            'partner_id': cls.partner_a.id,
            'currency_id': test_currency.id,
            'line_ids': [
                (0, 0, {
                    'currency_id': test_currency.id, 'account_id': receivable.id, 'partner_id': cls.partner_a.id,
                    'amount_currency': 100.0, 'debit': 111.11, 'credit': 0.0,
                }),
                (0, 0, {
                    'currency_id': test_currency.id, 'account_id': misc.id, 'partner_id': cls.partner_a.id,
                    'amount_currency': -100.0, 'debit': 0.0, 'credit': 111.11,
                }),
            ],
        })
        move_4 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-19',
            'journal_id': bank_journal.id,
            'partner_id': cls.partner_a.id,
            'currency_id': test_currency.id,
            'line_ids': [
                (0, 0, {
                    'currency_id': test_currency.id, 'account_id': receivable.id, 'partner_id': cls.partner_a.id,
                    'amount_currency': -99.0, 'debit': 0.0, 'credit': 123.75,
                }),
                (0, 0, {
                    'currency_id': test_currency.id, 'account_id': misc.id, 'partner_id': cls.partner_a.id,
                    'amount_currency': 99.0, 'debit': 123.75, 'credit': 0.0,
                }),
            ],
        })
        (move_3 + move_4).action_post()
        (move_3 + move_4).line_ids.filtered(lambda line: line.account_id == receivable).reconcile()

        cls.report = cls.env['account.aged.receivable']

    def test_aged_receivable_multi_currencies_rate(self):
        """Test in a multi-currencies environment with currencies rates difference."""

        line_id = 'partner_id-%s' % self.partner_a.id
        options = self._init_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        options['unfolded_lines'] = [line_id]

        report_lines = self.report._get_lines(options)
        self.assertLinesValues(
            report_lines,
            #   Name                    Due Date        Not Due On  1 - 30      31 - 60     61 - 90     91 - 120    Older       Total
            [   0,                      1,              5,          6,          7,          8,          9,          10,         11],
            [
                ('partner_a',           '',             0,          0,          1.38,       2.00,       0,          0,          3.38),
                ('INV/2016/11/0001',    '11/11/2016',   '',         '',         '',         2.00,       '',         '',         ''),
                ('INV/2016/12/0001',    '12/12/2016',   '',         '',         1.38,       '',         '',         '',         ''),
                ('Total',               '',             0,          0,          1.38,       2.00,       0,          0,          3.38),
            ],
        )
