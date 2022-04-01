# -*- coding: utf-8 -*-
{
    'name': 'Full Quotations',
    'version': '12.1.1.0',
    'category': 'Report Designer',
    'author': 'SCG LEGACY(THAILAND) CO.,LTD(HEAD OFFICE)',
    'website': 'https://scgl.co.th',
    'description': u"""
Export report using Report Designer
""",
    'depends': [
        'account', 'sale'
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
