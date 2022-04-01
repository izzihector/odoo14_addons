# -*- coding: utf-8 -*-
{
    'name': 'full_invoice_prepaid',
    'version': '14.0.0.0',
    'category': 'Report Designer',
    'author': 'SCG LEGACY(THAILAND) CO.,LTD(HEAD OFFICE)',
    'website': 'https://scgl.co.th',
    'description': u"""
Export report using Report Designer
""",
    'css': 'style/css/name_of_css_file.css',
    'depends': [
        'stock',
        'account',
    ],
    'data': [
        'report/paperformat.xml',
        'report/action_report.xml',
        'report/payment_report/payment_copy_header_footer.xml',
        'report/payment_report/payment_body.xml',
        'report/payment_report/payment_header_footer.xml',
    ],
    'application': False
    # 'report/header_footer.xml',

}
