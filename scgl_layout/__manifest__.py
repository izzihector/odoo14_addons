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
        'report/header_layout.xml',
        'data/report_layout_scgl.xml',
    ],
    'application': False
    # 'report/header_footer.xml',

}
