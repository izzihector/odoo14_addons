# -*- coding: utf-8 -*-
{
    'name': 'full_invoice',
    'version': '14.0.0.0',
    'category': 'Report Designer',
    'author': 'SCG LEGACY(THAILAND) CO.,LTD(HEAD OFFICE)',
    'website': 'https://scgl.co.th',
    'description': u"""
Export report using Report Designer
""",
    'css': 'style/css/name_of_css_file.css',
    'depends': [
        'invoice_promptpay',
        'stock',
        'account',
    ],
    'data': [
        'report/paperformat.xml',
        'report/draft_invoices_report/body.xml',
        'report/draft_invoices_report/header_footer.xml',
        'report/draft_invoices_report/Copyheader_footer.xml',
        'report/open_invoices_report/body.xml',
        'report/open_invoices_report/header_footer.xml',
        'report/open_invoices_report/Copyheader_footer.xml',
        'report/action_report.xml',

    ],
    'application': False
    # 'report/header_footer.xml',

}
