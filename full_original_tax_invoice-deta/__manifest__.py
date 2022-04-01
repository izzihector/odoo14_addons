# -*- coding: utf-8 -*-
{
    'name': 'full_original_tax_invoice',
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
        'report/invoices_report/body.xml',
        'report/invoices_report/header_footer.xml',
        'report/invoices_report/Copyheader_footer.xml',
        'report/action_report.xml',
    ],
    'application': False
    # 'report/header_footer.xml',

}
