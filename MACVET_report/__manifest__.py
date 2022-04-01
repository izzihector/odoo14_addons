# -*- coding: utf-8 -*-
{
    'name': 'MACVET_report',
    'version': '14.0.1.0.9',
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
        'report/invoices_report/body.xml',
        'report/invoices_report/header_footer.xml',
        'report/invoices_report/Copyheader_footer.xml',
        'report/action_report.xml',
        'report/original_report/original_body.xml',
        'report/original_report/original_header_footer.xml',
        'report/original_report/original_copy_header_footer.xml',
        'report/credit_notes_report/cn_body.xml',
        'report/credit_notes_report/cn_copy_header_footer.xml',
        'report/credit_notes_report/cn_header_footer.xml',
        'report/delivery_report/dalivery_body.xml',
        'report/delivery_report/delivery_header_footer.xml',
        'report/delivery_report/delivery_copy_header_footer.xml',
        'report/payment_report/payment_copy_header_footer.xml',
        'report/payment_report/payment_body.xml',
        'report/payment_report/payment_header_footer.xml',

    ],
    'application': False
    # 'report/header_footer.xml',

}
