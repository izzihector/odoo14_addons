# -*- coding: utf-8 -*-
{
    'name': 'full_invoice_open',
    'version': '14.0.0.0.0',
    'category': 'Report Designer',
    'author': 'SCG LEGACY(THAILAND) CO.,LTD(HEAD OFFICE)',
    'website': 'https://scgl.co.th',
    'description': u"""
Export report using Report Designer
""",
    'css': 'static/src/css/reset.min.css',
    'depends': [
        'account',
    ],
    'data': [
        'report/paperformat.xml',
        'report/body.xml',
        'report/action_report.xml',
    ],
    'application': False
    # 'report/header_footer.xml',

}
