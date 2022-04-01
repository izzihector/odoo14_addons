# -*- coding: utf-8 -*-

{
    "name" : "Post Dated Cheque Management(PDC) Odoo",
    "author": "Edge Technologies",
    "version" : "1.0.0",
    "live_test_url":'https://youtu.be/y5G6ehXbIgI',
    "images":["static/description/main_screenshot.png"],
    'summary': 'Apply PDC Payment, Generate PDC Payment Entries and Journal Entries With PDC Account, Filter Payment by Status and Customers.',
    "description": """ This app help to user Apply PDC Payment, Generate PDC Payment Entries, Generate Journal Entries with Default Configured PDC Account, Also Re-Generate Journal Entries with Configured PDC Account when the Done Collect Cash from PDC Payment from Customer Invoice and Vendor Bill. Filter Payment by Status and Customers.""", 
    "license" : "OPL-1",
    "depends" : ['base','sale','purchase','sale_management','account'],
    "data": [
        'data/pdc_payment_data.xml',
        'security/pdc_payment_group.xml',
        'security/ir.model.access.csv',
        'views/res_config_view.xml',
        'report/pdc_payment_template.xml',
        'report/pdc_payment_action.xml',
        'views/invoice_inherit_view.xml',
        # 'views/pdc_payment_view.xml',
        'wizard/payment_cash_bounced_wiz_views.xml',
        'wizard/payment_cash_cancelled_wiz_views.xml',
        'wizard/payment_cash_deposit_wiz_views.xml',
        'wizard/payment_cash_returned_wiz_views.xml',
        'wizard/payment_collect_cash_wiz_views.xml',
        'wizard/payment_done_wiz_views.xml',
        'views/account_pdc_payment_register_view.xml',
        'views/account_pdc_payment_view.xml',
    ],
    "auto_install": False,
    "installable": True,
    "price": 20,
    "currency": 'EUR',
    "category" : "Accounting",
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
